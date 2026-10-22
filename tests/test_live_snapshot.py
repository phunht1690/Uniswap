"""Pinning must use live inputs without changing old runs or their data."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
import json
import pytest
from tests.test_observed_inputs import observed
from src.data.live_snapshot import capture,SnapshotMarket
from src.models.service import SimulationInputError


def fake_live(pool):
    now=datetime.now(timezone.utc).isoformat()
    row={'id':pool['id'],'rpc':{'status':'ok','price_quote':pool['p0'],'sqrt_price_x96':pool['sqrt_price_x96'],
        'liquidity_raw':pool['liquidity_raw'],'tick':123,'block_number':999,'block_hash':'0x'+'a'*64,
        'block_time':now,'fetched_at':now,'age_seconds':0,'last_error':None},
        'metadata':{'status':'ok','tvl_usd':55555.,'volume_24h_usd':77777.,'quote_usd':1.,'fetched_at':now,'age_seconds':0,'last_error':None}}
    return row,SimpleNamespace(snapshot=lambda:{'pools':[deepcopy(row)]})


def test_live_run_and_stress_are_pinned_even_when_research_history_changes(client,observed):
    service=client.app.state.service;row,live=fake_live(observed['pools'][0])
    old=client.post('/api/v1/workbench/run',json={'config':{'horizon_days':7,'n_paths':12,'risk_max_exit_prob':1}}).json()
    registry=(observed['root']/'data/processed/pool_registry.json').read_bytes()
    client.app.state.live_enabled=True;client.app.state.live_market=live
    snap=client.post('/api/v1/market/snapshot',json={'pool':row['id']});assert snap.status_code==200,snap.text
    identity=snap.json()['snapshot_id']
    row['rpc']['age_seconds']=5;row['rpc']['block_age_seconds']=5;row['metadata']['age_seconds']=5
    assert client.post('/api/v1/market/snapshot',json={'pool':row['id']}).json()['snapshot_id']==identity
    request={'market_snapshot_id':identity,'config':{'horizon_days':7,'n_paths':12,'risk_max_exit_prob':1}}
    result=client.post('/api/v1/workbench/run',json=request);assert result.status_code==200,result.text
    current=result.json();assert datetime.fromisoformat(current['meta']['data_asof'])==datetime.fromisoformat(row['rpc']['block_time'])
    assert current['meta']['assumptions']['pool']['volume_24h_usd']==77777
    assert current['meta']['assumptions']['live_market_snapshot_id']==identity
    assert current['liquidity_ticks']==[] and current['meta']['assumptions']['liquidity_ticks_status'].startswith('not_captured')
    assert client.post('/api/v1/workbench/run',json=request).json()==current
    assert (observed['root']/'data/processed/pool_registry.json').read_bytes()==registry
    stress={'run_id':current['meta']['run_id']};before=client.post('/api/v1/workbench/stress',json=stress);assert before.status_code==200,before.text
    changed=observed['history'].copy();changed['price']*=1.3
    observed['context'].frame('history_'+row['id'],changed,'local_unit_test','local://changed',kind='observed_snapshot')
    assert client.post('/api/v1/workbench/stress',json=stress).json()==before.json()
    assert client.get('/api/v1/workbench/runs/'+old['meta']['run_id']).json()['result']==old
    wrong=deepcopy(request);wrong['config']['pool']='weth-usdc-3000'
    assert client.post('/api/v1/workbench/run',json=wrong).status_code==400


def test_capture_rejects_stale_inputs_zero_liquidity_and_tampered_snapshot(client,observed):
    row,live=fake_live(observed['pools'][0]);service=client.app.state.service
    row['metadata']['status']='stale'
    with pytest.raises(SimulationInputError):capture(service,live,row['id'])
    row['metadata']['status']='ok';row['rpc']['block_time']=(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat()
    with pytest.raises(SimulationInputError):capture(service,live,row['id'])
    row['rpc']['block_time']=datetime.now(timezone.utc).isoformat();original=row['rpc']['liquidity_raw'];row['rpc']['liquidity_raw']='0'
    with pytest.raises(SimulationInputError):capture(service,live,row['id'])
    row['rpc']['liquidity_raw']=original;snap=capture(service,live,row['id']);identity=snap['snapshot_id']
    path=observed['root']/'outputs/market_snapshots'/identity/'snapshot.json';original_manifest=path.read_bytes();obj=json.loads(path.read_text());obj['pool']['p0']*=2;path.write_text(json.dumps(obj))
    with pytest.raises(SimulationInputError):SnapshotMarket(observed['root'],identity)
    path.write_bytes(original_manifest);ledger=path.parent/'data/source_log.csv';ledger.write_text(ledger.read_text().replace('local_unit_test','changed_source'))
    with pytest.raises(SimulationInputError,match='nguồn'):SnapshotMarket(observed['root'],identity)


def test_disabled_live_capture_is_explicit_and_hash_paths_are_validated(client):
    assert client.post('/api/v1/market/snapshot',json={'pool':'weth-usdc-500'}).status_code==503
    assert client.post('/api/v1/workbench/run',json={'market_snapshot_id':'../secrets'}).status_code==422

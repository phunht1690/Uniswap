"""New financial rules: accounting identities, timing, pinned data and exports."""
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.app_schemas import WorkbenchRequest,StressRequest,SensitivityRequest,BacktestComparison
from api.main import create_app
from src.models.policies import simulate_policy
from src.evaluation.comparison import ComparisonService
from src.evaluation.backtest import replay
from src.data.backtest import load_inputs
from src.models.workbench import WorkbenchService
from tests.test_backtest import history_state
from tests.test_observed_inputs import observed


@pytest.mark.parametrize('policy',['none','weekly','threshold','hedged'])
def test_policy_cashflow_identity_and_no_price_moves(policy):
    prices=np.ones((3,22));volumes=np.full_like(prices,1e6)
    r=simulate_policy(prices,volumes,policy=policy,capital=10000,gas_usd=5,fee_rate=.003,
        half_width=.2,background_liquidity=1e7,min_gap=7,max_rebalances=20,slippage_bps=10,trace_index=0)
    hedge=0 if r.hedge_pnl is None else r.hedge_pnl
    assert np.allclose(r.excess,r.fees-r.il-r.gas-r.rebalance_cost+hedge)
    assert np.allclose(r.net*10000,r.excess)
    if policy=='weekly':assert np.all(r.rebalances==2) # days 7,14; no terminal recenter
    if policy=='threshold':assert np.all(r.rebalances==0)
    if policy=='hedged':
        assert np.all(r.gas==15) # LP + opening hedge + terminal hedge close
        assert np.all(r.hedge_pnl==0)


def test_daily_delta_hedge_and_inventory_threshold_are_distinct():
    prices=np.array([[1.,1.1,1.2,1.05]]);volumes=np.zeros_like(prices)
    common=dict(capital=10000,gas_usd=0,fee_rate=.003,half_width=.3,background_liquidity=1e6,min_gap=1,max_rebalances=20,slippage_bps=0)
    static=simulate_policy(prices,volumes,policy='none',**common)
    hedge=simulate_policy(prices,volumes,policy='hedged',**common)
    assert hedge.hedge_pnl[0]!=0 and hedge.rebalances[0]>0
    assert hedge.inventory[0]==pytest.approx(static.inventory[0]) # hedge never recenters LP
    threshold=simulate_policy(prices,volumes,policy='threshold',delta_threshold=.01,**common)
    assert threshold.rebalances[0]>0
    assert hedge.net[0]*10000==pytest.approx(hedge.inventory[0]+hedge.hedge_pnl[0]-10000)


def test_comparison_uses_same_history_and_hodl_is_free_of_lp_costs(history_state):
    root,*_=history_state;svc=ComparisonService(root)
    request=BacktestComparison(pool='weth-usdt-500',start='2023-02-15',end='2023-04-15',capital=10000)
    first=svc.run(request);assert first==svc.run(request)
    rows=first['strategies'];assert len(rows)==5
    assert len({tuple(p['timestamp'] for p in s['equity_curve']) for s in rows})==1
    for s in rows:
        m=s['summary'];assert m['excess_vs_hodl']==pytest.approx(m['fees']-m['il']-m['gas']-m['rebalance_cost'])
        if s['id']=='hodl':assert m['gas']==0 and m['excess_vs_hodl']==0 and m['active_share'] is None
        if s['id']=='dynamic':assert m['rebalance_count']==8
    with TestClient(create_app(root)) as client:
        response=client.post('/api/v1/backtests/compare',json=request.model_dump(mode='json'))
        assert response.status_code==200
        run_id=response.json()['meta']['run_id']
        export=client.get(f'/api/v1/backtests/comparisons/{run_id}/export.csv')
        assert export.status_code==200 and 'capital_usd' in export.text and 'historical_replay_modelled_fees' in export.text
        assert client.get('/api/v1/backtests/comparisons/'+'0'*64).status_code==404


def test_rolling_vol_width_cannot_see_future_close(history_state):
    root,*_=history_state;svc=ComparisonService(root)
    cfg=BacktestComparison(pool='weth-usdt-500',start='2023-02-15',end='2023-04-15')
    inputs=load_inputs(root,cfg,svc.settings)
    cfg=cfg.model_copy(update={'strategy':'vol_scaled'})
    first=replay(inputs,cfg,svc.settings,rebalance_rule='weekly',rolling_vol=True)
    changed=deepcopy(inputs);future=changed['bars'].index[20]
    changed['bars'].loc[changed['bars'].index>=future,'price']*=2
    changed['history'].loc[changed['history'].index>=future,'price']*=2
    second=replay(changed,cfg,svc.settings,rebalance_rule='weekly',rolling_vol=True)
    assert first['equity_curve'][:20]==second['equity_curve'][:20]


def test_mixed_microsecond_nanosecond_source_timestamps(history_state):
    root,history,tvl,pool,save=history_state
    tvl['timestamp']=tvl.timestamp.dt.as_unit('us');save()
    cfg=BacktestComparison(pool='weth-usdt-500',start='2023-02-15',end='2023-04-15')
    result=ComparisonService(root).run(cfg)
    assert all(s['status']=='ok' for s in result['strategies'])


def test_availability_selects_by_calendar_coverage_without_filling_gaps(history_state):
    root,history,tvl,pool,save=history_state
    history.drop(index=80,inplace=True);save()
    with TestClient(create_app(root)) as client:
        response=client.get('/api/v1/pools/weth-usdt-500/backtest-availability')
        assert response.status_code==200
        availability=response.json();assert availability['missing_days']==1
        suggestion=availability['suggestion'];assert suggestion is not None
        assert suggestion['end']<'2023-03-22' or suggestion['warmup_start']>'2023-03-22'
        result=client.post('/api/v1/backtests/compare',json={'pool':'weth-usdt-500','start':suggestion['start'],'end':suggestion['end'],'volatility_window_days':suggestion['volatility_window_days'],'allow_partial':False})
        assert result.status_code==200,result.text


def test_new_page_routes_are_packaged_and_legacy_remains(client):
    for page in ['overview','lp-optimizer','optimization-results','strategy-backtesting','risk-and-research','data-and-methodology']:
        response=client.get('/'+page);assert response.status_code==200
        assert 'cdn.tailwindcss.com' not in response.text
        assert '/dashboard/rangelab/assets/app.js' in response.text
    assert client.get('/legacy').status_code==200
    assert client.get('/dashboard/rangelab/assets/app.js').status_code==200


def test_workbench_contract_rejects_impossible_budgets_and_unavailable_sources(client):
    assert client.post('/api/v1/workbench/run',json={'config':{'n_paths':5000,'horizon_days':365}}).status_code==422
    assert client.post('/api/v1/workbench/run',json={}).status_code==400 # observed data required
    assert client.post('/api/v1/workbench/stress',json={'run_id':'../secret'}).status_code==422
    with pytest.raises(ValueError):SensitivityRequest(run_id='a'*64,low_vol_pct=120,high_vol_pct=30)


def test_workbench_saved_runs_volume_overrides_stress_and_exports(client,observed):
    request={'config':{'n_paths':20,'horizon_days':14,'capital':10000,'gas_usd':5,'vol_annual':.5,'risk_max_exit_prob':1},'volume_daily_override_usd':1e6}
    result=client.post('/api/v1/workbench/run',json=request)
    assert result.status_code==200,result.text
    result=result.json();run_id=result['meta']['run_id'];point=result['optimum']
    assert point['excess_vs_hodl']==pytest.approx(point['fees']-point['il']-point['gas']-point['rebalance_cost']+point['hedge_pnl'])
    assert result['mean_daily_volume_usd']==1e6
    assert len(result['selected_price_path'])==15
    assert result['aligned_ticks']['price_low_tick']==result['aligned_ticks']['upper'] # inverse USDC token0 ordering
    assert result['aligned_ticks']['price_high_tick']==result['aligned_ticks']['lower']
    assert client.post('/api/v1/workbench/run',json=request).json()==result
    saved=client.get('/api/v1/workbench/runs/'+run_id).json()
    assert saved['result']==result and saved['kind']=='workbench'
    assert client.get('/api/v1/workbench/runs/'+run_id+'/export.json').json()==saved
    for name in ['summary','methodology']:
        export=client.get(f'/api/v1/workbench/runs/{run_id}/{name}.pdf')
        assert export.status_code==200 and export.content.startswith(b'%PDF-')
    first=client.post('/api/v1/workbench/stress',json={'run_id':run_id,'price_shock_pct':-30,'volatility_multiplier':0}).json()
    second=client.post('/api/v1/workbench/stress',json={'run_id':run_id,'price_shock_pct':-30,'volatility_multiplier':3}).json()
    assert first['metrics']['hodl_value']==second['metrics']['hodl_value']==pytest.approx(8500)
    assert first['metrics']['inventory_value']==pytest.approx(second['metrics']['inventory_value'])
    assert first['metrics']['fees']!=second['metrics']['fees'] # volatility changes occupation, not terminal HODL
    sensitivity=client.post('/api/v1/workbench/sensitivity',json={'run_id':run_id,'low_vol_pct':30,'high_vol_pct':50,'steps':3}).json()
    assert len(sensitivity['rows'])==3
    assert sensitivity['meta']['range_reoptimized_per_vol']
    zero=client.post('/api/v1/workbench/run',json={**request,'volume_daily_override_usd':0}).json()
    assert zero['meta']['run_id']!=run_id and zero['optimum']['fees']==0
    for policy in ['weekly','threshold','hedged']:
        changed=client.post('/api/v1/workbench/run',json={**request,'rebalance_policy':policy}).json()
        m=changed['optimum']
        assert m['excess_vs_hodl']==pytest.approx(m['fees']-m['il']-m['gas']-m['rebalance_cost']+m['hedge_pnl'])
    observed['pools'][0]['tvl_usd']*=2;observed['save']()
    assert client.post('/api/v1/workbench/stress',json={'run_id':run_id}).status_code==400 # never mix snapshots


def test_risk_replay_rejects_model_and_settings_changes(client,observed,monkeypatch):
    import src.models.workbench as module
    request={'config':{'n_paths':12,'horizon_days':7,'risk_max_exit_prob':1}}
    result=client.post('/api/v1/workbench/run',json=request).json();run_id=result['meta']['run_id']
    version=module.VERSION
    monkeypatch.setattr(module,'VERSION',version+'-changed')
    assert client.post('/api/v1/workbench/stress',json={'run_id':run_id}).status_code==400
    monkeypatch.setattr(module,'VERSION',version)
    client.app.state.service.settings['research']['optimizer']['grid_points']+=1
    response=client.post('/api/v1/workbench/stress',json={'run_id':run_id})
    assert response.status_code==400 and 'cấu hình engine' in response.json()['detail']

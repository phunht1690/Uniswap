"""Historical replay: lagged decisions, coherent USD cashflows and API evidence."""
import csv
import hashlib
import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.schemas import BacktestRequest
from src.data.backtest import BacktestUnavailable, load_inputs
from src.evaluation.backtest import replay
from src.evaluation.backtest_service import BacktestService


@pytest.fixture
def history_state(tmp_path):
    data = tmp_path/'data/processed'
    data.mkdir(parents=True)
    dates = pd.date_range('2023-01-01', periods=160, tz='UTC')
    prices = 2000*np.exp(np.cumsum(np.sin(np.arange(160)*.7)*.035))
    history = pd.DataFrame({'timestamp': dates, 'price': prices, 'volume_usd': 10e6*(1+.3*np.cos(np.arange(160)))})
    tvl = pd.DataFrame({'timestamp': dates-pd.Timedelta(days=10), 'tvl_usd': np.full(160,50e6)})
    pool = {'id': 'weth-usdt-500', 'address': '0x'+'1'*40, 'base': 'WETH', 'quote': 'USDT', 'fee_rate': .0005, 'fee_tier': 500}
    def save():
        history.to_parquet(data/'history_weth-usdt-500.parquet',index=False)
        tvl.to_parquet(data/'tvl_weth-usdt-500.parquet',index=False)
        (data/'pool_registry.json').write_text(json.dumps({'data_kind':'observed_snapshot','pools':[pool]}),encoding='utf-8')
        with (tmp_path/'data/source_log.csv').open('w',encoding='utf-8',newline='') as stream:
            fields=['source','endpoint','downloaded_at_utc','period_start','period_end','row_count','file_path','sha256','data_kind']
            writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
            for path in data.iterdir():
                writer.writerow({'source':'test_observed_fixture','endpoint':'fixture://labelled','file_path':path.relative_to(tmp_path).as_posix(),
                                 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'data_kind':'observed_fixture'})
    save()
    return tmp_path,history,tvl,pool,save


def config(**overrides):
    return BacktestRequest(**{'pool':'weth-usdt-500','start':'2023-02-15','end':'2023-04-15','gas_usd':15,**overrides})


def test_backtest_decomposition_and_costs(history_state):
    root,*_=history_state
    svc=BacktestService(root)
    for strategy in ['full','fixed','vol_scaled','dynamic','optimizer']:
        result=svc.run(config(strategy=strategy))
        assert result['status']=='ok'
        summary=result['summary']
        assert summary['excess_vs_hodl']==pytest.approx(summary['fees']-summary['il']-summary['gas']-summary['rebalance_cost'])
        assert summary['gas']==pytest.approx(summary['gas_units']*15/50000)
        assert len(result['equity_curve'])==60
        assert result['equity_curve'][0]['lp']==pytest.approx(-15/50000)
        assert result['meta']['assumptions']['liquidity_observed'] is False
    assert svc.run(config())==svc.run(config())


def test_future_rows_and_current_snapshot_cannot_change_prior_run(history_state):
    root,history,tvl,pool,save=history_state
    svc=BacktestService(root)
    first=svc.run(config())
    history.loc[history.timestamp>pd.Timestamp('2023-04-15',tz='UTC'),'price']*=9
    history.loc[history.timestamp>pd.Timestamp('2023-04-15',tz='UTC'),'volume_usd']*=100
    tvl.loc[tvl.timestamp>=pd.Timestamp('2023-04-15',tz='UTC'),'tvl_usd']*=100
    pool['p0']=1e15;pool['liquidity_raw']='123';save()
    assert svc.run(config())==first


def test_volatility_and_tvl_strictly_predate_decision(history_state):
    root,history,tvl,pool,save=history_state
    svc=BacktestService(root)
    inputs=load_inputs(root,config(),svc.settings)
    assert pd.Timestamp(inputs['feature_asof'])<pd.Timestamp(inputs['start'])
    assert (inputs['bars'].tvl_available_at<inputs['bars'].decision_time).all()
    changed=history.copy()
    history.loc[history.timestamp>=pd.Timestamp(inputs['start']),'price']*=2;save()
    new=load_inputs(root,config(),svc.settings)
    assert new['vol']==inputs['vol']
    assert new['mean_volume']==inputs['mean_volume']


def test_gap_warmup_and_stale_tvl_are_explicit(history_state):
    root,history,tvl,pool,save=history_state
    svc=BacktestService(root)
    partial=svc.run(config(start='2022-01-01'))
    assert partial['meta']['partial_period']
    with pytest.raises(BacktestUnavailable):svc.run(config(start='2022-01-01',allow_partial=False))
    history.drop(index=65,inplace=True);save()
    with pytest.raises(BacktestUnavailable,match='ngày trống'):svc.run(config())


def test_usd_quote_exposure_and_protocol_fee_scenario(history_state):
    root,history,tvl,pool,save=history_state
    svc=BacktestService(root)
    base=svc.run(config(gas_usd=0))
    cut=svc.run(config(gas_usd=0,protocol_fee_fraction=.25))
    assert cut['summary']['fees']==pytest.approx(base['summary']['fees']*.75)
    pool['quote']='WETH';pool['base']='WBTC';save()
    reference=pd.DataFrame({'timestamp':history.timestamp,'price':2000*np.exp(np.arange(len(history))*.001)})
    path=root/'data/processed/reference_ethusdt_1d.parquet';reference.to_parquet(path,index=False)
    with (root/'data/source_log.csv').open('a',newline='',encoding='utf-8') as stream:
        csv.writer(stream).writerow(['test','fixture://quote','','','',len(reference),path.relative_to(root).as_posix(),hashlib.sha256(path.read_bytes()).hexdigest(),'observed_fixture'])
    result=svc.run(config())
    bars=load_inputs(root,config(),svc.settings)['bars']
    expected=.5*(1+bars.price.iloc[-1]/bars.price.iloc[0])*bars.quote_usd.iloc[-1]/bars.quote_usd.iloc[0]-1
    assert result['summary']['hodl_return']==pytest.approx(expected)
    assert result['summary']['hodl_return']!=pytest.approx(base['summary']['hodl_return'])


def test_backtest_api_replay_download_and_validation(history_state):
    root,*_=history_state
    with TestClient(create_app(state_dir=root)) as client:
        params=config().model_dump(mode='json');pool=params.pop('pool')
        first=client.get('/api/v1/backtest/'+pool,params=params)
        assert first.status_code==200,first.text
        result=first.json();run_id=result['meta']['run_id']
        assert client.get('/api/v1/runs/'+run_id).json()['result']==result
        csv_result=client.get('/api/v1/backtests/'+run_id+'/curve.csv')
        assert csv_result.status_code==200 and 'timestamp,lp,hodl' in csv_result.text
        assert client.get('/api/v1/backtest/'+pool,params={**params,'capital':0}).status_code==422
        assert client.get('/api/v1/backtest/'+pool,params={**params,'start':'2023-05-01'}).status_code==400
        assert client.get('/api/v1/backtest/unknown',params=params).status_code==400
        path=root/'data/processed/history_weth-usdt-500.parquet'
        path.write_bytes(b'corrupt')
        assert client.get('/api/v1/backtest/'+pool,params=params).status_code==503


def test_rebalance_happens_after_observation_and_can_be_disabled(history_state):
    root,history,tvl,pool,save=history_state
    history.loc[:,'price']=np.where(np.arange(len(history))<50,2000,3500);save()
    svc=BacktestService(root)
    result=svc.run(config(strategy='dynamic',start='2023-02-15',end='2023-03-15'))
    curve=result['equity_curve']
    jump=next(i for i,row in enumerate(curve) if row['price']==3500)
    assert curve[jump]['rebalance_count']==0
    assert curve[jump+1]['rebalance_count']==1
    disabled=svc.run(config(strategy='dynamic',max_rebalances=0))
    assert disabled['summary']['rebalance_count']==0


def test_stale_tvl_and_insolvent_cost_scenarios(history_state):
    root,history,tvl,pool,save=history_state
    svc=BacktestService(root)
    result=svc.run(config(capital=1000,gas_usd=1_000_000))
    assert result['summary']['solvent'] is False and result['summary']['sharpe_lp_daily'] is None
    assert np.isfinite(result['summary']['net'])
    tvl.drop(tvl.index[tvl.timestamp>pd.Timestamp('2023-01-10',tz='UTC')],inplace=True);save()
    with pytest.raises(BacktestUnavailable,match='TVL'):svc.run(config())


def test_optimizer_infeasibility_never_uses_an_unsafe_fallback(history_state):
    root,*_=history_state
    svc=BacktestService(root);svc.settings={**svc.settings,'optimizer_grid_points':1}
    result=svc.run(config(strategy='optimizer',risk_max_exit_prob=0))
    assert result['status']=='infeasible' and result['summary'] is None and result['equity_curve']==[]

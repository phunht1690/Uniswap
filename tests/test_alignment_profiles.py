"""Research-rule parity and explicit versioned product comparisons."""
from copy import deepcopy
import csv
import io
import json

import pytest
from fastapi.testclient import TestClient

from api.app_schemas import BacktestComparison
from api.main import create_app
from api.schemas import BacktestRequest
from src.evaluation.backtest_service import BacktestService
from src.evaluation.comparison import ComparisonService,comparison_presets,VERSION
from tests.test_backtest import history_state


def preset_request(mode='research',**overrides):
    preset=next(row for row in comparison_presets()['presets'] if row['id']==mode)
    return BacktestComparison(**{**preset['config'],'pool':'weth-usdt-500',
        'start':'2023-02-15','end':'2023-04-15',**overrides})


def test_research_rules_match_direct_archived_replay_contract(history_state):
    root,*_=history_state
    names=['full','fixed','vol_scaled','dynamic','optimizer','hodl']
    request=preset_request(strategies=names)
    result=ComparisonService(root).run(request)
    assert result['meta']['model_version']==VERSION=='rangelab-comparison-v2'
    assert result['meta']['configuration_profile']['id']=='research'
    assert result==ComparisonService(root).run(request)
    direct=BacktestService(root)
    for row in result['strategies']:
        if row['id']=='hodl':
            assert row['summary']['gas']==0
            assert row['summary']['excess_vs_hodl']==0
            continue
        config=BacktestRequest.model_validate({key:value for key,value in request.model_dump().items()
            if key not in {'strategy_mode','strategies'}}).model_copy(update={'strategy':row['id']})
        reference=direct.run(config)
        assert row['summary']==reference['summary'],row['id']
        assert row['equity_curve']==reference['equity_curve'],row['id']
    dynamic=next(row for row in result['strategies'] if row['id']=='dynamic')
    scaled=next(row for row in result['strategies'] if row['id']=='vol_scaled')
    assert dynamic['rules']['rebalance_rule']=='out_of_range'
    assert scaled['rules']['rebalance_rule']=='none'
    assert scaled['rules']['width_rule']=='volatility_at_entry'
    assert 'ra ngoài khoảng' in dynamic['label']
    assert '30 ngày' in scaled['label'] and 'entry' in scaled['label']


def test_rule_change_has_distinct_identity_and_no_forced_weekly_research_trades(history_state):
    root,*_=history_state
    request=preset_request(strategies=['dynamic','vol_scaled'])
    service=ComparisonService(root)
    research=service.run(request)
    weekly=service.run(request.model_copy(update={'strategy_mode':'weekly'}))
    assert research['meta']['run_id']!=weekly['meta']['run_id']
    assert research['strategies'][0]['summary']['rebalance_count']==0
    assert weekly['strategies'][0]['summary']['rebalance_count']==8
    assert research['strategies'][0]['summary']['gas']<weekly['strategies'][0]['summary']['gas']
    assert research['strategies'][0]['summary']['net']!=weekly['strategies'][0]['summary']['net']
    assert weekly['strategies'][1]['rules']['width_rule']=='rolling_weekly'
    assert weekly['meta']['configuration_profile']['id']=='custom' # research numeric settings, weekly rules
    assert not weekly['meta']['configuration_profile']['matches_preset']


def test_omitted_mode_keeps_product_api_defaults_and_weekly_behavior(history_state):
    root,*_=history_state
    request=BacktestComparison(pool='weth-usdt-500',start='2023-02-15',end='2023-04-15')
    assert request.strategy_mode=='weekly'
    assert request.half_width==.15 and request.volatility_window_days==14
    result=ComparisonService(root).run(request)
    assert result['meta']['configuration_profile']['id']=='weekly'
    assert len(result['strategies'])==5
    dynamic=next(row for row in result['strategies'] if row['id']=='dynamic')
    assert dynamic['summary']['rebalance_count']==8
    assert dynamic['rules']['rebalance_rule']=='weekly'


def test_presets_are_detached_and_profile_does_not_claim_archived_sample():
    first=comparison_presets()
    assert first['default_id']=='research'
    configs={p['id']:p['config'] for p in first['presets']}
    assert configs['research']['half_width']==.2 and configs['research']['volatility_window_days']==30
    assert configs['weekly']['half_width']==.15 and configs['weekly']['volatility_window_days']==14
    for config in configs.values():
        assert config['capital']==50000 and config['gas_usd']==15
        assert config['seed']==42 and config['min_rebalance_gap_days']==7
        assert config['max_rebalances']==52 and config['rebalance_slippage_bps']==0
        assert config['concentration']==3 and config['protocol_fee_fraction']==0
        assert config['risk_max_exit_prob']==.4 and config['price_source']=='pool'
        assert not {'pool','start','end'} & set(config)
    configs['research']['half_width']=10
    assert comparison_presets()['presets'][0]['config']['half_width']==.2
    assert 'dữ liệu' in first['note'] and 'thời gian' in first['note']


def test_custom_configuration_is_assessed_by_values_not_client_label(history_state):
    root,*_=history_state
    request=preset_request(half_width=.21,capital=12345,strategies=['fixed'])
    result=ComparisonService(root).run(request)
    profile=result['meta']['configuration_profile']
    assert profile['id']=='custom' and not profile['matches_preset']
    assert 'không khớp' in profile['description'] and not profile['description'].startswith('Khớp')
    assert result['meta']['effective_config']['half_width']==.21
    assert '0.21' in result['strategies'][0]['label']
    assert 'half_width' in profile['checked_fields'] and 'capital' in profile['checked_fields']


def test_alignment_api_validation_presets_and_csv_reproduction_columns(history_state):
    root,*_=history_state
    with TestClient(create_app(root)) as client:
        presets=client.get('/api/v1/backtests/presets')
        assert presets.status_code==200
        assert presets.json()['default_id']=='research'
        request=preset_request(strategies=['fixed','dynamic'])
        body=request.model_dump(mode='json')
        assert client.post('/api/v1/backtests/compare',json={**body,'strategy_mode':'ambiguous'}).status_code==422
        assert client.post('/api/v1/backtests/compare',json={**body,'profile_label':'research'}).status_code==422
        response=client.post('/api/v1/backtests/compare',json=body)
        assert response.status_code==200,response.text
        result=response.json()
        exported=client.get('/api/v1/backtests/comparisons/'+result['meta']['run_id']+'/export.csv')
        rows=list(csv.DictReader(io.StringIO(exported.text.lstrip('\ufeff'))))
        assert rows
        assert {'model_version','strategy_mode','configuration_profile','half_width','volatility_window_days','rebalance_rule','width_rule'}<=set(rows[0])
        assert all(r['strategy_mode']=='research' and r['model_version']==VERSION for r in rows)
        dynamic=next(r for r in rows if r['strategy']=='dynamic')
        assert dynamic['rebalance_rule']=='out_of_range'
        assert float(dynamic['half_width'])==.2 and int(dynamic['volatility_window_days'])==30


def test_legacy_v1_get_is_unchanged_and_csv_keeps_old_weekly_semantics(history_state):
    root,*_=history_state
    service=ComparisonService(root)
    current=service.run(preset_request('weekly',strategies=['dynamic']))
    old=deepcopy(current);old_id='f'*64
    old['meta'].update(run_id=old_id,model_version='rangelab-comparison-v1')
    for key in ['strategy_mode','configuration_profile','strategy_rules']:old['meta'].pop(key)
    old['meta']['effective_config'].pop('strategy_mode')
    old['meta']['rules']={'dynamic':'Initial vol-scaled width, weekly recenter'}
    old['strategies'][0].pop('rules')
    old['strategies'][0]['label']='Tên lưu từ phiên bản một hằng tuần'
    record={'kind':'backtest_comparison','config':deepcopy(old['meta']['effective_config']),'result':old}
    path=root/'outputs/comparisons'/(old_id+'.json')
    path.write_bytes(json.dumps(record,ensure_ascii=False,indent=2).encode('utf-8'))
    before=path.read_bytes()
    assert service.get(old_id)==record
    with TestClient(create_app(root)) as client:
        response=client.get('/api/v1/backtests/comparisons/'+old_id)
        assert response.status_code==200 and response.json()==record
        exported=client.get('/api/v1/backtests/comparisons/'+old_id+'/export.csv')
        rows=list(csv.DictReader(io.StringIO(exported.text.lstrip('\ufeff'))))
        assert rows and all(r['strategy_mode']=='weekly' and r['rebalance_rule']=='weekly' for r in rows)
        assert all(r['label']=='Tên lưu từ phiên bản một hằng tuần' for r in rows)
        assert all(r['model_version']=='rangelab-comparison-v1' for r in rows)
    assert path.read_bytes()==before
    assert current['meta']['run_id']!=old_id

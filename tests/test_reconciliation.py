"""Archive reconciliation preserves provenance, paired accounting and scope."""
import csv
import hashlib
import io
import json
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from src.evaluation.reconciliation import research_reconciliation


def _publish(root, name, payload):
    manifest_path = root/'outputs/research/latest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    directory = root/'outputs/research'/manifest['research_id']
    directory.mkdir(parents=True, exist_ok=True)
    data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    (directory/name).write_bytes(data)
    manifest['files'] = [row for row in manifest['files'] if row['name'] != name]
    manifest['files'].append({'name': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')


def _csv(rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
    return stream.getvalue().encode()


@pytest.fixture
def archive(tmp_path):
    manifest = {'research_id': 'a'*64, 'version': 'published-archive-v2', 'files': [],
                'settings': {'fixed_width': .2, 'volatility_window_days': 30, 'panel_holding_days': 30},
                'spec': {'capital': 50000, 'gas_usd': 15},
                'status': {'confirmatory_oos_status': 'unavailable'}}
    path = tmp_path/'outputs/research/latest.json';path.parent.mkdir(parents=True)
    path.write_text(json.dumps(manifest), encoding='utf-8')
    full = []
    for i, pool in enumerate(['pool-a', 'pool-b', 'pool-c']):
        for strategy in ['fixed', 'optimizer']:
            fee = [.10, .20, .30][i] if strategy == 'fixed' else [.06, .08, .10][i]
            il = [.01, .15, .02][i] if strategy == 'fixed' else [.02, .04, .06][i]
            excess = fee-il-.0006
            full.append({'pool': pool, 'strategy': strategy, 'run_id': ('a' if strategy == 'fixed' else 'b')*63+str(i),
                         'start': '2025-01-01', 'end': '2025-04-01', 'net': excess,
                         'excess_vs_hodl': excess, 'fees': fee, 'il': il, 'gas': .0006,
                         'rebalance_cost': 0, 'rebalance_count': 0, 'half_width': .2, 'holding_days': 90})
    monthly = []
    for period in range(4):
        start = date(2025, 1, 1)+timedelta(days=period*30)
        for pool in ['pool-a', 'pool-b']:
            for strategy in ['fixed', 'optimizer']:
                monthly.append({'pool': pool, 'strategy': strategy, 'start': str(start),
                                'end': str(start+timedelta(days=30)), 'half_width': .2,
                                'excess_vs_hodl': period*.003+(strategy == 'optimizer')*.01})
    gas = [{'pool': 'pool-'+str(i), 'dynamic_minus_static_before_gas_usd': 0,
            'extra_gas_units': 0, 'break_even_gas_usd': '', 'status': 'dynamic_not_better_at_zero_gas'}
           for i in range(6)]
    bootstrap = {'status': 'exploratory_model_conditional', 'mean_optimizer_minus_fixed': .01,
                 'ci95_low': .005, 'ci95_high': .015, 'time_windows': 4, 'paired_pool_windows': 8,
                 'repetitions': 99, 'circular_block_windows': 2, 'seed': 42, 'not_confirmatory_OOS': True}
    _publish(tmp_path, 'strategy_returns.csv', _csv(full))
    _publish(tmp_path, 'monthly_returns.csv', _csv(monthly))
    _publish(tmp_path, 'gas_break_even.csv', _csv(gas))
    _publish(tmp_path, 'optimizer_paired_bootstrap.json', bootstrap)
    return tmp_path


def test_zero_gain_and_zero_extra_gas_are_not_evidence_of_a_rebalance_tradeoff(archive):
    directory = archive/'outputs/research'/('a'*64)
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    result = research_reconciliation(archive)
    gas = result['gas_evidence']
    assert gas['rows'] == 6 and gas['gain_zero_rows'] == 6 and gas['extra_gas_zero_rows'] == 6
    assert gas['break_even_defined_rows'] == 0 and gas['informative'] is False
    assert gas['status'] == 'no_rebalance_events'
    assert next(row for row in result['claims'] if row['id'] == 'H4')['status'] == 'not_testable_with_archive'
    assert 'không phải 0 USD' in gas['interpretation']
    assert {path.name: path.read_bytes() for path in directory.iterdir()} == before


def test_cost_identity_uses_paired_rows_not_differences_of_independent_medians(archive):
    result = research_reconciliation(archive)
    full = result['full_period']
    assert full['rows_count'] == 6 and full['costs']['zero_rebalance_rows'] == 6
    assert full['costs']['gas_percent_min'] == pytest.approx(.06)
    assert full['costs']['gas_percent_max'] == pytest.approx(.06)
    assert full['costs']['slippage_percent_max'] == 0
    assert full['costs']['max_abs_accounting_residual'] < 1e-12
    fixed = next(row for row in full['strategies'] if row['id'] == 'fixed')
    assert fixed['median_paired_cost'] == pytest.approx(.0006)
    assert fixed['cost_from_independent_medians'] != pytest.approx(.0006)
    assert fixed['max_abs_paired_residual'] < 1e-12


def test_monthly_paired_mean_and_full_period_medians_are_separate_estimands(archive):
    result = research_reconciliation(archive)
    window = result['optimizer_window']
    assert window['mean_optimizer_minus_fixed'] == pytest.approx(.01)
    assert window['time_windows'] == 4 and window['paired_pool_windows'] == 8
    assert window['ci95_low'] == .005 and window['ci95_high'] == .015
    assert window['holding_days'] == 30 and window['fixed_half_width'] == .2
    assert window['not_confirmatory_OOS'] is True
    assert result['full_period']['optimizer_minus_fixed_medians'] < 0
    assert result['archive_version'] == 'published-archive-v2'
    assert result['archive_profile']['volatility_window_days'] == 30
    assert result['archive_profile']['dynamic_rule'] == 'out_of_range'
    assert result['archive_profile']['vol_scaled_rule'] == 'initial_width_static'


@pytest.mark.parametrize('name', ['strategy_returns.csv', 'monthly_returns.csv',
                                 'gas_break_even.csv', 'optimizer_paired_bootstrap.json'])
def test_any_tampered_evidence_file_is_rejected(archive, name):
    path = archive/'outputs/research'/('a'*64)/name
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError, match='Hash'):
        research_reconciliation(archive)


def test_api_handles_missing_tampered_and_valid_evidence_without_faking_a_summary(archive):
    path = archive/'outputs/research'/('a'*64)/'gas_break_even.csv'
    original = path.read_bytes()
    with TestClient(create_app(state_dir=archive)) as client:
        response = client.get('/api/v1/research/reconciliation')
        assert response.status_code == 200
        assert response.json()['artifact_hashes_verified'] is True
        path.unlink()
        assert client.get('/api/v1/research/reconciliation').status_code == 404
        path.write_bytes(b'not the published content')
        assert client.get('/api/v1/research/reconciliation').status_code == 503
        path.write_bytes(original)
        assert client.get('/api/v1/research/reconciliation').status_code == 200


def test_matching_hash_but_mismatched_bootstrap_cannot_be_reported_as_paired_evidence(archive):
    _publish(archive, 'optimizer_paired_bootstrap.json', {
        'status': 'exploratory_model_conditional', 'mean_optimizer_minus_fixed': .50,
        'ci95_low': .40, 'ci95_high': .60, 'paired_pool_windows': 8, 'time_windows': 4})
    with pytest.raises(ValueError, match='Bootstrap'):
        research_reconciliation(archive)


def test_incremental_gas_case_remains_conditional_instead_of_degenerate(archive):
    _publish(archive, 'gas_break_even.csv', _csv([{
        'dynamic_minus_static_before_gas_usd': 100, 'extra_gas_units': 2,
        'break_even_gas_usd': 50}]))
    result = research_reconciliation(archive)
    assert result['gas_evidence']['informative'] is True
    assert result['gas_evidence']['break_even_defined_rows'] == 1
    assert next(row for row in result['claims'] if row['id'] == 'H4')['status'] == 'conditional_evidence'

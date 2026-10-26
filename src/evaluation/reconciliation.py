"""Read-only reconciliation of published, content-hashed research evidence.

The published archive remains immutable. Summary figures are calculated from
its rows; current interactive results must never be substituted for those rows.
Returns and costs use fractions of initial capital except explicit *_percent
fields, which are percentages of initial capital.
"""
import csv
import io
import json
import math
from collections import defaultdict
from datetime import date
from statistics import mean, median

from src.evaluation.artifacts import artifact, latest_manifest


FILES = ('strategy_returns.csv', 'gas_break_even.csv', 'monthly_returns.csv',
         'optimizer_paired_bootstrap.json')
LABELS = {'full': 'Toàn dải', 'fixed': 'Khoảng cố định',
          'vol_scaled': 'Theo biến động tại thời điểm mở',
          'dynamic': 'Đặt lại khoảng khi giá ra ngoài', 'optimizer': 'Tối ưu tại thời điểm mở'}
EPSILON = 1e-10


def _number(value, optional=False):
    if optional and (value is None or value == ''):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError('Dữ liệu nghiên cứu thiếu trường số hợp lệ.') from None
    if not math.isfinite(result):
        raise ValueError('Dữ liệu nghiên cứu có giá trị số không hữu hạn.')
    return result


def _table(payload, required):
    reader = csv.DictReader(io.StringIO(payload.decode('utf-8-sig')))
    if not set(required).issubset(reader.fieldnames or []):
        raise ValueError('Bảng nghiên cứu thiếu các cột cần để đối chiếu.')
    rows = list(reader)
    if not rows:
        raise ValueError('Bảng nghiên cứu chưa có dữ liệu để đối chiếu.')
    return rows


def _range(values):
    return min(values), max(values)


def _full_period(rows):
    fields = ('net', 'excess_vs_hodl', 'fees', 'il', 'gas', 'rebalance_cost', 'rebalance_count')
    parsed = []
    groups = defaultdict(list)
    seen = set()
    for raw in rows:
        identity = raw['pool'], raw['strategy']
        if identity in seen:
            raise ValueError('Bảng toàn kỳ có kết quả pool và chiến lược bị trùng.')
        seen.add(identity)
        row = {key: raw[key] for key in ('pool', 'strategy', 'run_id', 'start', 'end')}
        row.update({key: _number(raw.get(key)) for key in fields})
        row['half_width'] = _number(raw.get('half_width'), optional=True)
        row['holding_days'] = _number(raw.get('holding_days'))
        row['hedge_pnl'] = _number(raw.get('hedge_pnl') or 0)
        row['paired_cost'] = row['gas'] + row['rebalance_cost']
        row['accounting_residual'] = (row['fees'] - row['il'] + row['hedge_pnl']
                                      - row['paired_cost'] - row['excess_vs_hodl'])
        parsed.append(row)
        groups[row['strategy']].append(row)
    summaries = []
    for strategy, values in groups.items():
        medians = {key: median(row[key] for row in values) for key in fields}
        summaries.append({
            'id': strategy, 'label': LABELS.get(strategy, strategy), 'rows_count': len(values),
            'median': medians,
            'cost_from_independent_medians': medians['fees'] - medians['il'] - medians['excess_vs_hodl'],
            'median_paired_cost': median(row['paired_cost'] for row in values),
            'median_paired_residual': median(row['accounting_residual'] for row in values),
            'max_abs_paired_residual': max(abs(row['accounting_residual']) for row in values),
        })
    summary_by_id = {row['id']: row['median'] for row in summaries}
    difference = (summary_by_id['optimizer']['excess_vs_hodl'] - summary_by_id['fixed']['excess_vs_hodl']
                  if {'optimizer', 'fixed'}.issubset(summary_by_id) else None)
    gas_min, gas_max = _range([row['gas'] for row in parsed])
    slip_min, slip_max = _range([row['rebalance_cost'] for row in parsed])
    return {
        'rows_count': len(parsed), 'pool_count': len({row['pool'] for row in parsed}),
        'start': min(row['start'] for row in parsed), 'end': max(row['end'] for row in parsed),
        'strategies': summaries, 'optimizer_minus_fixed_medians': difference,
        'costs': {
            'gas_min': gas_min, 'gas_max': gas_max,
            'gas_percent_min': gas_min * 100, 'gas_percent_max': gas_max * 100,
            'slippage_min': slip_min, 'slippage_max': slip_max,
            'slippage_percent_min': slip_min * 100, 'slippage_percent_max': slip_max * 100,
            'zero_rebalance_rows': sum(abs(row['rebalance_count']) <= EPSILON for row in parsed),
            'max_abs_accounting_residual': max(abs(row['accounting_residual']) for row in parsed),
            'identity': 'excess_vs_hodl = fees - il - gas - rebalance_cost + hedge_pnl',
        },
        'rows': parsed,
    }


def _gas_evidence(rows):
    gains = [_number(row['dynamic_minus_static_before_gas_usd']) for row in rows]
    units = [_number(row['extra_gas_units']) for row in rows]
    thresholds = [_number(row.get('break_even_gas_usd'), optional=True) for row in rows]
    gain_zero = sum(abs(value) <= EPSILON for value in gains)
    units_zero = sum(abs(value) <= EPSILON for value in units)
    informative = any(value > EPSILON for value in units)
    if gain_zero == len(rows) and units_zero == len(rows):
        status = 'no_rebalance_events'
        interpretation = ('Các tình huống đều có lợi ích trước gas bằng 0 và số đơn vị gas tăng thêm bằng 0. '
                          'Không phát sinh điều chỉnh so với khoảng tĩnh cùng độ rộng; chưa kiểm tra được '
                          'đánh đổi lợi ích và chi phí của việc dời khoảng. Ngưỡng hòa vốn không xác định, không phải 0 USD.')
    elif not informative:
        status = 'no_incremental_gas_units'
        interpretation = ('Không có trường hợp tăng số đơn vị gas để xác định ngưỡng hòa vốn. '
                          'Chưa đủ bằng chứng kết luận về đánh đổi chi phí điều chỉnh vị thế.')
    else:
        status = 'incremental_costs_observed'
        interpretation = ('Có tình huống phát sinh gas tăng thêm; cần đọc lợi ích trước gas và ngưỡng theo từng '
                          'pool, vốn và khoảng cách điều chỉnh. Kết quả phụ thuộc mô hình, không tự xác nhận H4.')
    return {
        'rows': len(rows), 'gain_zero_rows': gain_zero, 'extra_gas_zero_rows': units_zero,
        'break_even_defined_rows': sum(value is not None for value in thresholds),
        'positive_extra_gas_rows': sum(value > EPSILON for value in units),
        'informative': informative, 'status': status, 'interpretation': interpretation,
        'benchmark': 'static_same_initial_width',
        'gain_unit': 'USD', 'extra_gas_unit': 'gas_operation_units',
        'threshold_unit': 'USD_per_gas_operation',
    }


def _optimizer_window(rows, bootstrap, settings):
    pairs = defaultdict(dict)
    widths = set()
    horizons = set()
    for row in rows:
        strategy = row['strategy']
        if strategy not in {'optimizer', 'fixed'}:
            continue
        key = row['pool'], row['start'], row['end']
        if strategy in pairs[key]:
            raise ValueError('Cửa sổ nghiên cứu bị trùng trong phép so sánh ghép cặp.')
        pairs[key][strategy] = _number(row['excess_vs_hodl'])
        if strategy == 'fixed':
            width = _number(row.get('half_width'), optional=True)
            if width is not None:
                widths.add(width)
        horizons.add((date.fromisoformat(row['end'][:10]) - date.fromisoformat(row['start'][:10])).days)
    differences = {key: values['optimizer'] - values['fixed']
                   for key, values in pairs.items() if {'optimizer', 'fixed'}.issubset(values)}
    if not differences:
        raise ValueError('Chưa có cửa sổ optimizer và fixed ghép cặp để đối chiếu.')
    by_time = defaultdict(list)
    for (_, start, end), difference in differences.items():
        by_time[start, end].append(difference)
    paired_mean = mean(mean(values) for values in by_time.values())
    if 'mean_optimizer_minus_fixed' in bootstrap:
        published_mean = _number(bootstrap['mean_optimizer_minus_fixed'])
        if not math.isclose(published_mean, paired_mean, rel_tol=1e-8, abs_tol=1e-10):
            raise ValueError('Bootstrap và bảng cửa sổ không cùng phép so sánh ghép cặp.')
    for key, count in [('paired_pool_windows', len(differences)), ('time_windows', len(by_time))]:
        if key in bootstrap and bootstrap[key] != count:
            raise ValueError('Số quan sát bootstrap không khớp bảng cửa sổ.')
    low = _number(bootstrap.get('ci95_low'), optional=True)
    high = _number(bootstrap.get('ci95_high'), optional=True)
    if (low is None) != (high is None) or (low is not None and low > high):
        raise ValueError('Khoảng bootstrap không hợp lệ.')
    return {
        'mean_optimizer_minus_fixed': paired_mean,
        'ci95_low': low, 'ci95_high': high,
        'time_windows': len(by_time), 'paired_pool_windows': len(differences),
        'repetitions': bootstrap.get('repetitions'),
        'circular_block_windows': bootstrap.get('circular_block_windows'),
        'seed': bootstrap.get('seed'), 'status': bootstrap.get('status', 'not_reported'),
        'not_confirmatory_OOS': bootstrap.get('not_confirmatory_OOS', True),
        'holding_days': next(iter(horizons)) if len(horizons) == 1 else settings.get('panel_holding_days'),
        'fixed_half_width': next(iter(widths)) if len(widths) == 1 else settings.get('fixed_width'),
        'positive_pairs': sum(value > EPSILON for value in differences.values()),
        'negative_pairs': sum(value < -EPSILON for value in differences.values()),
        'median_pair_difference': median(differences.values()),
        'metric_unit': 'fraction_of_initial_capital',
        'aggregation': 'mean of within-window mean paired optimizer minus fixed across pools',
        'interpretation': ('Đây là trung bình chênh lệch ghép cặp theo cửa sổ, khác với hiệu giữa trung vị '
                           'toàn kỳ. Dấu trung bình không có nghĩa optimizer thắng trên mọi pool hoặc mọi cửa sổ. '
                           'Khoảng bootstrap chỉ có tính thăm dò, có điều kiện trên mô hình phí.'),
    }


def research_reconciliation(root):
    manifest = latest_manifest(root)
    payloads = {name: artifact(root, name) for name in FILES}
    if latest_manifest(root) != manifest:
        raise ValueError('Báo cáo mới thay đổi khi đang đọc; vui lòng tải lại để đối chiếu cùng một phiên bản.')
    full_rows = _table(payloads['strategy_returns.csv'],
                       ('pool', 'strategy', 'run_id', 'start', 'end', 'net', 'excess_vs_hodl',
                        'fees', 'il', 'gas', 'rebalance_cost', 'rebalance_count', 'holding_days'))
    gas_rows = _table(payloads['gas_break_even.csv'],
                      ('dynamic_minus_static_before_gas_usd', 'extra_gas_units', 'break_even_gas_usd'))
    monthly_rows = _table(payloads['monthly_returns.csv'],
                          ('pool', 'strategy', 'start', 'end', 'excess_vs_hodl'))
    bootstrap = json.loads(payloads['optimizer_paired_bootstrap.json'])
    settings, spec = manifest.get('settings', {}), manifest.get('spec', {})
    full, gas = _full_period(full_rows), _gas_evidence(gas_rows)
    window = _optimizer_window(monthly_rows, bootstrap, settings)
    return {
        'research_id': manifest['research_id'], 'archive_version': manifest.get('version'),
        'archive_settings': settings, 'archive_spec': spec, 'archive_status': manifest.get('status', {}),
        'metric_unit': 'fraction_of_initial_capital', 'artifact_hashes_verified': True,
        'artifact_files': [row for row in manifest['files'] if row['name'] in FILES],
        'archive_profile': {
            'id': 'research_archive', 'label': 'Nghiên cứu đã lưu',
            'fixed_half_width': settings.get('fixed_width'),
            'volatility_window_days': settings.get('volatility_window_days'),
            'capital': spec.get('capital'), 'gas_usd': spec.get('gas_usd'),
            'dynamic_rule': 'out_of_range', 'vol_scaled_rule': 'initial_width_static',
            'dynamic_description': 'Đặt lại tâm khoảng sau quan sát giá ra ngoài; giữ độ rộng ban đầu.',
            'vol_scaled_description': 'Tính độ rộng từ biến động tại thời điểm mở và giữ vị thế, không cập nhật tuần.',
        },
        'full_period': full, 'gas_evidence': gas, 'optimizer_window': window,
        'claims': [
            {'id': 'strategy_rule', 'status': 'distinct_rules',
             'message': 'Cùng tên khoảng động chưa đủ để so sánh: cần cùng quy tắc điều chỉnh, độ rộng, cửa sổ biến động và kỳ dữ liệu.'},
            {'id': 'H4', 'status': 'conditional_evidence' if gas['informative'] else 'not_testable_with_archive',
             'message': gas['interpretation']},
            {'id': 'cost_accounting', 'status': 'paired_rows_required',
             'message': 'Tính phí, IL, gas và ma sát trên cùng từng dòng. Hiệu của các trung vị độc lập không phải chi phí thực trả.'},
            {'id': 'optimizer_horizon', 'status': 'different_estimands',
             'message': window['interpretation']},
            {'id': 'hedging_scope', 'status': 'archive_unhedged',
             'message': 'Công thức đầy đủ có thêm PnL phòng hộ. Báo cáo nghiên cứu này không triển khai chiến lược hedge; không dùng nó thay cho kết quả workbench có phòng hộ.'},
        ],
        'limitations': [
            'Giá và volume là quan sát; phí LP và thanh khoản nền được mô hình hóa, chưa tái dựng phí NFT thực tế.',
            'Nghiên cứu đã lưu và kết quả giao diện mới có phiên bản, quy tắc và cấu hình riêng; các run cũ được giữ nguyên.',
            'Chưa có đủ dữ liệu hiệu chỉnh pool 2022–2024 để xác nhận kiểm định ngoài mẫu 2025–2026.',
            'Các bảng bổ sung đã tồn tại phải được đọc cùng các kết luận của bài luận; trạng thái hoàn tất mô tả không đồng nghĩa chứng minh giả thuyết.',
        ],
    }

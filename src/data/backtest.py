"""Logged event-time history for an explicitly modelled historical replay."""
from io import BytesIO
import json
import re

import numpy as np
import pandas as pd

from src.data.market import MarketUnavailable, logged_payload
from src.features.point_in_time import validate_history
from src.utils.serialization import digest


class BacktestUnavailable(ValueError):
    pass


def logged_frame(root, name):
    content, _, provenance = logged_payload(root, root / 'data/processed' / (name + '.parquet'))
    frame = pd.read_parquet(BytesIO(content))
    frame['timestamp'] = pd.to_datetime(frame.timestamp, utc=True, errors='raise').dt.as_unit('ns')
    if frame.timestamp.duplicated().any() or not frame.timestamp.is_monotonic_increasing:
        raise MarketUnavailable('Lịch sử chưa được sắp xếp hoặc có timestamp trùng: ' + name)
    return frame.set_index('timestamp'), provenance


def pool_identity(root, pool):
    if not re.fullmatch(r'[a-z0-9-]{1,80}', pool):
        raise BacktestUnavailable('Pool không hợp lệ.')
    path = root / 'data/processed/pool_registry.json'
    if not path.exists():
        raise MarketUnavailable('Chưa có registry/dữ liệu quan sát để backtest; không dùng fixture minh họa.')
    payload, _, provenance = logged_payload(root, path)
    rows = json.loads(payload)['pools']
    found = next((row for row in rows if row['id'] == pool), None)
    if found is None:
        raise BacktestUnavailable('Pool không tồn tại trong registry quan sát.')
    identity = {key: found[key] for key in ['id', 'address', 'base', 'quote', 'fee_rate', 'fee_tier']}
    return identity, provenance


def load_inputs(root, config, settings):
    identity, registry_source = pool_identity(root, config.pool)
    history, history_source = logged_frame(root, 'history_' + config.pool)
    history = validate_history(history)
    tvl, tvl_source = logged_frame(root, 'tvl_' + config.pool)
    if 'tvl_usd' not in tvl or not np.isfinite(tvl.tvl_usd).all() or (tvl.tvl_usd <= 0).any():
        raise MarketUnavailable('TVL lịch sử cần giá trị USD dương, không được thay bằng current snapshot.')
    provenance = {'pool_identity': registry_source, 'history': history_source, 'tvl': tvl_source}
    # Quotes are priced independently, without using the current quote/USD snapshot.
    quote = identity['quote']
    if quote == 'USDT':
        history['quote_usd'] = 1.0
        quote_note = 'USDT/USD = 1 assumption; depeg risk not modelled.'
    elif quote in {'USDC', 'WETH'}:
        symbol = 'usdcusdt' if quote == 'USDC' else 'ethusdt'
        reference, source = logged_frame(root, 'reference_' + symbol + '_1d')
        history['quote_usd'] = reference.price.reindex(history.index)
        provenance['quote_reference'] = source
        quote_note = f'{symbol.upper()} historical close proxy for quote/USD; USDT/USD = 1 assumption.'
    else:
        raise BacktestUnavailable('Chưa có chuỗi quote/USD lịch sử cho pool này.')
    if config.price_source == 'reference':
        symbols = {('WETH', 'USDC'): 'ethusdc', ('WETH', 'USDT'): 'ethusdt', ('USDC', 'USDT'): 'usdcusdt'}
        symbol = symbols.get((identity['base'], quote))
        if symbol is None:
            raise BacktestUnavailable('Chưa có reference WBTC/WETH đúng cặp; không thay WBTC bằng BTC ngầm định.')
        reference, source = logged_frame(root, 'reference_' + symbol + '_1d')
        history['price'] = reference.price.reindex(history.index)
        provenance['price_reference'] = source
    low = pd.Timestamp(config.start, tz='UTC')
    high = pd.Timestamp(config.end, tz='UTC')
    if low >= high:
        raise BacktestUnavailable('Ngày bắt đầu phải trước ngày kết thúc để có ít nhất một kỳ lợi suất.')
    # Cut before feature calculation and hashing; adding future data cannot affect this run.
    history = history.loc[history.index <= high].copy()
    tvl = tvl.loc[tvl.index < high].copy()
    if history.empty or not np.isfinite(history[['price', 'volume_usd', 'quote_usd']]).all().all() or (history.quote_usd <= 0).any():
        raise BacktestUnavailable('Thiếu giá pool hoặc quote/USD trong phạm vi lịch sử yêu cầu.')
    window = config.volatility_window_days
    if len(history) <= window + 2:
        raise BacktestUnavailable(f'Chưa đủ {window+1} giá ngày trước entry để hiệu chỉnh volatility.')
    earliest = history.index[window+1]
    effective_start, effective_end = max(low, earliest), min(high, history.index[-1])
    if effective_start >= effective_end or effective_start not in history.index:
        raise BacktestUnavailable('Khoảng yêu cầu không còn ngày backtest sau warmup; lịch sử bắt đầu ' + str(earliest.date()))
    if not config.allow_partial and (effective_start != low or effective_end != high):
        raise BacktestUnavailable('Khoảng yêu cầu vượt dữ liệu/warmup. Bật allow_partial hoặc đổi khoảng ngày.')
    selected = history.loc[effective_start:effective_end]
    warm = history.loc[:effective_start].tail(window+2)
    required = history.loc[warm.index[0]:effective_end]
    if not required.index.to_series().diff().dropna().eq(pd.Timedelta(days=1)).all():
        raise BacktestUnavailable('Lịch sử có ngày trống trong warmup/backtest; không tự điền hoặc bỏ ngày.')
    # TVL observations get an explicit publication lag, then must predate each decision.
    available = tvl.rename_axis('tvl_timestamp').reset_index()
    available['tvl_available_at'] = available.tvl_timestamp + pd.Timedelta(days=settings['tvl_publication_lag_days'])
    left = pd.DataFrame({'decision_time': selected.index - pd.Timedelta(days=1)})
    merged = pd.merge_asof(left, available[['tvl_timestamp', 'tvl_available_at', 'tvl_usd']],
                           left_on='decision_time', right_on='tvl_available_at', direction='backward',
                           allow_exact_matches=False, tolerance=pd.Timedelta(days=settings['tvl_max_age_days']))
    if merged.tvl_usd.isna().any():
        raise BacktestUnavailable('Thiếu TVL trước quyết định hoặc quá cũ; không lấy TVL/tick hiện tại thay lịch sử.')
    selected = selected.copy()
    for key in ['tvl_timestamp', 'tvl_available_at', 'tvl_usd', 'decision_time']:
        selected[key] = merged[key].to_numpy()
    prior = history.loc[history.index < effective_start].tail(window+1)
    vol = float(np.log(prior.price).diff().dropna().std(ddof=1) * np.sqrt(365))
    mean_volume = float(prior.volume_usd.tail(settings['volume_window_days']).mean())
    hash_rows = lambda frame: frame.reset_index().to_json(orient='records', date_format='iso', double_precision=15)
    data_hash = digest({'identity': identity, 'history_through_end': hash_rows(history),
                        'lagged_tvl': hash_rows(selected[['tvl_usd', 'tvl_timestamp', 'tvl_available_at']]), 'provenance': provenance})
    return {'pool': identity, 'history': history, 'bars': selected, 'vol': vol, 'mean_volume': mean_volume,
            'feature_asof': prior.index[-1].isoformat(), 'data_hash': data_hash, 'provenance': provenance,
            'quote_note': quote_note, 'requested_start': low.isoformat(), 'requested_end': high.isoformat(),
            'start': effective_start.isoformat(), 'end': effective_end.isoformat(),
            'partial': effective_start != low or effective_end != high}

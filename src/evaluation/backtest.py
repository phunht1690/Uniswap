"""Historical price replay with lagged TVL liquidity proxy and USD cash costs."""
import importlib.metadata as metadata

import numpy as np

from src.models.fees import fee_amount
from src.models.price_models import gbm
from src.models.strategies import select_optimum, simulate_strategy, width_grid
from src.models.v3 import pos


BACKTEST_VERSION = 'stage5-historical-replay-v2'


def versions():
    return {name: metadata.version(name) for name in ['numpy', 'pandas']}


def initial_width(inputs, config, settings):
    vol = inputs['vol']
    if config.strategy == 'full':
        return None, {'status': 'fixed_prior_rule'}
    if config.strategy == 'fixed':
        return config.half_width, {'status': 'fixed_prior_rule'}
    horizon = len(inputs['bars'])-1
    if config.strategy in {'vol_scaled', 'dynamic'}:
        width = max(settings['minimum_scaled_width'], settings['scaled_width_multiplier'] * vol * np.sqrt(horizon / 365))
        return width, {'status': 'fixed_volatility_rule', 'decision_horizon_days': horizon}
    paths = gbm(vol, horizon, settings['optimizer_paths'], config.seed)
    volumes = np.full_like(paths.prices, inputs['mean_volume'])
    volumes[:, 0] = 0
    background = config.concentration * float(inputs['bars'].iloc[0].tvl_usd) / 2
    sweep = []
    for width in width_grid(vol, horizon, size=settings['optimizer_grid_points']):
        result = simulate_strategy(paths.prices, volumes, capital=config.capital, gas_usd=config.gas_usd,
                                   fee_rate=inputs['pool']['fee_rate']*(1-config.protocol_fee_fraction),
                                   background_liquidity=background, half_width=width)
        sweep.append({'half_width': float(width), 'exit_prob': float(result.exited.mean()),
                      'excess_vs_hodl': float(result.excess.mean()/config.capital)})
    chosen = select_optimum(sweep, config.risk_max_exit_prob)
    return (None if chosen is None else chosen['half_width']), {
        'status': 'infeasible' if chosen is None else 'feasible', 'forecast_model': 'GBM_mu0',
        'volume_model': 'prior_30d_mean', 'quote_usd_forecast': 'held_at_entry',
        'decision_horizon_days': horizon, 'paths': settings['optimizer_paths'], 'seed': config.seed,
        'feature_asof': inputs['feature_asof'], 'sweep': sweep,
        'selection_uses_realized_future_outcomes': False}


def path_metrics(curve, capital, active, gas, rebalances, width):
    end = curve[-1]
    lp = np.array([row['lp'] for row in curve])
    hodl = np.array([row['hodl'] for row in curve])
    wealth = 1 + lp
    base = np.r_[1., wealth[1:-1]]
    solvent = bool((wealth > 0).all())
    daily = np.diff(np.r_[1., wealth[1:]]) / base if solvent else None
    excess_daily = np.diff(lp-hodl)
    sd = float(np.std(daily, ddof=1)) if daily is not None and len(daily)>1 else 0
    down = float(np.sqrt(np.mean(np.minimum(daily,0)**2))) if daily is not None else 0
    tail = np.sort(excess_daily)[:max(1,int(np.ceil(.05*len(excess_daily))))]
    peak = np.maximum.accumulate(np.r_[1., wealth])
    drawdown = np.r_[1., wealth] / peak - 1
    return {'net': end['lp'], 'hodl_return': end['hodl'], 'excess_vs_hodl': end['lp']-end['hodl'],
            'fees': end['fees'], 'il': end['il'], 'gas': gas/capital, 'rebalance_cost': end['rebalance_cost'],
            'active_share': float(np.mean(active)), 'ever_exited': bool(not all(active)),
            'rebalance_count': rebalances, 'half_width': width, 'holding_days': len(curve)-1,
            'max_drawdown': float(drawdown.min()), 'sharpe_lp_daily': float(np.mean(daily)/sd*np.sqrt(365)) if sd>1e-14 else None,
            'sortino_lp_daily': float(np.mean(daily)/down*np.sqrt(365)) if down>1e-14 else None,
            'q5_daily_excess_increment': float(np.quantile(excess_daily,.05)),
            'cvar5_daily_excess_increment': float(tail.mean()), 'solvent': solvent,
            'gas_units': 2+2*rebalances,
            'break_even_gas_vs_hodl_usd': float((end['fees']-end['il']-end['rebalance_cost'])*capital/(2+2*rebalances))}


def replay(inputs, config, settings, *, rebalance_rule='out_of_range', rolling_vol=False):
    bars = inputs['bars']
    width, decision = initial_width(inputs, config, settings)
    assumptions = {'liquidity_model': 'concentration * lagged_TVL_USD / (2*sqrt(previous_normalized_price)*previous_quote_USD_ratio)',
                   'concentration': config.concentration, 'liquidity_observed': False,
                   'tvl_publication_lag_days': settings['tvl_publication_lag_days'],
                   'tvl_max_age_days': settings['tvl_max_age_days'], 'original_publication_vintages_verified': False,
                   'quote_usd': inputs['quote_note'], 'volume': 'realized daily pool volume; not a CEX volume',
                   'fee_allocation': 'end_of_day_in_range_indicator; intraday crossing and token fee balances not reconstructed',
                   'protocol_fee_fraction': config.protocol_fee_fraction,
                   'protocol_fee_history_verified': False, 'gas': 'flat user assumption, opening 1 + closing 1 + 2 per recenter',
                   'fees_currency': 'USD cash, not reinvested; ignores token fee balance exposure',
                   'rebalance': 'on prior close after an out-of-range observation; new range earns from next bar; fixed initial width',
                   'slippage': 'bps times recentered USD inventory, separate cash cost',
                   'solvency_constraint': 'Not imposed: cash costs can make total wealth negative; Sharpe/Sortino then null.',
                   'feature_asof': inputs['feature_asof'], 'vol_annual_at_entry': inputs['vol'],
                   'mean_volume_at_entry': inputs['mean_volume'], 'optimizer': decision,
                   'historical_ticks_used': False, 'missing_history_filled': False,
                   'test_used_for_hyperparameter_selection': False,
                   'evaluation_status': 'descriptive_historical_replay_not_confirmatory_OOS',
                   'limitations': ['No historical active-L or fee-growth reconstruction', 'TVL reporting lag assumed, not archived publication vintage',
                                   'No historical protocol fee changes, MEV/JIT or market impact', 'Daily endpoints miss intraday fee attribution',
                                   'No 2022-2024 pool price/volume sample for calibration']}
    meta = {'model_version': BACKTEST_VERSION, 'data_kind': 'historical_replay_modelled_fees',
            'data_label': settings['label'], 'assumptions': assumptions, 'data_asof': inputs['end'],
            'provenance': inputs['provenance'], 'effective_start': inputs['start'], 'effective_end': inputs['end'],
            'requested_start': inputs['requested_start'], 'requested_end': inputs['requested_end'],
            'partial_period': inputs['partial'], 'price_source': config.price_source}
    if rebalance_rule == 'weekly':
        assumptions['rebalance'] = 'Weekly after 7 completed bars at the prior close; new range earns next bar.'
    if rolling_vol:
        assumptions['width_update'] = f'Weekly width = 1.5 * annualized trailing {config.volatility_window_days}d log-return std * sqrt(original holding days/365); observations strictly before decision close.'
    if config.strategy == 'optimizer' and decision['status'] == 'infeasible':
        return {'status': 'infeasible', 'returns_unit': 'fraction_of_initial_capital', 'equity_curve': [],
                'summary': None, 'meta': meta}
    p = bars.price.to_numpy()/bars.price.iloc[0]
    q = bars.quote_usd.to_numpy()/bars.quote_usd.iloc[0]
    position = pos(config.capital, 1., width)
    fees, gas, slippage, rebalances, last_reset = 0., config.gas_usd, 0., 0, -config.min_rebalance_gap_days
    active = []
    def point(day):
        inventory = float(position.value(p[day]))*q[day]
        hodl = config.capital*.5*(1+p[day])*q[day]
        return {'timestamp': bars.index[day].isoformat(), 'lp': (inventory+fees-gas-slippage)/config.capital-1,
                'hodl': hodl/config.capital-1, 'fees': fees/config.capital, 'il': (hodl-inventory)/config.capital,
                'gas': gas/config.capital, 'rebalance_cost': slippage/config.capital,
                'price': float(bars.price.iloc[day]), 'p_low': float(position.pl*bars.price.iloc[0]),
                'p_high': float(position.pu*bars.price.iloc[0]), 'quote_usd': float(bars.quote_usd.iloc[day]),
                'rebalance_count': rebalances}
    curve = [point(0)]
    for day in range(1,len(bars)):
        previous = p[day-1]
        out = previous < position.pl or previous > position.pu
        trigger = out if rebalance_rule == 'out_of_range' else day > 1 and (day-1) % 7 == 0
        if (config.strategy == 'dynamic' or rolling_vol) and trigger and day-1-last_reset >= config.min_rebalance_gap_days and rebalances < config.max_rebalances:
            value_quote = float(position.value(previous))
            slippage += value_quote*q[day-1]*config.rebalance_slippage_bps/10000
            if rolling_vol:
                past = inputs['history'].loc[inputs['history'].index < bars.index[day-1]].price.tail(config.volatility_window_days+1)
                rolling = float(np.log(past).diff().dropna().std(ddof=1)*np.sqrt(365))
                width = max(settings['minimum_scaled_width'], settings['scaled_width_multiplier']*rolling*np.sqrt((len(bars)-1)/365))
            position = pos(value_quote, previous, width)
            gas += 2*config.gas_usd
            rebalances += 1
            last_reset = day-1
        in_range = bool(position.pl <= p[day] <= position.pu)
        active.append(in_range)
        background = config.concentration*float(bars.tvl_usd.iloc[day])/(2*np.sqrt(previous)*q[day-1])
        fees += float(fee_amount(float(bars.volume_usd.iloc[day]), inputs['pool']['fee_rate']*(1-config.protocol_fee_fraction),
                                 position.L, background, in_range))
        if day == len(bars)-1:
            gas += config.gas_usd
        curve.append(point(day))
    return {'status': 'ok', 'returns_unit': 'fraction_of_initial_capital', 'equity_curve': curve,
            'summary': path_metrics(curve, config.capital, active, gas, rebalances, width), 'meta': meta}

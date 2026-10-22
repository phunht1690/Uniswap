"""Versioned RangeLab scenarios. Legacy engine/contracts remain reproducible."""
import copy
import json
from pathlib import Path

import numpy as np

from api.app_schemas import WorkbenchRecord, WorkbenchRequest
from api.schemas import SimulationRequest
from src.evaluation.metrics import summarize
from src.models.fees import observed_volumes
from src.models.policies import simulate_policy
from src.models.price_models import gbm, garch, stationary_bootstrap
from src.models.service import SimulationInputError
from src.models.strategies import select_optimum, simulate_strategy, width_grid
from src.models.v3 import pos
from src.utils.serialization import atomic_json, digest

VERSION = 'rangelab-workbench-v3'


class WorkbenchService:
    def __init__(self, service):
        self.service = service
        self.root = service.state_dir

    def get(self, run_id):
        return WorkbenchRecord.model_validate_json((self.root/'outputs/workbench'/(run_id+'.json')).read_text(encoding='utf-8'))

    def context(self, request):
        source=self.service
        if request.market_snapshot_id:
            from src.data.live_snapshot import PinnedLiveService
            source=PinnedLiveService(self.service,request.market_snapshot_id)
        base = source.simulate(request.config)
        config = SimulationRequest.model_validate(base.meta.assumptions['effective_config'])
        registry = source.market.registry()
        if registry is None:
            raise SimulationInputError('RangeLab yêu cầu dữ liệu pool quan sát. Dashboard minh họa ở /legacy.')
        pool = registry[0][config.pool]
        history, _, _ = source.market.history(config.pool, config.calibration_asof, required=config.price_model!='gbm')
        if config.price_model=='gbm':
            paths = gbm(config.vol_annual,config.horizon_days,config.n_paths,config.seed)
        elif config.price_model=='bootstrap':
            paths = stationary_bootstrap(history,config.calibration_asof,config.horizon_days,config.n_paths,config.seed,config.bootstrap_mean_block_days)
        else:
            paths = garch(history,config.calibration_asof,config.horizon_days,config.n_paths,config.seed)
        vol = config.vol_annual if config.price_model=='gbm' else float(paths.daily_sd[0,1]*np.sqrt(365))
        settings=self.service.settings['research']
        if request.volume_daily_override_usd is not None:
            volumes=np.full_like(paths.prices,request.volume_daily_override_usd);volumes[:,0]=0
            info={'method':'user_fixed_daily_USD_assumption','mean_volume_usd':request.volume_daily_override_usd}
        else:
            estimation=settings['estimation'];simulation=settings['simulation']
            volumes,info=observed_volumes(paths,history,config.calibration_asof,pool['volume_24h_usd'],
                lookback_days=estimation.get('volume_fit_lookback_days',180),min_regime_rows=estimation.get('min_volume_regime_rows',10),
                factor_cap=simulation['volume_factor_cap'],shock_scale=simulation['volume_shock_scale'])
        common=dict(capital=config.capital,gas_usd=config.gas_usd,fee_rate=pool['fee_rate'],
            background_liquidity=pool['background_liquidity_normalized_usd'],min_gap=config.min_rebalance_gap_days,
            max_rebalances=config.max_rebalances,slippage_bps=config.rebalance_slippage_bps,
            rebalance_gas_multiplier=settings['html_compatibility']['dynamic_rebalance_gas_multiplier'])
        return base,config,pool,paths,vol,volumes,info,common

    def run(self, request, persist=True):
        base,config,pool,paths,vol,volumes,volume_info,common=self.context(request)
        effective=request.model_copy(update={'config':config})
        identity=effective.model_dump(mode='json')
        if identity['market_snapshot_id'] is None:identity.pop('market_snapshot_id') # Preserve pre-live run identities.
        run_id=digest({'version':VERSION,'base_run_id':base.meta.run_id,'request':identity})
        path=self.root/'outputs/workbench'/(run_id+'.json')
        if path.exists():return self.get(run_id).result
        settings=self.service.settings['research'];optsettings=settings['optimizer']
        def evaluate(width,policy=request.rebalance_policy,trace=False,full=False):
            kw=dict(common,half_width=width,trace_index=config.path_index if trace else None)
            result=simulate_strategy(paths.prices,volumes,mode='full',**kw) if full else simulate_policy(paths.prices,volumes,policy=policy,delta_threshold=request.delta_threshold,**kw)
            point=summarize(result,config.capital,width,pool['p0'])
            point.update(hodl_return=float(np.mean(result.hodl)/config.capital-1),inventory_return=float(np.mean(result.inventory)/config.capital-1),
                hedge_pnl=float(np.mean(result.hedge_pnl)/config.capital) if result.hedge_pnl is not None else 0.,
                feasible=point['exit_prob']<=config.risk_max_exit_prob)
            return result,point
        grid=width_grid(vol,config.horizon_days,config.min_half_width,config.max_half_width,size=optsettings['grid_points'],
            width_floor=optsettings['auto_max_width_floor_log'],sigma_multiplier=optsettings['auto_max_width_sigma_multiplier'])
        sweep=[evaluate(float(width))[1] for width in grid]
        optimum=select_optimum(sweep,config.risk_max_exit_prob)
        scaled=max(.03,1.5*vol*np.sqrt(config.horizon_days/365))
        strategies=[]
        for name,label,width,policy,full in [('full','Toàn dải',None,'none',True),('fixed','Cố định ±15% log',.15,'none',False),
                ('vol_scaled','Theo biến động (1,5σ√T)',scaled,'none',False),('dynamic','Tái cân bằng hàng tuần',scaled,'weekly',False)]:
            point=evaluate(width,policy,full=full)[1];strategies.append(dict(id=name,label=label,**point))
        trace=[];distribution=[];ticks=None;efficiency=None
        if optimum is not None:
            selected,point=evaluate(optimum['half_width'],trace=True)
            trace=selected.trace;strategies.append(dict(id='optimizer',label='Range tối ưu · '+request.rebalance_policy,**point))
            distribution=[{'lp_return':float(selected.net[i]),'hodl_return':float(selected.hodl[i]/config.capital-1),
                'excess':float(selected.excess[i]/config.capital)} for i in range(config.n_paths)]
            # Display-only aligned ticks. Continuous-range valuation is explicitly retained.
            prices=np.array([optimum['p_low'],optimum['p_high']]);ratios=(1/prices if pool['inverted'] else prices)*10**(pool['decimals1']-pool['decimals0'])
            raw=np.log(ratios)/np.log(1.0001);spacing={100:1,500:10,3000:60,10000:200}[pool['fee_tier']]
            ticks={'lower':int(np.floor(raw.min()/spacing)*spacing),'upper':int(np.ceil(raw.max()/spacing)*spacing),'spacing':spacing,
                'applied_to_valuation':False,'note':'Tick tham khảo được làm tròn ra ngoài; định giá dùng range liên tục trên lưới.'}
            ticks.update(price_low_tick=ticks['upper'] if pool['inverted'] else ticks['lower'],
                         price_high_tick=ticks['lower'] if pool['inverted'] else ticks['upper'])
            efficiency=float(pos(config.capital,1,optimum['half_width']).L/pos(config.capital,1,None).L)
        meta=copy.deepcopy(base.meta.model_dump(mode='json'))
        meta.update(run_id=run_id,base_run_id=base.meta.run_id,model_version=VERSION,optimization_status='feasible' if optimum else 'infeasible',
            messages=[] if optimum else ['Không có range thỏa giới hạn rời range. Điều chỉnh thời gian, độ rộng hoặc ngưỡng rủi ro.'])
        meta['assumptions'].update(effective_config=config.model_dump(mode='json'),volume_method=volume_info,
            rebalance_policy=request.rebalance_policy,delta_threshold=request.delta_threshold,
            hedging='Daily discrete short of LP base inventory; opening and terminal hedge liquidation charged gas and turnover bps, cash-settled PnL, no funding/borrow/margin model. Not continuous hedging.' if request.rebalance_policy=='hedged' else None,
            optimizer={'grid_points':len(grid),'objective':'mean_excess_vs_hodl','constraint':'empirical_ever_exit_at_daily_closes','selected_policy':request.rebalance_policy},
            policy_timing='Fees first; weekly/threshold recenter at current close for subsequent bars; hedge marked daily. No terminal LP recenter.',
            pool={**meta['assumptions']['pool'],'chain_id':pool.get('chain_id',1),'network':pool.get('network','eth')},
            limitations=['Forward scenario with frozen current active liquidity; not a historical backtest.','Quote/USD fixed, including WETH quote.','Daily endpoints miss intraday crossing; no MEV/JIT/funding/market impact.','No solvency constraint. Costs can exceed capital.','Annualized returns are extrapolations, not protocol APR.'])
        result=dict(optimum=optimum,sweep=sweep,strategies=strategies,pnl_path=trace,sample_paths=(paths.prices[:30]*pool['p0']).tolist(),
            selected_price_path=(paths.prices[config.path_index]*pool['p0']).tolist(),
            distribution=distribution,liquidity_ticks=[t.model_dump() for t in base.liquidity_ticks],aligned_ticks=ticks,capital_efficiency=efficiency,
            mean_daily_volume_usd=float(volumes[:,1:].mean()),effective_vol_annual=vol,meta=meta)
        if persist:atomic_json(path,WorkbenchRecord(config=effective,result=result).model_dump(mode='json'))
        return result

    def pinned_context(self, run_id):
        record=self.get(run_id)
        if record.result['meta']['model_version']!=VERSION:
            raise SimulationInputError('Phiên bản mô hình của run khác engine hiện tại. Chạy tối ưu hóa mới trước khi stress/sensitivity; run cũ vẫn xem và xuất được.')
        context=self.context(record.config)
        if context[0].meta.data_hash!=record.result['meta']['data_hash'] or context[0].meta.run_id!=record.result['meta']['base_run_id']:
            raise SimulationInputError('Dữ liệu, cấu hình engine hoặc phiên bản thư viện khác snapshot của run. Chạy tối ưu hóa mới trước khi stress/sensitivity; run cũ vẫn xem và xuất được.')
        if record.result['optimum'] is None:raise SimulationInputError('Run không có range khả thi để kiểm tra rủi ro.')
        return record,context

    def stress(self, request):
        record,context=self.pinned_context(request.run_id)
        _,config,pool,_,vol,_,_,common=context
        horizon=config.horizon_days;n=config.n_paths;t=np.arange(horizon+1,dtype=float)/horizon
        # Conditional GBM log bridge: terminal shock is fixed, volatility changes intermediate occupation/fees.
        rng=np.random.Generator(np.random.PCG64(config.seed));w=np.c_[np.zeros(n),np.cumsum(rng.standard_normal((n,horizon)),axis=1)]
        bridge=w-w[:,-1,None]*t[None,:]
        logp=t[None,:]*np.log1p(request.price_shock_pct/100)+bridge*vol*request.volatility_multiplier/np.sqrt(365)
        prices=np.exp(logp);volumes=np.full_like(prices,record.result['mean_daily_volume_usd']);volumes[:,0]=0
        common.update(gas_usd=config.gas_usd*request.gas_multiplier)
        selected=simulate_policy(prices,volumes,policy=record.config.rebalance_policy,delta_threshold=record.config.delta_threshold,
            half_width=record.result['optimum']['half_width'],**common)
        point=summarize(selected,config.capital,record.result['optimum']['half_width'],pool['p0'])
        terminal=pool['p0']*(1+request.price_shock_pct/100)
        point.update(lp_value=float(np.mean(selected.net+1)*config.capital),hodl_value=float(np.mean(selected.hodl)),
            inventory_value=float(np.mean(selected.inventory)),il_usd=float(np.mean(selected.il)),
            hedge_pnl_usd=float(np.mean(selected.hedge_pnl)) if selected.hedge_pnl is not None else 0,
            terminal_price=terminal,initial_range_status='below' if terminal<point['p_low'] else 'above' if terminal>point['p_high'] else 'inside')
        return {'scenario':request.model_dump(mode='json'),'metrics':point,'meta':{'version':VERSION,'base_run_id':request.run_id,'seed':config.seed,'n_paths':n,
            'model':'conditional_GBM_log_bridge_fixed_terminal_shock','range_reoptimized':False,'fixed_daily_volume_usd':record.result['mean_daily_volume_usd'],
            'note':'Cú sốc cuối kỳ cố định, volatility đổi đường đi và thời gian tạo phí. Range ban đầu giữ nguyên; policy đã chọn vẫn hoạt động. Quote/USD và active-L giữ cố định.'}}

    def sensitivity(self, request):
        record,_=self.pinned_context(request.run_id)
        rows=[]
        for vol in np.linspace(request.low_vol_pct,request.high_vol_pct,request.steps):
            config=record.config.config.model_copy(update={'price_model':'gbm','vol_annual':float(vol/100)})
            req=record.config.model_copy(update={'config':config,'volume_daily_override_usd':record.result['mean_daily_volume_usd']})
            result=self.run(req)
            rows.append({'vol_annual':float(vol/100),'optimum':result['optimum'],'run_id':result['meta']['run_id']})
        return {'rows':rows,'meta':{'base_run_id':request.run_id,'model':'gbm','fixed_daily_volume_usd':record.result['mean_daily_volume_usd'],
            'same_seed_and_paths':True,'range_reoptimized_per_vol':True,'note':'Quét giả định GBM, tối ưu lại trên cùng lưới quy tắc, không phải kiểm định ngoài mẫu.'}}

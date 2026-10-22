"""Reproducible descriptive research exports; no tuning on test outcomes."""
import argparse
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path

import numpy as np
import pandas as pd

from api.schemas import BacktestRequest
from src.data.backtest import load_inputs
from src.data.market import MarketCatalog
from src.data.ethereum import specs as ethereum_pool_specs
from src.evaluation.backtest_service import BacktestService
from src.evaluation.econometrics import fit_regressions, paired_block_interval, stationarity_rows
from src.utils.config import ROOT, state_directory
from src.utils.serialization import atomic_json, digest


RESEARCH_VERSION='stage5-descriptive-research-v3'


def partition(timestamp):
    year=pd.Timestamp(timestamp).year
    return 'train' if 2022<=year<=2023 else 'validation' if year==2024 else 'test' if 2025<=year<=2026 else 'warmup_or_other'


def study_spec():
    return {'capital':50000.,'gas_usd':15.,'concentration':3.,'protocol_fee_fraction':0.,'seed':42,
            'strategies':['full','fixed','vol_scaled','dynamic','optimizer'],
            'selection':'prior rules only; no model/hyperparameter selection from test returns',
            'numeraire':'USD proxies with historical quote exposure; USDT/USD parity assumed',
            'pool_scope':'Original eight Ethereum pools; added RangeLab pools require a separately declared study.'}


def run_research(root):
    service=BacktestService(root);settings=service.settings;spec=study_spec()
    registry=MarketCatalog(root).registry()
    if registry is None:raise ValueError('Cần registry quan sát trước khi chạy research.')
    pools=[row['id'] for row in ethereum_pool_specs() if row['id'] in registry[0]]
    full=[];monthly=[];panel=[];equity=[];characteristics=[];coverage=[];adf=[];input_hashes={};sensitivity=[];robustness=[]
    end=max(pd.Timestamp(registry[0][name]['data_asof']).normalize() for name in pools).date()
    for pool in pools:
        print('Research pool:',pool,flush=True)
        base=BacktestRequest(pool=pool,start='2022-01-01',end=end)
        inputs=load_inputs(root,base,settings)
        history=inputs['history'];bars=inputs['bars'];input_hashes[pool]=inputs['data_hash']
        identity=inputs['pool'];pair=identity['base']+'/'+identity['quote']
        characteristics.append({'pool':pool,'pair':pair,'fee_bps':identity['fee_rate']*10000,'history_days':len(history),
                 'start':history.index[0].isoformat(),'end':history.index[-1].isoformat(),'mean_daily_volume_usd':float(history.volume_usd.mean()),
                 'median_daily_volume_usd':float(history.volume_usd.median()),'data_kind':'observed_history'})
        for part in ['train','validation','test']:
            rows=sum(partition(t)==part for t in history.index)
            coverage.append({'pool':pool,'partition':part,'price_volume_days':rows,
                            'calibration_eligible':part!='test' and rows>31,'test_used_for_selection':False})
        adf+=stationarity_rows(history,pool)
        for strategy in spec['strategies']:
            cfg=base.model_copy(update={'strategy':strategy})
            result=service.run(cfg)
            if result['summary'] is None:continue
            full.append({'pool':pool,'strategy':strategy,**result['summary'],'start':inputs['start'],'end':inputs['end'],
                         'run_id':result['meta']['run_id'],'data_kind':'historical_replay_modelled_fees'})
            if pool==pools[0]:
                equity += [{'pool':pool,'strategy':strategy,**row} for row in result['equity_curve']]
        # All entry points and widths were fixed before reading their realized outcomes.
        holding=settings['panel_holding_days']
        for index in range(0,len(bars)-holding,holding):
            start=bars.index[index].date();finish=bars.index[index+holding].date()
            window=base.model_copy(update={'start':start,'end':finish,'allow_partial':False})
            prepared=load_inputs(root,window,settings)
            common={'pool':pool,'pair':pair,'start':str(start),'end':str(finish),'partition':partition(start),
                    'vol_annual':prepared['vol'],'log_volume_usd':float(np.log1p(prepared['mean_volume'])),
                    'fee_bps':identity['fee_rate']*10000,'feature_asof':prepared['feature_asof'],
                    'data_kind':'historical_replay_modelled_fees'}
            for strategy in spec['strategies']:
                result=service.run(window.model_copy(update={'strategy':strategy}),persist=False)
                if result['summary'] is not None:
                    monthly.append({**common,'strategy':strategy,**result['summary'],'run_id':result['meta']['run_id']})
                    if strategy=='dynamic':
                        width=float(result['summary']['half_width'])
                        panel.append({**common,**result['summary'],'strategy':strategy,'width':width,'log_width':float(np.log(width)),
                                      'rebalance_policy':1,'run_id':result['meta']['run_id']})
            for width in settings['panel_widths']:
                result=service.run(window.model_copy(update={'strategy':'fixed','half_width':width}),persist=False)
                panel.append({**common,**result['summary'],'strategy':'fixed','width':width,'log_width':float(np.log(width)),
                              'rebalance_policy':0,'run_id':result['meta']['run_id']})
        # Sensitivity is descriptive; do not choose a winning setting from these tables.
        for capital in [5000.,50000.,500000.]:
            for gas in [0.,15.,100.]:
                for gap in [1,7,30]:
                    for strategy in ['fixed','dynamic','static_matched_width']:
                        updates={'capital':capital,'gas_usd':gas,'min_rebalance_gap_days':gap,
                                 'strategy':'fixed' if strategy=='static_matched_width' else strategy}
                        if strategy=='static_matched_width':
                            updates['half_width']=max(settings['minimum_scaled_width'],settings['scaled_width_multiplier']*inputs['vol']*np.sqrt((len(bars)-1)/365))
                        result=service.run(base.model_copy(update=updates),persist=False)
                        sensitivity.append({'pool':pool,'capital':capital,'gas_usd':gas,'gap_days':gap,'strategy':strategy,
                                            **result['summary'],'data_kind':'historical_replay_modelled_fees'})
        for concentration in [1.,3.,10.]:
            for haircut in [0.,.25]:
                for strategy in ['fixed','dynamic','optimizer']:
                    result=service.run(base.model_copy(update={'strategy':strategy,'concentration':concentration,'protocol_fee_fraction':haircut}),persist=False)
                    if result['summary'] is not None:
                        robustness.append({'pool':pool,'scenario':'liquidity_protocol_fee','strategy':strategy,'concentration':concentration,
                                           'protocol_fee_fraction':haircut,**result['summary']})
        for slippage in [0.,5.,25.]:
            for strategy in ['fixed','dynamic']:
                result=service.run(base.model_copy(update={'strategy':strategy,'rebalance_slippage_bps':slippage}),persist=False)
                robustness.append({'pool':pool,'scenario':'slippage_bps','strategy':strategy,'slippage_bps':slippage,**result['summary']})
        robust_start=history.index[61].date()
        for window in [7,30,60]:
            for source in ['pool','reference']:
                if pair=='WBTC/WETH' and source=='reference':continue
                result=service.run(base.model_copy(update={'strategy':'vol_scaled','start':robust_start,'allow_partial':False,'volatility_window_days':window,'price_source':source}),persist=False)
                if result['summary'] is not None:
                    robustness.append({'pool':pool,'scenario':'vol_window_price_reference','strategy':'vol_scaled',
                                       'volatility_window_days':window,'price_source':source,'start':str(robust_start),'end':str(end),**result['summary']})
    print('Fitting descriptive panel and quantile models...',flush=True)
    panel=pd.DataFrame(panel);monthly=pd.DataFrame(monthly)
    coeff,diagnostics=fit_regressions(panel,settings)
    interval=paired_block_interval(monthly,settings['bootstrap_repetitions'],settings['bootstrap_block_windows'],settings['seed'])
    full=pd.DataFrame(full);sens=pd.DataFrame(sensitivity)
    pivot=sens.pivot(index=['pool','capital','gas_usd','gap_days'],columns='strategy',values='excess_vs_hodl').reset_index()
    pivot['dynamic_minus_fixed']=pivot.dynamic-pivot.fixed
    pivot['dynamic_minus_matched_static']=pivot.dynamic-pivot.static_matched_width
    zero=sens.loc[sens.gas_usd==0].pivot(index=['pool','capital','gap_days'],columns='strategy',values=['net','gas_units'])
    breaks=[]
    for idx,row in zero.iterrows():
        gain=(row[('net','dynamic')]-row[('net','static_matched_width')])*idx[1]
        units=row[('gas_units','dynamic')]-row[('gas_units','static_matched_width')]
        breaks.append({'pool':idx[0],'capital':idx[1],'gap_days':idx[2],
                       'benchmark':'static_same_initial_width','dynamic_minus_static_before_gas_usd':gain,'extra_gas_units':units,
                       'break_even_gas_usd':gain/units if units>0 else None,
                       'status':'positive_threshold' if units>0 and gain>0 else 'dynamic_not_better_at_zero_gas' if gain<=0 else 'no_extra_gas_units'})
    source_hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                   for folder in ['src','config'] for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in {'.py','.yaml'}}
    numeric={name:metadata.version(name) for name in ['numpy','pandas','scipy','statsmodels','matplotlib']}
    research_id=digest({'version':RESEARCH_VERSION,'spec':spec,'settings':settings,'data':input_hashes,'code':source_hashes,'versions':numeric})
    directory=root/'outputs/research'/research_id;directory.mkdir(parents=True,exist_ok=True)
    risk=[]
    for (pool,strategy),g in monthly.groupby(['pool','strategy']):
        values=np.sort(g.excess_vs_hodl.to_numpy())
        risk.append({'pool':pool,'strategy':strategy,'windows':len(values),'mean_excess':float(values.mean()),
                     'q5_terminal_30d_excess':float(np.quantile(values,.05)),
                     'cvar5_terminal_30d_excess':float(values[:max(1,int(np.ceil(.05*len(values))))].mean()),
                     'positive_excess_share':float(np.mean(values>0))})
    tables={'pool_characteristics':pd.DataFrame(characteristics),'strategy_returns':full,'monthly_returns':monthly,'monthly_risk_summary':pd.DataFrame(risk),
            'width_panel':panel,'regressions':coeff,'stationarity_adf':pd.DataFrame(adf),'sensitivity':sens,
            'dynamic_vs_fixed':pivot,'gas_break_even':pd.DataFrame(breaks),'robustness':pd.DataFrame(robustness),
            'split_coverage':pd.DataFrame(coverage),'daily_equity':pd.DataFrame(equity)}
    for name,table in tables.items():
        table['result_label']='Observed historical inputs; modelled LP fees; descriptive, not confirmed OOS'
        table.to_csv(directory/(name+'.csv'),index=False,float_format='%.12g')
    atomic_json(directory/'regression_diagnostics.json',diagnostics)
    atomic_json(directory/'optimizer_paired_bootstrap.json',interval)
    from src.evaluation.figures import export_figures
    export_figures(directory,tables,root)
    train_rows=sum(r['price_volume_days'] for r in coverage if r['partition'] in {'train','validation'})
    study_status={'status':'completed_descriptive_replay','confirmatory_oos_status':'unavailable_missing_2022_2024_pool_calibration',
          'test_used_for_hyperparameter_selection':False,'train_validation_pool_days':train_rows,
          'pool_count':len(pools),'full_period_runs':len(full),'monthly_strategy_rows':len(monthly),'panel_rows':len(panel),
          'panel_time_windows':int(panel.start.nunique()),'effective_start':full.start.min(),'effective_end':full.end.max(),
          'fee_model':'lagged TVL proxy, concentration=3; not reconstructed historical active L',
          'protocol_fee_history':'not verified; 0% and 25% scenario sensitivity',
          'original_vintage_availability':'not verified; event-time lagged replay from latest downloaded history',
          'quote_usd':'historical ETHUSDT/USDCUSDT proxies, USDT/USD assumed 1',
          'optimizer_paired_interval':interval,'regression_status':diagnostics['status']}
    atomic_json(directory/'study_status.json',study_status)
    report=research_report(study_status,full,diagnostics)
    (directory/'research_report.md').write_text(report,encoding='utf-8')
    files=[{'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'kind':p.suffix.lstrip('.')}
           for p in sorted(directory.iterdir()) if p.is_file()]
    manifest={'research_id':research_id,'version':RESEARCH_VERSION,'data_kind':'historical_replay_modelled_fees',
              'status':study_status,'spec':spec,'settings':settings,'input_hashes':input_hashes,'code_hashes':source_hashes,
              'numerical_versions':numeric,'files':files}
    atomic_json(directory/'manifest.json',manifest)
    atomic_json(root/'outputs/research/latest.json',manifest)
    print(json.dumps({'research_id':research_id,**study_status},ensure_ascii=False),flush=True)
    return manifest


def research_report(status,full,diagnostics):
    lines=['# Báo cáo nghiên cứu — historical replay có giả định','',
      '**Giá/volume lịch sử quan sát; phí LP ước tính từ TVL trễ. Không phải lợi nhuận LP thực tế đã tái dựng.**','',
      f"Phạm vi sau warmup: {status['effective_start']} → {status['effective_end']}; {status['pool_count']} pool. Có {status['panel_rows']} dòng panel, {status['panel_time_windows']} cửa sổ thời gian.",'',
      '## Khả năng diễn giải','',
      'Dữ liệu pool giá/volume chỉ có từ cuối 2025. Không có tập hiệu chỉnh pool 2022–2024 nên chưa thể xác nhận optimizer ngoài mẫu theo thiết kế gốc. Các quy tắc và lưới được cố định trước khi tính lợi suất; không dùng lợi suất test để chọn hyperparameter. Các hồi quy dưới đây là mô tả trên historical replay có giả định, không phải thiết kế nhận diện nhân quả.','',
      '## Kết quả theo chiến lược','',
      '| Chiến lược | Median ΔR | Median phí | Median IL |','|---|---:|---:|---:|']
    for strategy,group in full.groupby('strategy'):
        lines.append(f"| {strategy} | {group.excess_vs_hodl.median():.2%} | {group.fees.median():.2%} | {group.il.median():.2%} |")
    lines+=['','Các giá trị là trên vốn ban đầu cho toàn kỳ, không phải APR. So sánh giữa pool chịu ảnh hưởng mạnh từ giả định thanh khoản nền và protocol fee. Xem robustness.csv trước khi diễn giải dấu lợi nhuận.','',
      '## RQ và giả thuyết','',
      '- H1/RQ1: bảng strategy_returns và fee_decomposition tách fees, IL, gas, slippage; ΔR=fees−IL−gas−slippage. Chưa thể khẳng định lợi nhuận LP thực tế khi active L lịch sử thiếu.',
      '- H2/RQ2: width_panel dùng 4 độ rộng cố định và cửa sổ 30 ngày không chồng lấn theo từng chiến lược. Đồ thị width_tradeoff mô tả phí/IL/active và Sharpe của ΔR theo cửa sổ; không dùng chọn tham số test.',
      '- H3/RQ3: pool FE bỏ fee tier vì bất biến theo pool; mô hình pair FE riêng ước lượng liên hệ fee tier giữa các pool cùng cặp. Volatility/mean volume trễ trước entry; rebalance_policy là quy tắc dự kiến, không dùng số rebalance tương lai làm predictor. OLS dùng Driscoll–Kraay HAC; quantile 0.1/0.5/0.9 có time-block bootstrap. Số thời kỳ ít nên inference chỉ thăm dò.',
      '- H4/RQ4: sensitivity so sánh vốn × gas × min_gap, cả fixed ±0.2 và static có cùng độ rộng ban đầu với dynamic. gas_break_even dùng static cùng độ rộng để tách chi phí recenter. Threshold âm nghĩa là dynamic đã kém static ngay khi gas bằng 0; không diễn giải như mức gas khả thi.',
      '- H5/RQ5: optimizer dùng GBM và volume trước entry để chọn range theo ràng buộc, không nhìn giá tương lai; CI chênh lệch optimizer−fixed dùng circular block bootstrap theo cửa sổ chung cho mọi pool. Đây là bằng chứng có điều kiện trên fee model, chưa phải xác nhận OOS.','',
      '## Giả định và giới hạn','',
      'Active L proxy = C×TVL trễ/(2√P_norm×quote_USD_ratio), C=3 không hiệu chỉnh; kiểm tra C=1/3/10. TVL có publication lag giả định 1 ngày, join chỉ trước quyết định và giới hạn stale 7 ngày. Không dùng tick snapshot hiện tại cho quá khứ. Không có archived publication vintage nên chỉ kiểm soát event-time leakage, chưa bảo đảm data-vintage point-in-time.',
      '', 'Phí theo volume pool thực tế và trạng thái trong range tại close, không tái dựng crossing intraday hay fee-growth theo tick. Phí chuyển thành USD cash, không tái đầu tư. Protocol fee lịch sử chưa xác minh; sensitivity haircut 25% là kịch bản, không phải cấu hình quan sát. Gas phẳng; slippage bps; chưa có MEV/JIT hay market impact. USDT/USD giả định 1; WETH và USDC được định giá bằng reference lịch sử, không giữ current USD price ngược về quá khứ.','',
      '## Tái lập','',
      '`python manage.py research` sinh manifest có hash dữ liệu đầu vào, code, settings và phiên bản thư viện. Mỗi backtest API lưu config/result và run_id trong outputs/backtests. `/api/v1/runs/{id}` đọc lại; `/api/v1/backtests/{id}/curve.csv` xuất curve. Hình PNG và bảng CSV có cùng nhãn mô hình.','',
      'Nguồn phương pháp: [Uniswap v3 whitepaper](https://app.uniswap.org/whitepaper-v3.pdf), [statsmodels covariance](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html), [QuantReg](https://www.statsmodels.org/stable/generated/statsmodels.regression.quantile_regression.QuantReg.fit.html), [pandas merge_asof](https://pandas.pydata.org/docs/reference/api/pandas.merge_asof.html), [protocol fee](https://developers.uniswap.org/docs/protocols/protocol-fee/concepts/fees).','',
      'Công cụ mô phỏng nghiên cứu, không phải lời khuyên đầu tư.','']
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--state-dir',type=Path)
    args=parser.parse_args();run_research(args.state_dir or state_directory())


if __name__=='__main__':main()

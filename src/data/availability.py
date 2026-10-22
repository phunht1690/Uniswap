"""Suggest calendar-contiguous replay windows by coverage, never by returns."""
import pandas as pd
from api.app_schemas import BacktestComparison
from src.data.backtest import logged_frame,load_inputs,BacktestUnavailable
from src.data.market import MarketUnavailable
from src.utils.config import load_config


def backtest_availability(root,pool,window=14):
    frame,_=logged_frame(root,'history_'+pool)
    groups=frame.index.to_series().diff().ne(pd.Timedelta(days=1)).cumsum()
    segments=[part for _,part in frame.groupby(groups)]
    segments.sort(key=lambda part:(len(part),part.index[-1]),reverse=True)
    missing=len(pd.date_range(frame.index.min(),frame.index.max(),freq='D').difference(frame.index))
    result={'pool':pool,'history_rows':len(frame),'missing_days':missing,'requested_window_days':window,
        'selection':'longest_contiguous_calendar_window_then_latest_end; no returns used','suggestion':None}
    settings=load_config('backtest')
    errors=[]
    for candidate_window in dict.fromkeys([window,7]):
        for segment in segments:
            if len(segment)<candidate_window+3:continue
            start=segment.index[candidate_window+1].date();end=segment.index[-1].date()
            cfg=BacktestComparison(pool=pool,start=start,end=end,volatility_window_days=candidate_window,allow_partial=False)
            try:
                inputs=load_inputs(root,cfg,settings)
                result['suggestion']={'start':str(start),'end':str(end),'warmup_start':str(segment.index[0].date()),
                    'volatility_window_days':candidate_window,'holding_days':len(inputs['bars'])-1,'window_changed':candidate_window!=window}
                return result
            except (BacktestUnavailable,MarketUnavailable) as exc:errors.append(str(exc))
    result['reason']=errors[0] if errors else 'Không có đoạn ngày liên tiếp đủ warmup và một kỳ replay; cần thêm dữ liệu.'
    return result

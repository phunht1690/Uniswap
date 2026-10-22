"""RangeLab pages use these explicit scenario, comparison and export endpoints."""
import csv
import io
import json
from typing import Annotated

import numpy as np
import pandas as pd
from fastapi import APIRouter,HTTPException,Path,Request,Query
from fastapi.responses import Response

from api.app_schemas import WorkbenchRequest,StressRequest,SensitivityRequest,BacktestComparison
from src.data.backtest import BacktestUnavailable,logged_frame
from src.data.market import MarketUnavailable
from src.data.availability import backtest_availability
from src.evaluation.comparison import ComparisonService
from src.evaluation.pdf_report import pdf_bytes
from src.models.workbench import WorkbenchService
from src.models.service import SimulationInputError,UnknownPool

router=APIRouter(prefix='/api/v1')
RunId=Annotated[str,Path(pattern=r'^[0-9a-f]{64}$')]


def guarded(fn):
    try:return fn()
    except FileNotFoundError as exc:raise HTTPException(404,detail='Chưa có dữ liệu hoặc run này trên máy chủ. Chạy mô phỏng/ingestion trước.') from exc
    except MarketUnavailable as exc:raise HTTPException(503,detail=str(exc)) from exc
    except (SimulationInputError,UnknownPool,BacktestUnavailable,ValueError) as exc:raise HTTPException(400,detail=str(exc)) from exc
    except OSError as exc:raise HTTPException(503,detail='Không đọc/ghi được dữ liệu hoặc cache. Kiểm tra quyền thư mục dự án.') from exc


def service(request):return WorkbenchService(request.app.state.service)


@router.post('/workbench/run')
def run(body:WorkbenchRequest,request:Request):return guarded(lambda:service(request).run(body))


@router.get('/workbench/runs/{run_id}')
def record(run_id:RunId,request:Request):return guarded(lambda:service(request).get(run_id))


@router.post('/workbench/stress')
def stress(body:StressRequest,request:Request):return guarded(lambda:service(request).stress(body))


@router.post('/workbench/sensitivity')
def sensitivity(body:SensitivityRequest,request:Request):return guarded(lambda:service(request).sensitivity(body))


@router.get('/workbench/runs/{run_id}/export.json')
def export_json(run_id:RunId,request:Request):
    obj=guarded(lambda:service(request).get(run_id)).model_dump(mode='json')
    return Response(json.dumps(obj,ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="rangelab-{run_id[:12]}.json"'})


@router.get('/workbench/runs/{run_id}/summary.pdf')
def summary_pdf(run_id:RunId,request:Request):
    obj=guarded(lambda:service(request).get(run_id))
    data=guarded(lambda:pdf_bytes(obj))
    return Response(data,media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="rangelab-summary-{run_id[:12]}.pdf"'})


@router.get('/workbench/runs/{run_id}/methodology.pdf')
def methods_pdf(run_id:RunId,request:Request):
    obj=guarded(lambda:service(request).get(run_id))
    return Response(guarded(lambda:pdf_bytes(obj,methodology=True)),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="rangelab-methodology-{run_id[:12]}.pdf"'})


@router.get('/pools/{pool_id}/history')
def history(pool_id:str,request:Request,days:int=30):
    if days not in {7,30,90,365}:raise HTTPException(400,detail='days phải là 7, 30, 90 hoặc 365.')
    def read():
        registry=request.app.state.service.market.registry()
        if registry is None or pool_id not in registry[0]:raise UnknownPool('Pool không tồn tại.')
        frame,provenance=logged_frame(request.app.state.service.state_dir,'history_'+pool_id)
        cutoff=frame.index.max()-pd.Timedelta(days=days-1);window=frame.loc[frame.index>=cutoff]
        returns=np.log(window.price).diff().dropna();valid=len(returns)>1 and window.index.to_series().diff().dropna().eq(pd.Timedelta(days=1)).all()
        rows=[{'timestamp':idx.isoformat(),'price':float(row.price),'volume_usd':float(row.volume_usd)} for idx,row in window.iterrows()]
        return {'pool':pool_id,'rows':rows,'stats':{'min':float(window.price.min()),'max':float(window.price.max()),'mean':float(window.price.mean()),
            'vol_annual':float(returns.std(ddof=1)*np.sqrt(365)) if valid else None},
            'meta':{'source':'geckoterminal','kind':'observed_daily_aggregator','requested_days':days,'available_rows':len(window),'start':window.index.min().isoformat(),'end':window.index.max().isoformat(),
                'history_start':frame.index.min().isoformat(),'history_end':frame.index.max().isoformat(),'missing_intervals':len(pd.date_range(window.index.min(),window.index.max(),freq='D').difference(window.index)), 'provenance':provenance}}
    return guarded(read)


@router.post('/backtests/compare')
def compare(body:BacktestComparison,request:Request):return guarded(lambda:ComparisonService(request.app.state.service.state_dir).run(body))


@router.get('/pools/{pool_id}/backtest-availability')
def availability(pool_id:Annotated[str,Path(pattern='^[a-z0-9-]{1,80}$')],request:Request,window:Annotated[int,Query(ge=7,le=90)]=14):
    return guarded(lambda:backtest_availability(request.app.state.service.state_dir,pool_id,window))


@router.get('/backtests/comparisons/{run_id}')
def comparison(run_id:RunId,request:Request):return guarded(lambda:ComparisonService(request.app.state.service.state_dir).get(run_id))


@router.get('/backtests/comparisons/{run_id}/export.csv')
def comparison_csv(run_id:RunId,request:Request):
    result=guarded(lambda:ComparisonService(request.app.state.service.state_dir).get(run_id))['result']
    rows=[]
    for strategy in result['strategies']:
        for row in strategy['equity_curve']:
            rows.append({'run_id':run_id,'strategy':strategy['id'],'label':strategy['label'],**row,'capital_usd':result['meta']['effective_config']['capital'],
                'data_kind':result['meta']['data_kind'],'effective_start':result['meta']['effective_start'],'effective_end':result['meta']['effective_end']})
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(rows[0]) if rows else ['run_id','strategy','timestamp'])
    writer.writeheader();writer.writerows(rows)
    return Response('\ufeff'+stream.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="rangelab-backtest-{run_id[:12]}.csv"'})

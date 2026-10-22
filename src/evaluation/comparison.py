"""Five-strategy historical comparison on a shared point-in-time sample."""
import copy
import json
import numpy as np

from api.app_schemas import BacktestComparison
from api.schemas import BacktestRequest
from src.data.backtest import load_inputs
from src.evaluation.backtest import replay,path_metrics,versions
from src.utils.config import load_config
from src.utils.serialization import atomic_json,digest

VERSION='rangelab-comparison-v1'
LABELS={'full':'Toàn dải','fixed':'Cố định ±15% log','vol_scaled':'Volatility rolling 14 ngày · cập nhật tuần','dynamic':'Tái cân bằng hàng tuần','hodl':'HODL 50:50','optimizer':'Tối ưu tại entry'}


class ComparisonService:
    def __init__(self,root):self.root=root;self.settings=load_config('backtest')

    def get(self,run_id):return json.loads((self.root/'outputs/comparisons'/(run_id+'.json')).read_text(encoding='utf-8'))

    def run(self,request):
        inputs=load_inputs(self.root,request,self.settings)
        run_id=digest({'version':VERSION,'config':request.model_dump(mode='json'),'data_hash':inputs['data_hash'],'settings':self.settings,'versions':versions()})
        path=self.root/'outputs/comparisons'/(run_id+'.json')
        if path.exists():return self.get(run_id)['result']
        rows=[];meta=None
        for name in dict.fromkeys(request.strategies):
            cfg=BacktestRequest.model_validate({key:value for key,value in request.model_dump().items() if key!='strategies'})
            cfg=cfg.model_copy(update={'strategy':'full' if name=='hodl' else name})
            result=replay(inputs,cfg,self.settings,rebalance_rule='weekly' if name in {'dynamic','vol_scaled'} else 'out_of_range',rolling_vol=name=='vol_scaled')
            meta=result['meta']
            if name=='hodl':
                curve=[dict(row,lp=row['hodl'],fees=0.,il=0.,gas=0.,rebalance_cost=0.,rebalance_count=0) for row in result['equity_curve']]
                result.update(equity_curve=curve,summary=path_metrics(curve,request.capital,[True]*(len(curve)-1),0.,0,None))
                result['summary'].update(active_share=None,ever_exited=None,gas_units=0,break_even_gas_vs_hodl_usd=None)
            label=LABELS[name]
            if name=='fixed':label=f'Cố định ±{request.half_width*100:g}% log'
            if name=='vol_scaled':label=f'Volatility rolling {request.volatility_window_days} ngày · cập nhật tuần'
            rows.append({'id':name,'label':label,**result})
        result={'strategies':rows,'meta':{**meta,'run_id':run_id,'model_version':VERSION,'effective_config':request.model_dump(mode='json'),
            'data_hash':inputs['data_hash'],'seed':request.seed,'ranking':'ex_post_descriptive_not_investment_recommendation',
            'rules':{'fixed':'Symmetric log half-width fixed at entry','vol_scaled':'Lagged rolling volatility, weekly update','dynamic':'Initial vol-scaled width, weekly recenter','hodl':'50:50 entry tokens, no gas assumption'}}}
        atomic_json(path,{'kind':'backtest_comparison','config':request.model_dump(mode='json'),'result':result})
        return result

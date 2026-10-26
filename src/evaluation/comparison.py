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

VERSION='rangelab-comparison-v2'
PROFILE_NOTE='Khớp quy tắc và tham số; cần kiểm tra dữ liệu và thời gian để tái lập cùng số liệu. Không tự mở rộng phạm vi nghiên cứu tám pool.'
COMMON_PRESET={'capital':50000.,'gas_usd':15.,'min_rebalance_gap_days':7,'max_rebalances':52,
               'rebalance_slippage_bps':0.,'concentration':3.,'protocol_fee_fraction':0.,
               'risk_max_exit_prob':.4,'seed':42,'price_source':'pool','allow_partial':True}
PRESETS=[
    {'id':'research','label':'Quy tắc nghiên cứu','description':'Khoảng cố định w = 0,20; volatility 30 ngày. Khoảng theo volatility giữ độ rộng tại entry; khoảng động chỉ dời sau quan sát ngoài khoảng. '+PROFILE_NOTE,
     'config':{**COMMON_PRESET,'half_width':.2,'volatility_window_days':30,'strategy_mode':'research'}},
    {'id':'weekly','label':'Quy tắc cập nhật hằng tuần','description':'Biến thể giao diện trước đây: khoảng cố định w = 0,15; volatility 14 ngày. Khoảng động dời hằng tuần; khoảng theo volatility cập nhật độ rộng hằng tuần. '+PROFILE_NOTE,
     'config':{**COMMON_PRESET,'half_width':.15,'volatility_window_days':14,'strategy_mode':'weekly'}},
]


def comparison_presets():
    """Rules are presets, never a claim that current data reproduce an archive."""
    return {'default_id':'research','model_version':VERSION,'presets':copy.deepcopy(PRESETS),'note':PROFILE_NOTE}


def configuration_profile(request):
    actual=request.model_dump(mode='json')
    checked=list(PRESETS[0]['config'])
    matched=next((preset for preset in PRESETS if all(actual[key]==value for key,value in preset['config'].items())),None)
    return {'id':matched['id'] if matched else 'custom',
            'label':matched['label'] if matched else 'Tham số tùy chỉnh',
            'matches_preset':matched is not None,'checked_fields':checked,
            'description':PROFILE_NOTE if matched else 'Tham số hiện tại không khớp trọn bộ preset nghiên cứu hoặc hằng tuần. Đây là cấu hình tùy chỉnh; cần kiểm tra riêng quy tắc, dữ liệu và thời gian trước khi đối chiếu kết quả lưu trữ.'}


def strategy_rule(name,request):
    weekly=request.strategy_mode=='weekly'
    rebalance='weekly' if weekly else 'out_of_range'
    return {'rebalance_rule':rebalance if name=='dynamic' else 'weekly' if name=='vol_scaled' and weekly else 'none',
            'width_rule':{'full':'full','fixed':'fixed','vol_scaled':'rolling_weekly' if weekly else 'volatility_at_entry',
                          'dynamic':'volatility_at_entry','optimizer':'optimizer_at_entry','hodl':'hodl'}[name],
            'volatility_window_days':request.volatility_window_days,
            'half_width':request.half_width if name=='fixed' else None}


def strategy_label(name,request):
    labels={'full':'Toàn dải','fixed':f'Cố định w = {request.half_width:g} log',
            'vol_scaled':f'Volatility {request.volatility_window_days} ngày · '+('cập nhật tuần' if request.strategy_mode=='weekly' else 'giữ độ rộng tại entry'),
            'dynamic':'Tái cân bằng hằng tuần' if request.strategy_mode=='weekly' else 'Tái cân bằng khi ra ngoài khoảng',
            'hodl':'HODL 50:50','optimizer':'Tối ưu tại entry'}
    return labels[name]


class ComparisonService:
    def __init__(self,root):self.root=root;self.settings=load_config('backtest')

    def get(self,run_id):return json.loads((self.root/'outputs/comparisons'/(run_id+'.json')).read_text(encoding='utf-8'))

    def run(self,request):
        inputs=load_inputs(self.root,request,self.settings)
        run_id=digest({'version':VERSION,'config':request.model_dump(mode='json'),'data_hash':inputs['data_hash'],'settings':self.settings,'versions':versions()})
        path=self.root/'outputs/comparisons'/(run_id+'.json')
        if path.exists():return self.get(run_id)['result']
        rows=[];meta=None;rule_map={};rule_labels={}
        for name in dict.fromkeys(request.strategies):
            cfg=BacktestRequest.model_validate({key:value for key,value in request.model_dump().items() if key not in {'strategies','strategy_mode'}})
            cfg=cfg.model_copy(update={'strategy':'full' if name=='hodl' else name})
            weekly=request.strategy_mode=='weekly'
            result=replay(inputs,cfg,self.settings,rebalance_rule='weekly' if weekly and name in {'dynamic','vol_scaled'} else 'out_of_range',
                          rolling_vol=weekly and name=='vol_scaled')
            meta=result['meta']
            if name=='hodl':
                curve=[dict(row,lp=row['hodl'],fees=0.,il=0.,gas=0.,rebalance_cost=0.,rebalance_count=0) for row in result['equity_curve']]
                result.update(equity_curve=curve,summary=path_metrics(curve,request.capital,[True]*(len(curve)-1),0.,0,None))
                result['summary'].update(active_share=None,ever_exited=None,gas_units=0,break_even_gas_vs_hodl_usd=None)
            label=strategy_label(name,request);rules=strategy_rule(name,request)
            rule_map[name]=rules;rule_labels[name]=label
            rows.append({'id':name,'label':label,'rules':rules,**result})
        result={'strategies':rows,'meta':{**meta,'run_id':run_id,'model_version':VERSION,'effective_config':request.model_dump(mode='json'),
            'data_hash':inputs['data_hash'],'seed':request.seed,'ranking':'ex_post_descriptive_not_investment_recommendation',
            'strategy_mode':request.strategy_mode,'configuration_profile':configuration_profile(request),
            'rules':rule_labels,'strategy_rules':rule_map}}
        atomic_json(path,{'kind':'backtest_comparison','config':request.model_dump(mode='json'),'result':result})
        return result

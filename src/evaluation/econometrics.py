"""Descriptive panel/quantile regressions with explicit identification limits."""
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tsa.stattools import adfuller


def block_indices(size, block, rng):
    starts = rng.integers(0,size,size=int(np.ceil(size/block)))
    return np.concatenate([(start+np.arange(block))%size for start in starts])[:size]


def paired_block_interval(frame, repetitions=999, block=2, seed=42):
    """Resample common time windows jointly across pools, preserving pairing."""
    pivot=frame.pivot(index=['pool','start'],columns='strategy',values='excess_vs_hodl').dropna(subset=['fixed','optimizer'])
    by_time=(pivot.optimizer-pivot.fixed).groupby(level='start').mean().sort_index()
    if len(by_time)<4:
        return {'status':'insufficient_time_windows','time_windows':len(by_time)}
    rng=np.random.default_rng(seed)
    values=by_time.to_numpy()
    means=np.array([values[block_indices(len(values),block,rng)].mean() for _ in range(repetitions)])
    return {'status':'exploratory_model_conditional','mean_optimizer_minus_fixed':float(values.mean()),
            'ci95_low':float(np.quantile(means,.025)),'ci95_high':float(np.quantile(means,.975)),
            'time_windows':len(values),'paired_pool_windows':len(pivot),'repetitions':repetitions,
            'circular_block_windows':block,'seed':seed,'not_confirmatory_OOS':True}


def design(frame, effect='pool', include_fee=False):
    names=['vol_annual','log_volume_usd','log_width','rebalance_policy'] + (['fee_bps'] if include_fee else [])
    columns={'const':np.ones(len(frame))};scaling={}
    for name in names:
        values=frame[name].to_numpy(dtype=float);sd=float(values.std())
        if sd>1e-12:
            columns['z_'+name]=(values-values.mean())/sd
            scaling[name]={'mean':float(values.mean()),'sd':sd}
    x=pd.DataFrame(columns,index=frame.index)
    dummies=pd.get_dummies(frame[effect],prefix=effect,drop_first=True,dtype=float)
    return pd.concat([x,dummies],axis=1).astype(float),scaling


def fit_regressions(panel, settings):
    frame=panel.sort_values(['start','pool','width','rebalance_policy']).reset_index(drop=True)
    if len(frame)<40 or frame.start.nunique()<5:
        return pd.DataFrame(),{'status':'insufficient_sample','rows':len(frame),'time_windows':int(frame.start.nunique())}
    y=frame.excess_vs_hodl.to_numpy(dtype=float)
    time=pd.factorize(frame.start,sort=True)[0]
    coefficients=[];diagnostics={'status':'descriptive_only','rows':len(frame),'time_windows':int(frame.start.nunique()),
        'sample_partitions':sorted(frame.partition.unique().tolist()),
        'outcome_is_modelled_fee_replay':True,'causal_identification':False,
        'fee_tier_in_pool_FE':'omitted: time invariant fee tier is collinear with pool fixed effects',
        'small_T_warning':'About one year and few common time windows; HAC/bootstrap inference is exploratory.',
        'models':{}}
    for model,effect,fee in [('pool_FE_DK','pool',False),('pair_FE_fee_DK','pair',True)]:
        x,scaling=design(frame,effect,fee)
        if np.linalg.matrix_rank(x.to_numpy())<x.shape[1]:
            diagnostics['models'][model]={'status':'rank_deficient'};continue
        fit=sm.OLS(y,x).fit(cov_type='hac-groupsum',cov_kwds={'time':time,'maxlags':settings['hac_lags'],
                                   'use_correction':'cluster','df_correction':True},use_t=True)
        ci=fit.conf_int()
        for i,name in enumerate(x.columns):
            coefficients.append({'model':model,'term':name,'coefficient':float(fit.params.iloc[i]),'std_error':float(fit.bse.iloc[i]),
                                 'p_value':float(fit.pvalues.iloc[i]),'ci95_low':float(ci.iloc[i,0]),'ci95_high':float(ci.iloc[i,1]),
                                 'inference':'Driscoll-Kraay HAC, exploratory small T','n':len(frame)})
        bp=het_breuschpagan(fit.resid,x)
        diagnostics['models'][model]={'status':'fit','r_squared':float(fit.rsquared),'rank':x.shape[1],
             'condition_number_standardized':float(np.linalg.cond(x)), 'scaling':scaling,
             'breusch_pagan_p':float(bp[1]),'covariance':'hac-groupsum','hac_lags':settings['hac_lags'],
             'vif':{name:float(variance_inflation_factor(x.to_numpy(),i)) for i,name in enumerate(x.columns) if name.startswith('z_')}}
    x,scaling=design(frame,'pool',False)
    unique=np.unique(time);rng=np.random.default_rng(settings['seed'])
    resamples=[np.concatenate([np.flatnonzero(time==t) for t in unique[block_indices(len(unique),settings['bootstrap_block_windows'],rng)]])
               for _ in range(settings['quantile_bootstrap_repetitions'])]
    for quantile in settings['quantiles']:
        model=f'quantile_{quantile:.1f}_pool_FE'
        with warnings.catch_warnings(record=True) as recorded:
            fit=sm.QuantReg(y,x).fit(q=quantile,vcov='robust',max_iter=3000,p_tol=1e-6)
            samples=[];failures=0
            for indices in resamples:
                xx=x.iloc[indices]
                if np.linalg.matrix_rank(xx.to_numpy())<xx.shape[1]:failures+=1;continue
                candidate=sm.QuantReg(y[indices],xx).fit(q=quantile,vcov='robust',max_iter=1500,p_tol=1e-6)
                if candidate.iterations>=1500 or not np.isfinite(candidate.params).all():failures+=1;continue
                samples.append(candidate.params.to_numpy())
        converged=fit.iterations<3000
        diagnostics['models'][model]={'status':'fit' if converged else 'iteration_limit','iterations':int(fit.iterations),
             'bootstrap_successes':len(samples),'bootstrap_failures':failures,'warnings':len(recorded),
             'bootstrap_method':'circular common-time blocks, all pools/widths sampled together', 'scaling':scaling}
        for i,name in enumerate(x.columns):
            enough=converged and len(samples)>=max(2,settings['quantile_bootstrap_repetitions']//2)
            values=np.array(samples)[:,i] if enough else None
            coefficients.append({'model':model,'term':name,'coefficient':float(fit.params.iloc[i]),
                'std_error':float(values.std(ddof=1)) if enough else None,'p_value':None,
                'ci95_low':float(np.quantile(values,.025)) if enough else None,'ci95_high':float(np.quantile(values,.975)) if enough else None,
                'inference':'time-block bootstrap, exploratory; no IID p-values','n':len(frame)})
    return pd.DataFrame(coefficients),diagnostics


def stationarity_rows(history, pool):
    returns=np.log(history.price).diff()
    features={'log_volume_usd':np.log1p(history.volume_usd).shift(1),
              'vol_annual':returns.rolling(30,min_periods=30).std(ddof=1).shift(1)*np.sqrt(365)}
    rows=[]
    for feature,values in features.items():
        clean=values.dropna()
        if len(clean)<50 or clean.std()<1e-12:
            rows.append({'pool':pool,'feature':feature,'status':'insufficient_or_constant','n':len(clean)});continue
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore',message='adfuller currently returns a plain tuple.*',category=FutureWarning)
            fit=adfuller(clean,maxlag=min(7,len(clean)//10),regression='c',autolag='AIC')
        rows.append({'pool':pool,'feature':feature,'status':'descriptive_latest_vintage','n':len(clean),
                     'adf_statistic':float(fit[0]),'p_value':float(fit[1]),'lags':int(fit[2])})
    return rows

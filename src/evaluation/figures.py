"""Standalone research PNGs with units and model limitations on each figure."""
import os

import numpy as np
import pandas as pd


def export_figures(directory,tables,root):
    os.environ.setdefault('MPLCONFIGDIR',str(root/'outputs/.matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter
    from src.data.market import MarketCatalog
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.18})
    colors={'full':'#64748b','fixed':'#06b6d4','vol_scaled':'#8b5cf6','dynamic':'#ef7d37','optimizer':'#15976b'}
    note='Observed historical prices/volume; LP fees MODELLED from lagged TVL. C=3, flat gas; descriptive, not confirmed OOS.'
    def finish(fig,name,caption=note):
        fig.text(.02,.015,caption,fontsize=8,color='#475569',wrap=True)
        fig.tight_layout(rect=(0,.06,1,.97));fig.savefig(directory/(name+'.png'),dpi=160,bbox_inches='tight');plt.close(fig)
    equity=tables['daily_equity'].copy();equity['timestamp']=pd.to_datetime(equity.timestamp,utc=True)
    fig,ax=plt.subplots(figsize=(11,5))
    for strategy,g in equity.groupby('strategy'):
        ax.plot(g.timestamp,g.lp,label=strategy,color=colors[strategy],lw=1.7)
    first=equity[equity.strategy=='fixed'];ax.plot(first.timestamp,first.hodl,label='HODL',color='#111827',ls='--')
    ax.yaxis.set_major_formatter(PercentFormatter(1));ax.set(title='WETH/USDC 0.05% — cumulative return on initial capital',ylabel='Return',xlabel='UTC date');ax.legend(ncol=3)
    finish(fig,'equity_curves')
    full=tables['strategy_returns'];means=full.groupby('strategy')[['fees','il','gas','rebalance_cost','excess_vs_hodl']].median().reindex(colors)
    fig,ax=plt.subplots(figsize=(11,5));x=np.arange(len(means));bottom=np.zeros(len(means))
    ax.bar(x,means.fees,label='Estimated fees',color='#15976b',width=.6)
    for col,label,color in [('il','IL vs HODL','#d65c72'),('gas','Gas','#64748b'),('rebalance_cost','Slippage','#f3b43f')]:
        ax.bar(x,-means[col],bottom=bottom,label=label,color=color,width=.6);bottom-=means[col].to_numpy()
    ax.scatter(x,means.excess_vs_hodl,color='#111827',label='Median excess return',zorder=4)
    ax.set_xticks(x,means.index);ax.yaxis.set_major_formatter(PercentFormatter(1));ax.axhline(0,color='gray',lw=.6)
    ax.set(title='Fee / IL / cost decomposition — medians across 8 pools',ylabel='Fraction of initial capital');ax.legend(ncol=3)
    finish(fig,'fee_decomposition',note+' Component medians need not sum to median excess.')
    panel=tables['width_panel'];fixed=panel[panel.strategy=='fixed']
    fig,axes=plt.subplots(1,2,figsize=(11,4.8))
    for pair,g in fixed.groupby('pair'):
        mean=g.groupby('width')[['fees','il','excess_vs_hodl','active_share']].mean()
        axes[0].plot(mean.index,mean.excess_vs_hodl,'o-',label=pair)
        stats=g.groupby('width').excess_vs_hodl.agg(['mean','std'])
        axes[1].plot(stats.index,np.where(stats['std']>1e-12,stats['mean']/stats['std']*np.sqrt(365/30),np.nan),'o-',label=pair)
    for ax in axes:ax.set_xscale('log');ax.set_xlabel('Half width in log price');ax.legend(fontsize=8)
    axes[0].yaxis.set_major_formatter(PercentFormatter(1));axes[0].set(title='30-day excess return vs width',ylabel='Mean excess return')
    axes[1].set(title='Window excess mean / standard deviation',ylabel='Annualized ratio, exploratory')
    finish(fig,'width_tradeoff')
    fig,ax=plt.subplots(figsize=(11,5));g=first
    ax.plot(g.timestamp,g.price,color='#111827',label='Observed close')
    ax.fill_between(g.timestamp,g.p_low,g.p_high,alpha=.16,color=colors['fixed'],label='Fixed range, chosen at entry')
    opt=equity[equity.strategy=='optimizer'];ax.plot(opt.timestamp,opt.p_low,color=colors['optimizer'],ls=':',label='Optimizer entry bounds')
    ax.plot(opt.timestamp,opt.p_high,color=colors['optimizer'],ls=':')
    ax.set(title='WETH/USDC — price and ex ante ranges',ylabel='USDC per WETH',xlabel='UTC date');ax.legend()
    finish(fig,'price_ranges')
    monthly=tables['monthly_returns'];opts=monthly[monthly.strategy=='optimizer']
    fig,ax=plt.subplots(figsize=(8,5))
    for pair,g in opts.groupby('pair'):ax.scatter(g.vol_annual,g.half_width,label=pair,alpha=.7,s=22)
    ax.set(title='Optimizer width vs pre-entry volatility — 30-day windows',xlabel='Volatility, annual fraction',ylabel='Chosen half width, log price');ax.legend()
    finish(fig,'optimal_width_volatility')
    coeff=tables['regressions'];focus=coeff[(coeff.model=='pool_FE_DK')&coeff.term.str.startswith('z_')].copy()
    fig,ax=plt.subplots(figsize=(10,4.5));x=np.arange(len(focus))
    if len(focus):
        ax.errorbar(focus.coefficient,x,xerr=[np.maximum(0,focus.coefficient-focus.ci95_low),np.maximum(0,focus.ci95_high-focus.coefficient)],fmt='o',capsize=4,color='#15976b')
        ax.set_yticks(x,focus.term.str.replace('z_','',regex=False));ax.axvline(0,color='gray',ls='--')
    ax.set(title='Pool fixed effects OLS — Driscoll–Kraay 95% intervals',xlabel='Excess return per one sample SD of predictor')
    finish(fig,'regression_coefficients',note+' Small number of time windows: intervals are exploratory.')
    sens=tables['sensitivity'];part=sens[(sens.pool=='weth-usdc-500')&(sens.capital==5000)]
    fig,ax=plt.subplots(figsize=(9,5))
    for (strategy,gap),g in part.groupby(['strategy','gap_days']):
        if strategy=='fixed' and gap!=7:continue
        ax.plot(g.gas_usd,g.excess_vs_hodl,'o-',label=f'{strategy}, gap {gap}d')
    ax.yaxis.set_major_formatter(PercentFormatter(1));ax.set(title='WETH/USDC — capital $5,000: sensitivity to flat gas',xlabel='USD per gas unit',ylabel='Full-period excess return');ax.legend(fontsize=8)
    finish(fig,'gas_sensitivity')
    catalog=MarketCatalog(root);registry=catalog.registry();pool=registry[0]['weth-usdc-500'];ticks,_,_=catalog.ticks(pool)
    fig,ax=plt.subplots(figsize=(11,4.8))
    for left,right in zip(ticks,ticks[1:]):
        low,high=sorted([left['price'],right['price']]);ax.bar(low,left['liquidity'],width=high-low,align='edge',color='#3fa5b5',linewidth=0)
    ax.axvline(pool['p0'],color='#111827',ls='--',label='Snapshot price');ax.legend()
    ax.set(title=f"Current liquidity snapshot — WETH/USDC, block {pool['block_number']}",xlabel='USDC/WETH',ylabel='Normalized L (initial USD units, not TVL)')
    finish(fig,'current_tick_liquidity','CURRENT snapshot only, not used for historical backtest fees. Raw tick interval convention preserved when price is inverted.')

"""Scheduled recentering, inventory threshold and discrete delta hedging."""
import numpy as np

from src.models.fees import fee_amount
from src.models.strategies import StrategyResult,simulate_strategy
from src.models.v3 import pos,Position


def simulate_policy(prices,volumes,*,policy='none',delta_threshold=.1,**kwargs):
    if policy=='none':return simulate_strategy(prices,volumes,mode='fixed',**kwargs)
    if policy=='out_of_range':return simulate_strategy(prices,volumes,mode='dynamic',**kwargs)
    if policy not in {'weekly','threshold','hedged'}:raise ValueError('Unknown rebalance policy')
    capital=kwargs['capital'];gas_usd=kwargs['gas_usd'];width=kwargs['half_width'];trace_index=kwargs.get('trace_index')
    n,steps=prices.shape;position=pos(np.full(n,capital),np.ones(n),width)
    fees=np.zeros(n);gas=np.full(n,gas_usd*(2 if policy=='hedged' else 1));cost=np.zeros(n)
    counts=np.zeros(n,dtype=int);last=np.full(n,-kwargs.get('min_gap',7));active_counts=np.zeros(n);exited=np.zeros(n,dtype=bool)
    hedge_pnl=np.zeros(n);hedge_qty=-position.amounts(np.ones(n))[0] if policy=='hedged' else np.zeros(n)
    background=np.broadcast_to(np.asarray(kwargs['background_liquidity'],float),prices.shape)
    slippage=kwargs.get('slippage_bps',0)/10000;trace=[]
    if policy=='hedged':cost+=np.abs(hedge_qty)*slippage
    if trace_index is not None:trace.append({'day':0,'lp':-float(gas[trace_index]+cost[trace_index])/capital,'hodl':0.})
    for day in range(1,steps):
        price=prices[:,day];active=(price>=position.pl)&(price<=position.pu)
        fees+=fee_amount(volumes[:,day],kwargs['fee_rate'],position.L,background[:,day],active)
        active_counts+=active;exited|=~active
        hedge_pnl+=hedge_qty*(price-prices[:,day-1])
        if policy=='hedged':
            terminal=day==steps-1
            reset=np.ones(n,dtype=bool) if terminal else (counts<kwargs.get('max_rebalances',52))
            replacement=np.zeros(n) if terminal else -position.amounts(price)[0]
            traded=np.abs(replacement-hedge_qty)*price
            reset&=traded>1e-12
            cost[reset]+=traded[reset]*slippage;gas[reset]+=gas_usd
            if not terminal:counts[reset]+=1
            hedge_qty=np.where(reset,replacement,hedge_qty)
        else:
            x,y=position.amounts(price);base_share=x*price/(x*price+y)
            trigger=np.full(n,day%7==0) if policy=='weekly' else np.abs(base_share-.5)>=delta_threshold
            reset=trigger&((day-last)>=kwargs.get('min_gap',7))&(counts<kwargs.get('max_rebalances',52))
            # No terminal recenter: it cannot earn a subsequent bar's fees.
            if day==steps-1:reset[:]=False
            if np.any(reset):
                value=position.value(price);replacement=pos(value[reset],price[reset],width)
                low,high,liquidity=position.pl.copy(),position.pu.copy(),position.L.copy()
                low[reset],high[reset],liquidity[reset]=replacement.pl,replacement.pu,replacement.L
                position=Position(low,high,liquidity)
                cost[reset]+=value[reset]*slippage
                gas[reset]+=kwargs.get('rebalance_gas_multiplier',2)*gas_usd;counts[reset]+=1;last[reset]=day
        if trace_index is not None:
            i=trace_index;wealth=position.value(price)[i]+fees[i]-gas[i]-cost[i]+hedge_pnl[i]
            trace.append({'day':day,'lp':float(wealth/capital-1),'hodl':float((1+price[i])/2-1)})
    inventory=position.value(prices[:,-1]);hodl=capital/2*(1+prices[:,-1])
    excess=inventory+fees-gas-cost+hedge_pnl-hodl
    net=(inventory+fees-gas-cost+hedge_pnl)/capital-1
    return StrategyResult(fees,gas,hodl-inventory,excess,net,active_counts/(steps-1),exited,counts,cost,inventory,hodl,trace,hedge_pnl)

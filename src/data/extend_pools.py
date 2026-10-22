"""Acquire additional design-listed pools without replacing existing snapshots."""
import hashlib
import json
from pathlib import Path

import pandas as pd

from src.data import defillama,ethereum,geckoterminal
from src.data.common import Acquisition,atomic_bytes,coverage_row
from src.data.quality import audit
from src.utils.config import state_directory
from src.utils.serialization import atomic_json


def run(root):
    root=Path(root);path=root/'data/processed/pool_registry.json'
    old=json.loads(path.read_text(encoding='utf-8'));known={row['id'] for row in old['pools']}
    context=Acquisition(root,attempts=2,timeout=25)
    found=[];coverage=[];failures=[]
    try:
        tokens={'ARB':'0x912ce59144191c1204e64559fe8253a0e49e6548','WETH':'0x82af49447d8a07e3bd95bd0d56f35241523fbab1'}
        eth_specs=[{**p,'fee_tier':10000,'fee_rate':.01,'id':p['id'].rsplit('-',1)[0]+'-10000',
                    'label':p['base']+'/'+p['quote']+' 1%'} for p in ethereum.specs() if p['fee_tier'] in {3000}]
        arb_specs=[{'id':f'arb-weth-{fee}','label':f'ARB/WETH {fee/10000:g}% (Arbitrum)',
                    'base':'ARB','quote':'WETH','base_address':tokens['ARB'],'quote_address':tokens['WETH'],
                    'fee_tier':fee,'fee_rate':fee/1e6,'chain':'Arbitrum'} for fee in [500,3000,10000]]
        batches=[(eth_specs,ethereum.TOKENS,'https://ethereum-rpc.publicnode.com',1,'eth'),
                 (arb_specs,tokens,'https://arb1.arbitrum.io/rpc',42161,'arbitrum')]
        for specs,tokens_map,endpoint,chain,network in batches:
            specs=[s for s in specs if s['id'] not in known]
            if not specs:continue
            print('Discover',network,[s['id'] for s in specs],flush=True)
            try:
                rows,rpc,entry=ethereum.fetch(context,endpoint,pool_specs=specs,tokens=tokens_map,
                    expected_chain_id=chain,network=network,snapshot_name='extra_'+network+'_snapshot',gas_name='extra_'+network+'_gas')
                coverage.append(entry)
            except Exception as exc:
                failures.append({'network':network,'error':str(exc)});print(failures[-1],flush=True);continue
            active=[]
            for pool in rows:
                try:
                    if int(pool['liquidity_raw'])<=0:raise ValueError('No active liquidity at snapshot')
                    info=geckoterminal.metadata(context,pool)
                    pool.update({k:info[k] for k in ['tvl_usd','volume_24h_usd','quote_usd']})
                    pool['context_available_at']=info['data_asof']
                    _,normalized,entry=ethereum.fetch_ticks(context,rpc,pool,pool['quote_usd'])
                    pool['background_liquidity_normalized_usd']=normalized
                    active.append(pool);coverage.append(entry)
                    print('Snapshot ready',pool['id'],flush=True)
                except Exception as exc:
                    failures.append({'pool':pool['id'],'error':str(exc)});print(failures[-1],flush=True)
            for pool in active:
                try:
                    _,entry=geckoterminal.fetch(context,pool,'day',max_pages=5);coverage.append(entry)
                except Exception as exc:failures.append({'pool':pool['id'],'history_error':str(exc)})
            found.extend(active)
        if found:
            try:
                _,entries=defillama.fetch(context,found,context_name='extra_defillama_context');coverage+=entries
            except Exception as exc:failures.append({'tvl_error':str(exc)})
            old_version=path.parent/'_versions/pool_registry'/(hashlib.sha256(path.read_bytes()).hexdigest()+'.json')
            if not old_version.exists():atomic_bytes(old_version,path.read_bytes())
            payload={'data_kind':'observed_snapshot','pools':old['pools']+found}
            atomic_json(path,payload)
            version=path.parent/'_versions/pool_registry'/(hashlib.sha256(path.read_bytes()).hexdigest()+'.json')
            atomic_bytes(version,path.read_bytes())
            for p in [path,version]:context.log('ethereum_rpc+geckoterminal','local://verified-pool-registry',p,len(payload['pools']),kind='observed_snapshot')
        report={'added':[p['id'] for p in found],'failures':failures,'datasets':coverage}
        atomic_json(root/'data/extension_status.json',report)
        existing=root/'data/coverage.json'
        if existing.exists():
            data=json.loads(existing.read_text(encoding='utf-8'));data['datasets']+=coverage
            from src.data.maintenance import finalize
            quality=finalize(context,data)
        else:
            quality=audit(root);atomic_json(root/'data/quality_report.json',quality)
        print(json.dumps({'added':report['added'],'failures':failures,'quality_ok':quality['ok']},ensure_ascii=False),flush=True)
        return report
    finally:context.close()


if __name__=='__main__':run(state_directory())

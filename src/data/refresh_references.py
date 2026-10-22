"""Append newly closed daily reference bars without revising archived history."""
import json
import pandas as pd
from src.data import binance
from src.data.common import Acquisition,utc_now,coverage_row
from src.data.quality import audit
from src.utils.config import state_directory
from src.utils.serialization import atomic_json


def run(root):
    context=Acquisition(root,attempts=2)
    try:
        status=json.loads((root/'data/coverage.json').read_text(encoding='utf-8'))
        for symbol in ['ETHUSDT','USDCUSDT','ETHUSDC','BTCUSDT','ETHBTC']:
            name='reference_'+symbol.lower()+'_1d';path=root/'data/processed'/(name+'.parquet')
            previous=pd.read_parquet(path)
            prior_reference=context.reference(path)
            frame,entry=binance.fetch(context,symbol,'1d')
            new=frame.loc[frame.timestamp>previous.timestamp.max()]
            merged=pd.concat([previous,new],ignore_index=True).sort_values('timestamp')
            context.frame(name,merged,'binance',binance.ENDPOINT,start=merged.timestamp.min().isoformat(),end=merged.timestamp.max().isoformat(),kind='observed',
                lineage=[prior_reference,context.reference(path)])
            entry=coverage_row('binance',name,'complete_available',merged,'CEX reference, existing closed bars frozen; newly closed bars appended. Not Uniswap volume.',missing_intervals=len(pd.date_range(merged.timestamp.min(),merged.timestamp.max(),freq='D').difference(merged.timestamp)))
            status['datasets']=[d for d in status['datasets'] if d['dataset']!=name]+[entry]
            print(symbol,len(new),'new closed bars',str(merged.timestamp.max()),flush=True)
        from src.data.maintenance import finalize
        finalize(context,status)
    finally:context.close()


if __name__=='__main__':run(state_directory())

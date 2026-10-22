"""Immutable, content-addressed live inputs; never overwrite research snapshots."""
import copy
import csv
from datetime import datetime,timezone
import hashlib
import io
import json
import math
import re

from api.schemas import RunRecord,SimulationRequest
from src.data.common import atomic_bytes,utc_now
from src.data.history import history_snapshot,HistoryUnavailable
from src.data.market import logged_payload,MarketUnavailable,aware
from src.models.service import SimulationService,SimulationInputError
from src.utils.serialization import atomic_json,digest


def capture(service,live,pool_id):
    registry=service.market.registry()
    if registry is None or pool_id not in registry[0]:raise SimulationInputError('Không tìm thấy cặp thanh khoản.')
    current=next((p for p in live.snapshot()['pools'] if p['id']==pool_id),None)
    if current is None:raise SimulationInputError('Chưa có dữ liệu thị trường cho cặp này. Đợi cập nhật rồi thử lại.')
    rpc,meta=current['rpc'],current['metadata']
    if rpc['status']!='ok' or meta['status']!='ok':
        raise SimulationInputError('Chưa có đủ dữ liệu thị trường mới từ cả RPC và nguồn TVL/khối lượng. Đợi cập nhật hoặc chủ động chọn dữ liệu nghiên cứu đã lưu.')
    now=datetime.now(timezone.utc)
    if (now-aware(rpc['block_time']).to_pydatetime()).total_seconds()>180:
        raise SimulationInputError('Block RPC đã trễ hơn 3 phút. Không dùng dữ liệu này để tạo mô phỏng thị trường mới.')
    # Elapsed ages and UI status are derived at read time, not simulation inputs.
    rpc={k:v for k,v in rpc.items() if k not in {'age_seconds','block_age_seconds','status','last_error'}}
    meta={k:v for k,v in meta.items() if k not in {'age_seconds','status','last_error'}}
    pool=copy.deepcopy(registry[0][pool_id]);raw=int(rpc['liquidity_raw']);sqrt=int(rpc['sqrt_price_x96'])
    if raw<=0:raise SimulationInputError('Pool hiện không có thanh khoản hoạt động; chưa thể mô phỏng phí LP.')
    root=sqrt/2**96
    quote_usd=float(meta['quote_usd'])
    factor=quote_usd/(root*10**pool['decimals0']) if pool['inverted'] else quote_usd*root/10**pool['decimals1']
    normalized=raw*factor
    if not math.isfinite(normalized) or normalized<=0:raise SimulationInputError('Thanh khoản quy đổi không hợp lệ.')
    available=max(aware(rpc['block_time']),aware(rpc['fetched_at']),aware(meta['fetched_at'])).isoformat()
    pool.update(p0=rpc['price_quote'],sqrt_price_x96=rpc['sqrt_price_x96'],liquidity_raw=rpc['liquidity_raw'],tick=rpc['tick'],
        block_number=rpc['block_number'],block_hash=rpc['block_hash'],data_asof=rpc['block_time'],available_at=available,
        context_available_at=meta['fetched_at'],tvl_usd=meta['tvl_usd'],volume_24h_usd=meta['volume_24h_usd'],quote_usd=quote_usd,
        background_liquidity_normalized_usd=normalized)
    history_path=service.state_dir/'data/processed'/f'history_{pool_id}.parquet'
    content=None;source=None
    if history_path.exists():
        content,sha,provenance=logged_payload(service.state_dir,history_path)
        with (service.state_dir/'data/source_log.csv').open(encoding='utf-8',newline='') as f:
            source=[r for r in csv.DictReader(f) if r['file_path']==history_path.relative_to(service.state_dir).as_posix() and r['sha256']==sha][-1]
    payload={'version':'live-pinned-inputs-v1','pool':pool,'rpc':rpc,'metadata':meta,
        'history_sha256':hashlib.sha256(content).hexdigest() if content else None,'history_source':source,
        'limitations':['Latest block is provisional and may be reorganized.','TVL and volume are provider aggregates with separate retrieval time.',
            'Only current active liquidity captured; initialized tick distribution is not refreshed.','Historical calibration candles are pinned from the stored research dataset.']}
    identity=digest(payload);directory=service.state_dir/'outputs/market_snapshots'/identity
    if not (directory/'snapshot.json').exists():
        directory.mkdir(parents=True,exist_ok=True)
        if content is not None:
            atomic_bytes(directory/'data/processed'/history_path.name,content)
            stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(source));writer.writeheader();writer.writerow(source)
            atomic_bytes(directory/'data/source_log.csv',stream.getvalue().encode('utf-8'))
        atomic_json(directory/'snapshot.json',payload)
    return {'snapshot_id':identity,'pool':pool_id,'price':pool['p0'],'data_asof':pool['data_asof'],'available_at':available,
        'block_number':pool['block_number'],'metadata_fetched_at':meta['fetched_at'],'history_pinned':content is not None}


class SnapshotMarket:
    def __init__(self,root,identity):
        if not re.fullmatch('[0-9a-f]{64}',identity):raise SimulationInputError('Mã dữ liệu thị trường không hợp lệ.')
        self.identity=identity;self.root=root/'outputs/market_snapshots'/identity
        try:self.payload=json.loads((self.root/'snapshot.json').read_text(encoding='utf-8'))
        except (OSError,ValueError) as exc:raise SimulationInputError('Không tìm thấy bản dữ liệu thị trường đã lưu.') from exc
        if digest(self.payload)!=identity:raise SimulationInputError('Bản dữ liệu thị trường đã thay đổi; không thể tái lập kết quả.')
        self.pool=self.payload['pool']
        expected=self.payload['history_sha256']
        if expected:
            path=self.root/'data/processed'/f"history_{self.pool['id']}.parquet"
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
                raise SimulationInputError('Lịch sử hiệu chỉnh của bản dữ liệu đã thiếu hoặc thay đổi.')
            try:
                with (self.root/'data/source_log.csv').open(encoding='utf-8',newline='') as stream:
                    entries=list(csv.DictReader(stream))
                if entries!=[self.payload['history_source']]:raise ValueError('changed source ledger')
            except (OSError,ValueError) as exc:
                raise SimulationInputError('Thông tin nguồn của lịch sử đã thiếu hoặc thay đổi.') from exc

    def registry(self):
        return {self.pool['id']:self.pool},self.identity,{'source':'live_pinned_rpc_and_geckoterminal','snapshot_id':self.identity}

    def history(self,pool,asof,required=False):
        if pool!=self.pool['id']:raise SimulationInputError('Bản dữ liệu thị trường thuộc một cặp khác.')
        if not self.payload['history_sha256'] and not required:return None,None,[]
        try:return history_snapshot(self.root,pool,asof)
        except HistoryUnavailable as exc:raise MarketUnavailable(str(exc)) from exc

    def ticks(self,pool):
        return [],digest({'snapshot_id':self.identity,'active_L':pool['liquidity_raw']}),{'source':'live_rpc','full_tick_profile':False}


class PinnedLiveService(SimulationService):
    def __init__(self,base,identity):
        self.state_dir=base.state_dir;self.settings=base.settings;self.pools=base.pools;self.dataset=base.dataset
        self.market=SnapshotMarket(base.state_dir,identity)

    def simulate(self,config):
        if config.pool!=self.market.pool['id']:raise SimulationInputError('Bản dữ liệu đã lưu không khớp cặp thanh khoản đang chọn.')
        result=super().simulate(config)
        result.meta.assumptions.update(live_market_snapshot_id=self.market.identity,
            liquidity_ticks_status='not_captured_live_active_liquidity_only',
            live_data=self.market.payload['limitations'],live_metadata_fetched_at=self.market.payload['metadata']['fetched_at'])
        effective=SimulationRequest.model_validate(result.meta.assumptions['effective_config'])
        atomic_json(self.state_dir/'outputs/runs'/(result.meta.run_id+'.json'),RunRecord(config=effective,result=result).model_dump(mode='json'))
        return result

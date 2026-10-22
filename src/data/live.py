"""Bounded, memory-only market monitoring, separate from research snapshots.

No acquisition/normalization helpers are called: live values must never rewrite
the registry, source ledger, historical data, or content-addressed saved runs.
"""
import asyncio
import copy
from datetime import datetime, timezone
import math
import os
import re
import threading
import time

import httpx

from src.data.ethereum import selector, signed


RPC_DEFAULTS = {
    1: ('eth', 'ETHEREUM_RPC_URL', 'https://ethereum-rpc.publicnode.com'),
    42161: ('arbitrum', 'ARBITRUM_RPC_URL', 'https://arb1.arbitrum.io/rpc'),
}
GECKO_BASE = 'https://api.geckoterminal.com/api/v2/networks/'
DEX_IDS = {'eth': 'uniswap_v3', 'arbitrum': 'uniswap_v3_arbitrum'}


def _now():
    return datetime.now(timezone.utc)


def _iso(value):
    return value.isoformat()


def _age(value, now):
    if value is None:
        return None
    return max(0., (now-datetime.fromisoformat(value)).total_seconds())


def _uint(value, bits=256):
    if not isinstance(value, str) or not re.fullmatch(r'0x[0-9a-fA-F]+', value):
        raise ValueError('invalid integer')
    result = int(value, 16)
    if result >= 2**bits:
        raise ValueError('integer out of bounds')
    return result


def _number(value, *, positive=False):
    if value is None or isinstance(value, bool):
        raise ValueError('missing number')
    result = float(value)
    if not math.isfinite(result) or result < 0 or (positive and result == 0):
        raise ValueError('invalid number')
    return result


def _words(value):
    if not isinstance(value, str) or not re.fullmatch(r'0x(?:[0-9a-fA-F]{64})+', value):
        raise ValueError('invalid ABI response')
    return [int(value[i:i+64], 16) for i in range(2, len(value), 64)]


class _LiveError(Exception):
    """Only static, non-sensitive error descriptions may be constructed."""


class LiveMarket:
    def __init__(self, service, interval_seconds=30, metadata_interval_seconds=300, transport=None):
        self.interval_seconds = float(interval_seconds)
        self.metadata_interval_seconds = float(metadata_interval_seconds)
        if not all(math.isfinite(v) and v > 0 for v in [self.interval_seconds, self.metadata_interval_seconds]):
            raise ValueError('Live refresh intervals must be finite and positive.')
        self._transport = transport
        self._client = None
        self._task = None
        self._stop_event = asyncio.Event()
        self._refresh_lock = asyncio.Lock()
        self._state_lock = threading.RLock()
        self._next_rpc = self._next_metadata = 0.
        self._source_not_before = {}
        self._registry_error = None
        try:
            registry = service.market.registry()
            self._identities = copy.deepcopy(registry[0]) if registry is not None else {}
        except Exception:
            self._identities = {}
            self._registry_error = 'Verified pool registry unavailable.'
        self._rows = {}
        for pool_id, pool in self._identities.items():
            chain = pool.get('chain_id', 1)
            self._rows[pool_id] = {
                'id': pool_id, 'address': pool['address'], 'chain_id': chain,
                'network': pool.get('network', RPC_DEFAULTS.get(chain, ('unknown',))[0]),
                'base': pool['base'], 'quote': pool['quote'],
                'rpc': dict.fromkeys(['price_quote', 'liquidity_raw', 'sqrt_price_x96', 'tick',
                                     'block_number', 'block_hash', 'block_time', 'fetched_at',
                                     'age_seconds', 'block_age_seconds', 'last_error', 'base_fee_gwei']),
                'metadata': dict.fromkeys(['tvl_usd', 'volume_24h_usd', 'quote_usd', 'fetched_at',
                                          'age_seconds', 'last_error']),
            }
            self._rows[pool_id]['rpc'].update(status='pending', source='ethereum_rpc' if chain == 1 else 'arbitrum_rpc')
            self._rows[pool_id]['metadata'].update(status='pending', source='geckoterminal')

    def snapshot(self):
        """Immediate independent copy; GET requests never wait for upstream I/O."""
        now = _now()
        with self._state_lock:
            rows = copy.deepcopy(list(self._rows.values()))
        for row in rows:
            for name, interval in [('rpc', self.interval_seconds), ('metadata', self.metadata_interval_seconds)]:
                part = row[name]
                part['age_seconds'] = _age(part['fetched_at'], now)
                if name == 'rpc':
                    part['block_age_seconds'] = _age(part['block_time'], now)
                aged = part['age_seconds'] is not None and part['age_seconds'] > 3*interval
                old_block = name == 'rpc' and part['block_age_seconds'] is not None and part['block_age_seconds'] > max(90., 3*interval)
                if part['status'] == 'ok' and (aged or old_block):
                    part['status'] = 'stale'
        return {'server_time': _iso(now), 'interval_seconds': self.interval_seconds,
                'refresh_interval_seconds': self.interval_seconds,
                'metadata_interval_seconds': self.metadata_interval_seconds,
                'registry_error': self._registry_error, 'pools': rows}

    def _success(self, pool_id, section, values):
        with self._state_lock:
            previous = self._rows[pool_id][section]
            self._rows[pool_id][section] = {**previous, **values, 'fetched_at': _iso(_now()),
                                            'status': 'ok', 'last_error': None, 'age_seconds': 0.}

    def _failure(self, pool_id, section, message):
        with self._state_lock:
            previous = self._rows[pool_id][section]
            self._rows[pool_id][section] = {**previous, 'status': 'stale' if previous['fetched_at'] else 'error',
                                            'last_error': message}

    async def _ensure_client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(
                transport=self._transport, timeout=httpx.Timeout(8., connect=4.),
                limits=httpx.Limits(max_connections=4, max_keepalive_connections=4),
                follow_redirects=False, headers={'Accept': 'application/json', 'User-Agent': 'RangeLab-Live/1.0'})

    async def start(self):
        """Start one background worker; initial network reads do not delay startup."""
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._loop(), name='rangelab-live-market')

    async def stop(self):
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            finally:
                self._task = None
        # Wait for an explicitly invoked refresh too, so its client is not closed
        # midway through the final read. Network operations have bounded deadlines.
        async with self._refresh_lock:
            if self._client is not None:
                await self._client.aclose()
                self._client = None

    async def _loop(self):
        while not self._stop_event.is_set():
            await self._refresh(force_rpc=False)
            delay = max(.05, min(self._next_rpc, self._next_metadata)-time.monotonic())
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass

    async def refresh(self):
        """Explicitly refresh RPC; metadata is fetched only when its cadence is due.

        The shared lock makes manual and background refreshes single-flight.
        Neither path persists values or mutates the simulation service.
        """
        await self._refresh(force_rpc=True)

    async def _refresh(self, *, force_rpc):
        async with self._refresh_lock:
            await self._ensure_client()
            now = time.monotonic()
            groups = {}
            for pool_id, pool in self._identities.items():
                groups.setdefault(pool.get('chain_id', 1), []).append((pool_id, pool))
            work = []
            if force_rpc or now >= self._next_rpc:
                self._next_rpc = now+self.interval_seconds
                work = [self._rpc_chain(chain, pools) for chain, pools in groups.items()]
            if now >= self._next_metadata:
                self._next_metadata = now+self.metadata_interval_seconds
                work += [self._metadata_chain(chain, pools) for chain, pools in groups.items()]
            await asyncio.gather(*work)

    async def _json(self, method, endpoint, source, **kwargs):
        # Never include URLs, raw exception text, RPC error messages or response
        # bodies in public errors: providers can echo credentials in all of them.
        if time.monotonic() < self._source_not_before.get(endpoint, 0):
            raise _LiveError(source+': rate limited; waiting before retry.')
        for attempt in range(2):
            try:
                response = await self._client.request(method, endpoint, **kwargs)
            except httpx.RequestError:
                if attempt == 0:
                    await asyncio.sleep(.1)
                    continue
                raise _LiveError(source+': network request failed.') from None
            if response.status_code == 429:
                try:
                    after = max(30., float(response.headers.get('Retry-After', '30')))
                    if not math.isfinite(after):
                        after = 30.
                except ValueError:
                    after = 30.
                self._source_not_before[endpoint] = time.monotonic()+min(after, 86400.)
                raise _LiveError(source+': HTTP 429; waiting before retry.')
            if response.status_code >= 500 and attempt == 0:
                await asyncio.sleep(.1)
                continue
            if not 200 <= response.status_code < 300:
                raise _LiveError(source+': HTTP '+str(response.status_code)+'.')
            try:
                return response.json()
            except ValueError:
                raise _LiveError(source+': invalid JSON response.') from None

    async def _rpc_call(self, endpoint, method, params):
        payload = await self._json('POST', endpoint, 'RPC', json={'jsonrpc': '2.0', 'method': method, 'params': params, 'id': 1})
        if not isinstance(payload, dict) or 'result' not in payload or 'error' in payload:
            raise _LiveError('RPC: call failed.')
        return payload['result']

    async def _rpc_chain(self, chain, pools):
        try:
            async with asyncio.timeout(25.):
                if chain not in RPC_DEFAULTS:
                    raise _LiveError('RPC: unsupported network.')
                _, env, default = RPC_DEFAULTS[chain]
                endpoint = os.environ.get(env) or default
                if _uint(await self._rpc_call(endpoint, 'eth_chainId', [])) != chain:
                    raise _LiveError('RPC: chain identity mismatch.')
                block = await self._rpc_call(endpoint, 'eth_getBlockByNumber', ['latest', False])
                number = _uint(block['number'])
                block_datetime = datetime.fromtimestamp(_uint(block['timestamp']), timezone.utc)
                block_time = _iso(block_datetime)
                block_hash = block['hash']
                if not isinstance(block_hash, str) or not re.fullmatch(r'0x[0-9a-fA-F]{64}', block_hash):
                    raise ValueError('invalid block hash')
                if (block_datetime-_now()).total_seconds() > 300:
                    raise ValueError('future block time')
                base_fee = _uint(block['baseFeePerGas'])/1e9 if block.get('baseFeePerGas') is not None else None
                calls = []
                for pool_id, pool in pools:
                    for signature in ['slot0()', 'liquidity()']:
                        calls.append((pool_id, {'jsonrpc': '2.0', 'method': 'eth_call',
                            'params': [{'to': pool['address'], 'data': selector(signature)}, hex(number)], 'id': len(calls)+1}))
                results = {}
                errors = {}
                for offset in range(0, len(calls), 20):
                    chunk = calls[offset:offset+20]
                    try:
                        response = await self._json('POST', endpoint, 'RPC', json=[call for _, call in chunk])
                        if not isinstance(response, list):
                            raise _LiveError('RPC: batch response unavailable.')
                        ids = [row.get('id') for row in response if isinstance(row, dict)]
                        mapped = {row.get('id'): row for row in response if isinstance(row, dict) and isinstance(row.get('id'), int)}
                        for pool_id, call in chunk:
                            item = mapped.get(call['id'], {})
                            if ids.count(call['id']) != 1 or 'result' not in item or 'error' in item:
                                errors[pool_id] = 'RPC: pool call failed or missing from batch.'
                            else:
                                results[call['id']] = item['result']
                    except _LiveError as exc:
                        for pool_id, _ in chunk:
                            errors[pool_id] = str(exc)
                # A numeric block can be replaced by a reorganization while calls
                # run. Verify its hash again before publishing the joined state.
                check = await self._rpc_call(endpoint, 'eth_getBlockByNumber', [hex(number), False])
                if not isinstance(check, dict) or check.get('hash') != block_hash:
                    raise _LiveError('RPC: block changed during refresh; retrying next cycle.')
                for index, (pool_id, pool) in enumerate(pools):
                    if pool_id in errors:
                        self._failure(pool_id, 'rpc', errors[pool_id])
                        continue
                    try:
                        state = _words(results[2*index+1])
                        raw_l = _words(results[2*index+2])
                        if len(state) != 7 or len(raw_l) != 1 or not 0 < state[0] < 2**160 or not 0 <= raw_l[0] < 2**128:
                            raise ValueError('invalid pool values')
                        tick = signed(state[1], 24)
                        if not -887272 <= tick <= 887272:
                            raise ValueError('invalid tick')
                        ratio = (state[0]/2**96)**2 * 10**(pool['decimals0']-pool['decimals1'])
                        price = _number(1/ratio if pool['inverted'] else ratio, positive=True)
                        self._success(pool_id, 'rpc', {'price_quote': price, 'liquidity_raw': str(raw_l[0]),
                            'sqrt_price_x96': str(state[0]), 'tick': tick, 'block_number': number,
                            'block_hash': block_hash, 'block_time': block_time, 'base_fee_gwei': base_fee})
                    except (KeyError, TypeError, ValueError, OverflowError, ZeroDivisionError):
                        self._failure(pool_id, 'rpc', 'RPC: invalid pool state.')
        except (TimeoutError, _LiveError, KeyError, TypeError, ValueError, OverflowError) as exc:
            message = 'RPC: refresh timed out.' if isinstance(exc, TimeoutError) else 'RPC: network or block validation failed.'
            if isinstance(exc, _LiveError):
                message = str(exc)
            for pool_id, _ in pools:
                self._failure(pool_id, 'rpc', message)

    async def _metadata_chain(self, chain, pools):
        try:
            async with asyncio.timeout(20.):
                if chain not in RPC_DEFAULTS:
                    raise _LiveError('GeckoTerminal: unsupported network.')
                network = RPC_DEFAULTS[chain][0]
                endpoint = GECKO_BASE+network+'/pools/multi/'+','.join(pool['address'] for _, pool in pools)
                payload = await self._json('GET', endpoint, 'GeckoTerminal', headers={'Accept': 'application/json;version=20230203'})
                if not isinstance(payload, dict) or not isinstance(payload.get('data'), list):
                    raise _LiveError('GeckoTerminal: invalid pool response.')
                items = payload['data']
                for pool_id, pool in pools:
                    try:
                        matches = [item for item in items if item.get('id', '').lower() == network+'_'+pool['address'].lower()]
                        if len(matches) != 1:
                            raise ValueError('pool missing or duplicated')
                        item = matches[0]
                        attributes, relationships = item['attributes'], item['relationships']
                        if attributes.get('address', pool['address']).lower() != pool['address'].lower():
                            raise ValueError('address mismatch')
                        base = relationships['base_token']['data']['id'].removeprefix(network+'_').lower()
                        quote = relationships['quote_token']['data']['id'].removeprefix(network+'_').lower()
                        expected_base, expected_quote = pool['base_address'].lower(), pool['quote_address'].lower()
                        if {base, quote} != {expected_base, expected_quote} or relationships['dex']['data']['id'] != DEX_IDS[network]:
                            raise ValueError('token or dex mismatch')
                        quote_usd = attributes['quote_token_price_usd'] if quote == expected_quote else attributes['base_token_price_usd']
                        self._success(pool_id, 'metadata', {'tvl_usd': _number(attributes['reserve_in_usd']),
                            'volume_24h_usd': _number(attributes['volume_usd']['h24']), 'quote_usd': _number(quote_usd, positive=True)})
                    except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
                        self._failure(pool_id, 'metadata', 'GeckoTerminal: missing or invalid pool metadata.')
        except (TimeoutError, _LiveError, KeyError, TypeError, ValueError) as exc:
            message = str(exc) if isinstance(exc, _LiveError) else 'GeckoTerminal: refresh failed or timed out.'
            for pool_id, _ in pools:
                self._failure(pool_id, 'metadata', message)

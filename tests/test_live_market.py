"""Memory-only monitoring: block consistency, partial failures and lifecycle."""
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from types import SimpleNamespace

import httpx
import pytest

from src.data import live
from src.data.ethereum import selector


NOW = datetime(2026, 10, 21, 7, 0, tzinfo=timezone.utc)
USDC = '0x'+'1'*40
WETH = '0x'+'2'*40
WBTC = '0x'+'3'*40
ARB = '0x'+'4'*40


def specs():
    return [
        {'id': 'weth-usdc-500', 'address': '0x'+'a'*40, 'chain_id': 1, 'network': 'eth',
         'base': 'WETH', 'quote': 'USDC', 'base_address': WETH, 'quote_address': USDC,
         'decimals0': 6, 'decimals1': 18, 'inverted': True, 'expected_price': 2500., 'raw_l': 2**100+17},
        {'id': 'wbtc-weth-3000', 'address': '0x'+'b'*40, 'chain_id': 1, 'network': 'eth',
         'base': 'WBTC', 'quote': 'WETH', 'base_address': WBTC, 'quote_address': WETH,
         'decimals0': 8, 'decimals1': 18, 'inverted': False, 'expected_price': 20., 'raw_l': 2**99+31},
        {'id': 'arb-weth-500', 'address': '0x'+'c'*40, 'chain_id': 42161, 'network': 'arbitrum',
         'base': 'ARB', 'quote': 'WETH', 'base_address': ARB, 'quote_address': WETH,
         'decimals0': 18, 'decimals1': 18, 'inverted': True, 'expected_price': .0001, 'raw_l': 0},
    ]


def service(pools):
    registry = {p['id']: p for p in pools}
    return SimpleNamespace(market=SimpleNamespace(registry=lambda: (registry, 'fixture-hash', {})))


def abi(*values):
    return '0x'+''.join(format(value % 2**256, '064x') for value in values)


class Upstream:
    def __init__(self, pools):
        self.pools = pools
        self.calls = []
        self.fail_rpc = False
        self.bad_pool = None
        self.bad_metadata = None
        self.wrong_chain = False
        self.reorg = False
        self.metadata_http = 200
        self.metadata_count = 0
        self.active_rpc = self.max_active_rpc = 0
        self.delay = 0

    def metadata(self, pool):
        # Intentionally reverse the provider's base/quote presentation for USDC.
        flip = pool['quote'] == 'USDC'
        base, quote = (pool['quote_address'], pool['base_address']) if flip else (pool['base_address'], pool['quote_address'])
        usd = {'USDC': 1., 'WETH': 2500., 'ARB': .25, 'WBTC': 50000.}
        base_usd, quote_usd = (usd[pool['quote']], usd[pool['base']]) if flip else (usd[pool['base']], usd[pool['quote']])
        item = {'id': pool['network']+'_'+pool['address'], 'attributes': {'address': pool['address'],
            'reserve_in_usd': '1234567.5', 'volume_usd': {'h24': '98765.25'},
            'base_token_price_usd': str(base_usd), 'quote_token_price_usd': str(quote_usd)},
            'relationships': {'base_token': {'data': {'id': pool['network']+'_'+base}},
                'quote_token': {'data': {'id': pool['network']+'_'+quote}},
                'dex': {'data': {'id': live.DEX_IDS[pool['network']]}}}}
        if pool['id'] == self.bad_metadata:
            item['relationships']['dex']['data']['id'] = 'wrong_dex'
        return item

    async def __call__(self, request):
        body = json.loads(request.content) if request.content else None
        self.calls.append((request.method, body, request.url.path))
        if request.method == 'GET':
            self.metadata_count += 1
            if self.metadata_http != 200:
                return httpx.Response(self.metadata_http, headers={'Retry-After': '120'}, json={'error': 'DO_NOT_EXPOSE_SECRET'})
            network = request.url.path.split('/networks/')[1].split('/')[0]
            return httpx.Response(200, json={'data': [self.metadata(pool) for pool in self.pools if pool['network'] == network]})
        self.active_rpc += 1
        self.max_active_rpc = max(self.max_active_rpc, self.active_rpc)
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            if self.fail_rpc:
                raise httpx.ConnectError('DO_NOT_EXPOSE_SECRET https://key.example/private-token', request=request)
            chain = 1 if 'ethereum' in request.url.host else 42161
            if isinstance(body, list):
                result = []
                for call in body:
                    pool = next(pool for pool in self.pools if pool['address'] == call['params'][0]['to'])
                    assert call['params'][1] == '0x7b'  # Both methods pinned to the same numeric block.
                    if pool['id'] == self.bad_pool:
                        result.append({'id': call['id'], 'error': {'message': 'DO_NOT_EXPOSE_SECRET'}})
                    elif call['params'][0]['data'] == selector('slot0()'):
                        human = 1/pool['expected_price'] if pool['inverted'] else pool['expected_price']
                        sqrt = int(math.sqrt(human * 10**(pool['decimals1']-pool['decimals0']))*2**96)
                        result.append({'id': call['id'], 'result': abi(sqrt, -42, 0, 1, 1, 0, 1)})
                    else:
                        result.append({'id': call['id'], 'result': abi(pool['raw_l'])})
                return httpx.Response(200, json=list(reversed(result)))  # JSON-RPC batch order is not guaranteed.
            method = body['method']
            if method == 'eth_chainId':
                return httpx.Response(200, json={'id': 1, 'result': hex(2 if self.wrong_chain else chain)})
            assert method == 'eth_getBlockByNumber'
            changed = self.reorg and body['params'][0] != 'latest'
            return httpx.Response(200, json={'id': 1, 'result': {'number': '0x7b',
                'hash': '0x'+('f' if changed else 'd')*64,
                'timestamp': hex(int((NOW-timedelta(seconds=6)).timestamp())), 'baseFeePerGas': hex(3_000_000_000)}})
        finally:
            self.active_rpc -= 1


@pytest.fixture
def fixed_now(monkeypatch):
    clock = [NOW]
    monkeypatch.setattr(live, '_now', lambda: clock[0])
    monkeypatch.delenv('ETHEREUM_RPC_URL', raising=False)
    monkeypatch.delenv('ARBITRUM_RPC_URL', raising=False)
    return clock


def test_live_prices_units_zero_liquidity_and_metadata_orientation_are_correct(fixed_now, tmp_path):
    pools = specs()
    original = deepcopy(pools)
    marker = tmp_path/'saved-research.json'
    marker.write_text('{"immutable":true}', encoding='utf-8')
    old_hash = hashlib.sha256(marker.read_bytes()).hexdigest()
    upstream = Upstream(pools)
    svc = live.LiveMarket(service(pools), transport=httpx.MockTransport(upstream))
    assert upstream.calls == []
    assert all(row['rpc']['status'] == 'pending' and row['rpc']['price_quote'] is None for row in svc.snapshot()['pools'])

    async def scenario():
        await svc.refresh()
        result = svc.snapshot()
        assert result['server_time'] == NOW.isoformat()
        for row, pool in zip(result['pools'], pools):
            assert row['rpc']['status'] == row['metadata']['status'] == 'ok'
            assert row['rpc']['price_quote'] == pytest.approx(pool['expected_price'])
            assert row['rpc']['liquidity_raw'] == str(pool['raw_l'])
            assert row['rpc']['tick'] == -42
            assert row['rpc']['base_fee_gwei'] == 3
            assert row['rpc']['block_age_seconds'] == 6
            assert row['metadata']['quote_usd'] == (1 if pool['quote'] == 'USDC' else 2500)
            assert row['metadata']['tvl_usd'] == 1234567.5
        json.dumps(result, allow_nan=False)
        result['pools'][0]['rpc']['price_quote'] = 1
        assert svc.snapshot()['pools'][0]['rpc']['price_quote'] == pytest.approx(2500)
        await svc.refresh()
        assert upstream.metadata_count == 2  # One request per network, not per pool or RPC poll.
        await svc.stop()
    asyncio.run(scenario())
    assert pools == original
    assert hashlib.sha256(marker.read_bytes()).hexdigest() == old_hash
    assert list(tmp_path.iterdir()) == [marker]


def test_partial_pool_failure_retains_last_good_and_never_exposes_provider_secrets(fixed_now):
    pools = specs()
    upstream = Upstream(pools)
    svc = live.LiveMarket(service(pools), transport=httpx.MockTransport(upstream))

    async def scenario():
        await svc.refresh()
        before = svc.snapshot()['pools'][0]['rpc']
        upstream.bad_pool = pools[0]['id']
        fixed_now[0] += timedelta(seconds=40)
        await svc.refresh()
        rows = svc.snapshot()['pools']
        assert rows[0]['rpc']['status'] == 'stale'
        assert rows[0]['rpc']['price_quote'] == before['price_quote']
        assert rows[0]['rpc']['fetched_at'] == before['fetched_at']
        assert rows[0]['rpc']['age_seconds'] == 40
        assert rows[1]['rpc']['status'] == rows[2]['rpc']['status'] == 'ok'
        assert 'DO_NOT_EXPOSE' not in json.dumps(rows)
        upstream.fail_rpc = True
        await svc.refresh()
        assert all(row['rpc']['status'] == 'stale' for row in svc.snapshot()['pools'])
        assert 'private-token' not in json.dumps(svc.snapshot())
        await svc.stop()
    asyncio.run(scenario())


@pytest.mark.parametrize('failure', ['wrong_chain', 'reorg'])
def test_wrong_chain_and_reorg_never_publish_mismatched_state(fixed_now, failure):
    upstream = Upstream(specs())
    setattr(upstream, failure, True)
    svc = live.LiveMarket(service(upstream.pools), transport=httpx.MockTransport(upstream))

    async def scenario():
        await svc.refresh()
        for row in svc.snapshot()['pools']:
            assert row['rpc']['status'] == 'error'
            assert row['rpc']['price_quote'] is None
            assert row['metadata']['status'] == 'ok'  # Provider failure isolation.
        await svc.stop()
    asyncio.run(scenario())


def test_partial_invalid_metadata_does_not_remove_other_pools_or_rpc(fixed_now):
    upstream = Upstream(specs())
    upstream.bad_metadata = upstream.pools[0]['id']
    svc = live.LiveMarket(service(upstream.pools), transport=httpx.MockTransport(upstream))

    async def scenario():
        await svc.refresh()
        rows = svc.snapshot()['pools']
        assert rows[0]['metadata']['status'] == 'error'
        assert rows[0]['metadata']['tvl_usd'] is None
        assert all(row['rpc']['status'] == 'ok' for row in rows)
        assert all(row['metadata']['status'] == 'ok' for row in rows[1:])
        upstream.bad_metadata = None
        svc._next_metadata = 0
        await svc.refresh()
        assert all(row['metadata']['status'] == 'ok' for row in svc.snapshot()['pools'])
        await svc.stop()
    asyncio.run(scenario())


def test_age_staleness_is_reported_without_network_and_rate_limits_are_bounded(fixed_now):
    upstream = Upstream(specs())
    svc = live.LiveMarket(service(upstream.pools), transport=httpx.MockTransport(upstream))

    async def scenario():
        await svc.refresh()
        calls = len(upstream.calls)
        fixed_now[0] += timedelta(seconds=901)
        rows = svc.snapshot()['pools']
        assert all(row['rpc']['status'] == row['metadata']['status'] == 'stale' for row in rows)
        assert len(upstream.calls) == calls
        upstream.metadata_http = 429
        svc._next_metadata = 0
        await svc.refresh()
        count = upstream.metadata_count
        svc._next_metadata = 0
        await svc.refresh()
        assert upstream.metadata_count == count  # Honor Retry-After, no immediate retry storm.
        assert all('429' not in (row['rpc']['last_error'] or '') for row in svc.snapshot()['pools'])
        assert 'DO_NOT_EXPOSE_SECRET' not in json.dumps(svc.snapshot())
        await svc.stop()
    asyncio.run(scenario())


def test_concurrent_refreshes_are_single_flight(fixed_now):
    upstream = Upstream(specs()[:1])
    upstream.delay = .01
    svc = live.LiveMarket(service(upstream.pools), transport=httpx.MockTransport(upstream))

    async def scenario():
        await asyncio.gather(svc.refresh(), svc.refresh())
        assert upstream.max_active_rpc == 1
        assert upstream.metadata_count == 1
        await svc.stop()
    asyncio.run(scenario())


def test_start_is_nonblocking_and_shutdown_cancels_inflight_requests(fixed_now):
    entered = asyncio.Event()
    active = [0]

    async def slow(request):
        active[0] += 1
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            active[0] -= 1

    svc = live.LiveMarket(service(specs()), transport=httpx.MockTransport(slow))

    async def scenario():
        await asyncio.wait_for(svc.start(), timeout=.2)
        task = svc._task
        await svc.start()
        assert svc._task is task  # Idempotent startup; no duplicate pollers.
        await asyncio.wait_for(entered.wait(), timeout=.2)
        await asyncio.wait_for(svc.stop(), timeout=.5)
        assert active[0] == 0 and svc._task is None and svc._client is None
        count = active[0]
        await asyncio.sleep(.01)
        assert active[0] == count
    asyncio.run(scenario())

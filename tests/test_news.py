"""Real-format news fixtures: source isolation, freshness and safe rendering."""
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from html import escape
import json
from types import SimpleNamespace

import httpx
import pytest

from src.data import news


NOW = datetime(2026, 10, 22, 8, 0, tzinfo=timezone.utc)
POOL = {'id': 'weth-usdc-500', 'base': 'WETH', 'quote': 'USDC', 'network': 'eth', 'address': '0x'+'a'*40}
OTHER = {'id': 'wbtc-weth-500', 'base': 'WBTC', 'quote': 'WETH', 'network': 'eth', 'address': '0x'+'b'*40}


def blog_post(title='Uniswap v4 hooks for Ethereum and USD Coin', slug='pool-update', when=None):
    return {'__typename': 'BlogPost', 'title': title, 'slug': slug,
            'date': (when or NOW-timedelta(days=1)).isoformat(),
            'description': '<p>Liquidity <b>update</b> from Uniswap.</p>'}


def blog_html(posts):
    data = {'props': {'pageProps': {'featured': {'deeply': {'nested': posts}},
                                  'other': {'title': 'A non-post object is not a headline'}}}}
    return '<html><script id="__NEXT_DATA__" type="application/json">'+json.dumps(data)+'</script></html>'


def rss_item(title='Uniswap v3 governance vote', url='https://gov.uniswap.org/t/pool-update/123', when=None, summary=None):
    summary = summary or '<p>Pool <b>liquidity</b> discussion &amp; voting.</p>'
    return '<item><title>'+escape(title)+'</title><link>'+escape(url)+'</link><pubDate>'+format_datetime(when or NOW-timedelta(hours=2))+'</pubDate><description><![CDATA['+summary+']]></description></item>'


def rss(items):
    return '<?xml version="1.0"?><rss version="2.0"><channel><title>Uniswap Governance</title>'+''.join(items)+'</channel></rss>'


def make_service():
    pools = {POOL['id']: deepcopy(POOL), OTHER['id']: deepcopy(OTHER)}
    return SimpleNamespace(market=SimpleNamespace(registry=lambda: (pools, 'synthetic-news-registry', {}))), pools


def source_map(snapshot):
    return {source['id']: source for source in snapshot['sources']}


@pytest.fixture
def clock(monkeypatch):
    value = [NOW]
    monkeypatch.setattr(news, '_now', lambda: value[0])
    return value


def test_blog_parser_walks_real_next_data_and_rejects_bad_dates_or_slugs():
    posts = [blog_post(), {'wrapper': [blog_post('Older valid update', 'older-update', NOW-timedelta(days=89))]},
             blog_post('Old', 'old', NOW-timedelta(days=91)),
             blog_post('Future', 'future', NOW+timedelta(seconds=1)),
             blog_post('', 'empty-title'), blog_post('No date', 'no-date'),
             blog_post('External slug', 'https://evil.example/escape'),
             blog_post('Protocol-relative slug', '//evil.example/escape'),
             blog_post('Script slug', 'javascript:alert(1)'),
             blog_post('Traversal', '../escape')]
    posts[5]['date'] = 'not-a-date'
    result = news.parse_blog(blog_html(posts), NOW)
    assert {row['title'] for row in result} == {'Uniswap v4 hooks for Ethereum and USD Coin', 'Older valid update'}
    assert all(row['url'].startswith('https://blog.uniswap.org/') for row in result)
    assert all(row['published_at'] and '<' not in row['summary'] and 'Liquidity update' in row['summary'] for row in result)
    assert not any('non-post' in row['title'] for row in result)


def test_governance_parser_strips_markup_and_skips_unsafe_or_outdated_items():
    text = rss([rss_item(),
                rss_item('External', 'https://evil.example/t/123'),
                rss_item('Similar hostname', 'https://gov.uniswap.org.evil.example/t/123'),
                rss_item('Credentials', 'https://alice@gov.uniswap.org/t/123'),
                rss_item('Script', 'javascript:alert(1)'),
                rss_item('HTTP', 'http://gov.uniswap.org/t/123'),
                rss_item('Old', when=NOW-timedelta(days=91)),
                rss_item('Future', when=NOW+timedelta(seconds=1)),
                rss_item('', 'https://gov.uniswap.org/t/no-title/123')])
    result = news.parse_governance(text, NOW)
    assert len(result) == 1
    assert result[0]['url'] == 'https://gov.uniswap.org/t/pool-update/123'
    assert result[0]['summary'] == 'Pool liquidity discussion & voting.'
    assert datetime.fromisoformat(result[0]['published_at']) == NOW-timedelta(hours=2)


@pytest.mark.parametrize('parser,text', [
    (news.parse_blog, '<html><p>A changed layout without Next data</p></html>'),
    (news.parse_blog, '<script id="__NEXT_DATA__">not JSON</script>'),
    (news.parse_governance, '<html>A gateway error</html>'),
    (news.parse_governance, '<!DOCTYPE rss [<!ENTITY injected "content">]><rss><channel/></rss>'),
])
def test_unrecognized_formats_raise_instead_of_becoming_successful_empty_sources(parser, text):
    with pytest.raises(ValueError):
        parser(text, NOW)


@pytest.mark.parametrize('title,topics,relevance,version', [
    ('Uniswap v3 fee changes for Ethereum / USD Coin', {'WETH', 'USDC'}, 'token', 'v3'),
    ('Uniswap v4 hooks for $ETH liquidity', {'WETH'}, 'token', 'v4'),
    ('Uniswap governance announcement', set(), 'protocol', 'ecosystem'),
    ('UNI university reunion and weather update', set(), 'protocol', 'ecosystem'),
    ('Pool incident '+POOL['address'].upper(), set(), 'pool', 'ecosystem'),
])
def test_relevance_uses_canonical_tokens_word_boundaries_and_exact_pool_address(title, topics, relevance, version):
    result = news.classify({'title': title, 'summary': ''}, POOL)
    assert set(result['topics']) == topics
    assert result['relevance'] == relevance and result['relevance_label']
    assert result['version'] == version


class Upstream:
    def __init__(self):
        self.calls = []
        self.blog_failure = None
        self.governance_failure = False
        self.delay = 0

    async def __call__(self, request):
        assert request.method == 'GET'
        assert str(request.url) in {'https://blog.uniswap.org/', 'https://gov.uniswap.org/latest.rss'}
        self.calls.append(str(request.url))
        if self.delay:
            await asyncio.sleep(self.delay)
        if request.url.host == 'blog.uniswap.org':
            if self.blog_failure == 'http':
                return httpx.Response(503, text='DO_NOT_EXPOSE_SECRET_TOKEN https://provider.invalid/private-key')
            if self.blog_failure == 'oversize':
                return httpx.Response(200, text=blog_html([blog_post()])+' '*(news.MAX_BYTES+1))
            if self.blog_failure == 'format':
                return httpx.Response(200, text='<html>Login changed DO_NOT_EXPOSE_SECRET_TOKEN</html>')
            if self.blog_failure == 'redirect':
                return httpx.Response(302, headers={'Location': 'https://evil.example/unsafe'}, text='Redirect')
            # The same URL occurs in featured and nested sections of real pages.
            return httpx.Response(200, text=blog_html([blog_post(), {'another_section': [blog_post()]}]),
                                  headers={'Content-Type': 'text/html; charset=utf-8'})
        if self.governance_failure:
            raise httpx.ConnectError('DO_NOT_EXPOSE_SECRET_TOKEN', request=request)
        return httpx.Response(200, text=rss([rss_item(), rss_item()]), headers={'Content-Type': 'application/rss+xml'})


def test_cache_shared_across_pools_deduplicates_and_never_fetches_social_sources(clock):
    service, pools = make_service()
    original = deepcopy(pools)
    upstream = Upstream()
    feed = news.NewsFeed(service, transport=httpx.MockTransport(upstream))
    assert upstream.calls == []
    with pytest.raises(ValueError):
        feed.snapshot('unknown-pool')

    async def scenario():
        await feed.refresh()
        first = feed.snapshot(POOL['id'])
        second = feed.snapshot(OTHER['id'])
        await feed.refresh()
        assert len(upstream.calls) == 2  # No per-pool upstream searches or duplicate refresh.
        assert len(first['items']) == len(second['items']) == 2
        assert len({item['url'] for item in first['items']}) == 2
        assert {item['source_id'] for item in first['items']} == set(news.PUBLIC_SOURCES)
        assert all('summary' not in item for item in first['items'])  # No article body in headline API.
        assert all(item['published_at'] and item['fetched_at'] for item in first['items'])
        assert source_map(first)['x']['status'] == source_map(first)['reddit']['status'] == source_map(first)['cryptopanic']['status'] == 'not_connected'
        assert all(source_map(first)[key]['status'] == 'ok' for key in news.PUBLIC_SOURCES)
        assert first['pool']['id'] == POOL['id'] and second['pool']['id'] == OTHER['id']
        topic_a = next(item for item in first['items'] if item['source_id'] == 'uniswap_blog')['topics']
        topic_b = next(item for item in second['items'] if item['source_id'] == 'uniswap_blog')['topics']
        assert set(topic_a) == {'WETH', 'USDC'} and set(topic_b) == {'WETH'}
        json.dumps(first, allow_nan=False)
        await feed.stop()
    asyncio.run(scenario())
    assert pools == original


def test_failure_retains_last_good_per_source_and_does_not_leak_response_text(clock):
    service, _ = make_service()
    upstream = Upstream()
    feed = news.NewsFeed(service, transport=httpx.MockTransport(upstream))

    async def scenario():
        await feed.refresh()
        before = feed.snapshot(POOL['id'])
        upstream.blog_failure = 'http'
        clock[0] += timedelta(minutes=6)
        await feed.refresh(force=True)
        result = feed.snapshot(POOL['id'])
        assert {item['url'] for item in result['items']} == {item['url'] for item in before['items']}
        assert source_map(result)['uniswap_blog']['status'] == 'stale'
        assert source_map(result)['uniswap_governance']['status'] == 'ok'
        assert source_map(result)['uniswap_blog']['fetched_at'] == source_map(before)['uniswap_blog']['fetched_at']
        assert source_map(result)['uniswap_governance']['fetched_at'] != source_map(before)['uniswap_governance']['fetched_at']
        assert 'DO_NOT_EXPOSE' not in json.dumps(result) and 'private-key' not in json.dumps(result)
        upstream.blog_failure = None
        upstream.governance_failure = True
        await feed.refresh(force=True)
        result = feed.snapshot(POOL['id'])
        assert source_map(result)['uniswap_blog']['status'] == 'ok'
        assert source_map(result)['uniswap_governance']['status'] == 'stale'
        assert len(result['items']) == 2
        await feed.stop()
    asyncio.run(scenario())


@pytest.mark.parametrize('failure', ['oversize', 'format', 'redirect'])
def test_unsafe_or_oversized_source_cannot_block_good_source_or_publish_fake_success(clock, failure):
    service, _ = make_service()
    upstream = Upstream()
    upstream.blog_failure = failure
    feed = news.NewsFeed(service, transport=httpx.MockTransport(upstream))

    async def scenario():
        await feed.refresh()
        result = feed.snapshot(POOL['id'])
        assert source_map(result)['uniswap_blog']['status'] == 'error'
        assert source_map(result)['uniswap_blog']['fetched_at'] is None
        assert source_map(result)['uniswap_governance']['status'] == 'ok'
        assert {item['source_id'] for item in result['items']} == {'uniswap_governance'}
        assert 'DO_NOT_EXPOSE' not in json.dumps(result)
        assert not any('evil.example' in url for url in upstream.calls)
        await feed.stop()
    asyncio.run(scenario())


def test_cached_news_age_expiry_and_snapshot_copy_are_honest_without_network(clock):
    service, _ = make_service()
    upstream = Upstream()
    feed = news.NewsFeed(service, transport=httpx.MockTransport(upstream))

    async def scenario():
        await feed.refresh()
        clock[0] += timedelta(seconds=901)
        snapshot = feed.snapshot(POOL['id'])
        assert all(source_map(snapshot)[key]['status'] == 'stale' for key in news.PUBLIC_SOURCES)
        assert source_map(snapshot)['uniswap_blog']['age_seconds'] == 901
        assert len(snapshot['items']) == 2
        snapshot['items'][0]['title'] = 'Changed in caller'
        snapshot['sources'][0]['status'] = 'forged'
        again = feed.snapshot(POOL['id'])
        assert all(item['title'] != 'Changed in caller' for item in again['items'])
        assert all(source['status'] != 'forged' for source in again['sources'])
        clock[0] = NOW+timedelta(days=91)
        assert feed.snapshot(POOL['id'])['items'] == []
        assert len(upstream.calls) == 2
        await feed.stop()
    asyncio.run(scenario())


def test_disabled_feed_never_starts_network_and_keeps_social_status_separate(clock):
    service, _ = make_service()
    upstream = Upstream()
    feed = news.NewsFeed(service, transport=httpx.MockTransport(upstream), enabled=False)

    async def scenario():
        await feed.start()
        await feed.refresh(force=True)
        snapshot = feed.snapshot(POOL['id'])
        assert snapshot['enabled'] is False and snapshot['items'] == []
        assert all(source_map(snapshot)[key]['status'] == 'disabled' for key in news.PUBLIC_SOURCES)
        assert all(source_map(snapshot)[key]['status'] == 'not_connected' for key in news.SOCIAL_SOURCES)
        assert upstream.calls == []
        await feed.stop()
        await feed.stop()
    asyncio.run(scenario())


def test_concurrent_refreshes_share_single_batch(clock):
    service, _ = make_service()
    upstream = Upstream()
    upstream.delay = .01
    feed = news.NewsFeed(service, transport=httpx.MockTransport(upstream))

    async def scenario():
        await asyncio.gather(feed.refresh(), feed.refresh(), feed.refresh())
        assert len(upstream.calls) == 2
        assert len(feed.snapshot(POOL['id'])['items']) == 2
        await feed.stop()
    asyncio.run(scenario())


def test_start_nonblocking_idempotent_and_stop_cancels_streams_and_closes_client(clock):
    service, _ = make_service()
    entered = asyncio.Event()
    active = [0]
    calls = []

    async def slow(request):
        calls.append(str(request.url))
        active[0] += 1
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            active[0] -= 1

    feed = news.NewsFeed(service, transport=httpx.MockTransport(slow))

    async def scenario():
        await asyncio.wait_for(feed.start(), timeout=.2)
        await feed.start()
        await asyncio.wait_for(entered.wait(), timeout=.2)
        await asyncio.sleep(.01)
        assert len(calls) == 2  # Two sources, not two workers.
        await asyncio.wait_for(feed.stop(), timeout=.5)
        assert active[0] == 0
        assert feed._client is None or feed._client.is_closed
        await feed.stop()
        count = len(calls)
        await asyncio.sleep(.01)
        assert len(calls) == count
    asyncio.run(scenario())

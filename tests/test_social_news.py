"""Official API contracts with strictly mocked HTTP; never spend live credits."""
import asyncio
import base64
from datetime import datetime, timedelta, timezone
import json
import logging
from types import SimpleNamespace

import httpx
import pytest

from src.data import news
from src.data.news_providers import SocialProviders, ProviderFailure
from src.utils.environment import read_local_environment, load_local_environment

NOW = datetime(2026, 10, 22, 5, 0, tzinfo=timezone.utc)
POOL = {'id': 'weth-usdc-500', 'base': 'WETH', 'quote': 'USDC', 'address': '0x'+'a'*40, 'network': 'eth'}
CONFIG = {'X_BEARER_TOKEN': 'fake_x_DO_NOT_LOG', 'REDDIT_CLIENT_ID': 'fake-client',
          'REDDIT_CLIENT_SECRET': 'fake_reddit_DO_NOT_LOG', 'REDDIT_USER_AGENT': 'windows:rangelab:test (by /u/fixture)',
          'CRYPTOPANIC_API_TOKEN': 'fake_cp_DO_NOT_LOG', 'CRYPTOPANIC_PLAN': 'growth'}


class Upstream:
    def __init__(self):
        self.calls = []; self.failures = {}; self.responses = {}

    async def __call__(self, request):
        self.calls.append(request)
        host = request.url.host; path = request.url.path
        key = 'x' if host == 'api.x.com' else 'reddit' if host in {'www.reddit.com', 'oauth.reddit.com'} else 'cryptopanic' if host == 'cryptopanic.com' else host
        assert host in {'blog.uniswap.org', 'gov.uniswap.org', 'api.x.com', 'www.reddit.com', 'oauth.reddit.com', 'cryptopanic.com'}
        if key in self.failures:
            return httpx.Response(self.failures[key], headers={'Retry-After': '120'}, text='fake_cp_DO_NOT_LOG fake_x_DO_NOT_LOG')
        if key in self.responses:
            return httpx.Response(200, json=self.responses[key])
        if host == 'blog.uniswap.org':
            post = {'__typename': 'BlogPost', 'title': 'Official Uniswap update', 'slug': 'official-update', 'date': NOW.isoformat()}
            return httpx.Response(200, text='<script id="__NEXT_DATA__">'+json.dumps({'props': {'pageProps': {'post': post}}})+'</script>')
        if host == 'gov.uniswap.org':
            return httpx.Response(200, text='<rss><channel/></rss>')
        if key == 'x':
            assert request.headers['Authorization'] == 'Bearer '+CONFIG['X_BEARER_TOKEN']
            assert path == '/2/tweets/search/recent' and 'Uniswap' in request.url.params['query']
            return httpx.Response(200, json={'data': [
                {'id': '100', 'text': 'Uniswap v3 ETH / USDC pool update', 'created_at': NOW.isoformat()},
                {'id': '101', 'text': 'UNI university reunion', 'created_at': NOW.isoformat()}],
                'meta': {'result_count': 2, 'next_token': 'NEVER_FOLLOW_ANOTHER_PAGE'}})
        if host == 'www.reddit.com':
            assert request.method == 'POST' and path == '/api/v1/access_token'
            basic = base64.b64encode((CONFIG['REDDIT_CLIENT_ID']+':'+CONFIG['REDDIT_CLIENT_SECRET']).encode()).decode()
            assert request.headers['Authorization'] == 'Basic '+basic
            assert b'grant_type=client_credentials' in request.content or b'grant_type=refresh_token' in request.content
            return httpx.Response(200, json={'access_token': 'fake_generated_reddit_DO_NOT_LOG', 'expires_in': 3600})
        if key == 'reddit':
            assert request.headers['Authorization'].startswith('Bearer ')
            assert request.headers['User-Agent'] == CONFIG['REDDIT_USER_AGENT']
            assert path == '/r/Uniswap/new' and request.url.params['limit'] == '25'
            return httpx.Response(200, json={'data': {'children': [
                {'kind': 't3', 'data': {'title': 'Community pool discussion', 'subreddit': 'Uniswap', 'created_utc': NOW.timestamp(), 'permalink': '/r/Uniswap/comments/abc123/discussion/'}},
                {'kind': 't3', 'data': {'title': 'Unrelated subreddit', 'subreddit': 'weather', 'created_utc': NOW.timestamp(), 'permalink': '/r/weather/comments/abc12/rain/'}}]}})
        assert path == '/api/growth/v2/posts/'
        assert request.url.params['auth_token'] == CONFIG['CRYPTOPANIC_API_TOKEN']
        assert request.url.params['currencies'] == 'UNI' and request.url.params['public'] == 'true'
        return httpx.Response(200, json={'next': 'https://evil.invalid/?auth_token=DO_NOT_FOLLOW', 'results': [
            {'title': 'Uniswap new liquidity update', 'url': 'https://cryptopanic.com/news/123/update/', 'published_at': NOW.isoformat(), 'currencies': [{'code': 'UNI'}]},
            {'title': 'An unrelated price story', 'url': 'https://cryptopanic.com/news/124/story/', 'published_at': NOW.isoformat(), 'currencies': [{'code': 'BTC'}]},
            {'title': 'Uniswap unsafe credentials link', 'url': 'https://cryptopanic.com/news/125/?auth_token=unsafe', 'published_at': NOW.isoformat()}]})


def feed(upstream, config=None, enabled=True):
    service = SimpleNamespace(market=SimpleNamespace(registry=lambda: ({POOL['id']: POOL}, 'fixture', {})))
    return news.NewsFeed(service, transport=httpx.MockTransport(upstream), social_config=CONFIG if config is None else config, enabled=enabled)


@pytest.fixture(autouse=True)
def frozen_clock(monkeypatch):
    monkeypatch.setattr(news, '_now', lambda: NOW)


def test_three_real_api_contracts_filter_noise_and_do_not_leak_credentials(caplog):
    upstream = Upstream(); monitor = feed(upstream)
    caplog.set_level(logging.INFO, logger='httpx')
    async def scenario():
        await monitor.refresh()
        result = monitor.snapshot(POOL['id'])
        assert all(source['status'] == 'ok' for source in result['sources'])
        assert {item['source_id'] for item in result['items']} == {'uniswap_blog', 'x', 'reddit', 'cryptopanic'}
        assert len(result['items']) == 4
        assert all(secret not in json.dumps(result) for name, secret in CONFIG.items() if 'TOKEN' in name or 'SECRET' in name)
        assert not any('unrelated' in item['title'].lower() or 'university' in item['title'].lower() for item in result['items'])
        assert all('auth_token=' not in item['url'] for item in result['items'])
        assert result['browser_refresh_seconds'] == 30 and result['refresh_interval_seconds'] == 60
        assert len(upstream.calls) == 6
        await monitor.refresh(); assert len(upstream.calls) == 6
        await monitor.stop()
    asyncio.run(scenario())
    assert 'fake_cp_DO_NOT_LOG' not in caplog.text and 'fake_x_DO_NOT_LOG' not in caplog.text


def test_oauth_cache_and_incremental_x_cursor_are_shared_across_polls():
    upstream = Upstream(); monitor = feed(upstream)
    async def scenario():
        await monitor.refresh(); await monitor.refresh(force=True)
        x_calls = [r for r in upstream.calls if r.url.host == 'api.x.com']
        assert len(x_calls) == 2 and 'since_id' not in x_calls[0].url.params
        assert x_calls[1].url.params['since_id'] == '101'
        assert len([r for r in upstream.calls if r.url.path == '/api/v1/access_token']) == 1
        assert len([i for i in monitor.snapshot(POOL['id'])['items'] if i['source_id']=='x']) == 1
        await monitor.stop()
    asyncio.run(scenario())


@pytest.mark.parametrize('code,status', [(401,'auth_error'),(402,'access_denied'),(403,'access_denied'),(429,'rate_limited'),(503,'error'),(302,'error')])
def test_provider_failures_keep_last_good_and_honor_backoff_without_leaking_error(code,status):
    upstream = Upstream(); monitor = feed(upstream)
    async def scenario():
        await monitor.refresh(); before = monitor.snapshot(POOL['id'])
        upstream.failures['cryptopanic'] = code
        await monitor.refresh(force=True)
        result = monitor.snapshot(POOL['id']); source = next(s for s in result['sources'] if s['id']=='cryptopanic')
        assert source['status']==status and source['http_status']==code and source['next_retry_at']
        assert [i for i in result['items'] if i['source_id']=='cryptopanic'] == [i for i in before['items'] if i['source_id']=='cryptopanic']
        count = len([r for r in upstream.calls if r.url.host=='cryptopanic.com'])
        await monitor.refresh(force=True)
        assert len([r for r in upstream.calls if r.url.host=='cryptopanic.com']) == count
        assert 'fake_cp_DO_NOT_LOG' not in json.dumps(result)
        assert next(s for s in result['sources'] if s['id']=='x')['status']=='ok'
        await monitor.stop()
    asyncio.run(scenario())


def test_no_credentials_or_disabled_configuration_never_calls_social_apis():
    for config,enabled in [({},True),(CONFIG,False)]:
        upstream = Upstream(); monitor = feed(upstream,config=config,enabled=enabled)
        async def scenario():
            await monitor.refresh(force=True)
            result = monitor.snapshot(POOL['id'])
            assert not any(r.url.host in {'api.x.com','oauth.reddit.com','www.reddit.com','cryptopanic.com'} for r in upstream.calls)
            social = [s for s in result['sources'] if s['id'] in {'x','reddit','cryptopanic'}]
            assert all(s['status']==('disabled' if not enabled else 'not_connected') for s in social)
            await monitor.stop()
        asyncio.run(scenario())


def test_x_daily_call_cap_does_not_make_an_extra_paid_request():
    upstream = Upstream(); monitor = feed(upstream,config={**CONFIG,'X_MAX_REQUESTS_PER_DAY':'1'})
    async def scenario():
        await monitor.refresh(); await monitor.refresh(force=True)
        source = next(s for s in monitor.snapshot(POOL['id'])['sources'] if s['id']=='x')
        assert source['status']=='quota_paused' and source['next_retry_at']
        assert len([r for r in upstream.calls if r.url.host=='api.x.com'])==1
        await monitor.stop()
    asyncio.run(scenario())


@pytest.mark.parametrize('key,bad', [('x',{'meta':[],'data':[]}),('reddit',{'data':[]}),('cryptopanic',{'results':None})])
def test_malformed_provider_cannot_kill_other_sources(key,bad):
    upstream = Upstream(); upstream.responses[key] = bad; monitor = feed(upstream)
    async def scenario():
        await monitor.refresh()
        sources = {s['id']:s for s in monitor.snapshot(POOL['id'])['sources']}
        assert sources[key]['status'] in {'error','auth_error'}
        assert sources['uniswap_blog']['status']=='ok'
        await monitor.stop()
    asyncio.run(scenario())


def test_dotenv_is_allowlisted_literal_and_does_not_override_shell(tmp_path,monkeypatch):
    path = tmp_path/'.env'
    path.write_text('# comment\nX_BEARER_TOKEN="literal$()#token"\nREDDIT_CLIENT_ID=local # comment\nPYTHONPATH=unsafe\nREDDIT_CLIENT_SECRET="unterminated\n',encoding='utf-8')
    values = read_local_environment(path)
    assert values=={'X_BEARER_TOKEN':'literal$()#token','REDDIT_CLIENT_ID':'local'}
    monkeypatch.setenv('X_BEARER_TOKEN','from-shell'); monkeypatch.delenv('REDDIT_CLIENT_ID',raising=False)
    load_local_environment(path)
    import os
    assert os.environ['X_BEARER_TOKEN']=='from-shell' and os.environ['REDDIT_CLIENT_ID']=='local'


def test_refresh_token_grant_and_access_token_option_need_no_password():
    upstream = Upstream(); monitor = feed(upstream,config={**CONFIG,'REDDIT_REFRESH_TOKEN':'fake-refresh'})
    async def scenario():
        await monitor.refresh()
        request = next(r for r in upstream.calls if r.url.path=='/api/v1/access_token')
        assert b'grant_type=refresh_token' in request.content and b'password=' not in request.content
        await monitor.stop()
    asyncio.run(scenario())

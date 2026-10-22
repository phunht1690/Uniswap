"""Public Uniswap headlines, cached independently of simulation inputs.

Public sources and authenticated social APIs use independent refresh schedules.
No article bodies, credentials, or news records are written to research data.
"""
import asyncio
import copy
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
from html import unescape
from html.parser import HTMLParser
import json
import math
import re
import threading
import time
from urllib.parse import urlencode, urlsplit
import xml.etree.ElementTree as ET

import httpx
from src.data.news_providers import SocialProviders, ProviderFailure

LOOKBACK_DAYS = 90
MAX_BYTES = 2_000_000
PUBLIC_SOURCES = {
    'uniswap_blog': ('Uniswap Labs Blog', 'https://blog.uniswap.org/'),
    'uniswap_governance': ('Diễn đàn quản trị Uniswap', 'https://gov.uniswap.org/latest.rss'),
}
SOCIAL_SOURCES = {
    'x': ('X', 'https://x.com/Uniswap', 'Chưa kết nối API. Cần ứng dụng và quyền truy cập X; liên kết bên dưới mở tìm kiếm trên X.'),
    'reddit': ('Reddit', 'https://www.reddit.com/r/Uniswap/', 'Chưa kết nối API. Cần quyền truy cập được Reddit chấp thuận; liên kết bên dưới mở tìm kiếm trong r/Uniswap.'),
    'cryptopanic': ('CryptoPanic', 'https://cryptopanic.com/', 'Chưa kết nối API. Chưa có nguồn công khai không cần khóa được xác minh; mở CryptoPanic và tìm Uniswap.'),
}
ALIASES = {
    'WETH': ('WETH', 'ETH', 'Ethereum', 'Ether', 'Wrapped Ether'),
    'WBTC': ('WBTC', 'Wrapped Bitcoin', 'Wrapped BTC'),
    'USDC': ('USDC', 'USD Coin'), 'USDT': ('USDT', 'Tether'),
    'ARB': ('ARB', 'Arbitrum'),
}


def _now():
    return datetime.now(timezone.utc)


def _plain(text, limit=500):
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]*>', ' ', str(text or '')))).strip()[:limit]


def _date(value, now):
    try:
        value = str(value)
        result = datetime.fromisoformat(value.replace('Z', '+00:00')) if re.match(r'^\d{4}-', value) else parsedate_to_datetime(value)
        if result.tzinfo is None:
            raise ValueError('Missing timezone')
        result = result.astimezone(timezone.utc)
        if now-timedelta(days=LOOKBACK_DAYS) <= result <= now:
            return result.isoformat()
    except (ValueError, TypeError, OverflowError):
        pass
    return None


def _safe_url(value, host):
    try:
        url = str(value)
        parts = urlsplit(url)
        if len(url) <= 2048 and not re.search(r'[\x00-\x20]', url) and parts.scheme == 'https' and parts.hostname == host and not parts.username and not parts.password and parts.port in (None, 443):
            return url
    except (ValueError, TypeError):
        pass
    return None


class _NextData(HTMLParser):
    def __init__(self):
        super().__init__(); self.active = False; self.data = []

    def handle_starttag(self, tag, attrs):
        if tag == 'script' and dict(attrs).get('id') == '__NEXT_DATA__':
            self.active = True

    def handle_endtag(self, tag):
        if tag == 'script':
            self.active = False

    def handle_data(self, text):
        if self.active:
            self.data.append(text)


def parse_blog(text, now):
    parser = _NextData(); parser.feed(text)
    try:
        data = json.loads(''.join(parser.data))['props']['pageProps']
    except (ValueError, TypeError, KeyError):
        raise ValueError('Unrecognized blog format') from None
    posts = []

    def walk(value, depth=0):
        if depth > 30:
            return
        if isinstance(value, dict):
            if value.get('__typename') == 'BlogPost':
                posts.append(value)
            else:
                for child in value.values():
                    walk(child, depth+1)
        elif isinstance(value, list):
            for child in value[:300]:
                walk(child, depth+1)
    walk(data)
    if not posts:
        raise ValueError('Missing blog posts')
    rows = []
    for item in posts[:300]:
        slug = item.get('slug', '')
        if not isinstance(slug, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9-]{0,299}', slug):
            continue
        published = _date(item.get('date'), now)
        title = _plain(item.get('title'), 300)
        if title and published:
            rows.append({'title': title, 'url': 'https://blog.uniswap.org/'+slug,
                         'published_at': published, 'summary': _plain(item.get('description'), 1500)})
    return rows


def parse_governance(text, now):
    if re.search(r'<!\s*(?:DOCTYPE|ENTITY)', text, re.I):
        raise ValueError('Unsupported XML declarations')
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        raise ValueError('Invalid RSS') from None
    if root.tag != 'rss' or root.find('channel') is None:
        raise ValueError('Unrecognized RSS format')
    rows = []
    for item in root.findall('./channel/item')[:100]:
        url = _safe_url(item.findtext('link'), 'gov.uniswap.org')
        published = _date(item.findtext('pubDate'), now)
        title = _plain(item.findtext('title'), 300)
        if url and published and title:
            rows.append({'title': title, 'url': url, 'published_at': published,
                         'summary': _plain(item.findtext('description'), 1500)})
    return rows


def classify(item, pool):
    text = item['title']+' '+item.get('summary', '')
    topics = [token for token in dict.fromkeys((pool['base'], pool['quote']))
              if any(re.search(r'(?<![\w])'+re.escape(alias)+r'(?![\w])', text, re.I)
                     for alias in ALIASES.get(token, (token,)))]
    address = pool.get('address', '')
    exact_pool = bool(re.fullmatch(r'0x[0-9a-fA-F]{40}', address) and re.search(r'(?<![0-9a-fA-F])'+re.escape(address)+r'(?![0-9a-fA-F])', text, re.I))
    relevance = 'pool' if exact_pool else 'token' if topics else 'protocol'
    version = 'v4' if re.search(r'\bv4\b', text, re.I) else 'v3' if re.search(r'\bv3\b', text, re.I) else 'ecosystem'
    return {'topics': topics, 'relevance': relevance,
            'relevance_label': {'pool': 'Có địa chỉ pool', 'token': 'Token liên quan', 'protocol': 'Hệ sinh thái Uniswap'}[relevance],
            'version': version}


class NewsFeed:
    def __init__(self, service, interval_seconds=300, transport=None, enabled=True, social_config=None):
        self.interval_seconds = float(interval_seconds)
        if not math.isfinite(self.interval_seconds) or self.interval_seconds <= 0:
            raise ValueError('News interval must be positive and finite')
        self.enabled = enabled
        try:
            registry = service.market.registry()
            self._pools = copy.deepcopy(registry[0]) if registry is not None else {}
        except Exception:
            self._pools = {}
        self._transport = transport; self._client = None; self._task = None
        self._lock = threading.RLock(); self._refresh_lock = asyncio.Lock()
        self._stop_event = asyncio.Event(); self._next_refresh = 0.
        self._items = {key: [] for key in PUBLIC_SOURCES}
        self._sources = {key: {'id': key, 'name': name, 'url': url if key == 'uniswap_blog' else 'https://gov.uniswap.org/',
                              'status': 'pending' if enabled else 'disabled', 'last_checked_at': None,
                              'fetched_at': None, 'age_seconds': None, 'message': 'Đang chờ lấy tin công khai.' if enabled else 'Tự cập nhật tin đang tắt.'}
                         for key, (name, url) in PUBLIC_SOURCES.items()}
        self._social = SocialProviders(social_config, transport=transport)
        self._social_due = {}; self._social_retry = {}
        for key, (name, url, _) in SOCIAL_SOURCES.items():
            missing = self._social.missing(key)
            self._items[key] = []
            self._social_due[key] = 0.; self._social_retry[key] = 0.
            self._sources[key] = {'id': key, 'name': name, 'url': url, 'status': 'not_connected' if missing else 'pending' if enabled else 'disabled',
                'last_checked_at': None, 'fetched_at': None, 'age_seconds': None,
                'message': 'Thiếu cấu hình: '+', '.join(missing)+'. Xem hướng dẫn API; điền .env rồi khởi động lại.' if missing else 'Đang chờ lần gọi API đầu tiên.' if enabled else 'Tự cập nhật tin đang tắt.',
                'missing_configuration': missing, 'configured': not missing,
                'interval_seconds': self._social.intervals[key], 'next_retry_at': None, 'http_status': None}

    def snapshot(self, pool_id):
        if pool_id not in self._pools:
            raise ValueError('Unknown pool')
        now = _now(); pool = self._pools[pool_id]
        with self._lock:
            sources = copy.deepcopy(list(self._sources.values()))
            items = copy.deepcopy([item for rows in self._items.values() for item in rows])
        for source in sources:
            if source['fetched_at']:
                source['age_seconds'] = max(0., (now-datetime.fromisoformat(source['fetched_at'])).total_seconds())
                if source['status'] == 'ok' and source['age_seconds'] > 3*source.get('interval_seconds', self.interval_seconds):
                    source.update(status='stale', message='Chưa kiểm tra lại nguồn đúng chu kỳ; đang giữ tin lấy gần nhất.')
            source['search_url'] = source['url']
        for key, (name, url, message) in SOCIAL_SOURCES.items():
            search = 'https://x.com/search?'+urlencode({'q': '(Uniswap OR from:Uniswap) ('+pool['base']+' OR '+pool['quote']+')', 'f': 'live'}) if key == 'x' else 'https://www.reddit.com/r/Uniswap/search/?'+urlencode({'q': pool['base']+' OR '+pool['quote'], 'restrict_sr': 'on', 'sort': 'new'}) if key == 'reddit' else url
            next(source for source in sources if source['id'] == key)['search_url'] = search
        result = []
        for item in items:
            if _date(item['published_at'], now):
                item.update(classify(item, pool)); item.pop('summary', None); result.append(item)
        result.sort(key=lambda row: row['published_at'], reverse=True)
        active_intervals = [s['interval_seconds'] for s in sources if s.get('configured')]
        return {'enabled': self.enabled, 'server_time': now.isoformat(), 'refresh_interval_seconds': min([self.interval_seconds]+active_intervals),
                'public_interval_seconds': self.interval_seconds, 'browser_refresh_seconds': 30,
                'lookback_days': LOOKBACK_DAYS, 'pool': {key: pool.get(key, pool_id if key == 'id' else None) for key in ('id', 'base', 'quote', 'network', 'address')},
                'sources': sources, 'items': result[:100]}

    async def _read(self, url):
        if self._client is None:
            self._client = httpx.AsyncClient(transport=self._transport, follow_redirects=False,
                timeout=httpx.Timeout(12., connect=4.), limits=httpx.Limits(max_connections=2),
                headers={'User-Agent': 'RangeLab-Research/1.0', 'Accept': 'text/html,application/rss+xml'})
        async with self._client.stream('GET', url) as response:
            response.raise_for_status()
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > MAX_BYTES:
                    raise ValueError('News response too large')
            return body.decode('utf-8')

    async def _fetch_source(self, key):
        checked = _now().isoformat()
        try:
            async with asyncio.timeout(18.):
                text = await self._read(PUBLIC_SOURCES[key][1])
            parser = parse_blog if key == 'uniswap_blog' else parse_governance
            rows = parser(text, _now()); fetched = _now().isoformat(); seen = set(); items = []
            for row in sorted(rows, key=lambda row: row['published_at'], reverse=True):
                if row['url'] in seen:
                    continue
                seen.add(row['url'])
                items.append({**row, 'id': hashlib.sha256(row['url'].encode()).hexdigest()[:24],
                              'source_id': key, 'source_name': PUBLIC_SOURCES[key][0], 'fetched_at': fetched})
            with self._lock:
                self._items[key] = items[:100]
                self._sources[key].update(status='ok', fetched_at=fetched, last_checked_at=checked,
                    message='Đã kiểm tra nguồn công khai. Chỉ lấy tiêu đề và liên kết; không bảo đảm bao phủ mọi bài đăng.')
        except (httpx.HTTPError, ValueError, UnicodeError, RecursionError, TimeoutError):
            with self._lock:
                source = self._sources[key]
                source.update(status='stale' if source['fetched_at'] else 'error', last_checked_at=checked,
                    message='Nguồn chưa phản hồi hoặc định dạng đã thay đổi. '+('Đang giữ tin lấy thành công gần nhất.' if source['fetched_at'] else 'Chưa có tin được lấy thành công.'))

    async def refresh(self, force=False):
        if not self.enabled:
            return
        async with self._refresh_lock:
            public_due = force or time.monotonic() >= self._next_refresh
            tasks = [self._fetch_source(key) for key in PUBLIC_SOURCES] if public_due else []
            for key in SOCIAL_SOURCES:
                if not self._social.missing(key) and time.monotonic() >= self._social_retry[key] and (force or time.monotonic() >= self._social_due[key]):
                    tasks.append(self._fetch_social(key))
            if tasks:await asyncio.gather(*tasks)
            if public_due:self._next_refresh = time.monotonic()+self.interval_seconds

    async def _fetch_social(self, key):
        checked = _now().isoformat(); delay = self._social.intervals[key]
        try:
            async with asyncio.timeout(20.):
                rows, more = await self._social.fetch(key, _now())
            fetched = _now().isoformat(); merged = {}
            with self._lock:
                if key == 'x':
                    merged = {row['url']: row for row in self._items[key] if _date(row['published_at'], _now())}
                for row in rows:
                    merged[row['url']] = {**row, 'id': hashlib.sha256(row['url'].encode()).hexdigest()[:24],
                        'source_id': key, 'source_name': SOCIAL_SOURCES[key][0], 'fetched_at': fetched}
                self._items[key] = sorted(merged.values(), key=lambda row: row['published_at'], reverse=True)[:100]
                self._sources[key].update(status='ok', fetched_at=fetched, last_checked_at=checked,
                    next_retry_at=None, http_status=200,
                    message='Đã lấy API thật. Một trang mỗi chu kỳ; không bảo đảm đầy đủ bài đăng.'+(' Nguồn còn các trang chưa lấy.' if more else ''))
        except (ProviderFailure, httpx.HTTPError, ValueError, TypeError, TimeoutError) as error:
            delay = max(delay, error.retry_seconds if isinstance(error, ProviderFailure) else 300)
            self._social_retry[key] = time.monotonic()+delay
            with self._lock:
                self._sources[key].update(status=error.status if isinstance(error, ProviderFailure) else 'error',
                    last_checked_at=checked, http_status=error.http_status if isinstance(error, ProviderFailure) else None,
                    next_retry_at=(_now()+timedelta(seconds=delay)).isoformat(),
                    message=(error.message if isinstance(error, ProviderFailure) else 'Chưa lấy được API do kết nối hoặc định dạng phản hồi.')+
                            (' Đang giữ lần lấy thành công gần nhất.' if self._sources[key]['fetched_at'] else ' Chưa có tin lấy thành công.'))
        self._social_due[key] = time.monotonic()+delay

    async def _loop(self):
        while not self._stop_event.is_set():
            await self.refresh()
            try:
                deadlines = [self._next_refresh]+[self._social_due[key] for key in SOCIAL_SOURCES if not self._social.missing(key)]
                await asyncio.wait_for(self._stop_event.wait(), timeout=max(.05, min(deadlines)-time.monotonic()))
            except asyncio.TimeoutError:
                pass

    async def start(self):
        if self.enabled and (self._task is None or self._task.done()):
            self._stop_event.clear(); self._task = asyncio.create_task(self._loop(), name='rangelab-news')

    async def stop(self):
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        async with self._refresh_lock:
            if self._client is not None:
                await self._client.aclose(); self._client = None
            await self._social.close()

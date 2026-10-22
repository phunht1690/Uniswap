"""Authenticated, read-only official news APIs. One bounded page per poll.

Secrets are used only on their provider's fixed HTTPS origin. No login scraping,
account creation, paid-plan activation, pagination URLs or credentials in output.
"""
import asyncio
import base64
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import logging
import re
import time
from urllib.parse import quote, quote_plus, urlsplit

import httpx

API_URLS = {
    'x': 'https://api.x.com/2/tweets/search/recent',
    'reddit': 'https://oauth.reddit.com/r/Uniswap/new',
}
SOCIAL_KEYS = ('x', 'reddit', 'cryptopanic')


def _integer(config, name, default, low, high):
    try:
        return max(low, min(high, int(config.get(name, default))))
    except (ValueError, TypeError, OverflowError):
        return default


class ProviderFailure(Exception):
    def __init__(self, status, message, retry_seconds=300, http_status=None):
        super().__init__(message)
        self.status = status; self.message = message
        self.retry_seconds = retry_seconds; self.http_status = http_status


class _HideSecrets(logging.Filter):
    def __init__(self, secrets):
        super().__init__(); self.secrets = secrets

    def filter(self, record):
        text = record.getMessage()
        for secret in self.secrets:
            for value in {secret, quote(secret, safe=''), quote_plus(secret)}:
                if value:
                    text = text.replace(value, '[redacted]')
        text = re.sub(r'([?&]auth_token=)[^\s&"\']+', r'\1[redacted]', text)
        record.msg = text; record.args = ()
        return True


def _retry(headers, now):
    value = headers.get('retry-after')
    try:
        delay = float(value)
    except (ValueError, TypeError):
        try:
            delay = (parsedate_to_datetime(value)-now).total_seconds()
        except (ValueError, TypeError, OverflowError):
            try:
                delay = float(headers.get('x-rate-limit-reset', ''))-now.timestamp()
            except (ValueError, TypeError, OverflowError):
                delay = 900
    return max(60, min(86400, delay)) if delay == delay else 900


class SocialProviders:
    def __init__(self, config=None, transport=None):
        self.config = dict(config or {}); self.transport = transport; self.client = None
        self._reddit_token = None; self._reddit_expires = 0.; self._since_id = None
        self._x_day = None; self._x_requests = 0
        self.intervals = {
            'x': _integer(self.config, 'X_POLL_SECONDS', 300, 60, 86400),
            'reddit': _integer(self.config, 'REDDIT_POLL_SECONDS', 60, 60, 86400),
            'cryptopanic': _integer(self.config, 'CRYPTOPANIC_POLL_SECONDS', 60, 60, 86400),
        }
        secrets = tuple(str(v) for k, v in self.config.items() if any(s in k for s in ('TOKEN', 'SECRET')) and v)
        if self.config.get('REDDIT_CLIENT_ID') and self.config.get('REDDIT_CLIENT_SECRET'):
            secrets += (base64.b64encode((self.config['REDDIT_CLIENT_ID']+':'+self.config['REDDIT_CLIENT_SECRET']).encode()).decode(),)
        self._filter = _HideSecrets(secrets)
        self._loggers = [logging.getLogger(name) for name in (
            'httpx', 'httpcore.connection', 'httpcore.http11', 'httpcore.http2',
            'httpcore.proxy', 'httpcore.socks', 'httpcore._backends.auto')]
        if secrets:
            for logger in self._loggers:
                logger.addFilter(self._filter)

    def missing(self, key):
        c = self.config
        if key == 'x':
            return [] if c.get('X_BEARER_TOKEN') else ['X_BEARER_TOKEN']
        if key == 'cryptopanic':
            return [] if c.get('CRYPTOPANIC_API_TOKEN') else ['CRYPTOPANIC_API_TOKEN']
        missing = [] if c.get('REDDIT_USER_AGENT') else ['REDDIT_USER_AGENT']
        if not c.get('REDDIT_ACCESS_TOKEN') and not (c.get('REDDIT_CLIENT_ID') and c.get('REDDIT_CLIENT_SECRET')):
            missing += ['REDDIT_ACCESS_TOKEN hoặc REDDIT_CLIENT_ID + REDDIT_CLIENT_SECRET']
        return missing

    async def _json(self, method, url, *, now, **kwargs):
        if self.client is None:
            self.client = httpx.AsyncClient(transport=self.transport, follow_redirects=False,
                timeout=httpx.Timeout(12., connect=4.), limits=httpx.Limits(max_connections=3),
                headers={'Accept': 'application/json', 'User-Agent': 'RangeLab-News/1.0'})
        async with self.client.stream(method, url, **kwargs) as response:
            status = response.status_code
            if status == 429:
                raise ProviderFailure('rate_limited', 'Nguồn đang giới hạn lượt gọi; sẽ thử lại sau thời điểm ghi bên dưới.', _retry(response.headers, now), status)
            if status == 401:
                raise ProviderFailure('auth_error', 'Khóa hoặc OAuth token không hợp lệ/hết hạn. Kiểm tra .env rồi khởi động lại máy chủ.', 900, status)
            if status in (402, 403):
                raise ProviderFailure('access_denied', 'Tài khoản/gói API chưa có quyền, hết hạn mức hoặc không còn tín dụng. Kiểm tra tài khoản nhà cung cấp.', 1800, status)
            if status < 200 or status >= 300:
                raise ProviderFailure('error', 'Nhà cung cấp API chưa phản hồi thành công.', 300, status)
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > 2_000_000:
                    raise ProviderFailure('error', 'Phản hồi API vượt giới hạn dung lượng.', 300)
            try:
                result = json.loads(body)
            except (ValueError, UnicodeError):
                raise ProviderFailure('error', 'API không trả JSON hợp lệ.', 300) from None
            if not isinstance(result, dict):
                raise ProviderFailure('error', 'Cấu trúc phản hồi API đã thay đổi.', 300)
            return result

    async def _reddit_auth(self, now, force=False):
        c = self.config
        if c.get('REDDIT_ACCESS_TOKEN'):
            return c['REDDIT_ACCESS_TOKEN']
        if self._reddit_token and time.monotonic() < self._reddit_expires and not force:
            return self._reddit_token
        data = {'grant_type': 'refresh_token', 'refresh_token': c['REDDIT_REFRESH_TOKEN']} if c.get('REDDIT_REFRESH_TOKEN') else {'grant_type': 'client_credentials'}
        response = await self._json('POST', 'https://www.reddit.com/api/v1/access_token', now=now,
            data=data, auth=httpx.BasicAuth(c['REDDIT_CLIENT_ID'], c['REDDIT_CLIENT_SECRET']),
            headers={'User-Agent': c['REDDIT_USER_AGENT']})
        token = response.get('access_token')
        if not isinstance(token, str) or not token or response.get('error'):
            raise ProviderFailure('auth_error', 'Reddit chưa cấp OAuth token cho ứng dụng này.', 900)
        self._reddit_token = token
        self._filter.secrets += (token,)
        self._reddit_expires = time.monotonic()+_integer(response, 'expires_in', 3600, 60, 86400)-30
        return token

    async def fetch(self, key, now):
        # Import after news module initialization; normalization is shared with public feeds.
        from src.data.news import _date, _plain, _safe_url
        c = self.config; rows = []; more = False
        if key == 'x':
            day = now.date()
            if self._x_day != day:
                self._x_day = day; self._x_requests = 0
            cap = _integer(c, 'X_MAX_REQUESTS_PER_DAY', 100, 1, 10000)
            if self._x_requests >= cap:
                midnight = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc).timestamp()+86400
                raise ProviderFailure('quota_paused', 'Đã đạt giới hạn lượt gọi X trong ngày của phiên máy chủ này.', max(60, midnight-now.timestamp()))
            query = {'query': '(Uniswap OR from:Uniswap) -is:retweet -is:reply',
                     'max_results': _integer(c, 'X_MAX_RESULTS', 10, 10, 100),
                     'tweet.fields': 'created_at', 'sort_order': 'recency'}
            if self._since_id:
                query['since_id'] = self._since_id
            self._x_requests += 1
            payload = await self._json('GET', API_URLS[key], now=now, params=query,
                                       headers={'Authorization': 'Bearer '+c['X_BEARER_TOKEN']})
            if not isinstance(payload.get('meta'), dict):
                raise ProviderFailure('error', 'Cấu trúc phản hồi X đã thay đổi.', 300)
            values = payload.get('data')
            if values is None and isinstance(payload.get('meta'), dict) and payload['meta'].get('result_count') == 0 and not payload.get('errors'):
                values = []
            if not isinstance(values, list) or payload.get('errors'):
                raise ProviderFailure('error', 'X trả kết quả thiếu hoặc lỗi; chưa cập nhật mốc bài mới.', 300)
            ids = []
            for value in values[:100]:
                if not isinstance(value, dict):continue
                ident = str(value.get('id', '')); text = _plain(value.get('text'), 3000)
                published = _date(value.get('created_at'), now)
                if re.fullmatch(r'[0-9]{1,20}', ident):ids.append(int(ident))
                if re.fullmatch(r'[0-9]{1,20}', ident) and published and re.search(r'\buniswap\b', text, re.I):
                    rows.append({'title': text[:240], 'summary': text, 'url': 'https://x.com/i/web/status/'+ident, 'published_at': published})
            if ids:self._since_id = str(max(ids))
            more = bool(payload.get('meta', {}).get('next_token'))
        elif key == 'reddit':
            token = await self._reddit_auth(now)
            try:
                payload = await self._json('GET', API_URLS[key], now=now,
                    params={'limit': 25, 'raw_json': 1}, headers={'Authorization': 'Bearer '+token, 'User-Agent': c['REDDIT_USER_AGENT']})
            except ProviderFailure as error:
                if error.http_status == 401 and not c.get('REDDIT_ACCESS_TOKEN'):
                    self._reddit_token = None
                raise
            values = payload.get('data', {}).get('children') if isinstance(payload.get('data'), dict) else None
            if not isinstance(values, list):
                raise ProviderFailure('error', 'Cấu trúc danh sách Reddit đã thay đổi.', 300)
            for child in values[:100]:
                if not isinstance(child, dict) or child.get('kind') != 't3':continue
                value = child.get('data')
                if not isinstance(value, dict) or str(value.get('subreddit', '')).lower() != 'uniswap':continue
                title = _plain(value.get('title'), 300); permalink = value.get('permalink', '')
                try:published = _date(datetime.fromtimestamp(float(value.get('created_utc')), timezone.utc).isoformat(), now)
                except (ValueError, TypeError, OverflowError, OSError):continue
                if not isinstance(permalink, str) or not re.match(r'^/r/uniswap/comments/[a-z0-9]+/', permalink, re.I):continue
                url = _safe_url('https://www.reddit.com'+permalink, 'www.reddit.com')
                if title and title not in {'[removed]', '[deleted]'} and not value.get('removed_by_category') and published and url:
                    rows.append({'title': title, 'summary': _plain(value.get('selftext'), 1500), 'url': url, 'published_at': published})
        else:
            plan = c.get('CRYPTOPANIC_PLAN', 'developer').lower()
            if plan not in {'developer', 'growth', 'enterprise'}:
                raise ProviderFailure('config_error', 'CRYPTOPANIC_PLAN phải là developer, growth hoặc enterprise theo gói được cấp.', 900)
            payload = await self._json('GET', f'https://cryptopanic.com/api/{plan}/v2/posts/', now=now,
                params={'auth_token': c['CRYPTOPANIC_API_TOKEN'], 'currencies': 'UNI', 'public': 'true', 'kind': 'news'})
            values = payload.get('results')
            if not isinstance(values, list):
                raise ProviderFailure('error', 'Cấu trúc danh sách CryptoPanic đã thay đổi.', 300)
            for value in values[:100]:
                if not isinstance(value, dict):continue
                title = _plain(value.get('title'), 300); published = _date(value.get('published_at'), now)
                url = _safe_url(value.get('url'), 'cryptopanic.com')
                currencies = value.get('currencies', [])
                uni = isinstance(currencies, list) and any(isinstance(v, dict) and v.get('code') == 'UNI' for v in currencies)
                if title and published and url and (uni or re.search(r'\buniswap\b', title+' '+_plain(value.get('description'), 1500), re.I)):
                    # Provider URLs must never carry the authentication query into the browser.
                    if urlsplit(url).query:continue
                    rows.append({'title': title, 'summary': _plain(value.get('description'), 1500), 'url': url, 'published_at': published})
            more = bool(payload.get('next'))
        # All content stays in memory; public errors or reflected secrets never enter output.
        for row in rows:
            for field in ('title', 'summary'):
                for secret in self._filter.secrets:
                    row[field] = row[field].replace(secret, '[redacted]')
        return rows, more

    async def close(self):
        if self.client is not None:
            await self.client.aclose(); self.client = None
        for logger in self._loggers:
            logger.removeFilter(self._filter)

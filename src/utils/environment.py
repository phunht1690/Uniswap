"""Read a small local .env as data; never execute or interpolate its contents."""
import os
from pathlib import Path
import re

NEWS_ENV_KEYS = {
    'X_BEARER_TOKEN', 'X_POLL_SECONDS', 'X_MAX_RESULTS', 'X_MAX_REQUESTS_PER_DAY',
    'REDDIT_ACCESS_TOKEN', 'REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET',
    'REDDIT_REFRESH_TOKEN', 'REDDIT_USER_AGENT', 'REDDIT_POLL_SECONDS',
    'CRYPTOPANIC_API_TOKEN', 'CRYPTOPANIC_PLAN', 'CRYPTOPANIC_POLL_SECONDS',
}
SUPPORTED_KEYS = NEWS_ENV_KEYS | {
    'UNISWAP_LIVE_ENABLED', 'UNISWAP_NEWS_ENABLED', 'UNISWAP_STATE_DIR',
    'ETHEREUM_RPC_URL', 'ARBITRUM_RPC_URL', 'THE_GRAPH_API_KEY',
    'UNISWAP_SUBGRAPH_ID', 'GOOGLE_CLOUD_PROJECT', 'GOOGLE_APPLICATION_CREDENTIALS',
    'COINGECKO_API_KEY', 'FRED_API_KEY',
}


def read_local_environment(path: Path) -> dict:
    if not path.is_file():
        return {}
    raw = path.read_bytes()
    if len(raw) > 65536:
        raise ValueError('Local .env exceeds 64 KB.')
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeError:
        raise ValueError('Local .env must use UTF-8 encoding.') from None
    result = {}
    for line in text.splitlines():
        match = re.fullmatch(r'\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*', line)
        if not match or match[1] not in SUPPORTED_KEYS:
            continue
        value = match[2]
        if value.startswith(('"', "'")):
            quote = value[0]; end = value.find(quote, 1)
            if end < 0 or (value[end+1:].strip() and not value[end+1:].strip().startswith('#')):
                continue
            value = value[1:end]
        else:
            value = re.split(r'\s+#', value, maxsplit=1)[0].strip()
        if value:
            result[match[1]] = value
    return result


def load_local_environment(path: Path) -> None:
    for name, value in read_local_environment(path).items():
        os.environ.setdefault(name, value)

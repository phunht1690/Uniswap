"""Public USD reference histories, bounded by the provider's free history limit."""
import pandas as pd

from src.data.common import coverage_row


def fetch(context, coin="ethereum"):
    endpoint = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
    payload, meta = context.json("coingecko", endpoint, params={"vs_currency": "usd", "days": 365}, ttl=3600)
    prices = pd.DataFrame(payload.get("prices", []), columns=["time_ms", "price_usd"])
    volumes = dict(payload.get("total_volumes", []))
    prices["timestamp"] = pd.to_datetime(prices.time_ms, unit="ms", utc=True)
    prices["aggregate_market_volume_usd"] = prices.time_ms.map(volumes)
    prices["coin"], prices["source"] = coin, "coingecko"
    prices = prices.drop(columns="time_ms").sort_values("timestamp").drop_duplicates("timestamp")
    if len(prices):
        context.frame("usd_reference_" + coin, prices, "coingecko", endpoint,
                      start=prices.timestamp.min().isoformat(), end=prices.timestamp.max().isoformat(), lineage=[meta["file_path"]])
    return prices, coverage_row("coingecko", "usd_reference_" + coin, "provider_limited", prices,
                                "Free public 365-day reference; market-wide volume is never Uniswap volume; current intraday last point is not a completed daily candle.")

"""EODHD: end-of-day bars, splits and dividends."""
import os
import time
from dataclasses import dataclass

from jef_data_rc.collectors.base import BaseCollector, CollectorError, HttpTransport, RateLimiter

DEFAULT_BASE_URL = "https://eodhd.com/api"
FIAT = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD", "SEK", "NOK", "DKK", "PLN",
        "CZK", "HUF", "TRY", "ZAR", "MXN", "SGD", "HKD", "CNY", "INR", "BRL", "KRW", "RUB"}
CRYPTO_QUOTES = {"USD", "USDT", "EUR", "BTC", "ETH", "BUSD", "USDC"}


@dataclass(frozen=True)
class SplitEvent:
    date: str
    ratio: float
    split: str


def normalize_symbol(symbol):
    """Canonical EODHD TICKER.EXCHANGE for a user-typed symbol."""
    if "." in symbol:
        return symbol
    if "/" in symbol:
        base, quote = symbol.upper().split("/", 1)
        if base in FIAT and quote in FIAT:
            return f"{base}{quote}.FOREX"
        if quote in CRYPTO_QUOTES:
            return f"{base}-{quote}.CC"
        raise CollectorError(f"cannot infer exchange for pair symbol {symbol!r}")
    return f"{symbol.upper()}.US"


def parse_split(text):
    """NEW/OLD provider split string -> ratio new/old."""
    if not isinstance(text, str):
        raise ValueError(f"unparseable split string: {text!r}")
    parts = text.split("/")
    if len(parts) != 2:
        raise ValueError(f"unparseable split string: {text!r}")
    try:
        new, old = float(parts[0]), float(parts[1])
    except ValueError:
        raise ValueError(f"unparseable split string: {text!r}") from None
    if new == 0 or old == 0:
        raise ValueError(f"degenerate split string: {text!r}")
    return new / old


def _positive_close(row):
    close = row.get("close")
    if close is None:
        return False
    return float(close) > 0


class EODHDCollector(BaseCollector):
    exchange = "eodhd"
    volume_basis = "split_adjusted"

    def __init__(self, api_key=None, base_url=DEFAULT_BASE_URL, transport=None,
                 rate_limiter="default", sleep=time.sleep):
        key = api_key or os.environ.get("EODHD_API_KEY", "")
        if not key:
            raise ValueError("EODHD API key required: pass api_key= or set EODHD_API_KEY")
        self.api_key = key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        if transport is None:
            transport = HttpTransport(timeout=30.0, secrets=[key])
        if rate_limiter == "default":
            rate_limiter = RateLimiter()
        super().__init__(transport, rate_limiter=rate_limiter, sleep=sleep, secrets=[key])

    def get_eod(self, symbol, start=None, end=None):
        sym = normalize_symbol(symbol)
        params = {"api_token": self.api_key, "fmt": "json", "period": "d", "order": "a"}
        if start:
            params["from"] = start
        if end:
            params["to"] = end
        data = self.get_json(f"{self.base_url}/eod/{sym}", params, f"eod {sym}")
        if not isinstance(data, list):
            raise CollectorError(f"eod {sym}: expected a JSON list")
        kept = []
        seen = set()
        for row in data:
            if not _positive_close(row):
                continue
            if row["date"] in seen:
                continue
            seen.add(row["date"])
            kept.append(row)
        return sorted(kept, key=lambda row: row["date"])

    def get_splits(self, symbol):
        sym = normalize_symbol(symbol)
        params = {"api_token": self.api_key, "fmt": "json"}
        data = self.get_json(f"{self.base_url}/splits/{sym}", params, f"splits {sym}")
        if not isinstance(data, list):
            raise CollectorError(f"splits {sym}: expected a JSON list")
        events = [SplitEvent(date=entry["date"], ratio=parse_split(entry["split"]),
                             split=entry["split"]) for entry in data]
        return sorted(events, key=lambda event: event.date)

    def get_dividends(self, symbol):
        sym = normalize_symbol(symbol)
        params = {"api_token": self.api_key, "fmt": "json"}
        data = self.get_json(f"{self.base_url}/div/{sym}", params, f"div {sym}")
        if not isinstance(data, list):
            raise CollectorError(f"div {sym}: expected a JSON list")
        return sorted(data, key=lambda entry: entry.get("date") or "")

    def search(self, query, exchange=None):
        params = {"api_token": self.api_key, "fmt": "json"}
        if exchange:
            params["exchange"] = exchange
        return self.get_json(f"{self.base_url}/search/{query}", params, f"search {query}")

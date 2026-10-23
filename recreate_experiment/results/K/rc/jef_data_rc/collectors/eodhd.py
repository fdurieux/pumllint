"""The EODHD collector: end-of-day bars, splits and dividends."""
from __future__ import annotations

import datetime as _dt
import os
import time
from typing import NamedTuple

from .base import BaseCollector, CollectorError, RateLimiter

DEFAULT_BASE_URL = "https://eodhd.com/api"

FIAT = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD", "SEK", "NOK", "DKK",
        "PLN", "CZK", "HUF", "TRY", "ZAR", "MXN", "SGD", "HKD", "CNY", "INR", "BRL",
        "KRW", "RUB"}
CRYPTO_QUOTES = {"USD", "USDT", "EUR", "BTC", "ETH", "BUSD", "USDC"}


class SplitEvent(NamedTuple):
    date: _dt.date
    ratio: float
    split_string: str | None = None


def normalize_symbol(symbol):
    """Canonical EODHD TICKER.EXCHANGE form of a symbol."""
    if "." in symbol:
        return symbol
    if "/" in symbol:
        base, quote = symbol.upper().split("/", 1)
        if base in FIAT and quote in FIAT:
            return f"{base}{quote}.FOREX"
        if quote in CRYPTO_QUOTES:
            return f"{base}-{quote}.CC"
        raise CollectorError(f"cannot infer exchange for pair symbol {symbol!r}")
    return f"{symbol}.US"


def parse_split(text):
    """The ratio new/old of a provider split string NEW/OLD."""
    parts = text.split("/") if isinstance(text, str) else []
    if len(parts) != 2:
        raise ValueError(f"unparseable split string: {text!r}")
    try:
        new, old = float(parts[0]), float(parts[1])
    except ValueError:
        raise ValueError(f"unparseable split string: {text!r}") from None
    if new == 0 or old == 0:
        raise ValueError(f"degenerate split string: {text!r}")
    return new / old


class EODHDCollector(BaseCollector):
    exchange = "eodhd"
    volume_basis = "split_adjusted"

    def __init__(self, api_key=None, base_url=DEFAULT_BASE_URL, transport=None,
                 rate_limiter="default", sleep=time.sleep):
        key = api_key if api_key else os.environ.get("EODHD_API_KEY", "")
        if not key:
            raise ValueError("EODHD API key required: pass api_key= or set EODHD_API_KEY")
        self.api_key = key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        if rate_limiter == "default":
            rate_limiter = RateLimiter()
        super().__init__(transport=transport, rate_limiter=rate_limiter, sleep=sleep,
                         secrets=(key,))

    def _params(self, **extra):
        params = {"api_token": self.api_key, "fmt": "json"}
        params.update(extra)
        return params

    def get_eod(self, symbol, start=None, end=None):
        sym = normalize_symbol(symbol)
        params = self._params(period="d", order="a")
        if start:
            params["from"] = start
        if end:
            params["to"] = end
        body = self.get_json(f"{self.base_url}/eod/{sym}", params, f"eod {sym}")
        if not isinstance(body, list):
            raise CollectorError(f"eod {sym}: expected a JSON list")
        rows = []
        seen = set()
        for row in body:
            close = row.get("close")
            if close is None or float(close) <= 0:
                continue
            date = row.get("date")
            if date in seen:
                continue
            seen.add(date)
            rows.append(row)
        return sorted(rows, key=lambda r: r["date"])

    def get_splits(self, symbol):
        sym = normalize_symbol(symbol)
        body = self.get_json(f"{self.base_url}/splits/{sym}", self._params(), f"splits {sym}")
        if not isinstance(body, list):
            raise CollectorError(f"splits {sym}: expected a JSON list")
        events = [SplitEvent(_dt.date.fromisoformat(entry["date"]),
                             parse_split(entry["split"]), entry["split"])
                  for entry in body]
        return sorted(events, key=lambda e: e.date)

    def get_dividends(self, symbol):
        sym = normalize_symbol(symbol)
        body = self.get_json(f"{self.base_url}/div/{sym}", self._params(), f"div {sym}")
        if not isinstance(body, list):
            raise CollectorError(f"div {sym}: expected a JSON list")
        return sorted(body, key=lambda e: e.get("date", ""))

    def search(self, query, exchange=None):
        params = self._params()
        if exchange:
            params["exchange"] = exchange
        return self.get_json(f"{self.base_url}/search/{query}", params, f"search {query}")

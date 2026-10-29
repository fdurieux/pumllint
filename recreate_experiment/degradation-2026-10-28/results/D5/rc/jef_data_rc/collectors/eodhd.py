"""EODHD collector: EOD bars, splits and dividends."""
from __future__ import annotations

import datetime as _dt
import os
import time

from .base import BaseCollector, CollectorError, HttpTransport

DEFAULT_BASE_URL = "https://eodhd.com/api"

FIAT = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD", "SEK", "NOK", "DKK",
        "PLN", "CZK", "HUF", "TRY", "ZAR", "MXN", "SGD", "HKD", "CNY", "INR", "BRL",
        "KRW", "RUB"}
CRYPTO_QUOTES = {"USD", "USDT", "EUR", "BTC", "ETH", "BUSD", "USDC"}


class SplitEvent:
    """One split: effective date, ratio (new/old) and the provider's string."""

    __slots__ = ("date", "ratio", "split")

    def __init__(self, date, ratio, split=None):
        self.date = date
        self.ratio = ratio
        self.split = split

    def __repr__(self):
        return f"SplitEvent({self.date!r}, {self.ratio!r}, {self.split!r})"


def normalize_symbol(symbol: str) -> str:
    """Canonical TICKER.EXCHANGE for a user-typed symbol."""
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


def parse_split_ratio(text) -> float:
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


class EODHDCollector(BaseCollector):
    exchange = "eodhd"
    volume_basis = "split_adjusted"

    def __init__(self, api_key=None, base_url=None, transport=None, *, rate_limit=True,
                 sleep=time.sleep):
        key = api_key or os.environ.get("EODHD_API_KEY", "")
        if not key:
            raise ValueError("EODHD API key required: pass api_key= or set EODHD_API_KEY")
        self.api_key = key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        if transport is None:
            transport = HttpTransport(secrets=[key])
        super().__init__(transport, rate_limit=rate_limit, sleep=sleep, secrets=[key])

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
        rows = self.get_json(f"{self.base_url}/eod/{sym}", params, f"eod {sym}")
        if not isinstance(rows, list):
            raise CollectorError(f"eod {sym}: expected a JSON list")
        kept = []
        seen = set()
        for row in rows:
            close = row.get("close")
            if close is None or float(close) <= 0:
                continue
            day = row["date"]
            if day in seen:
                continue
            seen.add(day)
            kept.append(row)
        return sorted(kept, key=lambda r: r["date"])

    def get_splits(self, symbol):
        sym = normalize_symbol(symbol)
        rows = self.get_json(f"{self.base_url}/splits/{sym}", self._params(), f"splits {sym}")
        if not isinstance(rows, list):
            raise CollectorError(f"splits {sym}: expected a JSON list")
        events = []
        for row in rows:
            text = row.get("split")
            ratio = parse_split_ratio(text)
            events.append(SplitEvent(_dt.date.fromisoformat(row["date"]), ratio, text))
        return sorted(events, key=lambda e: e.date)

    def get_dividends(self, symbol):
        sym = normalize_symbol(symbol)
        rows = self.get_json(f"{self.base_url}/div/{sym}", self._params(), f"div {sym}")
        if not isinstance(rows, list):
            raise CollectorError(f"div {sym}: expected a JSON list")
        return sorted(rows, key=lambda r: r.get("date") or "")

    def search(self, query, exchange=None):
        params = self._params()
        if exchange:
            params["exchange"] = exchange
        return self.get_json(f"{self.base_url}/search/{query}", params, f"search {query}")

"""The EODHD collector: end-of-day bars, splits and dividends."""
from __future__ import annotations

import os
from typing import NamedTuple

from .base import BaseCollector, CollectorError, register_secret

DEFAULT_BASE_URL = "https://eodhd.com/api"

FIAT = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD", "SEK", "NOK", "DKK", "PLN",
        "CZK", "HUF", "TRY", "ZAR", "MXN", "SGD", "HKD", "CNY", "INR", "BRL", "KRW", "RUB"}
CRYPTO_QUOTES = {"USD", "USDT", "EUR", "BTC", "ETH", "BUSD", "USDC"}


class SplitEvent(NamedTuple):
    date: str
    ratio: float
    split_string: str


def parse_split(text):
    """`NEW/OLD` -> new / old as a float."""
    parts = str(text).split("/")
    if len(parts) != 2:
        raise ValueError(f"unparseable split string: {text!r}")
    try:
        new = float(parts[0])
        old = float(parts[1])
    except ValueError:
        raise ValueError(f"unparseable split string: {text!r}") from None
    if new == 0 or old == 0:
        raise ValueError(f"degenerate split string: {text!r}")
    return new / old


def normalise_symbol(symbol):
    if "." in symbol:
        return symbol
    if "/" in symbol:
        base, _, quote = symbol.upper().partition("/")
        if base in FIAT and quote in FIAT:
            return f"{base}{quote}.FOREX"
        if quote in CRYPTO_QUOTES:
            return f"{base}-{quote}.CC"
        raise CollectorError(f"cannot infer exchange for pair symbol {symbol!r}")
    return f"{symbol}.US"


class EODHDCollector(BaseCollector):
    exchange = "eodhd"
    volume_basis = "split_adjusted"

    def __init__(self, api_key=None, base_url=None, transport=None, rate_limiter=None,
                 sleep=None):
        key = api_key if api_key else os.environ.get("EODHD_API_KEY", "")
        if not key:
            raise ValueError("EODHD API key required: pass api_key= or set EODHD_API_KEY")
        self.api_key = key
        register_secret(key)
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        super().__init__(transport=transport, rate_limiter=rate_limiter, sleep=sleep)

    normalise = staticmethod(normalise_symbol)

    def get_eod(self, symbol, start=None, end=None):
        sym = normalise_symbol(symbol)
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
            close = row.get("close")
            if close is None:
                continue
            if float(close) <= 0:
                continue
            day = row.get("date")
            if day in seen:
                continue
            seen.add(day)
            kept.append(row)
        kept.sort(key=lambda r: r["date"])
        return kept

    def get_splits(self, symbol):
        sym = normalise_symbol(symbol)
        params = {"api_token": self.api_key, "fmt": "json"}
        data = self.get_json(f"{self.base_url}/splits/{sym}", params, f"splits {sym}")
        if not isinstance(data, list):
            raise CollectorError(f"splits {sym}: expected a JSON list")
        events = [SplitEvent(entry["date"], parse_split(entry["split"]), entry["split"])
                  for entry in data]
        events.sort(key=lambda e: e.date)
        return events

    def get_dividends(self, symbol):
        sym = normalise_symbol(symbol)
        params = {"api_token": self.api_key, "fmt": "json"}
        data = self.get_json(f"{self.base_url}/div/{sym}", params, f"div {sym}")
        if not isinstance(data, list):
            raise CollectorError(f"div {sym}: expected a JSON list")
        entries = list(data)
        entries.sort(key=lambda e: e.get("date", ""))
        return entries

    def search(self, query, exchange=None):
        params = {"api_token": self.api_key, "fmt": "json"}
        if exchange:
            params["exchange"] = exchange
        return self.get_json(f"{self.base_url}/search/{query}", params, f"search {query}")

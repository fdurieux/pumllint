"""EODHD: end-of-day bars, splits and dividends."""
from __future__ import annotations

import os

from ..actions import SplitEvent, parse_split
from .base import BaseCollector, CollectorError, HttpTransport

DEFAULT_BASE_URL = "https://eodhd.com/api"

FIAT = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD", "SEK", "NOK", "DKK", "PLN",
        "CZK", "HUF", "TRY", "ZAR", "MXN", "SGD", "HKD", "CNY", "INR", "BRL", "KRW", "RUB"}
CRYPTO_QUOTES = {"USD", "USDT", "EUR", "BTC", "ETH", "BUSD", "USDC"}


def normalise_symbol(symbol: str) -> str:
    """Canonical TICKER.EXCHANGE for a user-typed symbol."""
    if "." in symbol:
        return symbol
    if "/" in symbol:
        base, _, quote = symbol.partition("/")
        base, quote = base.upper(), quote.upper()
        if base in FIAT and quote in FIAT:
            return f"{base}{quote}.FOREX"
        if quote in CRYPTO_QUOTES:
            return f"{base}-{quote}.CC"
        raise CollectorError(f"cannot infer exchange for pair symbol {symbol!r}")
    return f"{symbol.upper()}.US"


def _close_ok(row) -> bool:
    close = row.get("close")
    if close is None:
        return False
    return float(close) > 0


class EODHDCollector(BaseCollector):
    exchange = "eodhd"
    volume_basis = "split_adjusted"

    def __init__(self, api_key: str | None = None, base_url: str | None = None, transport=None,
                 rate_limit: bool = True, sleep=None):
        key = api_key if api_key else os.environ.get("EODHD_API_KEY", "")
        if not key:
            raise ValueError("EODHD API key required: pass api_key= or set EODHD_API_KEY")
        self.api_key = key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        if transport is None:
            transport = HttpTransport(secrets=[key])
        super().__init__(transport, rate_limit=rate_limit, sleep=sleep, secrets=[key])

    def _params(self, **extra) -> dict:
        params = {"api_token": self.api_key, "fmt": "json"}
        params.update(extra)
        return params

    def get_eod(self, symbol: str, start: str | None = None, end: str | None = None) -> list:
        sym = normalise_symbol(symbol)
        params = self._params(period="d", order="a")
        if start:
            params["from"] = start
        if end:
            params["to"] = end
        rows = self.get_json(f"{self.base_url}/eod/{sym}", params, f"eod {sym}")
        if not isinstance(rows, list):
            raise CollectorError(f"eod {sym}: expected a JSON list")
        seen = set()
        kept = []
        for row in rows:
            if not _close_ok(row):
                continue
            day = row.get("date")
            if day in seen:
                continue
            seen.add(day)
            kept.append(row)
        return sorted(kept, key=lambda r: r.get("date") or "")

    def get_splits(self, symbol: str) -> list:
        sym = normalise_symbol(symbol)
        rows = self.get_json(f"{self.base_url}/splits/{sym}", self._params(), f"splits {sym}")
        if not isinstance(rows, list):
            raise CollectorError(f"splits {sym}: expected a JSON list")
        events = [SplitEvent.from_provider(row["date"], row["split"]) for row in rows]
        return sorted(events, key=lambda e: e.date)

    def get_dividends(self, symbol: str) -> list:
        sym = normalise_symbol(symbol)
        rows = self.get_json(f"{self.base_url}/div/{sym}", self._params(), f"div {sym}")
        if not isinstance(rows, list):
            raise CollectorError(f"div {sym}: expected a JSON list")
        return sorted(rows, key=lambda r: r.get("date") or "")

    def search(self, query: str, exchange: str | None = None):
        params = self._params()
        if exchange:
            params["exchange"] = exchange
        return self.get_json(f"{self.base_url}/search/{query}", params, f"search {query}")


__all__ = ["EODHDCollector", "normalise_symbol", "parse_split", "DEFAULT_BASE_URL"]

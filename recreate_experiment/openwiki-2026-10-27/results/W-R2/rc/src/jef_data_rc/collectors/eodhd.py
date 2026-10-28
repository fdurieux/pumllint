"""EODHD adapter: EOD bars, splits, dividends and symbol search.

Prices are served raw; volume is served split-adjusted, which the store
undoes for a raw-basis ingest. The API key comes from `api_key=` or
`EODHD_API_KEY`, travels only as the `api_token` parameter, and is redacted
from collector error text.
"""

from __future__ import annotations

import math
import os
from typing import Any

from jef_data_rc.actions import SplitEvent
from jef_data_rc.collectors.base import BaseCollector, CollectorError

EODHD_BASE_URL = "https://eodhd.com/api"

EXCHANGE_MAP = {
    "NASDAQ": "US",
    "NYSE": "US",
    "NYSE ARCA": "US",
    "AMEX": "US",
    "BATS": "US",
    "US": "US",
    "LSE": "LSE",
    "LONDON": "LSE",
    "XETRA": "XETRA",
    "FRANKFURT": "F",
    "PARIS": "PA",
    "EURONEXT": "PA",
    "AMSTERDAM": "AS",
    "TORONTO": "TO",
    "TSX": "TO",
    "FOREX": "FOREX",
    "CRYPTO": "CC",
}

FIAT_CURRENCIES = frozenset({
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD", "SEK", "NOK", "DKK",
    "HKD", "SGD", "CNY", "CNH", "KRW", "INR", "MXN", "BRL", "ZAR", "PLN", "TRY",
})
CRYPTO_ASSETS = frozenset({
    "BTC", "ETH", "USDT", "USDC", "BNB", "XRP", "SOL", "ADA", "DOGE", "LTC",
    "DOT", "AVAX", "LINK", "BCH", "XLM", "TRX", "MATIC",
})


def normalize_symbol(symbol: str) -> str:
    """Canonical EODHD symbology.

    `AAPL.US` passes through, `AAPL` -> `AAPL.US`, `EUR/USD` -> `EURUSD.FOREX`,
    `BTC/USD` -> `BTC-USD.CC`; a pair that fits neither rule is refused.
    """
    s = symbol.strip()
    if "/" in s:
        base, _, quote = s.upper().partition("/")
        if not base or not quote or "/" in quote:
            raise CollectorError(f"cannot normalize symbol {symbol!r}")
        if base in FIAT_CURRENCIES and quote in FIAT_CURRENCIES:
            return f"{base}{quote}.FOREX"
        if base in CRYPTO_ASSETS or quote in CRYPTO_ASSETS:
            return f"{base}-{quote}.CC"
        raise CollectorError(f"cannot infer the EODHD exchange for pair {symbol!r}")
    if "." in s:
        return s
    if not s:
        raise CollectorError("empty symbol")
    return f"{s.upper()}.US"


def _num(value: Any) -> float:
    if value is None:
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


class EODHDCollector(BaseCollector):
    VOLUME_BASIS = "split_adjusted"

    def __init__(self, api_key: str | None = None, base_url: str = EODHD_BASE_URL, **kwargs):
        key = api_key or os.environ.get("EODHD_API_KEY")
        if not key:
            raise CollectorError("EODHD_API_KEY is not set (export it or pass api_key=)")
        super().__init__(**kwargs)
        self.api_key = key
        self.base_url = base_url.rstrip("/")
        self._secrets.append(key)

    def _get(self, path: str, params: dict | None = None) -> Any:
        query = dict(params or {})
        query["api_token"] = self.api_key
        query["fmt"] = "json"
        return self.get_json(f"{self.base_url}{path}", query)

    def get_eod(self, symbol: str, start: str | None = None, end: str | None = None,
                period: str = "d") -> list[dict]:
        params: dict[str, str] = {"order": "a", "period": period}
        if start:
            params["from"] = str(start)
        if end:
            params["to"] = str(end)
        data = self._get(f"/eod/{symbol}", params)
        if not isinstance(data, list):
            raise CollectorError(f"EODHD /eod/{symbol}: expected a JSON list, got {type(data).__name__}")
        seen: set[str] = set()
        bars: list[dict] = []
        for row in data:
            if not isinstance(row, dict) or "date" not in row:
                raise CollectorError(f"EODHD /eod/{symbol}: malformed row {row!r}")
            close = _num(row.get("close"))
            if not (close > 0):
                continue
            date = str(row["date"])[:10]
            if date in seen:
                continue
            seen.add(date)
            adj = row.get("adjusted_close")
            bars.append({
                "date": date,
                "open": _num(row.get("open")),
                "high": _num(row.get("high")),
                "low": _num(row.get("low")),
                "close": close,
                "adjusted_close": _num(adj) if adj is not None else close,
                "volume": _num(row.get("volume")),
            })
        bars.sort(key=lambda b: b["date"])
        return bars

    def get_splits(self, symbol: str, start: str | None = None, end: str | None = None) -> list[SplitEvent]:
        params: dict[str, str] = {}
        if start:
            params["from"] = str(start)
        if end:
            params["to"] = str(end)
        data = self._get(f"/splits/{symbol}", params)
        if not isinstance(data, list):
            raise CollectorError(f"EODHD /splits/{symbol}: expected a JSON list, got {type(data).__name__}")
        events = [SplitEvent.from_provider(e) for e in data]
        return sorted(events, key=lambda e: e.date)

    def get_dividends(self, symbol: str, start: str | None = None, end: str | None = None) -> list[dict]:
        params: dict[str, str] = {}
        if start:
            params["from"] = str(start)
        if end:
            params["to"] = str(end)
        data = self._get(f"/div/{symbol}", params)
        if not isinstance(data, list):
            raise CollectorError(f"EODHD /div/{symbol}: expected a JSON list, got {type(data).__name__}")
        return sorted((dict(d) for d in data), key=lambda d: str(d.get("date", "")))

    def search(self, query: str, exchange: str | None = None) -> list[dict]:
        params: dict[str, str] = {}
        if exchange:
            params["exchange"] = EXCHANGE_MAP.get(exchange.upper(), exchange)
        data = self._get(f"/search/{query}", params)
        if not isinstance(data, list):
            raise CollectorError(f"EODHD /search/{query}: expected a JSON list, got {type(data).__name__}")
        return data


def finite(x: float) -> bool:
    return math.isfinite(x)

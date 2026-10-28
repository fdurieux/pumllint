"""EODHD end-of-day, splits, dividends and search.

EODHD serves raw (unadjusted) OHLC prices with a split-and-dividend
``adjusted_close``, but its ``volume`` is already split-adjusted; hence
``VOLUME_BASIS = "split_adjusted"``. Whether a series is stored raw or
pre-adjusted is decided by the declared asset class in the sync runner, not
here.
"""
from __future__ import annotations

import os

from jef_data_rc.actions import SplitEvent, parse_split_ratio
from jef_data_rc.collectors.base import BaseCollector, CollectorError

BASE_URL = "https://eodhd.com/api"
API_KEY_ENV = "EODHD_API_KEY"

EXCHANGE_MAP = {
    "NASDAQ": "US",
    "NYSE": "US",
    "NYSE ARCA": "US",
    "NYSE MKT": "US",
    "AMEX": "US",
    "BATS": "US",
    "OTC": "US",
    "US": "US",
    "LSE": "LSE",
    "LONDON": "LSE",
    "XETRA": "XETRA",
    "FRANKFURT": "F",
    "PARIS": "PA",
    "EURONEXT PARIS": "PA",
    "AMSTERDAM": "AS",
    "TORONTO": "TO",
    "TSX": "TO",
    "CRYPTO": "CC",
    "FOREX": "FOREX",
}

FIAT = frozenset(
    {"USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD", "SEK", "NOK", "DKK", "HKD", "SGD", "CNY"}
)
CRYPTO = frozenset(
    {"BTC", "ETH", "USDT", "USDC", "BNB", "SOL", "XRP", "ADA", "DOGE", "LTC", "DOT", "AVAX", "TRX", "LINK"}
)


def normalize_symbol(symbol: str) -> str:
    """Make EODHD symbology explicit.

    ``AAPL.US`` passes through; ``AAPL`` -> ``AAPL.US``; ``EUR/USD`` ->
    ``EURUSD.FOREX``; ``BTC/USD`` -> ``BTC-USD.CC``. A pair that fits
    neither rule is refused.
    """
    text = str(symbol).strip()
    if not text:
        raise CollectorError("empty symbol")
    if "/" in text:
        base, _, quote = text.upper().partition("/")
        if not base or not quote or "/" in quote:
            raise CollectorError(f"cannot infer an EODHD exchange for {symbol!r}")
        if base in FIAT and quote in FIAT:
            return f"{base}{quote}.FOREX"
        if base in CRYPTO or quote in CRYPTO:
            return f"{base}-{quote}.CC"
        raise CollectorError(f"cannot infer an EODHD exchange for {symbol!r}")
    if "." in text:
        return text
    return f"{text}.US"


class EODHDCollector(BaseCollector):
    VOLUME_BASIS = "split_adjusted"
    page_limit = None

    def __init__(self, api_key: str | None = None, *, base_url: str = BASE_URL, **kwargs):
        key = api_key if api_key is not None else os.environ.get(API_KEY_ENV)
        if not key:
            raise CollectorError(
                f"EODHD requires an API key: pass api_key= or set {API_KEY_ENV}"
            )
        self.api_key = key
        self.base_url = base_url.rstrip("/")
        self._secrets = [key]
        super().__init__(**kwargs)

    def _get(self, endpoint: str, params: dict):
        query = {"api_token": self.api_key, "fmt": "json"}
        query.update(params)
        return self.get_json(f"{self.base_url}/{endpoint}", query)

    @staticmethod
    def _bounds(start, end) -> dict:
        params = {}
        if start is not None:
            params["from"] = str(start)
        if end is not None:
            params["to"] = str(end)
        return params

    def get_eod(self, symbol: str, start=None, end=None, period: str = "d") -> list[dict]:
        params = {"order": "a", "period": period}
        params.update(self._bounds(start, end))
        data = self._get(f"eod/{symbol}", params)
        if not isinstance(data, list):
            raise CollectorError(
                f"EODHD eod/{symbol}: expected a JSON list, got {type(data).__name__}"
            )
        seen: set[str] = set()
        bars = []
        for row in data:
            if not isinstance(row, dict):
                raise CollectorError(f"EODHD eod/{symbol}: row is not an object")
            try:
                day = str(row["date"])[:10]
                close = float(row["close"])
                bar = {
                    "date": day,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": close,
                    "adjusted_close": float(row["adjusted_close"])
                    if row.get("adjusted_close") is not None
                    else close,
                    "volume": float(row["volume"]),
                }
            except (KeyError, TypeError, ValueError) as exc:
                raise CollectorError(
                    f"EODHD eod/{symbol}: malformed row {row!r}: {exc}"
                ) from None
            if not close > 0:
                continue
            if day in seen:
                continue
            seen.add(day)
            bars.append(bar)
        bars.sort(key=lambda b: b["date"])
        return bars

    def get_splits(self, symbol: str, start=None, end=None) -> list[SplitEvent]:
        from datetime import date

        data = self._get(f"splits/{symbol}", self._bounds(start, end))
        if not isinstance(data, list):
            raise CollectorError(
                f"EODHD splits/{symbol}: expected a JSON list, got {type(data).__name__}"
            )
        events = []
        for row in data:
            try:
                text = str(row["split"])
                events.append(
                    SplitEvent(
                        date=date.fromisoformat(str(row["date"])[:10]),
                        ratio=parse_split_ratio(text),
                        split=text,
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise CollectorError(
                    f"EODHD splits/{symbol}: malformed entry {row!r}: {exc}"
                ) from None
        return sorted(events, key=lambda s: s.date)

    def get_dividends(self, symbol: str, start=None, end=None) -> list[dict]:
        data = self._get(f"div/{symbol}", self._bounds(start, end))
        if not isinstance(data, list):
            raise CollectorError(
                f"EODHD div/{symbol}: expected a JSON list, got {type(data).__name__}"
            )
        for row in data:
            if not isinstance(row, dict) or "date" not in row:
                raise CollectorError(f"EODHD div/{symbol}: malformed entry {row!r}")
        return sorted(data, key=lambda d: str(d["date"]))

    def search(self, query: str, exchange: str | None = None):
        params = {}
        if exchange:
            params["exchange"] = EXCHANGE_MAP.get(exchange.upper(), exchange)
        return self._get(f"search/{query}", params)

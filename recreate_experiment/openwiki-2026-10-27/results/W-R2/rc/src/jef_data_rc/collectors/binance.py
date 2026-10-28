"""Binance public daily klines.

Volume is BASE-ASSET volume (BTC for BTCUSDT), unlike the notional volume of
the EODHD and Yahoo sources; the two are not comparable across providers.
No API key, no corporate actions; series are stored pre-adjusted.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

from jef_data_rc.collectors.base import BaseCollector, CollectorError

BINANCE_BASE_URL = "https://api.binance.com"
KLINES_PATH = "/api/v3/klines"
DEFAULT_LIMIT = 1000
DAY_MS = 86_400_000


def _date_ms(date: str) -> int:
    d = _dt.date.fromisoformat(str(date)[:10])
    return (d - _dt.date(1970, 1, 1)).days * DAY_MS


def _utc_date(ms: int) -> str:
    return _dt.datetime.fromtimestamp(ms / 1000, tz=_dt.timezone.utc).date().isoformat()


class BinanceCollector(BaseCollector):
    VOLUME_BASIS = "raw"

    def __init__(self, base_url: str = BINANCE_BASE_URL, limit: int = DEFAULT_LIMIT, **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")
        self.limit = limit

    def get_klines(self, symbol: str, start: str | None = None, end: str | None = None) -> list[list]:
        url = f"{self.base_url}{KLINES_PATH}"
        end_ms = _date_ms(end) + DAY_MS - 1 if end else None

        def fetch(cursor: int | None) -> tuple[list, int | None]:
            params: dict[str, Any] = {"symbol": symbol, "interval": "1d", "limit": self.limit}
            if cursor is not None:
                params["startTime"] = cursor
            if end_ms is not None:
                params["endTime"] = end_ms
            page = self.get_json(url, params)
            if not isinstance(page, list):
                raise CollectorError(f"Binance {KLINES_PATH}: expected a JSON list, got {type(page).__name__}")
            if len(page) < self.limit:
                return page, None
            nxt = int(page[-1][0]) + DAY_MS
            if end_ms is not None and nxt > end_ms:
                return page, None
            return page, nxt

        start_ms = _date_ms(start) if start else None
        return self.paginate(fetch, start_ms)

    def get_eod(self, symbol: str, start: str | None = None, end: str | None = None) -> list[dict]:
        seen: set[str] = set()
        bars: list[dict] = []
        for k in self.get_klines(symbol, start, end):
            if not isinstance(k, (list, tuple)) or len(k) < 6:
                raise CollectorError(f"Binance {KLINES_PATH}: malformed kline {k!r}")
            close = float(k[4])
            if not (close > 0):
                continue
            date = _utc_date(int(k[0]))
            if date in seen:
                continue
            seen.add(date)
            bars.append({
                "date": date,
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": close,
                "volume": float(k[5]),
                "adjusted_close": close,
            })
        bars.sort(key=lambda b: b["date"])
        return bars

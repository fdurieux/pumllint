"""Binance: daily klines, paged ascending."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from .base import BaseCollector, CollectorError, HttpTransport

KLINES_URL = "https://api.binance.com/api/v3/klines"
DAY_MS = 86_400_000
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def date_ms(day: str) -> int:
    """Unix milliseconds of a date at 00:00 UTC."""
    d = date.fromisoformat(day[:10])
    return (d - date(1970, 1, 1)).days * DAY_MS


def ms_date(ms: int) -> str:
    return (_EPOCH + timedelta(milliseconds=int(ms))).date().isoformat()


class BinanceCollector(BaseCollector):
    exchange = "binance"
    volume_basis = "raw"
    limit = 1000
    max_pages = 100

    def __init__(self, transport=None, rate_limit: bool = True, sleep=None):
        if transport is None:
            transport = HttpTransport()
        super().__init__(transport, rate_limit=rate_limit, sleep=sleep)

    def get_eod(self, symbol: str, start: str | None = None, end: str | None = None) -> list:
        start_ms = date_ms(start) if start else None
        end_ms = date_ms(end) + DAY_MS - 1 if end else None
        what = f"klines {symbol}"

        def fetch_page(cursor):
            params = {"symbol": symbol, "interval": "1d", "limit": self.limit}
            if cursor is not None:
                params["startTime"] = cursor
            if end_ms is not None:
                params["endTime"] = end_ms
            page = self.get_json(KLINES_URL, params, what)
            if not isinstance(page, list):
                raise CollectorError(f"{what}: expected a JSON list")
            if not page:
                return [], None
            last_open = int(page[-1][0])
            if len(page) < self.limit or (end_ms is not None and last_open + DAY_MS > end_ms):
                return page, None
            return page, last_open + DAY_MS

        rows = self.paginate(fetch_page, start_ms, self.max_pages)
        bars = []
        seen = set()
        for row in rows:
            bar = {"date": ms_date(row[0]), "open": float(row[1]), "high": float(row[2]),
                   "low": float(row[3]), "close": float(row[4]), "adjusted_close": float(row[4]),
                   "volume": float(row[5])}
            if bar["close"] <= 0 or bar["date"] in seen:
                continue
            seen.add(bar["date"])
            bars.append(bar)
        return sorted(bars, key=lambda b: b["date"])

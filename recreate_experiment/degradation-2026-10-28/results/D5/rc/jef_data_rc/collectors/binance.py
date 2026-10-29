"""Binance collector: daily klines, paged ascending."""
from __future__ import annotations

import time
from datetime import datetime, timezone

from .base import BaseCollector, CollectorError, HttpTransport

KLINES_URL = "https://api.binance.com/api/v3/klines"
DAY_MS = 86_400_000


def day_start_ms(day) -> int:
    """Unix ms of the given date (or ISO date-time text) at 00:00 UTC."""
    text = str(day)
    stamp = datetime.fromisoformat(text)
    if stamp.tzinfo is not None:
        stamp = stamp.astimezone(timezone.utc)
    midnight = datetime(stamp.year, stamp.month, stamp.day, tzinfo=timezone.utc)
    return int(midnight.timestamp()) * 1000


def _utc_day(ms) -> str:
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


class BinanceCollector(BaseCollector):
    exchange = "binance"
    volume_basis = "raw"
    limit = 1000
    max_pages = 100

    def __init__(self, transport=None, *, rate_limit=True, sleep=time.sleep):
        if transport is None:
            transport = HttpTransport()
        super().__init__(transport, rate_limit=rate_limit, sleep=sleep)

    def get_eod(self, symbol, start=None, end=None):
        start_ms = day_start_ms(start) if start else None
        end_ms = day_start_ms(end) + DAY_MS - 1 if end else None

        def fetch_page(cursor):
            params = {"symbol": symbol, "interval": "1d", "limit": self.limit}
            if cursor is not None:
                params["startTime"] = cursor
            if end_ms is not None:
                params["endTime"] = end_ms
            page = self.get_json(KLINES_URL, params, f"klines {symbol}")
            if not isinstance(page, list):
                raise CollectorError(f"klines {symbol}: expected a JSON list")
            if not page:
                return page, None
            last_open = int(page[-1][0])
            if len(page) < self.limit or (end_ms is not None and last_open + DAY_MS > end_ms):
                return page, None
            return page, last_open + DAY_MS

        rows = self.paginate(fetch_page, start_ms, self.max_pages)
        bars = []
        seen = set()
        for row in rows:
            close = float(row[4])
            if close <= 0:
                continue
            day = _utc_day(row[0])
            if day in seen:
                continue
            seen.add(day)
            bars.append({"date": day, "open": float(row[1]), "high": float(row[2]),
                         "low": float(row[3]), "close": close, "adjusted_close": close,
                         "volume": float(row[5])})
        return sorted(bars, key=lambda b: b["date"])

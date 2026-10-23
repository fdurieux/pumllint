"""The Binance collector: daily klines, paged ascending."""
from __future__ import annotations

import datetime as _dt
import time

from .base import BaseCollector, CollectorError, RateLimiter

KLINES_URL = "https://api.binance.com/api/v3/klines"
DAY_MS = 86_400_000
PAGE_LIMIT = 1000
MAX_PAGES = 100


def _date_ms(text):
    day = _dt.date.fromisoformat(str(text)[:10])
    moment = _dt.datetime(day.year, day.month, day.day, tzinfo=_dt.timezone.utc)
    return int(moment.timestamp()) * 1000


def start_ms(text):
    return _date_ms(text)


def end_ms(text):
    return _date_ms(text) + DAY_MS - 1


class BinanceCollector(BaseCollector):
    exchange = "binance"
    volume_basis = "raw"
    limit = PAGE_LIMIT
    max_pages = MAX_PAGES

    def __init__(self, transport=None, rate_limiter="default", sleep=time.sleep,
                 base_url=KLINES_URL):
        if rate_limiter == "default":
            rate_limiter = RateLimiter()
        self.url = base_url
        super().__init__(transport=transport, rate_limiter=rate_limiter, sleep=sleep)

    def get_eod(self, symbol, start=None, end=None):
        what = f"klines {symbol}"
        end_time = end_ms(end) if end else None

        def fetch_page(cursor):
            params = {"symbol": symbol, "interval": "1d", "limit": self.limit}
            if cursor is not None:
                params["startTime"] = cursor
            if end_time is not None:
                params["endTime"] = end_time
            page = self.get_json(self.url, params, what)
            if not isinstance(page, list):
                raise CollectorError(f"{what}: expected a JSON list")
            if not page:
                return page, None
            last_open = int(page[-1][0])
            if len(page) < self.limit or (end_time is not None
                                          and last_open + DAY_MS > end_time):
                return page, None
            return page, last_open + DAY_MS

        cursor = start_ms(start) if start else None
        rows = self.paginate(fetch_page, cursor, self.max_pages)
        bars = []
        seen = set()
        for row in rows:
            opened = _dt.datetime.fromtimestamp(int(row[0]) // 1000, tz=_dt.timezone.utc)
            close = float(row[4])
            if close <= 0:
                continue
            date = opened.strftime("%Y-%m-%d")
            if date in seen:
                continue
            seen.add(date)
            bars.append({"date": date, "open": float(row[1]), "high": float(row[2]),
                         "low": float(row[3]), "close": close, "adjusted_close": close,
                         "volume": float(row[5])})
        return sorted(bars, key=lambda b: b["date"])

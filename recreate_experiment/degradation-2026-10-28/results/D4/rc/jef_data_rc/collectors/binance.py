"""Binance collector: daily klines, paged ascending."""
from __future__ import annotations

import datetime as _dt
import time

from .base import BaseCollector, CollectorError, RateLimiter
from .transport import HttpTransport

KLINES_URL = "https://api.binance.com/api/v3/klines"
DAY_MS = 86_400_000
_EPOCH = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)


def date_ms(text) -> int:
    day = _dt.date.fromisoformat(str(text)[:10])
    moment = _dt.datetime(day.year, day.month, day.day, tzinfo=_dt.timezone.utc)
    return int((moment - _EPOCH) // _dt.timedelta(milliseconds=1))


def ms_date(ms) -> str:
    return (_EPOCH + _dt.timedelta(milliseconds=int(ms))).date().isoformat()


class BinanceCollector(BaseCollector):
    exchange = "binance"
    volume_basis = "raw"
    limit = 1000

    def __init__(self, transport=None, rate_limiter=None, sleep=time.sleep):
        if transport is None:
            transport = HttpTransport()
        super().__init__(transport=transport,
                         rate_limiter=rate_limiter if rate_limiter is not None else RateLimiter(),
                         sleep=sleep)

    def get_eod(self, symbol: str, start=None, end=None, max_pages: int = 100) -> list:
        end_ms = date_ms(end) + DAY_MS - 1 if end else None
        cursor0 = date_ms(start) if start else None

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

        rows = self.paginate(fetch_page, cursor0, max_pages=max_pages)
        bars = []
        seen = set()
        for kline in rows:
            close = float(kline[4])
            if close <= 0:
                continue
            day = ms_date(kline[0])
            if day in seen:
                continue
            seen.add(day)
            bars.append({"date": day, "open": float(kline[1]), "high": float(kline[2]),
                         "low": float(kline[3]), "close": close, "adjusted_close": close,
                         "volume": float(kline[5])})
        return sorted(bars, key=lambda b: b["date"])

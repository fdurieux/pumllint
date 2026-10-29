"""Binance: daily klines, keyless, paged ascending."""
import time
from datetime import date, datetime, timedelta, timezone

from jef_data_rc.collectors.base import BaseCollector, CollectorError, HttpTransport, RateLimiter

KLINES_URL = "https://api.binance.com/api/v3/klines"
DAY_MS = 86_400_000
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _date_of(text):
    return date.fromisoformat(str(text)[:10])


def date_to_ms(day):
    """Unix milliseconds of a date at 00:00 UTC."""
    moment = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    return int((moment - EPOCH) // timedelta(milliseconds=1))


def ms_to_date(ms):
    return (EPOCH + timedelta(milliseconds=int(ms))).date().isoformat()


class BinanceCollector(BaseCollector):
    exchange = "binance"
    volume_basis = "raw"
    limit = 1000
    max_pages = 100

    def __init__(self, transport=None, rate_limiter="default", sleep=time.sleep):
        if transport is None:
            transport = HttpTransport(timeout=30.0)
        if rate_limiter == "default":
            rate_limiter = RateLimiter()
        super().__init__(transport, rate_limiter=rate_limiter, sleep=sleep)

    def get_eod(self, symbol, start=None, end=None):
        start_ms = date_to_ms(_date_of(start)) if start else None
        end_ms = date_to_ms(_date_of(end)) + DAY_MS - 1 if end else None
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
            day = ms_to_date(row[0])
            if day in seen:
                continue
            seen.add(day)
            bars.append({"date": day, "open": float(row[1]), "high": float(row[2]),
                         "low": float(row[3]), "close": close, "adjusted_close": close,
                         "volume": float(row[5])})
        return sorted(bars, key=lambda bar: bar["date"])

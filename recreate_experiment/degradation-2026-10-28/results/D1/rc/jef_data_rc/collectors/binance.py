"""Binance spot klines as daily bars (pre-adjusted, base-asset volume)."""
import time
from datetime import date, datetime, timezone

from .base import BaseCollector, CollectorError, RateLimiter

DEFAULT_BASE_URL = "https://api.binance.com"
DAY_MS = 86400000


def _day_start_ms(text):
    day = date.fromisoformat(str(text)[:10])
    return int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp()) * 1000


class BinanceCollector(BaseCollector):
    exchange = "binance"
    volume_basis = "raw"
    limit = 1000
    max_pages = 100

    def __init__(self, base_url=DEFAULT_BASE_URL, transport=None, limiter=None, sleep=time.sleep,
                 rate_limit=True):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        if transport is None:
            from .transport import HttpTransport

            transport = HttpTransport()
        if limiter is None and rate_limit:
            limiter = RateLimiter()
        super().__init__(transport, limiter=limiter, sleep=sleep)

    def get_eod(self, symbol, start=None, end=None):
        start_ms = None if start is None else _day_start_ms(start)
        end_ms = None if end is None else _day_start_ms(end) + DAY_MS - 1
        url = f"{self.base_url}/api/v3/klines"
        what = f"klines {symbol}"

        def fetch_page(cursor):
            params = {"symbol": symbol, "interval": "1d", "limit": self.limit}
            if cursor is not None:
                params["startTime"] = cursor
            if end_ms is not None:
                params["endTime"] = end_ms
            rows = self.get_json(url, params, what)
            if not isinstance(rows, list):
                raise CollectorError(f"klines {symbol}: expected a JSON list")
            if not rows:
                return rows, None
            last_open = int(rows[-1][0])
            if len(rows) < self.limit or (end_ms is not None and last_open + DAY_MS > end_ms):
                return rows, None
            return rows, last_open + DAY_MS

        rows = self.paginate(fetch_page, start_ms, self.max_pages)
        bars = []
        seen = set()
        for row in rows:
            close = float(row[4])
            if close <= 0:
                continue
            day = datetime.fromtimestamp(int(row[0]) // 1000, tz=timezone.utc).date().isoformat()
            if day in seen:
                continue
            seen.add(day)
            bars.append({"date": day, "open": float(row[1]), "high": float(row[2]),
                         "low": float(row[3]), "close": close, "adjusted_close": close,
                         "volume": float(row[5])})
        return sorted(bars, key=lambda bar: bar["date"])

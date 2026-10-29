"""Binance collector: daily klines, paged ascending."""
import datetime as _dt
import time

from .base import MAX_PAGES, BaseCollector, CollectorError

KLINES_URL = "https://api.binance.com/api/v3/klines"
DAY_MS = 86400000
PAGE_LIMIT = 1000
EPOCH = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)


def _day_ms(value):
    day = _dt.date.fromisoformat(str(value)[:10])
    midnight = _dt.datetime(day.year, day.month, day.day, tzinfo=_dt.timezone.utc)
    return int(midnight.timestamp()) * 1000


def start_ms(value):
    return _day_ms(value)


def end_ms(value):
    return _day_ms(value) + DAY_MS - 1


class BinanceCollector(BaseCollector):
    exchange = "binance"
    volume_basis = "raw"
    limit = PAGE_LIMIT

    def __init__(self, transport=None, rate_limit=True, sleep=time.sleep, max_pages=MAX_PAGES):
        if transport is None:
            from .transport import HttpTransport

            transport = HttpTransport()
        self.max_pages = max_pages
        super().__init__(transport, rate_limit=rate_limit, sleep=sleep)

    def get_eod(self, symbol, start=None, end=None):
        cursor0 = start_ms(start) if start is not None else None
        stop = end_ms(end) if end is not None else None
        what = f"klines {symbol}"

        def fetch_page(cursor):
            params = {"symbol": symbol, "interval": "1d", "limit": self.limit}
            if cursor is not None:
                params["startTime"] = cursor
            if stop is not None:
                params["endTime"] = stop
            page = self.get_json(KLINES_URL, params, what)
            if not isinstance(page, list):
                raise CollectorError(f"klines {symbol}: expected a JSON list")
            if not page:
                return [], None
            last_open = int(page[-1][0])
            if len(page) < self.limit or (stop is not None and last_open + DAY_MS > stop):
                return page, None
            return page, last_open + DAY_MS

        rows = self.paginate(fetch_page, cursor0, self.max_pages)
        seen = set()
        bars = []
        for row in rows:
            close = float(row[4])
            if close <= 0:
                continue
            date = (EPOCH + _dt.timedelta(milliseconds=int(row[0]))).date().isoformat()
            if date in seen:
                continue
            seen.add(date)
            bars.append({"date": date, "open": float(row[1]), "high": float(row[2]),
                         "low": float(row[3]), "close": close, "adjusted_close": close,
                         "volume": float(row[5])})
        return sorted(bars, key=lambda b: b["date"])

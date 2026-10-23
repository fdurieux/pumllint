"""The Binance collector: daily klines, paged ascending."""
from __future__ import annotations

import datetime as _dt

from .base import BaseCollector, CollectorError

KLINES_URL = "https://api.binance.com/api/v3/klines"
DAY_MS = 86_400_000


def _date_ms(text):
    day = _dt.date.fromisoformat(str(text)[:10])
    moment = _dt.datetime(day.year, day.month, day.day, tzinfo=_dt.timezone.utc)
    return int(moment.timestamp()) * 1000


def _utc_day(ms):
    return _dt.datetime.fromtimestamp(int(ms) / 1000, tz=_dt.timezone.utc).date().isoformat()


class BinanceCollector(BaseCollector):
    exchange = "binance"
    volume_basis = "raw"
    limit = 1000
    max_pages = 100

    def get_eod(self, symbol, start=None, end=None):
        start_ms = _date_ms(start) if start else None
        end_ms = _date_ms(end) + DAY_MS - 1 if end else None
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

        rows = self.paginate(fetch_page, start_ms, max_pages=self.max_pages)
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
        bars.sort(key=lambda b: b["date"])
        return bars

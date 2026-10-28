"""Binance public daily klines.

``volume`` is BASE-ASSET volume (BTC for ``BTCUSDT``), not notional, so it
is not comparable with EODHD or Yahoo volume. There is no corporate-action
path: sync stores Binance as ``price_basis="split_adjusted"``.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from jef_data_rc.collectors.base import BaseCollector, CollectorError

BASE_URL = "https://api.binance.com"
KLINES_PATH = "/api/v3/klines"
DEFAULT_LIMIT = 1000
_MS_PER_DAY = 86_400_000


def _day_ms(value) -> int:
    day = value if isinstance(value, date) else date.fromisoformat(str(value)[:10])
    moment = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    return int(moment.timestamp()) * 1000


class BinanceCollector(BaseCollector):
    VOLUME_BASIS = "raw"

    def __init__(self, *, base_url: str = BASE_URL, limit: int = DEFAULT_LIMIT, **kwargs):
        self.base_url = base_url.rstrip("/")
        self.limit = int(limit)
        self.page_limit = self.limit
        super().__init__(**kwargs)

    @staticmethod
    def _bar(kline) -> dict:
        try:
            opened = int(kline[0])
            close = float(kline[4])
            return {
                "date": datetime.fromtimestamp(opened / 1000, tz=timezone.utc)
                .date()
                .isoformat(),
                "open": float(kline[1]),
                "high": float(kline[2]),
                "low": float(kline[3]),
                "close": close,
                "adjusted_close": close,
                "volume": float(kline[5]),
                "_open_time": opened,
            }
        except (IndexError, TypeError, ValueError) as exc:
            raise CollectorError(f"Binance kline malformed {kline!r}: {exc}") from None

    def get_eod(self, symbol: str, start=None, end=None, period: str = "d") -> list[dict]:
        url = f"{self.base_url}{KLINES_PATH}"
        end_ms = _day_ms(end) + _MS_PER_DAY - 1 if end is not None else None
        start_ms = _day_ms(start) if start is not None else None

        def fetch_page(cursor):
            params = {"symbol": symbol, "interval": "1d", "limit": self.limit}
            if cursor is not None:
                params["startTime"] = cursor
            if end_ms is not None:
                params["endTime"] = end_ms
            data = self.get_json(url, params)
            if not isinstance(data, list):
                raise CollectorError(
                    f"Binance klines {symbol}: expected a JSON list, got "
                    f"{type(data).__name__}"
                )
            rows = [self._bar(k) for k in data]
            if len(data) < self.limit or not rows:
                return rows, None
            nxt = rows[-1]["_open_time"] + _MS_PER_DAY
            if end_ms is not None and nxt > end_ms:
                return rows, None
            return rows, nxt

        seen: set[str] = set()
        bars = []
        for bar in self.paginate(fetch_page, start_ms):
            bar.pop("_open_time", None)
            if not bar["close"] > 0:
                continue
            if bar["date"] in seen:
                continue
            seen.add(bar["date"])
            bars.append(bar)
        bars.sort(key=lambda b: b["date"])
        return bars

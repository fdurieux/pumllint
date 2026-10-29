"""EODHD: end-of-day bars, splits and dividends."""
import os
import time
from datetime import date

from .base import BaseCollector, CollectorError, RateLimiter

DEFAULT_BASE_URL = "https://eodhd.com/api"
FIAT = frozenset("USD EUR GBP JPY CHF AUD NZD CAD SEK NOK DKK PLN CZK HUF TRY ZAR MXN SGD HKD "
                 "CNY INR BRL KRW RUB".split())
CRYPTO_QUOTES = frozenset("USD USDT EUR BTC ETH BUSD USDC".split())


class SplitEvent:
    """One split: effective date, ratio (new/old) and the provider's split string."""

    __slots__ = ("date", "ratio", "split_string")

    def __init__(self, date, ratio, split_string=None):
        self.date = date
        self.ratio = ratio
        self.split_string = split_string

    def __repr__(self):
        return f"SplitEvent({self.date!r}, {self.ratio!r}, {self.split_string!r})"


def normalize_symbol(symbol):
    """EODHD's canonical TICKER.EXCHANGE for a user-typed symbol."""
    if "." in symbol:
        return symbol
    if "/" in symbol:
        base, quote = symbol.upper().split("/", 1)
        if base in FIAT and quote in FIAT:
            return f"{base}{quote}.FOREX"
        if quote in CRYPTO_QUOTES:
            return f"{base}-{quote}.CC"
        raise CollectorError(f"cannot infer exchange for pair symbol {symbol!r}")
    return f"{symbol.upper()}.US"


def parse_split(text):
    """Ratio new/old of a provider split string NEW/OLD."""
    parts = str(text).split("/")
    if len(parts) != 2:
        raise ValueError(f"unparseable split string: {text!r}")
    try:
        new, old = float(parts[0]), float(parts[1])
    except ValueError:
        raise ValueError(f"unparseable split string: {text!r}") from None
    if new == 0 or old == 0:
        raise ValueError(f"degenerate split string: {text!r}")
    return new / old


def _usable_close(row):
    close = row.get("close") if isinstance(row, dict) else None
    if close is None:
        return False
    return float(close) > 0


class EODHDCollector(BaseCollector):
    exchange = "eodhd"
    volume_basis = "split_adjusted"

    def __init__(self, api_key=None, base_url=DEFAULT_BASE_URL, transport=None, limiter=None,
                 sleep=time.sleep, rate_limit=True):
        key = api_key if api_key else os.environ.get("EODHD_API_KEY", "")
        if not key:
            raise ValueError("EODHD API key required: pass api_key= or set EODHD_API_KEY")
        self.api_key = key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        if transport is None:
            from .transport import HttpTransport

            transport = HttpTransport(secrets=(key,))
        if limiter is None and rate_limit:
            limiter = RateLimiter()
        super().__init__(transport, limiter=limiter, sleep=sleep, secrets=(key,))

    def _params(self, **extra):
        params = {"api_token": self.api_key, "fmt": "json"}
        params.update(extra)
        return params

    def get_eod(self, symbol, start=None, end=None):
        sym = normalize_symbol(symbol)
        params = self._params(period="d", order="a")
        if start is not None:
            params["from"] = start
        if end is not None:
            params["to"] = end
        data = self.get_json(f"{self.base_url}/eod/{sym}", params, f"eod {sym}")
        if not isinstance(data, list):
            raise CollectorError(f"eod {sym}: expected a JSON list")
        kept = []
        seen = set()
        for row in data:
            if not _usable_close(row):
                continue
            day = row.get("date")
            if day in seen:
                continue
            seen.add(day)
            kept.append(row)
        return sorted(kept, key=lambda row: row["date"])

    def get_splits(self, symbol):
        sym = normalize_symbol(symbol)
        data = self.get_json(f"{self.base_url}/splits/{sym}", self._params(), f"splits {sym}")
        if not isinstance(data, list):
            raise CollectorError(f"splits {sym}: expected a JSON list")
        events = [SplitEvent(date.fromisoformat(entry["date"]), parse_split(entry["split"]),
                             entry["split"]) for entry in data]
        return sorted(events, key=lambda event: event.date)

    def get_dividends(self, symbol):
        sym = normalize_symbol(symbol)
        data = self.get_json(f"{self.base_url}/div/{sym}", self._params(), f"div {sym}")
        if not isinstance(data, list):
            raise CollectorError(f"div {sym}: expected a JSON list")
        return sorted(data, key=lambda entry: entry.get("date", ""))

    def search(self, query, exchange=None):
        params = self._params()
        if exchange is not None:
            params["exchange"] = exchange
        return self.get_json(f"{self.base_url}/search/{query}", params, f"search {query}")

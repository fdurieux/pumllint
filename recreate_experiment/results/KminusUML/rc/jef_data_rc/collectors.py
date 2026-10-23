"""Provider collectors (EODHD, Binance), their transports and recorded fixtures."""
import collections
import datetime as _dt
import hashlib
import json
import os
import time
from urllib.parse import urlparse

EODHD_BASE_URL = "https://eodhd.com/api"
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
DAY_MS = 86_400_000
HTTP_TIMEOUT = 30
PER_MINUTE = 1000
PER_DAY = 100_000
MAX_RETRIES = 4
BACKOFF_BASE = 2.0

FIAT = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD", "SEK", "NOK", "DKK",
        "PLN", "CZK", "HUF", "TRY", "ZAR", "MXN", "SGD", "HKD", "CNY", "INR", "BRL",
        "KRW", "RUB"}
CRYPTO_QUOTES = {"USD", "USDT", "EUR", "BTC", "ETH", "BUSD", "USDC"}


class CollectorError(RuntimeError):
    """A provider request that cannot succeed."""


class DailyBudgetExhausted(CollectorError):
    """The per-UTC-day request budget is spent."""


class TransportConnectionError(ConnectionError):
    """A retryable network failure (token already redacted)."""


def _redact(text, secrets):
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


# ------------------------------------------------------------------ transports
class LiveTransport:
    """HTTP through a requests session."""

    def __init__(self, secrets=(), timeout=HTTP_TIMEOUT):
        import requests
        self._requests = requests
        self._session = requests.Session()
        self._secrets = tuple(s for s in secrets if s)
        self._timeout = timeout

    def request(self, method, url, params):
        try:
            response = self._session.request(method, url, params=params,
                                             timeout=self._timeout)
        except (self._requests.ConnectionError, self._requests.Timeout) as exc:
            raise TransportConnectionError(_redact(str(exc), self._secrets)) from None
        return response.status_code, response.text

    def close(self):
        self._session.close()


def fixture_key(method, url, params):
    """The recorded-fixture identity of one request."""
    clean = {name: str(value) for name, value in params.items() if name != "api_token"}
    return {"method": method.upper(), "path": urlparse(url).path,
            "params": dict(sorted(clean.items()))}


def _key_text(key):
    return json.dumps(key, sort_keys=True)


def fixture_filename(key):
    slug = key["path"].strip("/").replace("/", "_")
    digest = hashlib.sha256(_key_text(key).encode("utf-8")).hexdigest()[:10]
    return f"{slug}_{digest}.json"


class ReplayTransport:
    """Answers requests from recorded fixture files."""

    def __init__(self, fixture_dir):
        self._answers = {}
        for root, dirs, files in os.walk(fixture_dir):
            dirs.sort()
            for name in sorted(files):
                if not name.endswith(".json") or name == "manifest.json":
                    continue
                with open(os.path.join(root, name), encoding="utf-8") as handle:
                    doc = json.load(handle)
                key = doc["request"]
                self._answers[_key_text(key)] = (key, doc["response"])

    def request(self, method, url, params):
        key = fixture_key(method, url, params)
        found = self._answers.get(_key_text(key))
        if found is None:
            known = sorted(f"  {k['path']} {k['params']}" for k, _ in self._answers.values())
            lines = [f"no recorded fixture for {key['method']} {key['path']} {key['params']}",
                     "known fixtures:"] + known
            raise CollectorError("\n".join(lines))
        response = found[1]
        return int(response["status"]), json.dumps(response["json"])

    def close(self):
        pass


class RecordingTransport:
    """Passes requests to an inner transport and writes one fixture per request."""

    def __init__(self, inner, fixture_dir, secrets=()):
        self._inner = inner
        self._dir = fixture_dir
        self._secrets = tuple(s for s in secrets if s)

    def request(self, method, url, params):
        status, text = self._inner.request(method, url, params)
        key = fixture_key(method, url, params)
        try:
            body = json.loads(text)
        except ValueError:
            body = text
        fixture = {"request": key, "response": {"status": int(status), "json": body}}
        path = os.path.join(self._dir, fixture_filename(key))
        serialised = json.dumps(fixture, indent=1, sort_keys=True) + "\n"
        if any(secret in serialised for secret in self._secrets):
            raise CollectorError(
                f"refusing to write fixture: secret material in {path} response/request")
        os.makedirs(self._dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(serialised)
        return status, text

    def close(self):
        self._inner.close()


# ------------------------------------------------------------------ rate limiting
class RateLimiter:
    """1000 requests per sliding 60 s window and 100000 per UTC day."""

    def __init__(self, per_minute=PER_MINUTE, per_day=PER_DAY, clock=time.time,
                 sleep=time.sleep):
        self.per_minute = per_minute
        self.per_day = per_day
        self._clock = clock
        self._sleep = sleep
        self._window = collections.deque()
        self._day = None
        self._day_count = 0

    def acquire(self):
        now = self._clock()
        day = _dt.datetime.fromtimestamp(now, _dt.timezone.utc).date()
        if day != self._day:
            self._day = day
            self._day_count = 0
        if self._day_count >= self.per_day:
            raise DailyBudgetExhausted(
                f"daily API budget of {self.per_day} spent ({day.isoformat()}); the "
                f"per-minute window cannot lend quota across days")
        while self._window and now - self._window[0] >= 60:
            self._window.popleft()
        while len(self._window) >= self.per_minute:
            wait = 60 - (now - self._window[0])
            if wait > 0:
                self._sleep(wait)
            now = self._clock()
            while self._window and now - self._window[0] >= 60:
                self._window.popleft()
        self._window.append(now)
        self._day_count += 1


class _NoLimit:
    def acquire(self):
        pass


# ------------------------------------------------------------------ base collector
class _Collector:
    volume_basis = "raw"

    def __init__(self, transport, rate_limit, sleep, secrets):
        self._secrets = tuple(s for s in secrets if s)
        self._transport = transport
        self._limiter = RateLimiter() if rate_limit else _NoLimit()
        self._sleep = sleep
        self.max_retries = MAX_RETRIES

    def get_json(self, label, url, params):
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            self._limiter.acquire()
            try:
                status, text = self._transport.request("GET", url, params)
            except TransportConnectionError as exc:
                if attempt < self.max_retries:
                    self._sleep(BACKOFF_BASE * 2 ** attempt)
                    continue
                raise CollectorError(
                    f"{label}: network failure after {attempts} attempts: "
                    f"{_redact(str(exc), self._secrets)}") from None
            if status == 429 or status >= 500:
                if attempt < self.max_retries:
                    self._sleep(BACKOFF_BASE * 2 ** attempt)
                    continue
                raise CollectorError(f"{label}: HTTP {status} after {attempts} attempts")
            if status != 200:
                raise CollectorError(
                    f"{label}: HTTP {status}: {_redact(text[:200], self._secrets)}")
            try:
                return json.loads(text)
            except ValueError:
                raise CollectorError(
                    f"{label}: response is not JSON: "
                    f"{_redact(text[:200], self._secrets)}") from None
        raise CollectorError(f"{label}: HTTP request loop ended without an answer")

    def close(self):
        self._transport.close()


# ------------------------------------------------------------------ EODHD
class SplitEvent:
    """One split: effective date, ratio new/old and the provider string."""

    __slots__ = ("date", "ratio", "split")

    def __init__(self, date, ratio, split=None):
        self.date = date
        self.ratio = ratio
        self.split = split

    def __repr__(self):
        return f"SplitEvent({self.date!r}, {self.ratio!r}, {self.split!r})"


def parse_split_ratio(text):
    """'NEW/OLD' -> new/old as a float."""
    parts = text.split("/") if isinstance(text, str) else []
    if len(parts) != 2:
        raise ValueError(f"unparseable split string: {text!r}")
    try:
        new, old = float(parts[0]), float(parts[1])
    except ValueError:
        raise ValueError(f"unparseable split string: {text!r}") from None
    if new == 0 or old == 0:
        raise ValueError(f"degenerate split string: {text!r}")
    return new / old


def normalize_eodhd_symbol(symbol):
    if "." in symbol:
        return symbol
    if "/" in symbol:
        base, quote = symbol.split("/", 1)
        base, quote = base.upper(), quote.upper()
        if base in FIAT and quote in FIAT:
            return f"{base}{quote}.FOREX"
        if quote in CRYPTO_QUOTES:
            return f"{base}-{quote}.CC"
        raise CollectorError(f"cannot infer exchange for pair symbol {symbol!r}")
    return f"{symbol}.US"


class EODHDCollector(_Collector):
    volume_basis = "split_adjusted"
    provider = "eodhd"

    def __init__(self, api_key=None, base_url=None, transport=None, rate_limit=True,
                 sleep=time.sleep):
        key = api_key if api_key else os.environ.get("EODHD_API_KEY", "")
        if not key:
            raise ValueError("EODHD API key required: pass api_key= or set EODHD_API_KEY")
        self._key = key
        self.base_url = (base_url or EODHD_BASE_URL).rstrip("/")
        if transport is None:
            transport = LiveTransport(secrets=(key,))
        super().__init__(transport, rate_limit, sleep, (key,))

    def _params(self, **extra):
        params = {"api_token": self._key, "fmt": "json"}
        params.update(extra)
        return params

    def eod(self, symbol, start=None, end=None):
        sym = normalize_eodhd_symbol(symbol)
        params = self._params(period="d", order="a")
        if start:
            params["from"] = start
        if end:
            params["to"] = end
        data = self.get_json(f"eod {sym}", f"{self.base_url}/eod/{sym}", params)
        if not isinstance(data, list):
            raise CollectorError(f"eod {sym}: expected a JSON list")
        seen = set()
        rows = []
        for row in data:
            close = row.get("close")
            if close is None or float(close) <= 0:
                continue
            date = row.get("date")
            if date in seen:
                continue
            seen.add(date)
            rows.append(row)
        rows.sort(key=lambda r: r.get("date"))
        return rows

    fetch = eod

    def splits(self, symbol):
        sym = normalize_eodhd_symbol(symbol)
        data = self.get_json(f"splits {sym}", f"{self.base_url}/splits/{sym}",
                             self._params())
        if not isinstance(data, list):
            raise CollectorError(f"splits {sym}: expected a JSON list")
        events = [SplitEvent(item["date"], parse_split_ratio(item["split"]), item["split"])
                  for item in data]
        events.sort(key=lambda e: e.date)
        return events

    def dividends(self, symbol):
        sym = normalize_eodhd_symbol(symbol)
        data = self.get_json(f"div {sym}", f"{self.base_url}/div/{sym}", self._params())
        if not isinstance(data, list):
            raise CollectorError(f"div {sym}: expected a JSON list")
        return sorted(data, key=lambda d: d.get("date") or "")

    def search(self, query, exchange=None):
        params = self._params()
        if exchange:
            params["exchange"] = exchange
        return self.get_json(f"search {query}", f"{self.base_url}/search/{query}", params)


# ------------------------------------------------------------------ Binance
_EPOCH = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)


def _date_ms(text):
    day = _dt.date.fromisoformat(str(text)[:10])
    moment = _dt.datetime(day.year, day.month, day.day, tzinfo=_dt.timezone.utc)
    return int(moment.timestamp()) * 1000


class BinanceCollector(_Collector):
    volume_basis = "raw"
    provider = "binance"
    limit = 1000
    max_pages = 100

    def __init__(self, transport=None, rate_limit=True, sleep=time.sleep):
        if transport is None:
            transport = LiveTransport()
        super().__init__(transport, rate_limit, sleep, ())

    def klines(self, symbol, start=None, end=None):
        cursor = _date_ms(start) if start else None
        end_ms = _date_ms(end) + DAY_MS - 1 if end else None
        label = f"klines {symbol}"
        bars = []
        seen = set()
        pages = 0
        while True:
            if pages >= self.max_pages:
                raise CollectorError(
                    "pagination exceeded 100 pages - refusing to truncate silently; "
                    "raise max_pages if the range is real")
            params = {"symbol": symbol, "interval": "1d", "limit": self.limit}
            if cursor is not None:
                params["startTime"] = cursor
            if end_ms is not None:
                params["endTime"] = end_ms
            rows = self.get_json(label, BINANCE_KLINES_URL, params)
            pages += 1
            if not isinstance(rows, list):
                raise CollectorError(f"klines {symbol}: expected a JSON list")
            if not rows:
                break
            for row in rows:
                open_ms = int(row[0])
                close = float(row[4])
                if close <= 0:
                    continue
                date = (_EPOCH + _dt.timedelta(milliseconds=open_ms)).date().isoformat()
                if date in seen:
                    continue
                seen.add(date)
                bars.append({"date": date, "open": float(row[1]), "high": float(row[2]),
                             "low": float(row[3]), "close": close,
                             "adjusted_close": close, "volume": float(row[5])})
            last_open = int(rows[-1][0])
            if len(rows) < self.limit or (end_ms is not None and last_open + DAY_MS > end_ms):
                break
            cursor = last_open + DAY_MS
        bars.sort(key=lambda b: b["date"])
        return bars

    fetch = klines

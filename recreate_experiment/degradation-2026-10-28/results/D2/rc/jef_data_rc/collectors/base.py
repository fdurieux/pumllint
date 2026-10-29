"""Shared collector plumbing: errors, rate limiting, retries, pagination."""
import collections
import datetime as _dt
import json
import time

from .transport import TransportConnectionError, redact

PER_MINUTE = 1000
WINDOW_SECONDS = 60.0
DAILY_BUDGET = 100000
MAX_RETRIES = 4
BACKOFF = 2.0
MAX_PAGES = 100


class CollectorError(RuntimeError):
    """A provider request that cannot succeed."""


class DailyBudgetExhausted(CollectorError):
    """The per-UTC-day request budget is spent."""


class RateLimiter:
    """A sliding 60 s window plus a per-UTC-day budget."""

    def __init__(self, per_minute=PER_MINUTE, daily_budget=DAILY_BUDGET,
                 clock=time.monotonic, sleep=time.sleep, utc_today=None):
        self.per_minute = per_minute
        self.daily_budget = daily_budget
        self._clock = clock
        self._sleep = sleep
        self._utc_today = utc_today or (lambda: _dt.datetime.now(_dt.timezone.utc).date())
        self._window = collections.deque()
        self._day = None
        self._day_count = 0

    def acquire(self):
        today = self._utc_today()
        if today != self._day:
            self._day = today
            self._day_count = 0
        if self._day_count >= self.daily_budget:
            raise DailyBudgetExhausted(
                f"daily API budget of {self.daily_budget} spent ({today.isoformat()}); "
                "the per-minute window cannot lend quota across days")
        now = self._clock()
        while self._window and now - self._window[0] >= WINDOW_SECONDS:
            self._window.popleft()
        if len(self._window) >= self.per_minute:
            self._sleep(WINDOW_SECONDS - (now - self._window[0]))
            now = self._clock()
            while self._window and now - self._window[0] >= WINDOW_SECONDS:
                self._window.popleft()
        self._window.append(now)
        self._day_count += 1


class _NoLimit:
    def acquire(self):
        pass


class BaseCollector:
    max_retries = MAX_RETRIES
    backoff = BACKOFF
    exchange = None
    volume_basis = None

    def __init__(self, transport, rate_limit=True, sleep=time.sleep, secrets=()):
        self.transport = transport
        self._sleep = sleep
        self.secrets = [s for s in secrets if s]
        self.limiter = RateLimiter(sleep=sleep) if rate_limit else _NoLimit()

    def _redact(self, text):
        return redact(text, self.secrets)

    def get_json(self, url, params, what):
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            self.limiter.acquire()
            try:
                response = self.transport.request("GET", url, params)
            except TransportConnectionError as exc:
                if attempt < self.max_retries:
                    self._sleep(self.backoff * 2 ** attempt)
                    continue
                raise CollectorError(
                    f"{what}: network failure after {attempts} attempts: {self._redact(str(exc))}") from None
            status = int(response.status)
            if status == 429 or status >= 500:
                if attempt < self.max_retries:
                    self._sleep(self.backoff * 2 ** attempt)
                    continue
                raise CollectorError(f"{what}: HTTP {status} after {attempts} attempts")
            if status != 200:
                raise CollectorError(f"{what}: HTTP {status}: {self._redact(response.text[:200])}")
            try:
                return json.loads(response.text)
            except ValueError:
                raise CollectorError(
                    f"{what}: response is not JSON: {self._redact(response.text[:200])}") from None
        raise CollectorError(f"{what}: HTTP request loop ended")  # pragma: no cover

    def paginate(self, fetch_page, cursor, max_pages=MAX_PAGES):
        """Call fetch_page(cursor) -> (rows, next_cursor or None) until it stops."""
        rows = []
        pages = 0
        while True:
            if pages >= max_pages:
                raise CollectorError(
                    f"pagination exceeded {max_pages} pages - refusing to truncate silently; "
                    "raise max_pages if the range is real")
            page, cursor = fetch_page(cursor)
            pages += 1
            rows.extend(page)
            if cursor is None:
                return rows

    def close(self):
        self.transport.close()

"""Shared collector plumbing: errors, the rate limiter, retries, pagination."""
import collections
import json
import time
from datetime import datetime, timezone


class CollectorError(RuntimeError):
    """A provider request that cannot succeed."""


class DailyBudgetExhausted(CollectorError):
    """The per-UTC-day request budget is spent."""


class TransportConnectionError(RuntimeError):
    """A connection failure or timeout below the collector (retryable)."""


class RateLimiter:
    """A sliding 60 s window plus a per-UTC-day request budget."""

    def __init__(self, per_minute=1000, daily_budget=100000, clock=time.monotonic,
                 sleep=time.sleep, utc_now=None):
        self.per_minute = per_minute
        self.daily_budget = daily_budget
        self._clock = clock
        self._sleep = sleep
        self._utc_now = utc_now or (lambda: datetime.now(timezone.utc))
        self._window = collections.deque()
        self._day = None
        self._spent = 0

    def acquire(self):
        today = self._utc_now().date()
        if today != self._day:
            self._day = today
            self._spent = 0
        if self._spent >= self.daily_budget:
            raise DailyBudgetExhausted(
                f"daily API budget of {self.daily_budget} spent ({today.isoformat()}); "
                "the per-minute window cannot lend quota across days")
        now = self._clock()
        if len(self._window) >= self.per_minute:
            wait = 60 - (now - self._window[0])
            if wait > 0:
                self._sleep(wait)
            now = self._clock()
            while self._window and now - self._window[0] >= 60:
                self._window.popleft()
        self._window.append(now)
        self._spent += 1


class BaseCollector:
    """Retries, rate limiting and secret redaction over a transport."""

    max_retries = 4
    backoff = 2.0

    def __init__(self, transport, limiter=None, sleep=time.sleep, secrets=()):
        self.transport = transport
        self.limiter = limiter
        self._sleep = sleep
        self._secrets = [s for s in secrets if s]

    def _redact(self, text):
        text = str(text)
        for secret in self._secrets:
            text = text.replace(secret, "***")
        return text

    def get_json(self, url, params, what):
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            if self.limiter is not None:
                self.limiter.acquire()
            last = attempt == attempts - 1
            try:
                response = self.transport.request("GET", url, params)
            except TransportConnectionError as exc:
                if last:
                    raise CollectorError(f"{what}: network failure after {attempts} attempts: "
                                         f"{self._redact(exc)}") from None
                self._sleep(self.backoff * 2 ** attempt)
                continue
            status = response.status
            if status == 429 or status >= 500:
                if last:
                    raise CollectorError(f"{what}: HTTP {status} after {attempts} attempts")
                self._sleep(self.backoff * 2 ** attempt)
                continue
            if status != 200:
                raise CollectorError(f"{what}: HTTP {status}: {self._redact(response.text[:200])}")
            try:
                return json.loads(response.text)
            except ValueError:
                raise CollectorError(f"{what}: response is not JSON: "
                                     f"{self._redact(response.text[:200])}") from None
        raise AssertionError("unreachable")

    @staticmethod
    def paginate(fetch_page, cursor, max_pages=100):
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

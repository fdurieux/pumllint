"""Shared collector plumbing: rate limiting, retries, pagination."""
from __future__ import annotations

import collections
import datetime as _dt
import json
import time

from .transport import TransportConnectionError, redact


class CollectorError(RuntimeError):
    """A provider request that cannot succeed."""


class DailyBudgetExhausted(CollectorError):
    """The per-UTC-day request budget is spent."""


class RateLimiter:
    def __init__(self, per_minute: int = 1000, daily_budget: int = 100000,
                 window: float = 60.0, enabled: bool = True,
                 clock=time.monotonic, sleep=time.sleep, utc_today=None):
        self.per_minute = per_minute
        self.daily_budget = daily_budget
        self.window = window
        self.enabled = enabled
        self._clock = clock
        self._sleep = sleep
        self._utc_today = utc_today or (lambda: _dt.datetime.now(_dt.timezone.utc).date())
        self._stamps: collections.deque = collections.deque()
        self._day = None
        self._spent = 0

    def acquire(self) -> None:
        if not self.enabled:
            return
        day = self._utc_today()
        if day != self._day:
            self._day = day
            self._spent = 0
        if self._spent >= self.daily_budget:
            raise DailyBudgetExhausted(
                f"daily API budget of {self.daily_budget} spent ({day.isoformat()}); "
                "the per-minute window cannot lend quota across days")
        now = self._clock()
        while len(self._stamps) >= self.per_minute:
            wait = self.window - (now - self._stamps[0])
            if wait > 0:
                self._sleep(wait)
            now = self._clock()
            while self._stamps and now - self._stamps[0] >= self.window:
                self._stamps.popleft()
        self._stamps.append(now)
        self._spent += 1


class BaseCollector:
    max_retries = 4
    backoff = 2.0
    exchange = ""
    volume_basis = "raw"

    def __init__(self, transport=None, rate_limiter=None, sleep=time.sleep, secrets=()):
        self.secrets = tuple(s for s in secrets if s)
        self.transport = transport
        self.rate_limiter = rate_limiter if rate_limiter is not None else RateLimiter()
        self._sleep = sleep

    def _redact(self, text: str) -> str:
        return redact(text, self.secrets)

    def get_json(self, url, params, what):
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            self.rate_limiter.acquire()
            try:
                resp = self.transport.request("GET", url, params)
            except TransportConnectionError as exc:
                if attempt < self.max_retries:
                    self._sleep(self.backoff * 2 ** attempt)
                    continue
                raise CollectorError(self._redact(
                    f"{what}: network failure after {attempts} attempts: {exc}")) from None
            status = resp.status
            if status == 429 or status >= 500:
                if attempt < self.max_retries:
                    self._sleep(self.backoff * 2 ** attempt)
                    continue
                raise CollectorError(f"{what}: HTTP {status} after {attempts} attempts")
            if status != 200:
                raise CollectorError(self._redact(f"{what}: HTTP {status}: {resp.text[:200]}"))
            try:
                return json.loads(resp.text)
            except ValueError:
                raise CollectorError(self._redact(
                    f"{what}: response is not JSON: {resp.text[:200]}")) from None
        raise CollectorError(f"{what}: no attempt made")

    def paginate(self, fetch_page, cursor, max_pages: int = 100) -> list:
        rows: list = []
        pages = 0
        while True:
            if pages >= max_pages:
                raise CollectorError(
                    f"pagination exceeded {max_pages} pages - refusing to truncate silently; "
                    "raise max_pages if the range is real")
            page, cursor = fetch_page(cursor)
            pages += 1
            if page:
                rows.extend(page)
            if cursor is None:
                return rows

    def close(self) -> None:
        if self.transport is not None:
            self.transport.close()

"""Collector plumbing: transports, the rate limiter, retries and the fixture replayer."""
from __future__ import annotations

import collections
import datetime as _dt
import hashlib
import json
import os
import time
from typing import NamedTuple, Protocol
from urllib.parse import urlparse


class CollectorError(RuntimeError):
    """A provider request that cannot succeed."""


class DailyBudgetExhausted(CollectorError):
    """The per-UTC-day request budget is spent."""


class TransportConnectionError(RuntimeError):
    """A connection failure or timeout (retryable)."""


_SECRETS = set()


def register_secret(value):
    if value:
        _SECRETS.add(value)


def redact(text):
    text = str(text)
    for secret in _SECRETS:
        if secret:
            text = text.replace(secret, "***")
    return text


class Transport(Protocol):
    """request(method, url, params) -> (status, text); close()."""

    def request(self, method, url, params): ...

    def close(self): ...


class TransportResponse(NamedTuple):
    status: int
    text: str

    def json(self):
        return json.loads(self.text)


class HttpTransport:
    """Live HTTP through a requests session."""

    def __init__(self, timeout=30.0):
        import requests

        self.timeout = timeout
        self._requests = requests
        self._session = requests.Session()

    def request(self, method, url, params):
        try:
            response = self._session.request(method, url, params=params, timeout=self.timeout)
        except (self._requests.ConnectionError, self._requests.Timeout) as exc:
            raise TransportConnectionError(redact(exc)) from None
        return TransportResponse(response.status_code, response.text)

    def close(self):
        self._session.close()


def fixture_key(method, url, params):
    return {"method": method.upper(), "path": urlparse(url).path,
            "params": {name: str(value) for name, value in sorted((params or {}).items())
                       if name != "api_token"}}


def _key_text(key):
    return json.dumps(key, sort_keys=True)


def fixture_name(key):
    slug = key["path"].strip("/").replace("/", "_")
    digest = hashlib.sha256(_key_text(key).encode("utf-8")).hexdigest()[:10]
    return f"{slug}_{digest}.json"


class ReplayTransport:
    """Answers requests from recorded-fixture files; never reaches the network."""

    def __init__(self, fixture_dir):
        self.fixture_dir = str(fixture_dir)
        self.calls = []
        self._answers = {}
        for root, dirs, files in os.walk(self.fixture_dir):
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
        self.calls.append(key)
        hit = self._answers.get(_key_text(key))
        if hit is None:
            known = sorted(f"  {k['path']} {k['params']}" for k, _ in self._answers.values())
            raise CollectorError(
                f"no recorded fixture for {key['method']} {key['path']} {key['params']}\n"
                f"known fixtures:\n" + "\n".join(known))
        response = hit[1]
        return TransportResponse(int(response["status"]), json.dumps(response["json"]))

    def close(self):
        pass


class RecordingTransport:
    """Wraps an inner transport and writes one fixture file per request."""

    def __init__(self, inner, fixture_dir):
        self.inner = inner
        self.fixture_dir = str(fixture_dir)
        self.written = []

    def request(self, method, url, params):
        status, text = self.inner.request(method, url, params)
        key = fixture_key(method, url, params)
        try:
            body = json.loads(text)
        except ValueError:
            body = text
        fixture = {"request": key, "response": {"status": int(status), "json": body}}
        content = json.dumps(fixture, indent=1, sort_keys=True) + "\n"
        path = os.path.join(self.fixture_dir, fixture_name(key))
        if any(secret and secret in content for secret in _SECRETS):
            raise CollectorError(
                f"refusing to write fixture: secret material in {path} response/request")
        os.makedirs(self.fixture_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        self.written.append(path)
        return TransportResponse(status, text)

    def close(self):
        self.inner.close()


class RateLimiter:
    """A sliding 60 s window plus a per-UTC-day request budget."""

    def __init__(self, per_minute=1000, daily_budget=100000, enabled=True,
                 clock=time.monotonic, sleep=time.sleep, utc_now=None):
        self.per_minute = per_minute
        self.daily_budget = daily_budget
        self.enabled = enabled
        self._clock = clock
        self._sleep = sleep
        self._utc_now = utc_now or (lambda: _dt.datetime.now(_dt.timezone.utc))
        self._window = collections.deque()
        self._day = None
        self._spent = 0

    def acquire(self):
        if not self.enabled:
            return
        day = self._utc_now().date()
        if day != self._day:
            self._day = day
            self._spent = 0
        if self._spent >= self.daily_budget:
            raise DailyBudgetExhausted(
                f"daily API budget of {self.daily_budget} spent ({self._day}); the per-minute "
                f"window cannot lend quota across days")
        now = self._clock()
        while self._window and now - self._window[0] >= 60.0:
            self._window.popleft()
        if len(self._window) >= self.per_minute:
            self._sleep(60.0 - (now - self._window[0]))
            now = self._clock()
            while self._window and now - self._window[0] >= 60.0:
                self._window.popleft()
        self._window.append(now)
        self._spent += 1


class BaseCollector:
    """Retries, backoff and rate limiting around one transport."""

    max_retries = 4
    backoff = 2.0

    def __init__(self, transport=None, rate_limiter=None, sleep=None):
        self.transport = transport if transport is not None else HttpTransport()
        self.rate_limiter = rate_limiter if rate_limiter is not None else RateLimiter()
        self._sleep = sleep if sleep is not None else time.sleep

    def get_json(self, url, params, what):
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            self.rate_limiter.acquire()
            try:
                status, text = self.transport.request("GET", url, params)
            except TransportConnectionError as exc:
                if attempt < self.max_retries:
                    self._sleep(self.backoff * 2 ** attempt)
                    continue
                raise CollectorError(
                    f"{what}: network failure after {attempts} attempts: {redact(exc)}") from None
            if status == 429 or status >= 500:
                if attempt < self.max_retries:
                    self._sleep(self.backoff * 2 ** attempt)
                    continue
                raise CollectorError(f"{what}: HTTP {status} after {attempts} attempts")
            if status != 200:
                raise CollectorError(f"{what}: HTTP {status}: {redact(text[:200])}")
            try:
                return json.loads(text)
            except ValueError:
                raise CollectorError(
                    f"{what}: response is not JSON: {redact(text[:200])}") from None
        raise CollectorError(f"{what}: no attempt made")

    def paginate(self, fetch_page, cursor, max_pages=100):
        """Call fetch_page(cursor) -> (rows, next_cursor) until next_cursor is None."""
        rows = []
        pages = 0
        while True:
            if pages >= max_pages:
                raise CollectorError(
                    f"pagination exceeded {max_pages} pages - refusing to truncate silently; "
                    f"raise max_pages if the range is real")
            page, cursor = fetch_page(cursor)
            pages += 1
            rows.extend(page)
            if cursor is None:
                return rows

    def close(self):
        self.transport.close()

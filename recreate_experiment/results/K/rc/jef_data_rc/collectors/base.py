"""Collector plumbing: transports, recorded fixtures, rate limiting and retries."""
from __future__ import annotations

import collections
import datetime as _dt
import hashlib
import json
import os
import time
from typing import NamedTuple
from urllib.parse import urlparse

HTTP_TIMEOUT = 30.0
PER_MINUTE = 1000
WINDOW_SECONDS = 60.0
DAILY_BUDGET = 100000
MANIFEST_NAME = "manifest.json"


class CollectorError(RuntimeError):
    """A provider request that cannot succeed."""


class DailyBudgetExhausted(CollectorError):
    """The per-UTC-day request budget is spent."""


class TransportConnectionError(RuntimeError):
    """A retryable connection failure or timeout."""


class TransportResponse(NamedTuple):
    status: int
    text: str

    def json(self):
        return json.loads(self.text)


def redact(text, secrets):
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


def fixture_key(method, url, params):
    items = sorted((name, str(value)) for name, value in (params or {}).items()
                   if name != "api_token")
    return {"method": method.upper(), "path": urlparse(url).path, "params": dict(items)}


def _key_text(key):
    return json.dumps(key, sort_keys=True)


def fixture_filename(key):
    slug = key["path"].strip("/").replace("/", "_")
    digest = hashlib.sha256(_key_text(key).encode("utf-8")).hexdigest()[:10]
    return f"{slug}_{digest}.json"


class HttpTransport:
    """Live HTTP through a requests session."""

    def __init__(self, timeout=HTTP_TIMEOUT, secrets=()):
        import requests

        self._requests = requests
        self.timeout = timeout
        self.secrets = tuple(secrets)
        self.session = requests.Session()

    def request(self, method, url, params):
        requests = self._requests
        try:
            response = self.session.request(method, url, params=params, timeout=self.timeout)
        except (requests.ConnectionError, requests.Timeout) as exc:
            raise TransportConnectionError(redact(str(exc), self.secrets)) from None
        return TransportResponse(response.status_code, response.text)

    def close(self):
        self.session.close()


class ReplayTransport:
    """Answers requests from recorded fixture files."""

    def __init__(self, fixture_dir):
        self.fixture_dir = str(fixture_dir)
        self.calls = []
        self._answers = {}
        self._keys = {}
        for root, dirs, files in os.walk(self.fixture_dir):
            dirs.sort()
            for name in sorted(files):
                if not name.endswith(".json") or name == MANIFEST_NAME:
                    continue
                with open(os.path.join(root, name), encoding="utf-8") as handle:
                    doc = json.load(handle)
                key = doc["request"]
                text = _key_text(key)
                response = doc["response"]
                self._answers[text] = (int(response["status"]), json.dumps(response["json"]))
                self._keys[text] = key

    def request(self, method, url, params):
        key = fixture_key(method, url, params)
        self.calls.append(key)
        answer = self._answers.get(_key_text(key))
        if answer is None:
            known = sorted(f"  {k['path']} {k['params']}" for k in self._keys.values())
            message = (f"no recorded fixture for {key['method']} {key['path']} "
                       f"{key['params']}\nknown fixtures:")
            if known:
                message += "\n" + "\n".join(known)
            raise CollectorError(message)
        return TransportResponse(*answer)

    def close(self):
        pass


class RecordingTransport:
    """Wraps a transport and writes every exchange as a fixture file."""

    def __init__(self, inner, fixture_dir, secrets=()):
        self.inner = inner
        self.fixture_dir = str(fixture_dir)
        self.secrets = tuple(secrets)
        self.written = []

    def request(self, method, url, params):
        response = self.inner.request(method, url, params)
        key = fixture_key(method, url, params)
        try:
            body = json.loads(response.text)
        except ValueError:
            body = response.text
        fixture = {"request": key, "response": {"status": int(response.status), "json": body}}
        text = json.dumps(fixture, indent=1, sort_keys=True) + "\n"
        path = os.path.join(self.fixture_dir, fixture_filename(key))
        if any(secret and secret in text for secret in self.secrets):
            raise CollectorError(
                f"refusing to write fixture: secret material in {path} response/request")
        os.makedirs(self.fixture_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        self.written.append(path)
        return response

    def close(self):
        self.inner.close()


class RateLimiter:
    """A sliding per-minute window plus a per-UTC-day budget."""

    def __init__(self, per_minute=PER_MINUTE, daily_budget=DAILY_BUDGET,
                 window=WINDOW_SECONDS, clock=time.time, sleep=time.sleep):
        self.per_minute = per_minute
        self.daily_budget = daily_budget
        self.window = window
        self._clock = clock
        self._sleep = sleep
        self._stamps = collections.deque()
        self._day = None
        self._spent = 0

    def _drop_expired(self, now):
        while self._stamps and now - self._stamps[0] >= self.window:
            self._stamps.popleft()

    def acquire(self):
        now = self._clock()
        day = _dt.datetime.fromtimestamp(now, tz=_dt.timezone.utc).date()
        if day != self._day:
            self._day = day
            self._spent = 0
        if self._spent >= self.daily_budget:
            raise DailyBudgetExhausted(
                f"daily API budget of {self.daily_budget} spent ({day.isoformat()}); the "
                f"per-minute window cannot lend quota across days")
        self._drop_expired(now)
        if len(self._stamps) >= self.per_minute:
            self._sleep(self.window - (now - self._stamps[0]))
            now = self._clock()
            self._drop_expired(now)
        self._stamps.append(now)
        self._spent += 1


class BaseCollector:
    """Retries, rate limiting and JSON decoding shared by every collector."""

    max_retries = 4
    backoff = 2.0

    def __init__(self, transport=None, rate_limiter=None, sleep=time.sleep, secrets=()):
        self.secrets = tuple(secrets)
        self.transport = transport if transport is not None else HttpTransport(
            secrets=self.secrets)
        self.rate_limiter = rate_limiter
        self._sleep = sleep

    def _redact(self, text):
        return redact(text, self.secrets)

    def get_json(self, url, params, what):
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            if self.rate_limiter is not None:
                self.rate_limiter.acquire()
            try:
                status, text = self.transport.request("GET", url, params)
            except TransportConnectionError as exc:
                if attempt < self.max_retries:
                    self._sleep(self.backoff * 2 ** attempt)
                    continue
                raise CollectorError(
                    f"{what}: network failure after {attempts} attempts: "
                    f"{self._redact(str(exc))}") from None
            if status == 429 or status >= 500:
                if attempt < self.max_retries:
                    self._sleep(self.backoff * 2 ** attempt)
                    continue
                raise CollectorError(f"{what}: HTTP {status} after {attempts} attempts")
            if status != 200:
                raise CollectorError(f"{what}: HTTP {status}: {self._redact(text[:200])}")
            try:
                return json.loads(text)
            except ValueError:
                raise CollectorError(
                    f"{what}: response is not JSON: {self._redact(text[:200])}") from None
        raise CollectorError(f"{what}: no attempt made")

    def paginate(self, fetch_page, cursor, max_pages):
        """Call fetch_page(cursor) -> (rows, next_cursor) until next_cursor is None."""
        rows = []
        pages = 0
        while True:
            if pages >= max_pages:
                raise CollectorError(
                    f"pagination exceeded {max_pages} pages - refusing to truncate "
                    f"silently; raise max_pages if the range is real")
            page, cursor = fetch_page(cursor)
            pages += 1
            rows.extend(page)
            if cursor is None:
                return rows

    def close(self):
        self.transport.close()

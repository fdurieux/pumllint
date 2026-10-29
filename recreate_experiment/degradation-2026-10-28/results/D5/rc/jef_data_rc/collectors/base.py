"""Collector plumbing: transports, fixture identity, rate limiting, retries."""
from __future__ import annotations

import collections
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

DEFAULT_TIMEOUT = 30.0
PER_MINUTE = 1000
DAILY_BUDGET = 100000
WINDOW_SECONDS = 60.0


class CollectorError(RuntimeError):
    """A provider request that cannot succeed."""


class DailyBudgetExhausted(CollectorError):
    """The per-UTC-day request budget is spent."""


class TransportConnectionError(RuntimeError):
    """A connection error or timeout (retryable)."""


class TransportResponse:
    def __init__(self, status: int, text: str):
        self.status = int(status)
        self.text = text

    def json(self):
        return json.loads(self.text)

    def __iter__(self):
        return iter((self.status, self.text))


def redact(text: str, secrets) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


class HttpTransport:
    """Live transport over a requests session."""

    def __init__(self, timeout: float = DEFAULT_TIMEOUT, secrets=()):
        import requests

        self._requests = requests
        self.timeout = timeout
        self.secrets = list(secrets)
        self.session = requests.Session()

    def request(self, method, url, params):
        try:
            response = self.session.request(method, url, params=params, timeout=self.timeout)
        except (self._requests.ConnectionError, self._requests.Timeout) as exc:
            raise TransportConnectionError(redact(str(exc), self.secrets)) from None
        return TransportResponse(response.status_code, response.text)

    def close(self):
        self.session.close()


def request_key(method, url, params) -> dict:
    return {"method": method.upper(), "path": urlparse(url).path,
            "params": {name: str(value) for name, value in sorted(params.items())
                       if name != "api_token"}}


def _key_text(key) -> str:
    return json.dumps(key, sort_keys=True)


def fixture_name(key) -> str:
    slug = key["path"].strip("/").replace("/", "_")
    digest = hashlib.sha256(_key_text(key).encode("utf-8")).hexdigest()[:10]
    return f"{slug}_{digest}.json"


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
                if not name.endswith(".json") or name == "manifest.json":
                    continue
                with open(os.path.join(root, name), encoding="utf-8") as handle:
                    doc = json.load(handle)
                key = doc["request"]
                text = _key_text(key)
                self._answers[text] = doc["response"]
                self._keys[text] = key

    def request(self, method, url, params):
        key = request_key(method, url, params)
        self.calls.append(key)
        text = _key_text(key)
        if text not in self._answers:
            known = sorted(f"  {k['path']} {k['params']}" for k in self._keys.values())
            raise CollectorError(
                "\n".join([f"no recorded fixture for {key['method']} {key['path']} "
                           f"{key['params']}", "known fixtures:", *known]))
        response = self._answers[text]
        return TransportResponse(response["status"], json.dumps(response["json"]))

    def close(self):
        return None


class RecordingTransport:
    """Wraps a transport and writes one fixture file per request."""

    def __init__(self, inner, fixture_dir, secrets=()):
        self.inner = inner
        self.fixture_dir = str(fixture_dir)
        self.secrets = [s for s in secrets if s]
        self.written = []

    def request(self, method, url, params):
        response = self.inner.request(method, url, params)
        key = request_key(method, url, params)
        try:
            body = json.loads(response.text)
        except ValueError:
            body = response.text
        doc = {"request": key, "response": {"status": int(response.status), "json": body}}
        text = json.dumps(doc, indent=1, sort_keys=True) + "\n"
        path = os.path.join(self.fixture_dir, fixture_name(key))
        if any(secret in text for secret in self.secrets):
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
    """Sliding 60 s window plus a per-UTC-day request budget."""

    def __init__(self, per_minute=PER_MINUTE, daily_budget=DAILY_BUDGET,
                 clock=time.monotonic, sleep=time.sleep, utcnow=None):
        self.per_minute = per_minute
        self.daily_budget = daily_budget
        self._clock = clock
        self._sleep = sleep
        self._utcnow = utcnow or (lambda: datetime.now(timezone.utc))
        self._window = collections.deque()
        self._day = None
        self._day_count = 0

    def _expire(self, now):
        while self._window and now - self._window[0] >= WINDOW_SECONDS:
            self._window.popleft()

    def acquire(self):
        today = self._utcnow().date()
        if today != self._day:
            self._day = today
            self._day_count = 0
        if self._day_count >= self.daily_budget:
            raise DailyBudgetExhausted(
                f"daily API budget of {self.daily_budget} spent ({today}); "
                "the per-minute window cannot lend quota across days")
        now = self._clock()
        self._expire(now)
        if len(self._window) >= self.per_minute:
            self._sleep(WINDOW_SECONDS - (now - self._window[0]))
            now = self._clock()
            self._expire(now)
        self._window.append(now)
        self._day_count += 1


class NoLimiter:
    def acquire(self):
        return None


class BaseCollector:
    """Retries, rate limiting and JSON decoding shared by every collector."""

    max_retries = 4
    backoff = 2.0
    exchange = ""
    volume_basis = "raw"

    def __init__(self, transport, *, rate_limit=True, sleep=time.sleep, secrets=()):
        self.transport = transport
        self.limiter = RateLimiter() if rate_limit else NoLimiter()
        self._sleep = sleep
        self.secrets = [s for s in secrets if s]

    def _redact(self, text: str) -> str:
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
                raise CollectorError(self._redact(
                    f"{what}: network failure after {attempts} attempts: {exc}")) from None
            status = response.status
            if status == 429 or status >= 500:
                if attempt < self.max_retries:
                    self._sleep(self.backoff * 2 ** attempt)
                    continue
                raise CollectorError(f"{what}: HTTP {status} after {attempts} attempts")
            if status != 200:
                raise CollectorError(self._redact(f"{what}: HTTP {status}: {response.text[:200]}"))
            try:
                return json.loads(response.text)
            except ValueError:
                raise CollectorError(self._redact(
                    f"{what}: response is not JSON: {response.text[:200]}")) from None
        raise CollectorError(f"{what}: HTTP request failed")

    def paginate(self, fetch_page, cursor, max_pages):
        """Call fetch_page(cursor) -> (rows, next_cursor or None) until done."""
        rows = []
        pages = 0
        while True:
            if pages >= max_pages:
                raise CollectorError(
                    f"pagination exceeded {max_pages} pages - refusing to truncate "
                    "silently; raise max_pages if the range is real")
            page, cursor = fetch_page(cursor)
            pages += 1
            rows.extend(page)
            if cursor is None:
                return rows

    def close(self):
        self.transport.close()

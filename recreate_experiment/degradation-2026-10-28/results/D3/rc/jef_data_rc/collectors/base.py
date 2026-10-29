"""Collector plumbing: transports, recorded fixtures, rate limiting and retries."""
from __future__ import annotations

import hashlib
import json
import os
import time
from collections import deque
from datetime import datetime, timezone
from urllib.parse import urlparse


class CollectorError(RuntimeError):
    """A provider request that cannot succeed."""


class DailyBudgetExhausted(CollectorError):
    """The per-UTC-day request budget is spent."""


class TransportConnectionError(RuntimeError):
    """A connection failure or timeout; retryable."""


def redact(text: str, secrets) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


class TransportResponse:
    def __init__(self, status: int, text: str):
        self.status = int(status)
        self.text = text

    def json(self):
        return json.loads(self.text)


class HttpTransport:
    """Live HTTP through a requests session."""

    def __init__(self, timeout: float = 30.0, secrets=()):
        import requests

        self._requests = requests
        self.timeout = timeout
        self.secrets = tuple(secrets)
        self.session = requests.Session()

    def request(self, method: str, url: str, params: dict) -> TransportResponse:
        try:
            response = self.session.request(method, url, params=params, timeout=self.timeout)
        except (self._requests.ConnectionError, self._requests.Timeout) as exc:
            raise TransportConnectionError(redact(str(exc), self.secrets)) from None
        return TransportResponse(response.status_code, response.text)

    def close(self) -> None:
        self.session.close()


def fixture_key(method: str, url: str, params: dict) -> dict:
    clean = {name: str(value) for name, value in sorted(params.items()) if name != "api_token"}
    return {"method": method.upper(), "path": urlparse(url).path, "params": clean}


def key_text(key: dict) -> str:
    return json.dumps(key, sort_keys=True)


def fixture_name(key: dict) -> str:
    slug = key["path"].strip("/").replace("/", "_")
    digest = hashlib.sha256(key_text(key).encode("utf-8")).hexdigest()[:10]
    return f"{slug}_{digest}.json"


class ReplayTransport:
    """Answers requests from recorded fixture files."""

    def __init__(self, fixture_dir: str):
        self.fixture_dir = str(fixture_dir)
        self.calls: list = []
        self._answers: dict = {}
        self._keys: dict = {}
        for root, dirs, files in os.walk(self.fixture_dir):
            dirs.sort()
            for name in sorted(files):
                if not name.endswith(".json") or name == "manifest.json":
                    continue
                with open(os.path.join(root, name), encoding="utf-8") as handle:
                    doc = json.load(handle)
                key = doc["request"]
                text = key_text(key)
                self._answers[text] = doc["response"]
                self._keys[text] = key

    def request(self, method: str, url: str, params: dict) -> TransportResponse:
        key = fixture_key(method, url, params)
        self.calls.append(key)
        text = key_text(key)
        if text not in self._answers:
            known = sorted(f"  {k['path']} {k['params']!r}" for k in self._keys.values())
            message = f"no recorded fixture for {key['method']} {key['path']} {key['params']!r}\nknown fixtures:"
            if known:
                message += "\n" + "\n".join(known)
            raise CollectorError(message)
        answer = self._answers[text]
        return TransportResponse(answer["status"], json.dumps(answer["json"]))

    def close(self) -> None:
        pass


class RecordingTransport:
    """Wraps a transport and writes one fixture file per request."""

    def __init__(self, inner, fixture_dir: str, secrets=()):
        self.inner = inner
        self.fixture_dir = str(fixture_dir)
        self.secrets = tuple(s for s in secrets if s)
        self.written: list = []

    def request(self, method: str, url: str, params: dict) -> TransportResponse:
        response = self.inner.request(method, url, params)
        key = fixture_key(method, url, params)
        try:
            body = json.loads(response.text)
        except ValueError:
            body = response.text
        text = json.dumps({"request": key, "response": {"status": int(response.status), "json": body}},
                          indent=1, sort_keys=True) + "\n"
        path = os.path.join(self.fixture_dir, fixture_name(key))
        if any(secret in text for secret in self.secrets):
            raise CollectorError(f"refusing to write fixture: secret material in {path} response/request")
        os.makedirs(self.fixture_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        self.written.append(path)
        return response

    def close(self) -> None:
        self.inner.close()


class RateLimiter:
    """A sliding per-minute window plus a per-UTC-day budget."""

    def __init__(self, per_minute: int = 1000, daily_budget: int = 100000, enabled: bool = True,
                 sleep=time.sleep, clock=time.time):
        self.per_minute = per_minute
        self.daily_budget = daily_budget
        self.enabled = enabled
        self._sleep = sleep
        self._clock = clock
        self._window: deque = deque()
        self._day = None
        self._spent = 0

    def acquire(self) -> None:
        if not self.enabled:
            return
        now = self._clock()
        day = datetime.fromtimestamp(now, tz=timezone.utc).date()
        if day != self._day:
            self._day = day
            self._spent = 0
        if self._spent >= self.daily_budget:
            raise DailyBudgetExhausted(
                f"daily API budget of {self.daily_budget} spent ({day.isoformat()}); "
                f"the per-minute window cannot lend quota across days")
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
    """Retries, backoff and rate limiting shared by every collector."""

    max_retries = 4
    backoff = 2.0

    def __init__(self, transport, rate_limit: bool = True, sleep=None, secrets=()):
        self.transport = transport
        self._sleep = sleep if sleep is not None else time.sleep
        self.secrets = tuple(s for s in secrets if s)
        self.limiter = RateLimiter(enabled=rate_limit, sleep=self._sleep)

    def _redact(self, text: str) -> str:
        return redact(text, self.secrets)

    def get_json(self, url: str, params: dict, what: str):
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
            status = response.status
            if status == 429 or status >= 500:
                if attempt < self.max_retries:
                    self._sleep(self.backoff * 2 ** attempt)
                    continue
                raise CollectorError(f"{what}: HTTP {status} after {attempts} attempts")
            if status != 200:
                raise CollectorError(f"{what}: HTTP {status}: {self._redact(response.text)[:200]}")
            try:
                return json.loads(response.text)
            except ValueError:
                raise CollectorError(f"{what}: response is not JSON: {self._redact(response.text)[:200]}") from None
        raise CollectorError(f"{what}: HTTP failure after {attempts} attempts")

    def paginate(self, fetch_page, cursor, max_pages: int):
        """Call fetch_page(cursor) -> (rows, next_cursor or None) until it stops."""
        out = []
        pages = 0
        while True:
            if pages >= max_pages:
                raise CollectorError(
                    f"pagination exceeded {max_pages} pages - refusing to truncate silently; "
                    f"raise max_pages if the range is real")
            rows, cursor = fetch_page(cursor)
            pages += 1
            out.extend(rows)
            if cursor is None:
                return out

    def close(self) -> None:
        self.transport.close()

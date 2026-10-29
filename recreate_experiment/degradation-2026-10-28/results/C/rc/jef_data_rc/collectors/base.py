"""Collector plumbing: transports, recorded fixtures, rate limiting and retries."""
import hashlib
import json
import os
import time
from collections import deque
from datetime import datetime, timezone
from urllib.parse import urlparse

SECRET_PARAM = "api_token"


class CollectorError(RuntimeError):
    """A provider request that cannot succeed."""


class DailyBudgetExhausted(CollectorError):
    """The per-UTC-day request budget is spent."""


class TransportConnectionError(RuntimeError):
    """A connection error or timeout, retryable by the collector."""


def redact(text, secrets):
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


class TransportResponse:
    """An HTTP answer: status code and body text."""

    def __init__(self, status, text):
        self.status = int(status)
        self.text = text

    def json(self):
        return json.loads(self.text)

    def __iter__(self):
        return iter((self.status, self.text))


def fixture_key(method, url, params):
    """The recorded-fixture identity of a request."""
    clean = {name: str(value) for name, value in (params or {}).items() if name != SECRET_PARAM}
    return {"method": method.upper(), "path": urlparse(url).path,
            "params": {name: clean[name] for name in sorted(clean)}}


def key_text(key):
    return json.dumps(key, sort_keys=True)


def fixture_filename(key):
    slug = key["path"].strip("/").replace("/", "_")
    digest = hashlib.sha256(key_text(key).encode("utf-8")).hexdigest()[:10]
    return f"{slug}_{digest}.json"


class HttpTransport:
    """Live HTTP through a requests session."""

    def __init__(self, timeout=30.0, secrets=()):
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


class ReplayTransport:
    """Answers requests from recorded-fixture files; never reaches the network."""

    def __init__(self, fixture_dir):
        self.fixture_dir = str(fixture_dir)
        self.calls = []
        self._fixtures = {}
        for root, dirs, files in os.walk(self.fixture_dir):
            dirs.sort()
            for name in sorted(files):
                if not name.endswith(".json") or name == "manifest.json":
                    continue
                with open(os.path.join(root, name), encoding="utf-8") as handle:
                    doc = json.load(handle)
                request = doc["request"]
                self._fixtures[key_text(request)] = (request, doc["response"])

    def request(self, method, url, params):
        key = fixture_key(method, url, params)
        self.calls.append(key)
        found = self._fixtures.get(key_text(key))
        if found is None:
            known = sorted(f"  {req['path']} {req['params']}" for req, _ in self._fixtures.values())
            lines = [f"no recorded fixture for {key['method']} {key['path']} {key['params']}",
                     "known fixtures:"] + known
            raise CollectorError("\n".join(lines))
        response = found[1]
        return TransportResponse(response["status"], json.dumps(response["json"]))

    def close(self):
        pass


class RecordingTransport:
    """Wraps another transport and writes one fixture file per request."""

    def __init__(self, inner, fixture_dir, secrets=()):
        self.inner = inner
        self.fixture_dir = str(fixture_dir)
        self.secrets = [s for s in secrets if s]
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
        if any(secret in text for secret in self.secrets):
            raise CollectorError(f"refusing to write fixture: secret material in {path} response/request")
        os.makedirs(self.fixture_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        self.written.append(path)
        return response

    def close(self):
        self.inner.close()


class RateLimiter:
    """A sliding per-minute window plus a per-UTC-day budget."""

    def __init__(self, per_minute=1000, daily_budget=100000, clock=time.monotonic,
                 sleep=time.sleep, utc_now=None):
        self.per_minute = per_minute
        self.daily_budget = daily_budget
        self._clock = clock
        self._sleep = sleep
        self._utc_now = utc_now or (lambda: datetime.now(timezone.utc))
        self._window = deque()
        self._day = None
        self._spent = 0

    def _expire(self, now):
        while self._window and now - self._window[0] >= 60.0:
            self._window.popleft()

    def acquire(self):
        today = self._utc_now().date()
        if today != self._day:
            self._day = today
            self._spent = 0
        if self._spent >= self.daily_budget:
            raise DailyBudgetExhausted(
                f"daily API budget of {self.daily_budget} spent ({today}); the per-minute "
                f"window cannot lend quota across days")
        now = self._clock()
        self._expire(now)
        if len(self._window) >= self.per_minute:
            self._sleep(60.0 - (now - self._window[0]))
            now = self._clock()
            self._expire(now)
        self._window.append(now)
        self._spent += 1


class BaseCollector:
    """Retries, backoff and rate limiting shared by every collector."""

    max_retries = 4
    backoff = 2.0

    def __init__(self, transport, rate_limiter=None, sleep=time.sleep, secrets=()):
        self.transport = transport
        self.rate_limiter = rate_limiter
        self._sleep = sleep
        self.secrets = [s for s in secrets if s]

    def _redact(self, text):
        return redact(text, self.secrets)

    def get_json(self, url, params, what):
        attempts = self.max_retries + 1
        failure = None
        for attempt in range(attempts):
            if self.rate_limiter is not None:
                self.rate_limiter.acquire()
            try:
                response = self.transport.request("GET", url, params)
            except TransportConnectionError as exc:
                failure = ("network", exc)
            else:
                status = response.status
                if status == 429 or status >= 500:
                    failure = ("status", status)
                elif status != 200:
                    raise CollectorError(f"{what}: HTTP {status}: {self._redact(response.text[:200])}")
                else:
                    try:
                        return json.loads(response.text)
                    except ValueError:
                        raise CollectorError(
                            f"{what}: response is not JSON: {self._redact(response.text[:200])}") from None
            if attempt < attempts - 1:
                self._sleep(self.backoff * 2 ** attempt)
        if failure[0] == "status":
            raise CollectorError(f"{what}: HTTP {failure[1]} after {attempts} attempts")
        raise CollectorError(
            f"{what}: network failure after {attempts} attempts: {self._redact(str(failure[1]))}")

    def paginate(self, fetch_page, cursor, max_pages):
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

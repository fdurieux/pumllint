"""Provider-neutral HTTP collection plumbing.

Every collector sends requests through a transport with the protocol

    request(method, url, params) -> TransportResponse

while `BaseCollector` owns the rate budget and the retry loop, so the same
policy wraps live (`HttpTransport`), replayed (`ReplayTransport`) and recorded
(`RecordingTransport`) traffic. `requests` is imported only when an
`HttpTransport` is constructed.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import urlsplit

SECRET_PARAMS = ("api_token",)
DEFAULT_PER_MINUTE = 1000
DEFAULT_DAILY_BUDGET = 100_000
DEFAULT_MAX_RETRIES = 4
DEFAULT_BACKOFF = 2.0
DEFAULT_MAX_PAGES = 100
ERROR_BODY_CHARS = 200


class CollectorError(RuntimeError):
    """A provider request or response could not be turned into data."""


class DailyBudgetExhausted(CollectorError):
    """The hard UTC-day request budget is spent."""


class TransportConnectionError(Exception):
    """A retryable network failure (connection or timeout)."""


@dataclass
class TransportResponse:
    status: int
    text: str

    def json(self) -> Any:
        return json.loads(self.text)


def public_params(params: dict | None) -> dict[str, str]:
    """Request parameters without secrets, sorted, values as strings."""
    return {
        str(k): str(v)
        for k, v in sorted((params or {}).items(), key=lambda kv: str(kv[0]))
        if k not in SECRET_PARAMS and v is not None
    }


def request_identity(method: str, url: str, params: dict | None) -> dict:
    path = urlsplit(url).path or url
    return {"method": method.upper(), "path": path, "params": public_params(params)}


def request_key(method: str, url: str, params: dict | None) -> str:
    """Public request identity: uppercased method, URL path, sorted public params."""
    return json.dumps(request_identity(method, url, params), sort_keys=True)


def redact(text: str, secrets: Iterable[str]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(str(secret), "***")
    return text


class HttpTransport:
    """The live transport, backed by a `requests.Session`."""

    def __init__(self, timeout: float = 30.0, secret_params: Iterable[str] = SECRET_PARAMS):
        import requests

        self._requests = requests
        self.session = requests.Session()
        self.timeout = timeout
        self.secret_params = tuple(secret_params)

    def request(self, method: str, url: str, params: dict | None) -> TransportResponse:
        params = dict(params or {})
        try:
            resp = self.session.request(method, url, params=params, timeout=self.timeout)
        except (self._requests.ConnectionError, self._requests.Timeout) as exc:
            secrets = [str(params[k]) for k in self.secret_params if params.get(k)]
            raise TransportConnectionError(redact(str(exc), secrets)) from None
        return TransportResponse(resp.status_code, resp.text)

    def close(self) -> None:
        self.session.close()


def _fixture_identity(request: Any) -> str:
    if isinstance(request, str):
        method, _, rest = request.strip().partition(" ")
        parts = urlsplit(rest)
        params: dict[str, str] = {}
        if parts.query:
            for pair in parts.query.split("&"):
                k, _, v = pair.partition("=")
                params[k] = v
        return request_key(method or "GET", parts.path, params)
    if isinstance(request, dict):
        method = str(request.get("method", "GET"))
        target = request.get("path") or request.get("url") or ""
        params = request.get("params") or {}
        return request_key(method, str(target), params)
    raise CollectorError(f"unrecognized fixture request identity: {request!r}")


def _fixture_response(response: Any) -> TransportResponse:
    if not isinstance(response, dict):
        raise CollectorError(f"unrecognized fixture response: {response!r}")
    status = int(response.get("status", 200))
    for key in ("json", "body", "data"):
        if key in response:
            return TransportResponse(status, json.dumps(response[key]))
    if "text" in response:
        return TransportResponse(status, str(response["text"]))
    return TransportResponse(status, "null")


class ReplayTransport:
    """Serve recorded fixtures by public request identity; never the network."""

    def __init__(self, fixture_dir: str | Path):
        self.fixture_dir = Path(fixture_dir)
        self.fixtures: dict[str, Any] = {}
        self.calls: list[str] = []
        for path in sorted(self.fixture_dir.rglob("*.json")):
            if path.name == "manifest.json":
                continue
            with open(path, encoding="utf-8") as handle:
                doc = json.load(handle)
            if not isinstance(doc, dict) or "request" not in doc or "response" not in doc:
                continue
            self.fixtures.setdefault(_fixture_identity(doc["request"]), doc["response"])

    def request(self, method: str, url: str, params: dict | None) -> TransportResponse:
        key = request_key(method, url, params)
        self.calls.append(key)
        if key not in self.fixtures:
            known = "; ".join(sorted(self.fixtures)) or "none"
            raise CollectorError(f"no recorded fixture for request {key} (known: {known})")
        return _fixture_response(self.fixtures[key])

    def close(self) -> None:
        pass


class RecordingTransport:
    """Forward to `inner` and write each response as a public fixture."""

    def __init__(self, inner, fixture_dir: str | Path, secrets: Iterable[str] = ()):
        self.inner = inner
        self.fixture_dir = Path(fixture_dir)
        self.secrets = tuple(s for s in secrets if s)

    def request(self, method: str, url: str, params: dict | None) -> TransportResponse:
        resp = self.inner.request(method, url, params)
        identity = request_identity(method, url, params)
        fixture = {"request": identity, "response": {"status": resp.status, "json": resp.json()}}
        text = json.dumps(fixture, indent=2, sort_keys=True)
        for secret in self.secrets:
            if secret in text:
                raise CollectorError("refusing to record a fixture that contains a supplied secret")
        slug = re.sub(r"[^A-Za-z0-9]+", "_", identity["path"]).strip("_") or "root"
        digest = hashlib.sha256(request_key(method, url, params).encode("utf-8")).hexdigest()[:12]
        self.fixture_dir.mkdir(parents=True, exist_ok=True)
        (self.fixture_dir / f"{slug}-{digest}.json").write_text(text + "\n", encoding="utf-8")
        return resp

    def close(self) -> None:
        self.inner.close()


def _utc_today() -> _dt.date:
    return _dt.datetime.now(_dt.timezone.utc).date()


class RateLimiter:
    """A sliding 60-second window plus a hard budget for the current UTC date."""

    WINDOW_SECONDS = 60.0

    def __init__(self, per_minute: int = DEFAULT_PER_MINUTE, daily_budget: int = DEFAULT_DAILY_BUDGET,
                 clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep,
                 utc_today: Callable[[], _dt.date] = _utc_today):
        self.per_minute = per_minute
        self.daily_budget = daily_budget
        self._clock = clock
        self._sleep = sleep
        self._utc_today = utc_today
        self._window: deque[float] = deque()
        self._day: _dt.date | None = None
        self.daily_count = 0

    def _expire(self, now: float) -> None:
        while self._window and now - self._window[0] >= self.WINDOW_SECONDS:
            self._window.popleft()

    def acquire(self) -> None:
        today = self._utc_today()
        if today != self._day:
            self._day = today
            self.daily_count = 0
        if self.daily_count >= self.daily_budget:
            raise DailyBudgetExhausted(
                f"daily request budget of {self.daily_budget} exhausted for {today.isoformat()} (UTC)"
            )
        now = self._clock()
        self._expire(now)
        if len(self._window) >= self.per_minute:
            wait = self.WINDOW_SECONDS - (now - self._window[0])
            if wait > 0:
                self._sleep(wait)
            now = self._clock()
            self._expire(now)
            while len(self._window) >= self.per_minute:
                self._window.popleft()
        self._window.append(now)
        self.daily_count += 1


class BaseCollector:
    """Rate-limited, retrying JSON GETs over an injectable transport."""

    VOLUME_BASIS = "raw"

    def __init__(self, transport=None, rate_limiter: RateLimiter | None = None,
                 max_retries: int = DEFAULT_MAX_RETRIES, backoff: float = DEFAULT_BACKOFF,
                 sleep: Callable[[float], None] = time.sleep):
        self.transport = transport if transport is not None else HttpTransport()
        self.rate_limiter = rate_limiter if rate_limiter is not None else RateLimiter()
        self.max_retries = max_retries
        self.backoff = backoff
        self._sleep = sleep
        self._secrets: list[str] = []

    def _redact(self, text: str) -> str:
        return redact(text, self._secrets)

    def get_json(self, url: str, params: dict | None = None) -> Any:
        params = dict(params or {})
        path = urlsplit(url).path or url
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            self.rate_limiter.acquire()
            try:
                resp = self.transport.request("GET", url, params)
            except TransportConnectionError as exc:
                if attempt + 1 >= attempts:
                    raise CollectorError(self._redact(
                        f"GET {path}: network failure after {attempts} attempt(s): {exc}"
                    )) from None
                self._sleep(self.backoff * (2 ** attempt))
                continue
            if resp.status == 200:
                try:
                    return resp.json()
                except ValueError:
                    body = self._redact(resp.text or "")[:ERROR_BODY_CHARS]
                    raise CollectorError(f"GET {path}: invalid JSON in response: {body}") from None
            if resp.status == 429 or 500 <= resp.status <= 599:
                if attempt + 1 >= attempts:
                    raise CollectorError(f"GET {path}: HTTP {resp.status} after {attempts} attempt(s)")
                self._sleep(self.backoff * (2 ** attempt))
                continue
            body = self._redact(resp.text or "")[:ERROR_BODY_CHARS]
            raise CollectorError(f"GET {path}: HTTP {resp.status}: {body}")
        raise CollectorError(f"GET {path}: no attempt made")

    def paginate(self, fetch_page: Callable[[Any], tuple[list, Any]], cursor: Any,
                 max_pages: int = DEFAULT_MAX_PAGES) -> list:
        """Accumulate ascending pages until the callback returns a None cursor."""
        rows: list = []
        for _ in range(max_pages):
            page, cursor = fetch_page(cursor)
            rows.extend(page)
            if cursor is None:
                return rows
        raise CollectorError(f"pagination exceeded {max_pages} pages; refusing to return truncated history")

    def close(self) -> None:
        close = getattr(self.transport, "close", None)
        if close is not None:
            close()

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        self.close()

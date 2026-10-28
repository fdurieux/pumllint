"""Provider-neutral HTTP plumbing shared by every collector.

A transport is anything with ``request(method, url, params) ->
TransportResponse``. ``BaseCollector`` - not the transport - owns the rate
budget and the retry loop, so the same policy wraps the live
``HttpTransport``, a fixture-backed ``ReplayTransport`` and a
``RecordingTransport``.

Secrets: ``SECRET_PARAMS`` names request parameters that never enter a
fixture identity; values a collector registers in ``_secrets`` are redacted
from every error it raises.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

SECRET_PARAMS = frozenset({"api_token"})
REDACTED = "***"
BODY_EXCERPT = 200


class CollectorError(RuntimeError):
    """A provider request failed terminally or returned an unusable body."""


class DailyBudgetExhausted(CollectorError):
    """The collector's hard UTC-day request budget is spent."""


class TransportConnectionError(Exception):
    """A retryable network-level failure (connection error or timeout)."""


@dataclass
class TransportResponse:
    status: int
    text: str

    def json(self):
        return json.loads(self.text)


def public_params(params) -> dict:
    return {k: v for k, v in dict(params or {}).items() if k not in SECRET_PARAMS}


def request_key(method: str, url: str, params) -> tuple:
    """Public request identity: method, URL path, sorted public params."""
    path = urlparse(url).path if "://" in str(url) else str(url)
    items = tuple(sorted((str(k), str(v)) for k, v in public_params(params).items()))
    return (str(method).upper(), path, items)


def _key_json(key: tuple) -> dict:
    method, path, items = key
    return {"method": method, "path": path, "params": {k: v for k, v in items}}


def _key_from_fixture(request) -> tuple:
    """Accept the recorded identity as a dict, a [method, path, params]
    triple, or a ``"METHOD path?query"`` string."""
    if isinstance(request, dict):
        method = request.get("method", "GET")
        path = request.get("path")
        if path is None:
            path = request.get("url", "")
        params = request.get("params", {})
    elif isinstance(request, (list, tuple)) and len(request) == 3:
        method, path, params = request
    elif isinstance(request, str):
        method, _, rest = request.strip().partition(" ")
        path, _, query = rest.partition("?")
        params = {}
        for pair in filter(None, query.split("&")):
            k, _, v = pair.partition("=")
            params[k] = v
    else:
        raise CollectorError(f"unrecognised fixture request identity: {request!r}")
    if isinstance(params, (list, tuple)):
        params = {str(k): v for k, v in params}
    return request_key(method, path, params)


def _fixture_slug(path: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", path).strip("_")
    return slug or "root"


class HttpTransport:
    """The live transport; ``requests`` is imported only on construction."""

    def __init__(self, timeout: float = 30.0, secret_params=SECRET_PARAMS):
        import requests

        self._requests = requests
        self._session = requests.Session()
        self.timeout = timeout
        self.secret_params = frozenset(secret_params)

    def _redact(self, text: str, params) -> str:
        for name in self.secret_params:
            value = (params or {}).get(name)
            if value:
                text = text.replace(str(value), REDACTED)
        return text

    def request(self, method: str, url: str, params=None) -> TransportResponse:
        try:
            resp = self._session.request(
                method, url, params=params, timeout=self.timeout
            )
        except (
            self._requests.exceptions.ConnectionError,
            self._requests.exceptions.Timeout,
        ) as exc:
            raise TransportConnectionError(self._redact(str(exc), params)) from None
        return TransportResponse(status=resp.status_code, text=resp.text)

    def close(self) -> None:
        self._session.close()


class ReplayTransport:
    """Serve recorded fixtures by public request identity; never the network."""

    def __init__(self, fixture_dir):
        self.fixture_dir = Path(fixture_dir)
        self.calls: list[tuple] = []
        self._fixtures: dict[tuple, dict] = {}
        for path in sorted(self.fixture_dir.rglob("*.json")):
            if path.name == "manifest.json":
                continue
            with open(path, encoding="utf-8") as handle:
                doc = json.load(handle)
            if not isinstance(doc, dict) or "request" not in doc or "response" not in doc:
                continue
            self._fixtures[_key_from_fixture(doc["request"])] = doc["response"]

    def request(self, method: str, url: str, params=None) -> TransportResponse:
        key = request_key(method, url, params)
        self.calls.append(key)
        response = self._fixtures.get(key)
        if response is None:
            known = "; ".join(
                f"{m} {p} {dict(items)}" for m, p, items in sorted(self._fixtures)
            ) or "none"
            raise CollectorError(
                f"no recorded fixture for {key[0]} {key[1]} {dict(key[2])} "
                f"(known: {known})"
            )
        status = int(response.get("status", 200))
        if "json" in response:
            text = json.dumps(response["json"])
        elif "body" in response:
            body = response["body"]
            text = body if isinstance(body, str) else json.dumps(body)
        elif "text" in response:
            text = str(response["text"])
        else:
            text = json.dumps(response.get("data"))
        return TransportResponse(status=status, text=text)

    def close(self) -> None:
        pass


class RecordingTransport:
    """Forward to ``inner`` and write ``{request, response}`` fixtures.

    Refuses to write a fixture whose serialization contains any non-empty
    value passed in ``secrets``.
    """

    def __init__(self, inner, fixture_dir, secrets=()):
        self.inner = inner
        self.fixture_dir = Path(fixture_dir)
        self.secrets = tuple(s for s in secrets if s)

    def request(self, method: str, url: str, params=None) -> TransportResponse:
        response = self.inner.request(method, url, params)
        key = request_key(method, url, params)
        document = {
            "request": _key_json(key),
            "response": {"status": response.status, "json": response.json()},
        }
        text = json.dumps(document, indent=2, sort_keys=True)
        for secret in self.secrets:
            if secret in text:
                raise CollectorError(
                    "refusing to record a fixture that contains a supplied secret"
                )
        digest = hashlib.sha256(
            json.dumps(_key_json(key), sort_keys=True).encode("utf-8")
        ).hexdigest()[:12]
        self.fixture_dir.mkdir(parents=True, exist_ok=True)
        target = self.fixture_dir / f"{_fixture_slug(key[1])}-{digest}.json"
        target.write_text(text + "\n", encoding="utf-8")
        return response

    def close(self) -> None:
        close = getattr(self.inner, "close", None)
        if close is not None:
            close()


def _utc_today():
    return datetime.now(timezone.utc).date()


class RateLimiter:
    """A sliding 60-second window plus a hard budget for the current UTC date."""

    WINDOW_SECONDS = 60.0

    def __init__(
        self,
        per_minute: int = 1000,
        daily_budget: int = 100_000,
        *,
        clock=time.monotonic,
        sleep=time.sleep,
        utc_today=_utc_today,
    ):
        self.per_minute = int(per_minute)
        self.daily_budget = int(daily_budget)
        self._clock = clock
        self._sleep = sleep
        self._utc_today = utc_today
        self._window: deque[float] = deque()
        self._day = None
        self.daily_count = 0

    def acquire(self) -> None:
        today = self._utc_today()
        if today != self._day:
            self._day = today
            self.daily_count = 0
        if self.daily_count >= self.daily_budget:
            raise DailyBudgetExhausted(
                f"daily request budget of {self.daily_budget} exhausted for {today}"
            )
        now = self._clock()
        while self._window and now - self._window[0] >= self.WINDOW_SECONDS:
            self._window.popleft()
        if len(self._window) >= self.per_minute:
            wait = self.WINDOW_SECONDS - (now - self._window[0])
            if wait > 0:
                self._sleep(wait)
            now = self._clock()
            while self._window and now - self._window[0] >= self.WINDOW_SECONDS:
                self._window.popleft()
            while len(self._window) >= self.per_minute:
                self._window.popleft()
        self._window.append(now)
        self.daily_count += 1


class BaseCollector:
    """Rate limiting, retries with exponential backoff, redaction, paging."""

    VOLUME_BASIS = "raw"
    page_limit: int | None = None

    def __init__(
        self,
        *,
        transport=None,
        rate_limiter: RateLimiter | None = None,
        max_retries: int = 4,
        backoff: float = 2.0,
        sleep=time.sleep,
    ):
        self.transport = transport if transport is not None else HttpTransport()
        self.rate_limiter = rate_limiter if rate_limiter is not None else RateLimiter()
        self.max_retries = int(max_retries)
        self.backoff = float(backoff)
        self._sleep = sleep
        if not hasattr(self, "_secrets"):
            self._secrets: list[str] = []

    def _redact(self, text: str) -> str:
        for secret in self._secrets:
            if secret:
                text = text.replace(secret, REDACTED)
        return text

    def get_json(self, url: str, params=None):
        params = dict(params or {})
        path = urlparse(url).path
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            self.rate_limiter.acquire()
            last = attempt == attempts - 1
            try:
                response = self.transport.request("GET", url, params)
            except TransportConnectionError as exc:
                if last:
                    raise CollectorError(
                        self._redact(
                            f"GET {path}: network failure after {attempts} "
                            f"attempt(s): {exc}"
                        )
                    ) from None
                self._sleep(self.backoff * (2 ** attempt))
                continue
            status = response.status
            if status == 429 or 500 <= status <= 599:
                if last:
                    raise CollectorError(
                        f"GET {path}: HTTP {status} after {attempts} attempt(s)"
                    )
                self._sleep(self.backoff * (2 ** attempt))
                continue
            if status != 200:
                body = self._redact(response.text or "")[:BODY_EXCERPT]
                raise CollectorError(self._redact(f"GET {path}: HTTP {status}: {body}"))
            try:
                return response.json()
            except ValueError as exc:
                raise CollectorError(
                    self._redact(f"GET {path}: invalid JSON: {exc}")
                ) from None
        raise CollectorError(f"GET {path}: no attempt made")

    def paginate(self, fetch_page, cursor, max_pages: int = 100) -> list:
        rows: list = []
        for _ in range(max_pages):
            page, cursor = fetch_page(cursor)
            rows.extend(page)
            if cursor is None:
                return rows
        raise CollectorError(
            f"pagination exceeded {max_pages} pages without reaching the end"
        )

    def close(self) -> None:
        close = getattr(self.transport, "close", None)
        if close is not None:
            close()

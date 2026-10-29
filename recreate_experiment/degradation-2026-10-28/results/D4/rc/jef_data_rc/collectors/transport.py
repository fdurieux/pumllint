"""HTTP transports under the collectors: live, replayed and recording."""
from __future__ import annotations

import hashlib
import json
import os
from urllib.parse import urlparse


class TransportConnectionError(RuntimeError):
    """A connection error or timeout of the live transport (retryable)."""


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


def fixture_key(method: str, url: str, params) -> dict:
    items = {} if params is None else dict(params)
    return {"method": method.upper(), "path": urlparse(url).path,
            "params": {name: str(items[name]) for name in sorted(items) if name != "api_token"}}


def key_text(key: dict) -> str:
    return json.dumps(key, sort_keys=True)


def fixture_name(key: dict) -> str:
    slug = key["path"].strip("/").replace("/", "_")
    digest = hashlib.sha256(key_text(key).encode("utf-8")).hexdigest()[:10]
    return f"{slug}_{digest}.json"


class HttpTransport:
    timeout = 30.0

    def __init__(self, secrets=(), timeout: float | None = None):
        import requests

        self._requests = requests
        self.session = requests.Session()
        self.secrets = tuple(secrets)
        if timeout is not None:
            self.timeout = timeout

    def request(self, method, url, params) -> TransportResponse:
        try:
            resp = self.session.request(method, url, params=params, timeout=self.timeout)
        except (self._requests.ConnectionError, self._requests.Timeout) as exc:
            raise TransportConnectionError(redact(str(exc), self.secrets)) from None
        return TransportResponse(resp.status_code, resp.text)

    def close(self) -> None:
        self.session.close()


class ReplayTransport:
    """Answers requests from recorded-fixture files, never from the network."""

    def __init__(self, fixture_dir):
        self.fixture_dir = str(fixture_dir)
        self.calls: list = []
        self._answers: dict = {}
        self._keys: dict = {}
        for root, _dirs, files in os.walk(self.fixture_dir):
            for name in sorted(files):
                if not name.endswith(".json") or name == "manifest.json":
                    continue
                with open(os.path.join(root, name), encoding="utf-8") as handle:
                    doc = json.load(handle)
                key = doc["request"]
                text = key_text(key)
                self._answers[text] = (int(doc["response"]["status"]), doc["response"].get("json"))
                self._keys[text] = key

    def request(self, method, url, params) -> TransportResponse:
        from .base import CollectorError

        key = fixture_key(method, url, params)
        self.calls.append(key)
        text = key_text(key)
        if text not in self._answers:
            known = sorted(f"  {k['path']} {k['params']!r}" for k in self._keys.values())
            raise CollectorError(
                f"no recorded fixture for {key['method']} {key['path']} {key['params']!r}\n"
                "known fixtures:\n" + "\n".join(known))
        status, body = self._answers[text]
        return TransportResponse(status, json.dumps(body))

    def close(self) -> None:
        pass


class RecordingTransport:
    """Wraps another transport and writes one fixture file per request."""

    def __init__(self, inner, fixture_dir, secrets=()):
        self.inner = inner
        self.fixture_dir = str(fixture_dir)
        self.secrets = tuple(s for s in secrets if s)
        self.written: list = []

    def request(self, method, url, params) -> TransportResponse:
        from .base import CollectorError

        resp = self.inner.request(method, url, params)
        key = fixture_key(method, url, params)
        try:
            body = json.loads(resp.text)
        except ValueError:
            body = resp.text
        doc = {"request": key, "response": {"status": int(resp.status), "json": body}}
        text = json.dumps(doc, indent=1, sort_keys=True) + "\n"
        path = os.path.join(self.fixture_dir, fixture_name(key))
        if any(secret in text for secret in self.secrets):
            raise CollectorError(f"refusing to write fixture: secret material in {path} response/request")
        os.makedirs(self.fixture_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        self.written.append(path)
        return resp

    def close(self) -> None:
        self.inner.close()

"""HTTP transports under the collectors: live, replayed and recording."""
import hashlib
import json
import os
from urllib.parse import urlparse

LIVE_TIMEOUT = 30.0


class TransportConnectionError(RuntimeError):
    """A connection failure or timeout; retryable."""


class TransportResponse:
    def __init__(self, status, text):
        self.status = int(status)
        self.text = text

    def json(self):
        return json.loads(self.text)

    def __iter__(self):
        return iter((self.status, self.text))

    def __repr__(self):
        return f"TransportResponse(status={self.status!r}, text={self.text[:40]!r})"


def redact(text, secrets):
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


def request_key(method, url, params):
    """The recorded-fixture identity of a request."""
    items = {k: str(v) for k, v in (params or {}).items() if k != "api_token"}
    return {"method": method.upper(), "path": urlparse(url).path,
            "params": {k: items[k] for k in sorted(items)}}


def key_text(key):
    return json.dumps(key, sort_keys=True)


def fixture_name(key):
    slug = key["path"].strip("/").replace("/", "_")
    digest = hashlib.sha256(key_text(key).encode("utf-8")).hexdigest()[:10]
    return f"{slug}_{digest}.json"


class HttpTransport:
    """Live HTTP through a requests session."""

    def __init__(self, timeout=LIVE_TIMEOUT, secrets=()):
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
                text = key_text(key)
                self._answers[text] = doc["response"]
                self._keys[text] = key

    def request(self, method, url, params):
        key = request_key(method, url, params)
        self.calls.append(key)
        text = key_text(key)
        if text not in self._answers:
            known = sorted(f"{k['path']} {k['params']}" for k in self._keys.values())
            lines = [f"no recorded fixture for {key['method']} {key['path']} {key['params']}",
                     "known fixtures:"] + [f"  {line}" for line in known]
            from .base import CollectorError

            raise CollectorError("\n".join(lines))
        answer = self._answers[text]
        return TransportResponse(answer["status"], json.dumps(answer["json"]))

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
        key = request_key(method, url, params)
        try:
            body = json.loads(response.text)
        except ValueError:
            body = response.text
        doc = {"request": key, "response": {"status": int(response.status), "json": body}}
        text = json.dumps(doc, indent=1, sort_keys=True) + "\n"
        path = os.path.join(self.fixture_dir, fixture_name(key))
        if any(secret in text for secret in self.secrets):
            from .base import CollectorError

            raise CollectorError(f"refusing to write fixture: secret material in {path} response/request")
        os.makedirs(self.fixture_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        self.written.append(path)
        return response

    def close(self):
        self.inner.close()

"""Transports under the collectors: live HTTP, fixture replay, fixture recording."""
import hashlib
import json
import os
from urllib.parse import urlparse

from .base import CollectorError, TransportConnectionError


class TransportResponse:
    """An HTTP answer: status code and body text."""

    def __init__(self, status, text):
        self.status = int(status)
        self.text = text

    def json(self):
        return json.loads(self.text)


def fixture_key(method, url, params):
    """The recorded-fixture identity of a request (the api_token never enters it)."""
    clean = {name: str(value) for name, value in (params or {}).items() if name != "api_token"}
    return {"method": method.upper(), "path": urlparse(url).path,
            "params": dict(sorted(clean.items()))}


def key_text(key):
    return json.dumps(key, sort_keys=True)


def fixture_name(key):
    slug = key["path"].strip("/").replace("/", "_")
    digest = hashlib.sha256(key_text(key).encode("utf-8")).hexdigest()[:10]
    return f"{slug}_{digest}.json"


class HttpTransport:
    """Live traffic through a requests session."""

    def __init__(self, timeout=30.0, secrets=()):
        import requests

        self._requests = requests
        self.timeout = timeout
        self._secrets = [s for s in secrets if s]
        self._session = requests.Session()

    def _redact(self, text):
        for secret in self._secrets:
            text = text.replace(secret, "***")
        return text

    def request(self, method, url, params):
        try:
            response = self._session.request(method, url, params=params, timeout=self.timeout)
        except (self._requests.ConnectionError, self._requests.Timeout) as exc:
            raise TransportConnectionError(self._redact(f"{type(exc).__name__}: {exc}")) from None
        return TransportResponse(response.status_code, response.text)

    def close(self):
        self._session.close()


class ReplayTransport:
    """Answers requests from recorded-fixture files; never reaches the network."""

    def __init__(self, fixture_dir):
        self.fixture_dir = str(fixture_dir)
        self.calls = []
        self._fixtures = {}
        for directory, subdirs, files in os.walk(self.fixture_dir):
            subdirs.sort()
            for name in sorted(files):
                if not name.endswith(".json") or name == "manifest.json":
                    continue
                with open(os.path.join(directory, name), encoding="utf-8") as handle:
                    doc = json.load(handle)
                request = doc["request"]
                key = {"method": str(request["method"]).upper(), "path": request["path"],
                       "params": {k: str(v) for k, v in sorted(request.get("params", {}).items())}}
                self._fixtures[key_text(key)] = (key, doc["response"])

    def request(self, method, url, params):
        key = fixture_key(method, url, params)
        self.calls.append(key)
        found = self._fixtures.get(key_text(key))
        if found is None:
            known = sorted(f"  {k['path']} {k['params']}" for k, _ in self._fixtures.values())
            raise CollectorError("\n".join(
                [f"no recorded fixture for {key['method']} {key['path']} {key['params']}",
                 "known fixtures:"] + known))
        response = found[1]
        return TransportResponse(response["status"], json.dumps(response["json"]))

    def close(self):
        pass


class RecordingTransport:
    """Wraps a transport and writes every exchange as a recorded fixture."""

    def __init__(self, inner, fixture_dir, secrets=()):
        self.inner = inner
        self.fixture_dir = str(fixture_dir)
        self.written = []
        self._secrets = [s for s in secrets if s]

    def request(self, method, url, params):
        response = self.inner.request(method, url, params)
        key = fixture_key(method, url, params)
        try:
            body = json.loads(response.text)
        except ValueError:
            body = response.text
        doc = {"request": key, "response": {"status": response.status, "json": body}}
        text = json.dumps(doc, indent=1, sort_keys=True) + "\n"
        path = os.path.join(self.fixture_dir, fixture_name(key))
        if any(secret in text for secret in self._secrets):
            raise CollectorError(
                f"refusing to write fixture: secret material in {path} response/request")
        os.makedirs(self.fixture_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        self.written.append(path)
        return response

    def close(self):
        self.inner.close()

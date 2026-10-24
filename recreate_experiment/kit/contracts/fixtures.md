# Recorded-fixture files (what the replaying collectors read)

Requirements: JDL-024, JDL-025, JDL-026. The
harness's `make_collector(provider, fixture_dir)` must return a collector whose
HTTP layer replays these files (and the recorder, if you build one, must write
them).

## 1. Request identity (the key)

For a request `GET <url>` with parameters `params`:

```json
{"method": "GET", "path": "<urlparse(url).path>", "params": {"<name>": "<str(value)>", ...}}
```

* `method` upper-cased.
* `path` is only the URL's path component: `https://eodhd.com/api/eod/SPLT.US`
  → `/api/eod/SPLT.US`; `https://api.binance.com/api/v3/klines` →
  `/api/v3/klines`. Scheme, host and query string are not part of the key.
* `params`: every request parameter except `api_token`, each value converted
  with Python `str()` (so `1000` → `"1000"`, `1704067200000` →
  `"1704067200000"`), keys sorted.
* Two keys are equal when `json.dumps(key, sort_keys=True)` is equal.

Examples (the exact keys the scenarios replay):

```json
{"method": "GET", "path": "/api/eod/SPLT.US", "params": {"fmt": "json", "from": "2024-01-02", "order": "a", "period": "d"}}
{"method": "GET", "path": "/api/eod/ZERO-USD.CC", "params": {"fmt": "json", "from": "2024-01-01", "order": "a", "period": "d", "to": "2024-02-09"}}
{"method": "GET", "path": "/api/splits/SPLT.US", "params": {"fmt": "json"}}
{"method": "GET", "path": "/api/div/SPLT.US", "params": {"fmt": "json"}}
{"method": "GET", "path": "/api/v3/klines", "params": {"endTime": "1705795199999", "interval": "1d", "limit": "1000", "startTime": "1704067200000", "symbol": "PAIRUSDT"}}
```

## 2. File name

```
{slug}_{digest}.json
slug   = key.path stripped of leading/trailing "/", inner "/" replaced by "_"
digest = sha256(json.dumps(key, sort_keys=True).encode("utf-8")).hexdigest()[:10]
```

`json.dumps` here is Python's default (separators `", "` and `": "`,
`ensure_ascii=True`). Example: the first key above →
`api_eod_SPLT.US_34fa88fe69.json`. The replayer does not rely on the file
name (it keys on content), but a recorder must produce it.

## 3. File content

```json
{
 "request": {"method": "GET", "params": {...}, "path": "/api/eod/SPLT.US"},
 "response": {"json": <the response body as JSON>, "status": 200}
}
```

Written as `json.dumps(fixture, indent=1, sort_keys=True) + "\n"` (UTF-8). The
`json` member is the parsed response body (a list for `/eod/`, `/splits/`,
`/div/`, `/klines`; any JSON value for an error body such as
`{"error": "Ticker Not Found."}`). `status` is the HTTP status integer.

A recorder must refuse to write a fixture whose serialised text contains a
secret (the API token):
`refusing to write fixture: secret material in {path} response/request`.

## 4. Replay

* Load every file whose name ends in `.json` under the fixture directory,
  recursively (`os.walk` order; inside one directory, files in sorted name
  order), except files named `manifest.json`. A later file with an equal key
  replaces an earlier one.
* A request whose key matches answers `(status, json.dumps(response.json))`;
  the collector then applies its normal status handling (retries for 429/5xx
  — every retry gets the same recorded answer — errors for other non-200).
* A request with no matching key raises CollectorError:

```
no recorded fixture for GET /api/eod/X.US {'fmt': 'json', 'order': 'a', 'period': 'd'}
known fixtures:
  /api/div/SPLT.US {'fmt': 'json'}
  /api/eod/SPLT.US {'fmt': 'json', 'from': '2024-01-02', 'order': 'a', 'period': 'd'}
```

(params rendered as a Python dict; known keys sorted by that rendering). Inside
a sync this fails the leg (`CollectorError: no recorded fixture for …`).

## 5. The harness collector

`make_collector(provider, fixture_dir, api_key)` builds the normal collector
for `provider` (`eodhd` with the given api_key; `binance` keyless) on top of the
replayer, with the rate limiter disabled and backoff sleeps suppressed (so a
503 fixture is retried 5 times instantly). Everything else — parameters,
pagination, parsing, dedupe, retries, errors — is the collector's normal
behaviour (collectors.md).

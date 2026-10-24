"""Recorded-fixture files as the subject's replay transport reads them:
request key -> file name, and writers for the EODHD endpoints."""
import hashlib
import json
import os


def key_of(method, path, params):
    return {"method": method, "path": path,
            "params": {k: str(v) for k, v in sorted(params.items())}}


def filename(key):
    slug = key["path"].strip("/").replace("/", "_")
    digest = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:10]
    return f"{slug}_{digest}.json"


def write_fixture(dirname, path, params, body, status=200):
    key = key_of("GET", path, params)
    os.makedirs(dirname, exist_ok=True)
    with open(os.path.join(dirname, filename(key)), "w", encoding="utf-8") as f:
        json.dump({"request": key, "response": {"json": body, "status": status}}, f, indent=1, sort_keys=True)
        f.write("\n")


def eod_params(start=None, end=None):
    p = {"fmt": "json", "order": "a", "period": "d"}
    if start:
        p["from"] = str(start)
    if end:
        p["to"] = str(end)
    return p


def write_eodhd_set(dirname, symbol, bars, splits, dividends, start, end):
    """One EODHD fixture set: bars for the window, windowless splits and dividends."""
    write_fixture(os.path.join(dirname, "eodhd"), f"/api/eod/{symbol}", eod_params(start, end), bars)
    write_fixture(os.path.join(dirname, "eodhd"), f"/api/splits/{symbol}", {"fmt": "json"}, splits)
    write_fixture(os.path.join(dirname, "eodhd"), f"/api/div/{symbol}", {"fmt": "json"}, dividends)

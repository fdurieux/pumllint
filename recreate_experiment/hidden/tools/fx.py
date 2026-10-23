"""Fixture-writing helpers for the kit's synthetic recorded traffic.

Written from the kit's own fixtures contract (kit/contracts/fixtures.md):
request key = method + URL path + public params as strings, sorted;
file name = <path slug>_<first 10 hex of sha256(json.dumps(key, sort_keys))>.json.
"""
import hashlib
import json
import os
from datetime import date, datetime, timedelta, timezone

EODHD = "/api"
DAY_MS = 86_400_000


def key(path, params):
    return {"method": "GET", "path": path,
            "params": {k: str(v) for k, v in sorted(params.items())}}


def filename(k):
    slug = k["path"].strip("/").replace("/", "_")
    digest = hashlib.sha256(json.dumps(k, sort_keys=True).encode()).hexdigest()[:10]
    return f"{slug}_{digest}.json"


def write(directory, path, params, body, status=200):
    k = key(path, params)
    os.makedirs(directory, exist_ok=True)
    doc = {"request": k, "response": {"status": status, "json": body}}
    target = os.path.join(directory, filename(k))
    with open(target, "w", encoding="utf-8") as f:
        f.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    return target


def eod(directory, sym, rows, start=None, end=None, status=200):
    params = {"fmt": "json", "period": "d", "order": "a"}
    if start:
        params["from"] = start
    if end:
        params["to"] = end
    return write(directory, f"{EODHD}/eod/{sym}", params, rows, status)


def splits(directory, sym, rows, status=200):
    return write(directory, f"{EODHD}/splits/{sym}", {"fmt": "json"}, rows, status)


def divs(directory, sym, rows, status=200):
    return write(directory, f"{EODHD}/div/{sym}", {"fmt": "json"}, rows, status)


def ms(d):
    return int(datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc).timestamp() * 1000)


def klines(directory, sym, rows, start_ms=None, end_ms=None, limit=1000, status=200):
    params = {"symbol": sym, "interval": "1d", "limit": limit}
    if start_ms is not None:
        params["startTime"] = start_ms
    if end_ms is not None:
        params["endTime"] = end_ms
    return write(directory, "/api/v3/klines", params, rows, status)


def weekdays(first, last):
    out, d = [], first
    while d <= last:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def days(first, last):
    out, d = [], first
    while d <= last:
        out.append(d)
        d += timedelta(days=1)
    return out

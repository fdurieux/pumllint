"""Vendor-classification evidence and the declared-class verdict."""
from __future__ import annotations

import datetime as _dt
import re
import tomllib
from importlib import resources

ORIGIN = "packaged classifications.toml"
TOP_KEYS = ["instrument", "provenance", "schema"]
REQUIRED = ["exchange", "symbol", "code", "query_exchange", "vendor_type"]
OPTIONAL = ["isin", "name"]
INSTRUMENT_KEYS = sorted(REQUIRED + OPTIONAL + ["last_verified"])
VENDOR_TYPE_MAP = {"Common Stock": "stock", "ETF": "etf"}
NOT_COMPARABLE = "Currency"

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ClassificationError(ValueError):
    """A classifications file that violates its grammar."""


def parse_classifications(text, origin=ORIGIN):
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ClassificationError(f"{origin}: not valid TOML: {exc}") from None
    unknown = sorted(k for k in doc if k not in TOP_KEYS)
    if unknown:
        raise ClassificationError(
            f"{origin}: unknown key(s) {unknown}; allowed: {TOP_KEYS}")
    if doc.get("schema") != 1 or isinstance(doc.get("schema"), bool):
        raise ClassificationError(f"{origin}: schema must be 1, got {doc.get('schema')!r}")
    instruments = doc.get("instrument", [])
    if not isinstance(instruments, list):
        raise ClassificationError(f"{origin}: [[instrument]] must be a list")
    rows = {}
    for n, entry in enumerate(instruments, start=1):
        where = f"instrument #{n}"
        if not isinstance(entry, dict):
            raise ClassificationError(f"{where}: must be a table")
        unknown = sorted(k for k in entry if k not in INSTRUMENT_KEYS)
        if unknown:
            raise ClassificationError(
                f"{where}: unknown key(s) {unknown}; allowed: {INSTRUMENT_KEYS}")
        if "symbol" in entry and isinstance(entry["symbol"], str) and entry["symbol"]:
            where = f"instrument '{entry['symbol']}'"
        row = {}
        for key in REQUIRED:
            if key not in entry:
                raise ClassificationError(f"{where}: missing required key '{key}'")
            value = entry[key]
            if not isinstance(value, str):
                raise ClassificationError(f"{where}: {key} must be a string, got {value!r}")
            if value == "":
                raise ClassificationError(f"{where}: {key} must be non-empty")
            row[key] = value
        for key in OPTIONAL:
            value = entry.get(key, "")
            if not isinstance(value, str):
                raise ClassificationError(f"{where}: {key} must be a string, got {value!r}")
            row[key] = value
        verified = entry.get("last_verified")
        if verified is not None:
            if isinstance(verified, _dt.date) and not isinstance(verified, _dt.datetime):
                verified = verified.isoformat()
            elif not (isinstance(verified, str) and _DATE_RE.match(verified)):
                raise ClassificationError(
                    f"{where}: last_verified must be YYYY-MM-DD, got {verified!r}")
        row["last_verified"] = verified
        key = (row["exchange"], row["symbol"])
        if key in rows:
            raise ClassificationError(
                f"{origin}: duplicate entry for {row['exchange']}/{row['symbol']}")
        rows[key] = row
    return rows


_CACHE = {}


def packaged_evidence():
    if "rows" not in _CACHE:
        text = resources.files(__package__).joinpath("classifications.toml").read_text(
            encoding="utf-8")
        _CACHE["rows"] = parse_classifications(text)
    return _CACHE["rows"]


def compare(exchange, symbol, asset_type, evidence=None):
    """Return (verdict, message) for a declared store asset_type."""
    rows = packaged_evidence() if evidence is None else evidence
    row = rows.get((exchange, symbol))
    if row is None:
        return "no_evidence", ("no vendor classification recorded - run "
                               "tools/record_classifications.py")
    vendor_type = row["vendor_type"]
    seen = f", recorded {row['last_verified']}" if row.get("last_verified") else ""
    if vendor_type == NOT_COMPARABLE:
        return "not_comparable", (
            f"vendor type {vendor_type!r} cannot confirm asset_type {asset_type!r}{seen}: the "
            f".CC (crypto) and .FOREX namespaces both serve it, so only the symbol's own "
            f"namespace separates them and the evidence is not independent")
    if vendor_type not in VENDOR_TYPE_MAP:
        return "unmapped", (
            f"vendor type {vendor_type!r} has no store asset_type counterpart{seen} - no "
            f"verdict rather than a guess (mapped: {sorted(VENDOR_TYPE_MAP)})")
    mapped = VENDOR_TYPE_MAP[vendor_type]
    if mapped == asset_type:
        return "agree", (
            f"vendor type {vendor_type!r} agrees with declared asset_type {asset_type!r}{seen}")
    return "disagree", (
        f"declared asset_type {asset_type!r} but the vendor says {vendor_type!r} "
        f"(-> {mapped!r}){seen} for {exchange}/{symbol} - check the asset_class in "
        f"universe.toml against docs/EVALUATION_ASSET_CLASSIFICATION.md §5 C2")

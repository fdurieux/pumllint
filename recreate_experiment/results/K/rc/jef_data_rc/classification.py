"""Vendor-classification evidence and the declared-class verdict."""
from __future__ import annotations

import datetime as _dt
import tomllib
from importlib import resources

PACKAGED_ORIGIN = "packaged classifications.toml"

VENDOR_TYPE_TO_ASSET_TYPE = {"Common Stock": "stock", "ETF": "etf"}
NOT_COMPARABLE_TYPES = ("Currency",)

TOP_KEYS = ["instrument", "provenance", "schema"]
INSTRUMENT_KEYS = ["code", "exchange", "isin", "last_verified", "name",
                   "query_exchange", "symbol", "vendor_type"]
REQUIRED_KEYS = ["exchange", "symbol", "code", "query_exchange", "vendor_type"]
OPTIONAL_KEYS = ["isin", "name"]


class ClassificationError(ValueError):
    """A classifications document that violates its grammar."""


def _string(where, row, key, required):
    if key not in row:
        if required:
            raise ClassificationError(f"{where}: missing required key '{key}'")
        return ""
    value = row[key]
    if not isinstance(value, str):
        raise ClassificationError(f"{where}: {key} must be a string, got {value!r}")
    if required and not value:
        raise ClassificationError(f"{where}: {key} must be non-empty")
    return value


def parse_classifications(text, origin=PACKAGED_ORIGIN):
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ClassificationError(f"{origin}: not valid TOML: {exc}") from None
    unknown = sorted(k for k in doc if k not in TOP_KEYS)
    if unknown:
        raise ClassificationError(
            f"{origin}: unknown key(s) {unknown}; allowed: {TOP_KEYS}")
    schema = doc.get("schema")
    if schema != 1 or isinstance(schema, bool):
        raise ClassificationError(f"{origin}: schema must be 1, got {schema!r}")
    rows = doc.get("instrument", [])
    if not isinstance(rows, list):
        raise ClassificationError(f"{origin}: [[instrument]] must be a list")
    table = {}
    for n, row in enumerate(rows, start=1):
        where = f"instrument #{n}"
        if not isinstance(row, dict):
            raise ClassificationError(f"{where}: must be a table")
        unknown = sorted(k for k in row if k not in INSTRUMENT_KEYS)
        if unknown:
            raise ClassificationError(
                f"{where}: unknown key(s) {unknown}; allowed: {INSTRUMENT_KEYS}")
        entry = {}
        for key in REQUIRED_KEYS:
            entry[key] = _string(where, row, key, required=True)
            if key == "symbol":
                where = f"instrument '{entry['symbol']}'"
        for key in OPTIONAL_KEYS:
            entry[key] = _string(where, row, key, required=False)
        verified = row.get("last_verified")
        if verified is None:
            entry["last_verified"] = None
        elif isinstance(verified, _dt.date) and not isinstance(verified, _dt.datetime):
            entry["last_verified"] = verified.isoformat()
        elif isinstance(verified, str):
            try:
                parsed = _dt.date.fromisoformat(verified)
            except ValueError:
                parsed = None
            if parsed is None or parsed.isoformat() != verified:
                raise ClassificationError(
                    f"{where}: last_verified must be YYYY-MM-DD, got {verified!r}")
            entry["last_verified"] = verified
        else:
            raise ClassificationError(
                f"{where}: last_verified must be YYYY-MM-DD, got {verified!r}")
        key = (entry["exchange"], entry["symbol"])
        if key in table:
            raise ClassificationError(
                f"{origin}: duplicate entry for {key[0]}/{key[1]}")
        table[key] = entry
    return table


_PACKAGED = None


def packaged_evidence():
    global _PACKAGED
    if _PACKAGED is None:
        text = resources.files(__package__).joinpath("classifications.toml").read_text(
            encoding="utf-8")
        _PACKAGED = parse_classifications(text, PACKAGED_ORIGIN)
    return _PACKAGED


def compare(asset_type, row, exchange, symbol):
    """The (verdict, message) of a declared asset_type against an evidence row."""
    if row is None:
        return ("no_evidence",
                "no vendor classification recorded - run tools/record_classifications.py")
    vendor_type = row["vendor_type"]
    seen = f", recorded {row['last_verified']}" if row.get("last_verified") else ""
    if vendor_type in NOT_COMPARABLE_TYPES:
        return ("not_comparable",
                f"vendor type {vendor_type!r} cannot confirm asset_type {asset_type!r}{seen}: "
                f"the .CC (crypto) and .FOREX namespaces both serve it, so only the "
                f"symbol's own namespace separates them and the evidence is not independent")
    if vendor_type not in VENDOR_TYPE_TO_ASSET_TYPE:
        return ("unmapped",
                f"vendor type {vendor_type!r} has no store asset_type counterpart{seen} - "
                f"no verdict rather than a guess (mapped: "
                f"{list(VENDOR_TYPE_TO_ASSET_TYPE)})")
    mapped = VENDOR_TYPE_TO_ASSET_TYPE[vendor_type]
    if mapped == asset_type:
        return ("agree",
                f"vendor type {vendor_type!r} agrees with declared asset_type "
                f"{asset_type!r}{seen}")
    return ("disagree",
            f"declared asset_type {asset_type!r} but the vendor says {vendor_type!r} "
            f"(-> {mapped!r}){seen} for {exchange}/{symbol} - check the asset_class in "
            f"universe.toml against docs/EVALUATION_ASSET_CLASSIFICATION.md §5 C2")


def check_declared_class(exchange, symbol, asset_type, evidence=None):
    if evidence is None:
        evidence = packaged_evidence()
    return compare(asset_type, evidence.get((exchange, symbol)), exchange, symbol)

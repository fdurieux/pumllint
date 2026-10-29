"""Vendor-classification evidence and the declared-class verdict."""
from __future__ import annotations

import datetime as _dt
import tomllib
from importlib import resources

ORIGIN = "packaged classifications.toml"
TOP_KEYS = ("instrument", "provenance", "schema")
INSTRUMENT_KEYS = ("code", "exchange", "isin", "last_verified", "name", "query_exchange",
                   "symbol", "vendor_type")
REQUIRED_KEYS = ("exchange", "symbol", "code", "query_exchange", "vendor_type")
OPTIONAL_KEYS = ("isin", "name")
VENDOR_TYPE_MAP = {"Common Stock": "stock", "ETF": "etf"}
NOT_COMPARABLE = "Currency"


class ClassificationError(ValueError):
    """A malformed classifications.toml."""


def parse_classifications(text: str, origin: str = ORIGIN) -> dict:
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ClassificationError(f"{origin}: not valid TOML: {exc}") from None
    unknown = sorted(k for k in doc if k not in TOP_KEYS)
    if unknown:
        raise ClassificationError(
            f"{origin}: unknown key(s) {unknown}; allowed: {sorted(TOP_KEYS)}")
    if doc.get("schema") != 1:
        raise ClassificationError(f"{origin}: schema must be 1, got {doc.get('schema')!r}")
    entries = doc.get("instrument", [])
    if not isinstance(entries, list):
        raise ClassificationError(f"{origin}: [[instrument]] must be a list")
    rows = {}
    for n, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            raise ClassificationError(f"instrument #{n}: must be a table")
        unknown = sorted(k for k in entry if k not in INSTRUMENT_KEYS)
        if unknown:
            raise ClassificationError(
                f"instrument #{n}: unknown key(s) {unknown}; allowed: {sorted(INSTRUMENT_KEYS)}")
        where = f"instrument #{n}"
        if isinstance(entry.get("symbol"), str) and entry.get("symbol"):
            where = f"instrument '{entry['symbol']}'"
        row = {}
        for key in REQUIRED_KEYS:
            if key not in entry:
                raise ClassificationError(f"{where}: missing required key '{key}'")
            value = entry[key]
            if not isinstance(value, str):
                raise ClassificationError(f"{where}: {key} must be a string, got {value!r}")
            if not value:
                raise ClassificationError(f"{where}: {key} must be non-empty")
            row[key] = value
        for key in OPTIONAL_KEYS:
            value = entry.get(key, "")
            if not isinstance(value, str):
                raise ClassificationError(f"{where}: {key} must be a string, got {value!r}")
            row[key] = value
        verified = entry.get("last_verified")
        if verified is None:
            row["last_verified"] = None
        elif isinstance(verified, _dt.date) and not isinstance(verified, _dt.datetime):
            row["last_verified"] = verified.isoformat()
        else:
            try:
                row["last_verified"] = _dt.date.fromisoformat(str(verified)).isoformat()
                if not isinstance(verified, str) or len(verified) != 10:
                    raise ValueError
            except ValueError:
                raise ClassificationError(
                    f"{where}: last_verified must be YYYY-MM-DD, got {verified!r}") from None
        key = (row["exchange"], row["symbol"])
        if key in rows:
            raise ClassificationError(f"{origin}: duplicate entry for {key[0]}/{key[1]}")
        rows[key] = row
    return rows


def load_packaged() -> dict:
    text = resources.files(__package__).joinpath("classifications.toml").read_text(encoding="utf-8")
    return parse_classifications(text)


def compare(evidence: dict, exchange: str, symbol: str, asset_type: str):
    """Return (verdict, message) for a declared asset_type against the evidence."""
    row = evidence.get((exchange, symbol))
    if row is None:
        return "no_evidence", "no vendor classification recorded - run tools/record_classifications.py"
    vendor = row["vendor_type"]
    seen = f", recorded {row['last_verified']}" if row.get("last_verified") else ""
    if vendor == NOT_COMPARABLE:
        return "not_comparable", (
            f"vendor type {vendor!r} cannot confirm asset_type {asset_type!r}{seen}: the .CC "
            "(crypto) and .FOREX namespaces both serve it, so only the symbol's own namespace "
            "separates them and the evidence is not independent")
    mapped = VENDOR_TYPE_MAP.get(vendor)
    if mapped is None:
        return "unmapped", (
            f"vendor type {vendor!r} has no store asset_type counterpart{seen} - no verdict "
            f"rather than a guess (mapped: {sorted(VENDOR_TYPE_MAP)})")
    if mapped == asset_type:
        return "agree", f"vendor type {vendor!r} agrees with declared asset_type {asset_type!r}{seen}"
    return "disagree", (
        f"declared asset_type {asset_type!r} but the vendor says {vendor!r} (-> {mapped!r})"
        f"{seen} for {exchange}/{symbol} - check the asset_class in universe.toml against "
        "docs/EVALUATION_ASSET_CLASSIFICATION.md §5 C2")

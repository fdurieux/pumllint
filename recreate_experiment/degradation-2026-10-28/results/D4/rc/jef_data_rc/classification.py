"""Vendor-classification evidence and the declared-class verdict."""
from __future__ import annotations

import datetime as _dt
import tomllib
from importlib import resources

ORIGIN = "packaged classifications.toml"
TOP_KEYS = ("schema", "provenance", "instrument")
REQUIRED_KEYS = ("exchange", "symbol", "code", "query_exchange", "vendor_type")
OPTIONAL_KEYS = ("isin", "name", "last_verified")
VENDOR_TYPE_MAP = {"Common Stock": "stock", "ETF": "etf"}
NOT_COMPARABLE = "Currency"


class ClassificationError(ValueError):
    """The evidence file violates its grammar."""


def parse_classifications(text: str, origin: str = ORIGIN) -> dict:
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ClassificationError(f"{origin}: not valid TOML: {exc}") from None
    unknown = sorted(k for k in doc if k not in TOP_KEYS)
    if unknown:
        raise ClassificationError(f"{origin}: unknown key(s) {unknown}; allowed: {sorted(TOP_KEYS)}")
    if doc.get("schema") != 1 or isinstance(doc.get("schema"), bool):
        raise ClassificationError(f"{origin}: schema must be 1, got {doc.get('schema')!r}")
    instruments = doc.get("instrument", [])
    if not isinstance(instruments, list):
        raise ClassificationError(f"{origin}: [[instrument]] must be a list")
    rows: dict = {}
    allowed = sorted(REQUIRED_KEYS + OPTIONAL_KEYS)
    for n, item in enumerate(instruments, 1):
        where = f"instrument #{n}"
        if not isinstance(item, dict):
            raise ClassificationError(f"{where}: must be a table")
        unknown = sorted(k for k in item if k not in allowed)
        if unknown:
            raise ClassificationError(f"{where}: unknown key(s) {unknown}; allowed: {allowed}")
        if isinstance(item.get("symbol"), str) and item.get("symbol"):
            where = f"instrument '{item['symbol']}'"
        row = {}
        for key in REQUIRED_KEYS:
            if key not in item:
                raise ClassificationError(f"{where}: missing required key '{key}'")
            value = item[key]
            if not isinstance(value, str):
                raise ClassificationError(f"{where}: {key} must be a string, got {value!r}")
            if not value:
                raise ClassificationError(f"{where}: {key} must be non-empty")
            row[key] = value
        for key in ("isin", "name"):
            value = item.get(key, "")
            if not isinstance(value, str):
                raise ClassificationError(f"{where}: {key} must be a string, got {value!r}")
            row[key] = value
        verified = item.get("last_verified")
        if verified is not None:
            if isinstance(verified, _dt.date) and not isinstance(verified, _dt.datetime):
                verified = verified.isoformat()
            elif isinstance(verified, str):
                try:
                    _dt.date.fromisoformat(verified)
                except ValueError:
                    raise ClassificationError(
                        f"{where}: last_verified must be YYYY-MM-DD, got {verified!r}") from None
                if len(verified) != 10:
                    raise ClassificationError(
                        f"{where}: last_verified must be YYYY-MM-DD, got {verified!r}")
            else:
                raise ClassificationError(
                    f"{where}: last_verified must be YYYY-MM-DD, got {verified!r}")
        row["last_verified"] = verified
        key = (row["exchange"], row["symbol"])
        if key in rows:
            raise ClassificationError(f"{origin}: duplicate entry for {key[0]}/{key[1]}")
        rows[key] = row
    return rows


_PACKAGED = None


def packaged_rows() -> dict:
    global _PACKAGED
    if _PACKAGED is None:
        text = resources.files("jef_data_rc").joinpath("classifications.toml").read_text(encoding="utf-8")
        _PACKAGED = parse_classifications(text)
    return _PACKAGED


def compare(exchange: str, symbol: str, asset_type: str, rows: dict | None = None) -> tuple:
    rows = packaged_rows() if rows is None else rows
    row = rows.get((exchange, symbol))
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
        f"declared asset_type {asset_type!r} but the vendor says {vendor!r} (-> {mapped!r}){seen} "
        f"for {exchange}/{symbol} - check the asset_class in universe.toml against "
        "docs/EVALUATION_ASSET_CLASSIFICATION.md §5 C2")

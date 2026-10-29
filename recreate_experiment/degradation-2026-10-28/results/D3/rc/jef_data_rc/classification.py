"""Vendor-classification evidence and the declared-class verdict."""
from __future__ import annotations

import tomllib
from datetime import date
from importlib import resources

ORIGIN = "packaged classifications.toml"
TOP_KEYS = ["instrument", "provenance", "schema"]
INSTRUMENT_KEYS = ["code", "exchange", "isin", "last_verified", "name", "query_exchange",
                   "symbol", "vendor_type"]
REQUIRED = ["exchange", "symbol", "code", "query_exchange", "vendor_type"]
OPTIONAL = ["isin", "name"]
TYPE_MAP = {"Common Stock": "stock", "ETF": "etf"}
NOT_COMPARABLE = "Currency"


class ClassificationError(ValueError):
    """A malformed evidence file."""


def _string(entry: dict, key: str, where: str, required: bool) -> str:
    if key not in entry:
        if required:
            raise ClassificationError(f"{where}: missing required key '{key}'")
        return ""
    value = entry[key]
    if not isinstance(value, str):
        raise ClassificationError(f"{where}: {key} must be a string, got {value!r}")
    if required and value == "":
        raise ClassificationError(f"{where}: {key} must be non-empty")
    return value


def parse_classifications(text: str, origin: str = ORIGIN) -> dict:
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ClassificationError(f"{origin}: not valid TOML: {exc}") from None
    unknown = sorted(k for k in doc if k not in TOP_KEYS)
    if unknown:
        raise ClassificationError(f"{origin}: unknown key(s) {unknown}; allowed: {TOP_KEYS}")
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
        extra = sorted(k for k in entry if k not in INSTRUMENT_KEYS)
        if extra:
            raise ClassificationError(f"{where}: unknown key(s) {extra}; allowed: {INSTRUMENT_KEYS}")
        if "symbol" in entry and isinstance(entry["symbol"], str) and entry["symbol"]:
            where = f"instrument '{entry['symbol']}'"
        row = {key: _string(entry, key, where, True) for key in REQUIRED}
        for key in OPTIONAL:
            row[key] = _string(entry, key, where, False)
        verified = entry.get("last_verified")
        if verified is None:
            row["last_verified"] = None
        elif isinstance(verified, date):
            row["last_verified"] = verified.isoformat()
        else:
            try:
                row["last_verified"] = date.fromisoformat(str(verified)).isoformat()
                if not isinstance(verified, str) or len(verified) != 10:
                    raise ValueError
            except ValueError:
                raise ClassificationError(f"{where}: last_verified must be YYYY-MM-DD, got {verified!r}") from None
        key = (row["exchange"], row["symbol"])
        if key in rows:
            raise ClassificationError(f"{origin}: duplicate entry for {key[0]}/{key[1]}")
        rows[key] = row
    return rows


_PACKAGED = None


def packaged_evidence() -> dict:
    global _PACKAGED
    if _PACKAGED is None:
        text = resources.files(__package__).joinpath("classifications.toml").read_text(encoding="utf-8")
        _PACKAGED = parse_classifications(text)
    return _PACKAGED


def compare(exchange: str, symbol: str, asset_type: str, evidence: dict | None = None) -> tuple:
    """(verdict, message) for a declared asset_type against the vendor's row."""
    rows = packaged_evidence() if evidence is None else evidence
    row = rows.get((exchange, symbol))
    if row is None:
        return "no_evidence", "no vendor classification recorded - run tools/record_classifications.py"
    vendor_type = row["vendor_type"]
    seen = f", recorded {row['last_verified']}" if row.get("last_verified") else ""
    if vendor_type == NOT_COMPARABLE:
        return "not_comparable", (
            f"vendor type {vendor_type!r} cannot confirm asset_type {asset_type!r}{seen}: the .CC "
            f"(crypto) and .FOREX namespaces both serve it, so only the symbol's own namespace "
            f"separates them and the evidence is not independent")
    if vendor_type not in TYPE_MAP:
        return "unmapped", (
            f"vendor type {vendor_type!r} has no store asset_type counterpart{seen} - no verdict "
            f"rather than a guess (mapped: {sorted(TYPE_MAP)})")
    mapped = TYPE_MAP[vendor_type]
    if mapped == asset_type:
        return "agree", f"vendor type {vendor_type!r} agrees with declared asset_type {asset_type!r}{seen}"
    return "disagree", (
        f"declared asset_type {asset_type!r} but the vendor says {vendor_type!r} (-> {mapped!r}){seen} "
        f"for {exchange}/{symbol} - check the asset_class in universe.toml against "
        f"docs/EVALUATION_ASSET_CLASSIFICATION.md §5 C2")

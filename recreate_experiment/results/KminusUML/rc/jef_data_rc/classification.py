"""Vendor-classification evidence and the declared-class verdict."""
import datetime as _dt
import tomllib
from importlib import resources

ORIGIN = "packaged classifications.toml"
TOP_KEYS = ["instrument", "provenance", "schema"]
REQUIRED = ["exchange", "symbol", "code", "query_exchange", "vendor_type"]
OPTIONAL = ["isin", "name"]
INSTRUMENT_KEYS = sorted(REQUIRED + OPTIONAL + ["last_verified"])
VENDOR_TO_ASSET_TYPE = {"Common Stock": "stock", "ETF": "etf"}
NOT_COMPARABLE = "Currency"


class ClassificationError(ValueError):
    """A malformed classification evidence file."""


def parse(text, origin=ORIGIN):
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ClassificationError(f"{origin}: not valid TOML: {exc}") from None
    unknown = sorted(set(doc) - set(TOP_KEYS))
    if unknown:
        raise ClassificationError(
            f"{origin}: unknown key(s) {unknown}; allowed: {TOP_KEYS}")
    if doc.get("schema") != 1 or isinstance(doc.get("schema"), bool):
        raise ClassificationError(f"{origin}: schema must be 1, got {doc.get('schema')!r}")
    instruments = doc.get("instrument", [])
    if not isinstance(instruments, list):
        raise ClassificationError(f"{origin}: [[instrument]] must be a list")
    rows = {}
    for n, raw in enumerate(instruments, 1):
        if not isinstance(raw, dict):
            raise ClassificationError(f"instrument #{n}: must be a table")
        unknown = sorted(set(raw) - set(INSTRUMENT_KEYS))
        if unknown:
            raise ClassificationError(
                f"instrument #{n}: unknown key(s) {unknown}; allowed: {INSTRUMENT_KEYS}")
        where = f"instrument #{n}"
        if isinstance(raw.get("symbol"), str) and raw.get("symbol"):
            where = f"instrument '{raw['symbol']}'"
        row = {}
        for key in REQUIRED:
            if key not in raw:
                raise ClassificationError(f"{where}: missing required key '{key}'")
            value = raw[key]
            if not isinstance(value, str):
                raise ClassificationError(f"{where}: {key} must be a string, got {value!r}")
            if not value:
                raise ClassificationError(f"{where}: {key} must be non-empty")
            row[key] = value
        for key in OPTIONAL:
            value = raw.get(key, "")
            if not isinstance(value, str):
                raise ClassificationError(f"{where}: {key} must be a string, got {value!r}")
            row[key] = value
        verified = raw.get("last_verified")
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
            raise ClassificationError(
                f"{origin}: duplicate entry for {key[0]}/{key[1]}")
        rows[key] = row
    return rows


_PACKAGED = None


def packaged():
    global _PACKAGED
    if _PACKAGED is None:
        text = resources.files(__package__).joinpath("classifications.toml").read_text(
            encoding="utf-8")
        _PACKAGED = parse(text)
    return _PACKAGED


def verdict(exchange, symbol, asset_type, rows=None):
    """(verdict, message) of a declared asset_type against the vendor evidence."""
    rows = packaged() if rows is None else rows
    row = rows.get((exchange, symbol))
    if row is None:
        return "no_evidence", "no vendor classification recorded - run tools/record_classifications.py"
    vendor = row["vendor_type"]
    seen = f", recorded {row['last_verified']}" if row.get("last_verified") else ""
    if vendor == NOT_COMPARABLE:
        return "not_comparable", (
            f"vendor type {vendor!r} cannot confirm asset_type {asset_type!r}{seen}: the .CC "
            f"(crypto) and .FOREX namespaces both serve it, so only the symbol's own "
            f"namespace separates them and the evidence is not independent")
    mapped = VENDOR_TO_ASSET_TYPE.get(vendor)
    if mapped is None:
        return "unmapped", (
            f"vendor type {vendor!r} has no store asset_type counterpart{seen} - no verdict "
            f"rather than a guess (mapped: {sorted(VENDOR_TO_ASSET_TYPE)})")
    if mapped == asset_type:
        return "agree", f"vendor type {vendor!r} agrees with declared asset_type {asset_type!r}{seen}"
    return "disagree", (
        f"declared asset_type {asset_type!r} but the vendor says {vendor!r} (-> {mapped!r})"
        f"{seen} for {exchange}/{symbol} - check the asset_class in universe.toml against "
        f"docs/EVALUATION_ASSET_CLASSIFICATION.md §5 C2")

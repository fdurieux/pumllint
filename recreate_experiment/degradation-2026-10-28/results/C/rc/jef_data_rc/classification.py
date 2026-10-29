"""Vendor-classification evidence and the declared-class verdict."""
import tomllib
from datetime import date
from importlib import resources

ORIGIN = "packaged classifications.toml"
TOP_KEYS = ["instrument", "provenance", "schema"]
INSTRUMENT_KEYS = ["code", "exchange", "isin", "last_verified", "name", "query_exchange",
                   "symbol", "vendor_type"]
REQUIRED = ["exchange", "symbol", "code", "query_exchange", "vendor_type"]
OPTIONAL = ["isin", "name"]
VENDOR_TYPE_MAP = {"Common Stock": "stock", "ETF": "etf"}
NOT_COMPARABLE = "Currency"

_CACHE = {}


class ClassificationError(ValueError):
    """A classifications document that violates its grammar."""


def parse_classifications(text, origin=ORIGIN):
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ClassificationError(f"{origin}: not valid TOML: {exc}") from None
    unknown = sorted(set(doc) - set(TOP_KEYS))
    if unknown:
        raise ClassificationError(f"{origin}: unknown key(s) {unknown}; allowed: {TOP_KEYS}")
    schema = doc.get("schema")
    if schema != 1 or isinstance(schema, bool):
        raise ClassificationError(f"{origin}: schema must be 1, got {schema!r}")
    instruments = doc.get("instrument", [])
    if not isinstance(instruments, list):
        raise ClassificationError(f"{origin}: [[instrument]] must be a list")
    rows = {}
    for n, raw in enumerate(instruments, start=1):
        where = f"instrument #{n}"
        if not isinstance(raw, dict):
            raise ClassificationError(f"{where}: must be a table")
        unknown = sorted(set(raw) - set(INSTRUMENT_KEYS))
        if unknown:
            raise ClassificationError(
                f"{where}: unknown key(s) {unknown}; allowed: {sorted(INSTRUMENT_KEYS)}")
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
            if key == "symbol":
                where = f"instrument '{value}'"
        for key in OPTIONAL:
            value = raw.get(key, "")
            if not isinstance(value, str):
                raise ClassificationError(f"{where}: {key} must be a string, got {value!r}")
            row[key] = value
        verified = raw.get("last_verified")
        if verified is None:
            row["last_verified"] = None
        elif isinstance(verified, date):
            row["last_verified"] = verified.isoformat()
        elif isinstance(verified, str):
            try:
                row["last_verified"] = date.fromisoformat(verified).isoformat()
            except ValueError:
                raise ClassificationError(
                    f"{where}: last_verified must be YYYY-MM-DD, got {verified!r}") from None
            if len(verified) != 10:
                raise ClassificationError(
                    f"{where}: last_verified must be YYYY-MM-DD, got {verified!r}")
        else:
            raise ClassificationError(
                f"{where}: last_verified must be YYYY-MM-DD, got {verified!r}")
        key = (row["exchange"], row["symbol"])
        if key in rows:
            raise ClassificationError(
                f"{origin}: duplicate entry for {row['exchange']}/{row['symbol']}")
        rows[key] = row
    return rows


def packaged_evidence():
    if "rows" not in _CACHE:
        text = resources.files("jef_data_rc").joinpath("classifications.toml").read_text(
            encoding="utf-8")
        _CACHE["rows"] = parse_classifications(text)
    return _CACHE["rows"]


def compare(asset_type, exchange, symbol, evidence=None):
    """Return (verdict, message) for a declared asset_type against the vendor evidence."""
    rows = packaged_evidence() if evidence is None else evidence
    row = rows.get((exchange, symbol))
    if row is None:
        return "no_evidence", "no vendor classification recorded - run tools/record_classifications.py"
    vendor_type = row["vendor_type"]
    seen = f", recorded {row['last_verified']}" if row.get("last_verified") else ""
    if vendor_type == NOT_COMPARABLE:
        return "not_comparable", (
            f"vendor type {vendor_type!r} cannot confirm asset_type {asset_type!r}{seen}: the "
            f".CC (crypto) and .FOREX namespaces both serve it, so only the symbol's own "
            f"namespace separates them and the evidence is not independent")
    mapped = VENDOR_TYPE_MAP.get(vendor_type)
    if mapped is None:
        return "unmapped", (
            f"vendor type {vendor_type!r} has no store asset_type counterpart{seen} - no "
            f"verdict rather than a guess (mapped: {sorted(VENDOR_TYPE_MAP)})")
    if mapped == asset_type:
        return "agree", f"vendor type {vendor_type!r} agrees with declared asset_type {asset_type!r}{seen}"
    return "disagree", (
        f"declared asset_type {asset_type!r} but the vendor says {vendor_type!r} "
        f"(-> {mapped!r}){seen} for {exchange}/{symbol} - check the asset_class in "
        f"universe.toml against docs/EVALUATION_ASSET_CLASSIFICATION.md §5 C2")

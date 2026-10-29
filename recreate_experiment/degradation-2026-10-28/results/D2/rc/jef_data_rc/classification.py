"""Vendor-classification evidence and the declared-class verdict."""
import datetime as _dt
import tomllib
from importlib import resources

ORIGIN = "packaged classifications.toml"
TOP_KEYS = ["instrument", "provenance", "schema"]
REQUIRED = ["exchange", "symbol", "code", "query_exchange", "vendor_type"]
OPTIONAL = ["isin", "name"]
INSTRUMENT_KEYS = sorted(REQUIRED + OPTIONAL + ["last_verified"])
VENDOR_TYPE_MAP = {"Common Stock": "stock", "ETF": "etf"}


class ClassificationError(ValueError):
    """A classifications document that violates its grammar."""


def _string(where, key, value):
    if not isinstance(value, str):
        raise ClassificationError(f"{where}: {key} must be a string, got {value!r}")
    return value


def parse_classifications(text, origin=ORIGIN):
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ClassificationError(f"{origin}: not valid TOML: {exc}") from None
    extra = sorted(k for k in doc if k not in TOP_KEYS)
    if extra:
        raise ClassificationError(f"{origin}: unknown key(s) {extra}; allowed: {TOP_KEYS}")
    if doc.get("schema") != 1 or isinstance(doc.get("schema"), bool):
        raise ClassificationError(f"{origin}: schema must be 1, got {doc.get('schema')!r}")
    rows = doc.get("instrument", [])
    if not isinstance(rows, list):
        raise ClassificationError(f"{origin}: [[instrument]] must be a list")
    table = {}
    for n, raw in enumerate(rows, 1):
        where = f"instrument #{n}"
        if not isinstance(raw, dict):
            raise ClassificationError(f"{where}: must be a table")
        extra = sorted(k for k in raw if k not in INSTRUMENT_KEYS)
        if extra:
            raise ClassificationError(f"{where}: unknown key(s) {extra}; allowed: {INSTRUMENT_KEYS}")
        if "symbol" in raw and isinstance(raw["symbol"], str):
            where = f"instrument '{raw['symbol']}'"
        row = {}
        for key in REQUIRED:
            if key not in raw:
                raise ClassificationError(f"{where}: missing required key '{key}'")
            value = _string(where, key, raw[key])
            if not value:
                raise ClassificationError(f"{where}: {key} must be non-empty")
            row[key] = value
        for key in OPTIONAL:
            row[key] = _string(where, key, raw[key]) if key in raw else ""
        verified = raw.get("last_verified")
        if verified is not None:
            if isinstance(verified, _dt.date) and not isinstance(verified, _dt.datetime):
                verified = verified.isoformat()
            elif isinstance(verified, str):
                try:
                    if len(verified) != 10:
                        raise ValueError
                    verified = _dt.date.fromisoformat(verified).isoformat()
                except ValueError:
                    raise ClassificationError(
                        f"{where}: last_verified must be YYYY-MM-DD, got {raw['last_verified']!r}") from None
            else:
                raise ClassificationError(f"{where}: last_verified must be YYYY-MM-DD, got {verified!r}")
        row["last_verified"] = verified
        key = (row["exchange"], row["symbol"])
        if key in table:
            raise ClassificationError(f"{origin}: duplicate entry for {key[0]}/{key[1]}")
        table[key] = row
    return table


def load_classifications():
    text = resources.files(__package__).joinpath("classifications.toml").read_text(encoding="utf-8")
    return parse_classifications(text)


def compare(evidence, exchange, symbol, asset_type):
    """(verdict, message) of a declared asset_type against the vendor evidence."""
    row = evidence.get((exchange, symbol))
    if row is None:
        return "no_evidence", "no vendor classification recorded - run tools/record_classifications.py"
    seen = f", recorded {row['last_verified']}" if row.get("last_verified") else ""
    vendor_type = row["vendor_type"]
    if vendor_type == "Currency":
        return "not_comparable", (
            f"vendor type {vendor_type!r} cannot confirm asset_type {asset_type!r}{seen}: the .CC "
            "(crypto) and .FOREX namespaces both serve it, so only the symbol's own namespace "
            "separates them and the evidence is not independent")
    mapped = VENDOR_TYPE_MAP.get(vendor_type)
    if mapped is None:
        return "unmapped", (
            f"vendor type {vendor_type!r} has no store asset_type counterpart{seen} - no verdict "
            f"rather than a guess (mapped: {sorted(VENDOR_TYPE_MAP)})")
    if mapped == asset_type:
        return "agree", f"vendor type {vendor_type!r} agrees with declared asset_type {asset_type!r}{seen}"
    return "disagree", (
        f"declared asset_type {asset_type!r} but the vendor says {vendor_type!r} (-> {mapped!r}){seen} "
        f"for {exchange}/{symbol} - check the asset_class in universe.toml against "
        "docs/EVALUATION_ASSET_CLASSIFICATION.md §5 C2")

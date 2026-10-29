"""Vendor-classification evidence and the declared-class verdict."""
import tomllib
from datetime import date
from importlib import resources

ORIGIN = "packaged classifications.toml"
TOP_KEYS = ["instrument", "provenance", "schema"]
REQUIRED = ["exchange", "symbol", "code", "query_exchange", "vendor_type"]
OPTIONAL = ["isin", "name", "last_verified"]
VENDOR_TO_ASSET_TYPE = {"Common Stock": "stock", "ETF": "etf"}
NOT_COMPARABLE = {"Currency"}


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
    if doc.get("schema") != 1 or isinstance(doc.get("schema"), bool):
        raise ClassificationError(f"{origin}: schema must be 1, got {doc.get('schema')!r}")
    entries = doc.get("instrument", [])
    if not isinstance(entries, list):
        raise ClassificationError(f"{origin}: [[instrument]] must be a list")
    rows = {}
    for n, entry in enumerate(entries, 1):
        where = f"instrument #{n}"
        if not isinstance(entry, dict):
            raise ClassificationError(f"{where}: must be a table")
        allowed = sorted(REQUIRED + OPTIONAL)
        unknown = sorted(set(entry) - set(allowed))
        if unknown:
            raise ClassificationError(f"{where}: unknown key(s) {unknown}; allowed: {allowed}")
        if "symbol" in entry and isinstance(entry["symbol"], str) and entry["symbol"]:
            where = f"instrument '{entry['symbol']}'"
        row = {}
        for key in REQUIRED:
            if key not in entry:
                raise ClassificationError(f"{where}: missing required key '{key}'")
            value = entry[key]
            if not isinstance(value, str):
                raise ClassificationError(f"{where}: {key} must be a string, got {value!r}")
            if not value:
                raise ClassificationError(f"{where}: {key} must be non-empty")
            row[key] = value
        for key in ("isin", "name"):
            value = entry.get(key, "")
            if not isinstance(value, str):
                raise ClassificationError(f"{where}: {key} must be a string, got {value!r}")
            row[key] = value
        verified = entry.get("last_verified")
        if verified is not None:
            if isinstance(verified, date):
                verified = verified.isoformat()
            elif isinstance(verified, str):
                try:
                    verified = date.fromisoformat(verified).isoformat()
                except ValueError:
                    raise ClassificationError(
                        f"{where}: last_verified must be YYYY-MM-DD, got {verified!r}") from None
            else:
                raise ClassificationError(
                    f"{where}: last_verified must be YYYY-MM-DD, got {verified!r}")
        row["last_verified"] = verified
        key = (row["exchange"], row["symbol"])
        if key in rows:
            raise ClassificationError(f"{origin}: duplicate entry for {key[0]}/{key[1]}")
        rows[key] = row
    return rows


def load_classifications():
    text = resources.files(__package__).joinpath("classifications.toml").read_text(
        encoding="utf-8")
    return parse_classifications(text)


def compare(evidence, exchange, symbol, asset_type):
    """(verdict, message) of the declared asset_type against the vendor evidence."""
    row = evidence.get((exchange, symbol))
    if row is None:
        return "no_evidence", "no vendor classification recorded - run tools/record_classifications.py"
    vendor = row["vendor_type"]
    seen = f", recorded {row['last_verified']}" if row.get("last_verified") else ""
    if vendor in NOT_COMPARABLE:
        return "not_comparable", (
            f"vendor type {vendor!r} cannot confirm asset_type {asset_type!r}{seen}: the .CC "
            "(crypto) and .FOREX namespaces both serve it, so only the symbol's own namespace "
            "separates them and the evidence is not independent")
    mapped = VENDOR_TO_ASSET_TYPE.get(vendor)
    if mapped is None:
        return "unmapped", (
            f"vendor type {vendor!r} has no store asset_type counterpart{seen} - no verdict "
            f"rather than a guess (mapped: {sorted(VENDOR_TO_ASSET_TYPE)})")
    if mapped == asset_type:
        return "agree", f"vendor type {vendor!r} agrees with declared asset_type {asset_type!r}{seen}"
    return "disagree", (
        f"declared asset_type {asset_type!r} but the vendor says {vendor!r} (-> {mapped!r}){seen} "
        f"for {exchange}/{symbol} - check the asset_class in universe.toml against "
        "docs/EVALUATION_ASSET_CLASSIFICATION.md §5 C2")

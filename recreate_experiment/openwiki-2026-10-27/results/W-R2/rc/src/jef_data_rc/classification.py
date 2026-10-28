"""Committed vendor classification evidence, compared against declarations.

`classifications.toml` is evidence, not configuration: it can produce a
warning when a mapped vendor type disagrees with the declared class, but it
never selects a class or changes acquisition. Records are keyed by store
identity `(exchange, symbol)`; `code` and `query_exchange` only record the
vendor query that produced them. No network call is made.

Only `Common Stock -> stock` and `ETF -> etf` are mapped. `Currency` is not
comparable (EODHD uses it for both crypto and forex namespaces).
"""

from __future__ import annotations

import datetime as _dt
import tomllib
from importlib import resources
from pathlib import Path

SCHEMA_VERSION = 1
TOP_KEYS = ("schema", "instrument")
INSTRUMENT_KEYS = ("exchange", "symbol", "code", "query_exchange", "vendor_type", "isin", "name",
                   "last_verified")
REQUIRED_KEYS = ("exchange", "symbol", "code", "query_exchange", "vendor_type")

VENDOR_TYPE_MAP = {"Common Stock": "stock", "ETF": "etf"}
NOT_COMPARABLE = frozenset({"Currency"})

AGREE = "agree"
DISAGREE = "disagree"
NO_EVIDENCE = "no_evidence"
NOT_COMPARABLE_VERDICT = "not_comparable"
UNMAPPED = "unmapped"


class ClassificationError(ValueError):
    """The evidence document is malformed."""


def _parse(text: str, label: str) -> dict[tuple[str, str], dict]:
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ClassificationError(f"{label}: invalid TOML: {exc}") from exc
    unknown = sorted(k for k in doc if k not in TOP_KEYS)
    if unknown:
        raise ClassificationError(f"{label}: unknown top-level key(s): {', '.join(unknown)}")
    if doc.get("schema") != SCHEMA_VERSION:
        raise ClassificationError(f"{label}: schema must be {SCHEMA_VERSION}, got {doc.get('schema')!r}")
    instruments = doc.get("instrument", [])
    if not isinstance(instruments, list):
        raise ClassificationError(f"{label}: 'instrument' must be an array of tables")
    records: dict[tuple[str, str], dict] = {}
    for i, inst in enumerate(instruments):
        where = f"{label}: instrument[{i}]"
        if not isinstance(inst, dict):
            raise ClassificationError(f"{where}: must be a table")
        unknown = sorted(k for k in inst if k not in INSTRUMENT_KEYS)
        if unknown:
            raise ClassificationError(f"{where}: unknown key(s): {', '.join(unknown)}")
        for key in REQUIRED_KEYS:
            value = inst.get(key)
            if not isinstance(value, str) or not value:
                raise ClassificationError(f"{where}: '{key}' is required and must be a non-empty string")
        for key in ("isin", "name"):
            if key in inst and not isinstance(inst[key], str):
                raise ClassificationError(f"{where}: '{key}' must be a string")
        record = dict(inst)
        if "last_verified" in inst:
            lv = inst["last_verified"]
            if isinstance(lv, _dt.datetime) or not isinstance(lv, (_dt.date, str)):
                raise ClassificationError(f"{where}: 'last_verified' must be a date")
            if isinstance(lv, str):
                try:
                    lv = _dt.date.fromisoformat(lv)
                except ValueError as exc:
                    raise ClassificationError(f"{where}: invalid last_verified {lv!r}") from exc
            record["last_verified"] = lv.isoformat()
        key = (inst["exchange"], inst["symbol"])
        if key in records:
            raise ClassificationError(f"{where}: duplicate entry for {key[0]}/{key[1]}")
        records[key] = record
    return records


def load_classifications(path: str | Path | None = None) -> dict[tuple[str, str], dict]:
    """Parse the committed evidence file (the packaged one by default)."""
    if path is None:
        text = resources.files("jef_data_rc").joinpath("classifications.toml").read_text(encoding="utf-8")
        label = "classifications.toml"
    else:
        text = Path(path).read_text(encoding="utf-8")
        label = str(path)
    return _parse(text, label)


def compare(evidence: dict[tuple[str, str], dict], exchange: str, symbol: str,
            declared_type: str) -> dict:
    """Compare the declared store asset type with recorded vendor evidence."""
    record = evidence.get((exchange, symbol))
    if record is None:
        return {"verdict": NO_EVIDENCE, "declared": declared_type, "vendor_type": None, "mapped": None}
    vendor_type = record["vendor_type"]
    if vendor_type in NOT_COMPARABLE:
        verdict, mapped = NOT_COMPARABLE_VERDICT, None
    elif vendor_type not in VENDOR_TYPE_MAP:
        verdict, mapped = UNMAPPED, None
    else:
        mapped = VENDOR_TYPE_MAP[vendor_type]
        verdict = AGREE if mapped == declared_type else DISAGREE
    return {"verdict": verdict, "declared": declared_type, "vendor_type": vendor_type, "mapped": mapped}


def describe(check: dict, exchange: str, symbol: str) -> str:
    """The finding text for a comparison result."""
    v = check["verdict"]
    declared = check["declared"]
    vt = check["vendor_type"]
    if v == DISAGREE:
        return (f"declared class: declared {declared} but vendor type {vt!r} maps to "
                f"{check['mapped']} - review the universe declaration")
    if v == AGREE:
        return f"declared class: {declared} agrees with vendor type {vt!r}"
    if v == NOT_COMPARABLE_VERDICT:
        return (f"declared class: vendor type {vt!r} is not comparable "
                "(it does not distinguish crypto from forex)")
    if v == UNMAPPED:
        return f"declared class: vendor type {vt!r} has no store mapping; no verdict"
    return (f"declared class: no evidence recorded for {exchange}/{symbol} "
            "- record it in classifications.toml")

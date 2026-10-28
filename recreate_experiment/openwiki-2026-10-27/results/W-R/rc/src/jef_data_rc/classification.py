"""Committed vendor classification evidence, checked against the universe.

``classifications.toml`` records what EODHD said about each instrument,
keyed by store identity ``(exchange, symbol)``. It is evidence only: it can
make ``status`` warn, but it never selects a class, rewrites the universe or
changes an ingestion decision. No network call is made.

Verdicts: ``agree`` / ``disagree`` (only for mapped vendor types),
``not_comparable`` (``Currency``: EODHD uses it for crypto and forex alike),
``unmapped`` (a vendor type with no store mapping) and ``no_evidence``.
"""
from __future__ import annotations

import datetime as _dt
import re
import tomllib
from importlib import resources
from pathlib import Path

SCHEMA_VERSION = 1

VENDOR_TYPE_MAP = {"Common Stock": "stock", "ETF": "etf"}
NOT_COMPARABLE = frozenset({"Currency"})

VERDICTS = ("agree", "disagree", "not_comparable", "unmapped", "no_evidence")

_TOP_KEYS = frozenset({"schema", "instrument"})
_REQUIRED = ("exchange", "symbol", "code", "query_exchange", "vendor_type")
_OPTIONAL = ("isin", "name", "last_verified")
_INSTRUMENT_KEYS = frozenset(_REQUIRED + _OPTIONAL)


class ClassificationError(ValueError):
    """The committed evidence document is malformed."""


def packaged_classifications_path() -> Path:
    return Path(str(resources.files("jef_data_rc").joinpath("classifications.toml")))


def _date(where: str, value) -> str:
    if isinstance(value, _dt.datetime):
        return value.date().isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            return _dt.date.fromisoformat(value).isoformat()
        except ValueError:
            pass
    raise ClassificationError(f"{where}: 'last_verified' must be an ISO date")


def parse_classifications(document: dict, label: str = "classifications") -> dict:
    if not isinstance(document, dict):
        raise ClassificationError(f"{label}: must be a TOML table")
    extra = sorted(set(document) - _TOP_KEYS)
    if extra:
        raise ClassificationError(f"{label}: unknown key(s): {', '.join(extra)}")
    schema = document.get("schema")
    if isinstance(schema, bool) or schema != SCHEMA_VERSION:
        raise ClassificationError(
            f"{label}: schema must be {SCHEMA_VERSION} (got {schema!r})"
        )
    instruments = document.get("instrument", [])
    if not isinstance(instruments, list):
        raise ClassificationError(f"{label}: 'instrument' must be an array of tables")
    records: dict[tuple[str, str], dict] = {}
    for i, raw in enumerate(instruments):
        where = f"{label}: instrument[{i}]"
        if not isinstance(raw, dict):
            raise ClassificationError(f"{where}: must be a table")
        unknown = sorted(set(raw) - _INSTRUMENT_KEYS)
        if unknown:
            raise ClassificationError(f"{where}: unknown key(s): {', '.join(unknown)}")
        record = {}
        for key in _REQUIRED:
            value = raw.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ClassificationError(f"{where}: '{key}' must be a non-empty string")
            record[key] = value
        for key in ("isin", "name"):
            if key in raw:
                if not isinstance(raw[key], str):
                    raise ClassificationError(f"{where}: '{key}' must be a string")
                record[key] = raw[key]
        if "last_verified" in raw:
            record["last_verified"] = _date(where, raw["last_verified"])
        identity = (record["exchange"], record["symbol"])
        if identity in records:
            raise ClassificationError(
                f"{where}: duplicate entry for {identity[0]}:{identity[1]}"
            )
        records[identity] = record
    return records


def load_classifications(path: str | Path | None = None) -> dict:
    """Evidence keyed by ``(exchange, symbol)``."""
    source = packaged_classifications_path() if path is None else Path(path)
    label = "classifications.toml" if path is None else str(path)
    try:
        document = tomllib.loads(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ClassificationError(f"{label}: cannot read: {exc.strerror or exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ClassificationError(f"{label}: invalid TOML: {exc}") from exc
    return parse_classifications(document, label)


def compare(evidence: dict, exchange: str, symbol: str, declared: str) -> dict:
    """Compare the declared store asset type with the recorded vendor type."""
    record = evidence.get((exchange, symbol))
    if record is None:
        return {
            "verdict": "no_evidence",
            "declared": declared,
            "vendor_type": None,
            "mapped": None,
        }
    vendor_type = record["vendor_type"]
    if vendor_type in NOT_COMPARABLE:
        verdict, mapped = "not_comparable", None
    else:
        mapped = VENDOR_TYPE_MAP.get(vendor_type)
        if mapped is None:
            verdict = "unmapped"
        elif mapped == declared:
            verdict = "agree"
        else:
            verdict = "disagree"
    return {
        "verdict": verdict,
        "declared": declared,
        "vendor_type": vendor_type,
        "mapped": mapped,
    }


def describe(check: dict, exchange: str, symbol: str) -> str:
    verdict = check["verdict"]
    declared = check["declared"]
    vendor = check["vendor_type"]
    if verdict == "agree":
        return f"declared {declared} agrees with EODHD vendor type {vendor!r}"
    if verdict == "disagree":
        return (
            f"declared {declared} disagrees with EODHD vendor type {vendor!r} "
            f"(maps to {check['mapped']}) - review the universe declaration"
        )
    if verdict == "not_comparable":
        return (
            f"EODHD vendor type {vendor!r} is not comparable with declared "
            f"{declared} (it covers both crypto and forex)"
        )
    if verdict == "unmapped":
        return (
            f"EODHD vendor type {vendor!r} has no store mapping - no verdict on "
            f"declared {declared}"
        )
    return (
        f"no classification evidence recorded for {exchange}:{symbol} - record "
        "it in classifications.toml"
    )

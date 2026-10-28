"""Corporate actions: split events and dividend entries, per symbol, as JSON.

Layout below a store root::

    corporate_actions/splits/{symbol}.json
    corporate_actions/dividends/{symbol}.json

(``/`` in a symbol becomes ``_`` in the file name). Each file is an envelope
``{symbol, exchange, last_updated, splits|dividends}``. A missing file loads
as an empty list: "no known actions", not a reason to go to the network.

Saves are a direct truncating ``open(path, "w")`` + ``json.dump``; they do not
share the Parquet store's lock or temp-and-replace protocol.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

ACTIONS_DIR = "corporate_actions"
KINDS = ("splits", "dividends")


@dataclass(frozen=True)
class SplitEvent:
    """A split: ``ratio`` is new shares / old shares (``4/1`` -> 4.0).

    ``date`` is the first session that trades on the new price basis.
    """

    date: date
    ratio: float
    split: str

    def to_json(self) -> dict:
        return {"date": self.date.isoformat(), "ratio": self.ratio, "split": self.split}

    @classmethod
    def from_json(cls, entry: dict) -> "SplitEvent":
        return cls(
            date=date.fromisoformat(str(entry["date"])[:10]),
            ratio=float(entry["ratio"]),
            split=str(entry.get("split", "")),
        )


def parse_split_ratio(text: str) -> float:
    """``"4.000000/1.000000"`` -> 4.0 (new shares over old shares)."""
    parts = str(text).split("/")
    if len(parts) != 2:
        raise ValueError(f"unrecognised split string {text!r}")
    new, old = float(parts[0]), float(parts[1])
    if old == 0:
        raise ValueError(f"split {text!r} has a zero denominator")
    ratio = new / old
    if not math.isfinite(ratio):
        raise ValueError(f"split {text!r} has a non-finite ratio")
    return ratio


def _safe(symbol: str) -> str:
    return symbol.replace("/", "_")


def action_path(base, kind: str, symbol: str) -> Path:
    if kind not in KINDS:
        raise ValueError(f"unknown action kind {kind!r}")
    return Path(base) / ACTIONS_DIR / kind / f"{_safe(symbol)}.json"


def splits_path(base, symbol: str) -> Path:
    return action_path(base, "splits", symbol)


def dividends_path(base, symbol: str) -> Path:
    return action_path(base, "dividends", symbol)


def read_document(base, kind: str, symbol: str) -> dict | None:
    """The stored envelope for ``kind`` (``splits``/``dividends``), or None."""
    path = action_path(base, kind, symbol)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_splits(base, symbol: str) -> list[SplitEvent]:
    doc = read_document(base, "splits", symbol)
    if not doc:
        return []
    events = [SplitEvent.from_json(e) for e in doc.get("splits", [])]
    return sorted(events, key=lambda s: s.date)


def load_dividends(base, symbol: str) -> list[dict]:
    doc = read_document(base, "dividends", symbol)
    if not doc:
        return []
    return list(doc.get("dividends", []))


def last_updated(base, symbol: str) -> str | None:
    """The split file's ``last_updated`` stamp: the action-freshness clock."""
    doc = read_document(base, "splits", symbol)
    if not doc:
        return None
    stamp = doc.get("last_updated")
    return stamp or None


def stamp_date(stamp: str) -> date:
    """UTC calendar date of a ``last_updated`` stamp."""
    text = str(stamp).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is not None:
        moment = moment.astimezone(timezone.utc)
    return moment.date()


def _now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _write(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2)
        handle.write("\n")


def save_splits(base, symbol: str, splits, *, exchange: str = "eodhd", now=None) -> Path:
    ordered = sorted(splits, key=lambda s: s.date)
    document = {
        "symbol": symbol,
        "exchange": exchange,
        "last_updated": _now(now).isoformat(),
        "splits": [s.to_json() for s in ordered],
    }
    path = splits_path(base, symbol)
    _write(path, document)
    return path


def save_dividends(base, symbol: str, dividends, *, exchange: str = "eodhd", now=None) -> Path:
    ordered = sorted(dividends, key=lambda d: str(d.get("date", "")))
    document = {
        "symbol": symbol,
        "exchange": exchange,
        "last_updated": _now(now).isoformat(),
        "dividends": list(ordered),
    }
    path = dividends_path(base, symbol)
    _write(path, document)
    return path


def sync_actions(collector, base, symbol: str, *, exchange: str = "eodhd", now=None):
    """Fetch splits and dividends for ``symbol`` and persist both files."""
    splits = collector.get_splits(symbol)
    dividends = collector.get_dividends(symbol)
    save_splits(base, symbol, splits, exchange=exchange, now=now)
    save_dividends(base, symbol, dividends, exchange=exchange, now=now)
    return splits, dividends

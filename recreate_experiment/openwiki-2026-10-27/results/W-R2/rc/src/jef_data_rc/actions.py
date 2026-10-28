"""Corporate actions: split events and dividend entries, stored per symbol.

Files live below the store root at `corporate_actions/splits/{symbol}.json`
and `corporate_actions/dividends/{symbol}.json` (a `/` in a symbol becomes
`_`). Each file is an envelope `{symbol, exchange, last_updated, <list>}`.
An absent file loads as an empty list. Saves are a direct truncating write;
they do not use the Parquet store's lock or temp-and-replace protocol.

Dividends are retained from acquisition onward but never applied by the
split-only adjustment pass.
"""

from __future__ import annotations

import datetime as _dt
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


class ActionsError(ValueError):
    """A corporate-action record is malformed."""


def parse_ratio(split: str) -> float:
    """`"4/1"` (new shares / old shares) -> 4.0."""
    try:
        new, old = str(split).split("/")
        ratio = float(new) / float(old)
    except (ValueError, ZeroDivisionError) as exc:
        raise ActionsError(f"cannot parse split ratio {split!r}") from exc
    return ratio


@dataclass(frozen=True)
class SplitEvent:
    """A split effective on `date`: the first session at the new price basis.

    `ratio` is new shares divided by old shares, so a 4-for-1 split is 4.0.
    """

    date: str
    ratio: float
    split: str

    @classmethod
    def from_provider(cls, entry: dict) -> "SplitEvent":
        try:
            date = _dt.date.fromisoformat(str(entry["date"])[:10]).isoformat()
            split = str(entry["split"])
        except (KeyError, ValueError) as exc:
            raise ActionsError(f"malformed split entry {entry!r}") from exc
        return cls(date=date, ratio=parse_ratio(split), split=split)

    @classmethod
    def from_dict(cls, entry: dict) -> "SplitEvent":
        try:
            date = _dt.date.fromisoformat(str(entry["date"])[:10]).isoformat()
            split = str(entry.get("split", ""))
            ratio = float(entry["ratio"]) if "ratio" in entry else parse_ratio(split)
        except (KeyError, ValueError, TypeError) as exc:
            raise ActionsError(f"malformed stored split {entry!r}") from exc
        return cls(date=date, ratio=ratio, split=split)

    def to_dict(self) -> dict:
        return {"date": self.date, "ratio": self.ratio, "split": self.split}


def as_split_events(splits: Iterable[Any] | None) -> list[SplitEvent]:
    events = []
    for s in splits or ():
        if isinstance(s, SplitEvent):
            events.append(s)
        elif isinstance(s, dict):
            events.append(SplitEvent.from_dict(s))
        else:
            raise ActionsError(f"not a split event: {s!r}")
    return sorted(events, key=lambda e: e.date)


def _stamp(now: _dt.datetime | None) -> str:
    if now is None:
        now = _dt.datetime.now(_dt.timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=_dt.timezone.utc)
    return now.astimezone(_dt.timezone.utc).isoformat()


def safe_symbol(symbol: str) -> str:
    return symbol.replace("/", "_")


class ActionsStore:
    """Per-symbol split and dividend JSON files below a store root."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.base = self.root / "corporate_actions"

    def _path(self, kind: str, symbol: str) -> Path:
        return self.base / kind / f"{safe_symbol(symbol)}.json"

    def splits_path(self, symbol: str) -> Path:
        return self._path("splits", symbol)

    def dividends_path(self, symbol: str) -> Path:
        return self._path("dividends", symbol)

    def _load(self, kind: str, symbol: str) -> dict | None:
        path = self._path(kind, symbol)
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def _save(self, kind: str, symbol: str, exchange: str, items: list, now) -> None:
        path = self._path(kind, symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        envelope = {
            "symbol": symbol,
            "exchange": exchange,
            "last_updated": _stamp(now),
            kind: items,
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(envelope, handle, indent=2)

    def load_splits(self, symbol: str) -> list[SplitEvent]:
        doc = self._load("splits", symbol)
        if not doc:
            return []
        return as_split_events(doc.get("splits", []))

    def save_splits(self, symbol: str, splits: Iterable[Any], exchange: str = "eodhd",
                    now: _dt.datetime | None = None) -> None:
        events = as_split_events(splits)
        self._save("splits", symbol, exchange, [e.to_dict() for e in events], now)

    def load_dividends(self, symbol: str) -> list[dict]:
        doc = self._load("dividends", symbol)
        if not doc:
            return []
        return list(doc.get("dividends", []))

    def save_dividends(self, symbol: str, dividends: Iterable[dict], exchange: str = "eodhd",
                       now: _dt.datetime | None = None) -> None:
        items = sorted((dict(d) for d in dividends), key=lambda d: str(d.get("date", "")))
        self._save("dividends", symbol, exchange, items, now)

    def split_entries(self, symbol: str) -> list[dict]:
        """The split entries exactly as stored."""
        doc = self._load("splits", symbol)
        return list(doc.get("splits", [])) if doc else []

    def last_updated(self, symbol: str) -> str | None:
        """The split file's `last_updated` stamp, or None when absent."""
        doc = self._load("splits", symbol)
        if not doc:
            return None
        stamp = doc.get("last_updated")
        return stamp if stamp else None


def stamp_date(stamp: str | None) -> _dt.date | None:
    """The UTC date of an action-file stamp, or None when absent/unparseable."""
    if not stamp:
        return None
    try:
        parsed = _dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        try:
            return _dt.date.fromisoformat(str(stamp)[:10])
        except ValueError:
            return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(_dt.timezone.utc)
    return parsed.date()


def sync_actions(collector, store_root: str | Path, symbol: str, exchange: str = "eodhd",
                 now: _dt.datetime | None = None) -> tuple[list[SplitEvent], list[dict]]:
    """Fetch splits and dividends for `symbol` and persist both files."""
    splits = collector.get_splits(symbol)
    dividends = collector.get_dividends(symbol)
    store = ActionsStore(store_root)
    store.save_splits(symbol, splits, exchange=exchange, now=now)
    store.save_dividends(symbol, dividends, exchange=exchange, now=now)
    return as_split_events(splits), list(dividends)


def valid_ratio(ratio: float) -> bool:
    return isinstance(ratio, (int, float)) and math.isfinite(ratio) and ratio > 0

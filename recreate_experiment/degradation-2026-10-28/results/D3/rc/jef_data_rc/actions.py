"""The corporate-actions store: one splits and one dividends JSON file per symbol."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path


def parse_split(text: str) -> float:
    """Ratio new/old from a provider split string NEW/OLD."""
    parts = str(text).split("/")
    if len(parts) != 2:
        raise ValueError(f"unparseable split string: {text!r}")
    try:
        new, old = float(parts[0]), float(parts[1])
    except ValueError:
        raise ValueError(f"unparseable split string: {text!r}") from None
    if new == 0 or old == 0:
        raise ValueError(f"degenerate split string: {text!r}")
    return new / old


@dataclass(frozen=True)
class SplitEvent:
    date: date
    ratio: float
    split: str | None = None

    @classmethod
    def from_provider(cls, day: str, text: str) -> "SplitEvent":
        return cls(date=date.fromisoformat(day), ratio=parse_split(text), split=text)

    def to_item(self) -> dict:
        text = self.split if self.split is not None else f"{self.ratio:g}/1"
        return {"date": self.date.isoformat(), "split": text, "ratio": self.ratio}


def utc_stamp() -> str:
    """The real wall-clock UTC time, naive ISO 8601 plus Z."""
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"


def parse_stamp(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


class CorporateActionsStore:
    def __init__(self, store_root):
        self.base_path = Path(store_root) / "corporate_actions"

    def path(self, kind: str, symbol: str) -> Path:
        return self.base_path / kind / (symbol.replace("/", "_") + ".json")

    def _write(self, kind: str, symbol: str, exchange: str, items: list) -> str:
        path = self.path(kind, symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = {"symbol": symbol, "exchange": exchange, "last_updated": utc_stamp(), kind: items}
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(doc, indent=2) + "\n")
        return str(path)

    def _read(self, kind: str, symbol: str):
        path = self.path(kind, symbol)
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def save_splits(self, symbol: str, exchange: str, splits) -> str:
        items = [e.to_item() for e in sorted(splits, key=lambda e: e.date)]
        return self._write("splits", symbol, exchange, items)

    def save_dividends(self, symbol: str, exchange: str, entries) -> str:
        items = sorted(entries, key=lambda e: e.get("date") or "")
        return self._write("dividends", symbol, exchange, items)

    def raw_splits(self, symbol: str) -> list:
        doc = self._read("splits", symbol)
        return [] if doc is None else list(doc.get("splits", []))

    def load_splits(self, symbol: str) -> list:
        return [SplitEvent(date=date.fromisoformat(item["date"]), ratio=float(item["ratio"]),
                           split=item.get("split"))
                for item in self.raw_splits(symbol)]

    def load_dividends(self, symbol: str) -> list:
        doc = self._read("dividends", symbol)
        return [] if doc is None else list(doc.get("dividends", []))

    def stamp_text(self, symbol: str):
        doc = self._read("splits", symbol)
        return None if doc is None else doc.get("last_updated")

    def last_updated(self, symbol: str):
        text = self.stamp_text(symbol)
        return None if text is None else parse_stamp(text)


def sync_actions(collector, actions: CorporateActionsStore, symbol: str) -> tuple:
    """Fetch splits then dividends, write the splits file then the dividends file."""
    splits = collector.get_splits(symbol)
    dividends = collector.get_dividends(symbol)
    actions.save_splits(symbol, "eodhd", splits)
    actions.save_dividends(symbol, "eodhd", dividends)
    return len(splits), len(dividends)

"""The corporate-actions store: one JSON file per symbol and kind."""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from .collectors.eodhd import SplitEvent

KINDS = ("splits", "dividends")


def utc_stamp() -> str:
    """Real wall-clock UTC time, naive ISO 8601 plus Z."""
    now = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    return now.isoformat() + "Z"


def parse_stamp(text):
    if not text:
        return None
    stamp = _dt.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=_dt.timezone.utc)
    return stamp


class CorporateActionsStore:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.root = self.base_path / "corporate_actions"

    def path(self, kind, symbol) -> Path:
        return self.root / kind / (symbol.replace("/", "_") + ".json")

    def _write(self, kind, symbol, exchange, items) -> str:
        path = self.path(kind, symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = {"symbol": symbol, "exchange": exchange, "last_updated": utc_stamp(),
               kind: items}
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(doc, indent=2) + "\n")
        return str(path)

    def _read(self, kind, symbol):
        path = self.path(kind, symbol)
        if not path.is_file():
            return None
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def save_splits(self, symbol, exchange, splits) -> str:
        items = []
        for event in splits:
            text = event.split if event.split is not None else f"{event.ratio:g}/1"
            items.append({"date": event.date.isoformat(), "split": text,
                          "ratio": float(event.ratio)})
        items.sort(key=lambda item: item["date"])
        return self._write("splits", symbol, exchange, items)

    def save_dividends(self, symbol, exchange, entries) -> str:
        return self._write("dividends", symbol, exchange, list(entries))

    def load_splits(self, symbol) -> list:
        doc = self._read("splits", symbol)
        if doc is None:
            return []
        return [SplitEvent(_dt.date.fromisoformat(item["date"]), float(item["ratio"]),
                           item.get("split"))
                for item in doc.get("splits", [])]

    def load_dividends(self, symbol) -> list:
        doc = self._read("dividends", symbol)
        if doc is None:
            return []
        return list(doc.get("dividends", []))

    def last_updated(self, symbol):
        doc = self._read("splits", symbol)
        if doc is None:
            return None
        return parse_stamp(doc.get("last_updated"))

    def raw_state(self, symbol) -> dict:
        splits = self._read("splits", symbol)
        dividends = self._read("dividends", symbol)
        return {"splits": [] if splits is None else splits.get("splits", []),
                "dividends": [] if dividends is None else dividends.get("dividends", []),
                "last_updated": None if splits is None else splits.get("last_updated")}


def sync_actions(collector, store: CorporateActionsStore, symbol):
    """Fetch splits then dividends, write splits then dividends; return the counts."""
    splits = collector.get_splits(symbol)
    dividends = collector.get_dividends(symbol)
    exchange = getattr(collector, "exchange", "eodhd") or "eodhd"
    store.save_splits(symbol, exchange, splits)
    store.save_dividends(symbol, exchange, dividends)
    return len(splits), len(dividends)

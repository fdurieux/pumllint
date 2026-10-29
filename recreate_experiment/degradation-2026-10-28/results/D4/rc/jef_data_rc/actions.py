"""The corporate-actions store (splits and dividends per symbol, JSON)."""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from .adjust import SplitEvent

ACTIONS_EXCHANGE = "eodhd"


def utc_stamp() -> str:
    now = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    return now.isoformat() + "Z"


def parse_stamp(text: str) -> _dt.datetime:
    return _dt.datetime.fromisoformat(text.replace("Z", "+00:00"))


class CorporateActionsStore:
    def __init__(self, base_path):
        self.base_path = Path(base_path)

    def path(self, kind: str, symbol: str) -> Path:
        return self.base_path / "corporate_actions" / kind / (symbol.replace("/", "_") + ".json")

    def _write(self, kind: str, symbol: str, exchange: str, items: list) -> str:
        path = self.path(kind, symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = {"symbol": symbol, "exchange": exchange, "last_updated": utc_stamp(), kind: items}
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(doc, indent=2) + "\n")
        return str(path)

    def read_document(self, kind: str, symbol: str):
        path = self.path(kind, symbol)
        if not path.is_file():
            return None
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def save_splits(self, symbol: str, exchange: str, splits) -> str:
        items = []
        for event in sorted(splits, key=lambda e: e.date):
            text = event.split_string if event.split_string is not None else f"{float(event.ratio):g}/1"
            items.append({"date": str(event.date), "split": text, "ratio": float(event.ratio)})
        return self._write("splits", symbol, exchange, items)

    def save_dividends(self, symbol: str, exchange: str, entries) -> str:
        items = sorted(entries, key=lambda e: e.get("date") or "")
        return self._write("dividends", symbol, exchange, items)

    def load_splits(self, symbol: str) -> list:
        doc = self.read_document("splits", symbol)
        if doc is None:
            return []
        return [SplitEvent(item["date"], float(item["ratio"]), item.get("split"))
                for item in doc.get("splits", [])]

    def load_dividends(self, symbol: str) -> list:
        doc = self.read_document("dividends", symbol)
        if doc is None:
            return []
        return list(doc.get("dividends", []))

    def last_updated(self, symbol: str):
        doc = self.read_document("splits", symbol)
        if doc is None or not doc.get("last_updated"):
            return None
        return parse_stamp(doc["last_updated"])


def sync_actions(collector, store: CorporateActionsStore, symbol: str) -> tuple:
    splits = collector.get_splits(symbol)
    dividends = collector.get_dividends(symbol)
    store.save_splits(symbol, ACTIONS_EXCHANGE, splits)
    store.save_dividends(symbol, ACTIONS_EXCHANGE, dividends)
    return len(splits), len(dividends)

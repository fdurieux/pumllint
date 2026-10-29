"""The corporate-actions store (splits and dividends per symbol) and its sync."""
import datetime as _dt
import json
from pathlib import Path

from .collectors.eodhd import SplitEvent


def _stamp():
    return _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None).isoformat() + "Z"


def parse_stamp(text):
    if text is None:
        return None
    return _dt.datetime.fromisoformat(str(text).replace("Z", "+00:00"))


class CorporateActionsStore:
    def __init__(self, base_path):
        self.base_path = Path(base_path)

    def path(self, kind, symbol):
        return self.base_path / "corporate_actions" / kind / (symbol.replace("/", "_") + ".json")

    def _write(self, kind, symbol, exchange, items):
        path = self.path(kind, symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = {"symbol": symbol, "exchange": exchange, "last_updated": _stamp(), kind: items}
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(doc, indent=2) + "\n")
        return str(path)

    def read(self, kind, symbol):
        path = self.path(kind, symbol)
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def save_splits(self, symbol, exchange, splits):
        items = []
        for event in sorted(splits, key=lambda e: e.date):
            text = event.split if event.split else f"{event.ratio:g}/1"
            items.append({"date": event.date.isoformat(), "split": text, "ratio": float(event.ratio)})
        return self._write("splits", symbol, exchange, items)

    def save_dividends(self, symbol, exchange, entries):
        ordered = sorted(entries, key=lambda e: e.get("date", "") if isinstance(e, dict) else "")
        return self._write("dividends", symbol, exchange, ordered)

    def load_splits(self, symbol):
        doc = self.read("splits", symbol)
        if not doc:
            return []
        return [SplitEvent(item["date"], item["ratio"], item.get("split"))
                for item in doc.get("splits", [])]

    def load_dividends(self, symbol):
        doc = self.read("dividends", symbol)
        if not doc:
            return []
        return list(doc.get("dividends", []))

    def last_updated(self, symbol):
        doc = self.read("splits", symbol)
        if not doc:
            return None
        return parse_stamp(doc.get("last_updated"))


def sync_actions(collector, actions_store, symbol):
    """Fetch splits then dividends, write splits then dividends; returns the two counts."""
    splits = collector.get_splits(symbol)
    dividends = collector.get_dividends(symbol)
    exchange = collector.exchange or "eodhd"
    actions_store.save_splits(symbol, exchange, splits)
    actions_store.save_dividends(symbol, exchange, dividends)
    return len(splits), len(dividends)

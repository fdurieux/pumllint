"""The corporate-actions store (splits and dividends per symbol) and the actions sync."""
import json
from datetime import date, datetime, timezone
from pathlib import Path

from .collectors.eodhd import SplitEvent


def _stamp():
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return now.isoformat() + "Z"


def parse_stamp(text):
    if text is None:
        return None
    stamp = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc)


class CorporateActionsStore:
    """JSON files under {store}/corporate_actions/{splits,dividends}/{SYMBOL}.json."""

    def __init__(self, store_root):
        self.base_path = Path(str(store_root)) / "corporate_actions"

    def path(self, kind, symbol):
        return self.base_path / kind / (symbol.replace("/", "_") + ".json")

    def _write(self, kind, symbol, exchange, items):
        path = self.path(kind, symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = {"symbol": symbol, "exchange": exchange, "last_updated": _stamp(), kind: items}
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(doc, indent=2) + "\n")
        return str(path)

    def _read(self, kind, symbol):
        path = self.path(kind, symbol)
        if not path.is_file():
            return None
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def save_splits(self, symbol, exchange, splits):
        items = []
        for event in sorted(splits, key=lambda event: event.date):
            text = event.split_string if event.split_string is not None else f"{event.ratio:g}/1"
            items.append({"date": event.date.isoformat(), "split": text,
                          "ratio": float(event.ratio)})
        return self._write("splits", symbol, exchange, items)

    def save_dividends(self, symbol, exchange, entries):
        items = sorted(entries, key=lambda entry: entry.get("date", ""))
        return self._write("dividends", symbol, exchange, items)

    def raw_splits(self, symbol):
        doc = self._read("splits", symbol)
        return [] if doc is None else list(doc.get("splits", []))

    def load_splits(self, symbol):
        return [SplitEvent(date.fromisoformat(item["date"]), float(item["ratio"]),
                           item.get("split")) for item in self.raw_splits(symbol)]

    def load_dividends(self, symbol):
        doc = self._read("dividends", symbol)
        return [] if doc is None else list(doc.get("dividends", []))

    def stamp_text(self, symbol):
        doc = self._read("splits", symbol)
        return None if doc is None else doc.get("last_updated")

    def last_updated(self, symbol):
        return parse_stamp(self.stamp_text(symbol))


def sync_actions(collector, store, symbol):
    """Fetch splits then dividends, write splits then dividends; returns the two counts."""
    splits = collector.get_splits(symbol)
    dividends = collector.get_dividends(symbol)
    store.save_splits(symbol, "eodhd", splits)
    store.save_dividends(symbol, "eodhd", dividends)
    return len(splits), len(dividends)

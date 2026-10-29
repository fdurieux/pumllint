"""The corporate-actions store (splits and dividends per symbol) and its sync."""
import json
from datetime import datetime, timezone
from pathlib import Path

from jef_data_rc.collectors.eodhd import SplitEvent


def utc_stamp():
    """The real wall-clock UTC time as naive ISO 8601 plus Z."""
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"


def parse_stamp(text):
    moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


class CorporateActionsStore:
    """{root}/corporate_actions/{splits,dividends}/{SYMBOL}.json"""

    def __init__(self, root):
        self.base_path = Path(root) / "corporate_actions"

    def path(self, kind, symbol):
        return self.base_path / kind / (symbol.replace("/", "_") + ".json")

    def _write(self, kind, symbol, exchange, items):
        path = self.path(kind, symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = {"symbol": symbol, "exchange": exchange, "last_updated": utc_stamp(), kind: items}
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(doc, indent=2) + "\n")
        return str(path)

    def _read(self, kind, symbol):
        path = self.path(kind, symbol)
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def save_splits(self, symbol, exchange, splits):
        items = []
        for event in splits:
            ratio = float(event.ratio)
            text = event.split if event.split else f"{ratio:g}/1"
            items.append({"date": event.date, "split": text, "ratio": ratio})
        items.sort(key=lambda item: item["date"])
        return self._write("splits", symbol, exchange, items)

    def save_dividends(self, symbol, exchange, entries):
        return self._write("dividends", symbol, exchange, list(entries))

    def load_splits(self, symbol):
        doc = self._read("splits", symbol)
        if doc is None:
            return []
        return [SplitEvent(date=item["date"], ratio=item["ratio"], split=item.get("split", ""))
                for item in doc.get("splits", [])]

    def load_dividends(self, symbol):
        doc = self._read("dividends", symbol)
        return [] if doc is None else list(doc.get("dividends", []))

    def raw_splits(self, symbol):
        doc = self._read("splits", symbol)
        return [] if doc is None else list(doc.get("splits", []))

    def stamp_text(self, symbol):
        doc = self._read("splits", symbol)
        return None if doc is None else doc.get("last_updated")

    def last_updated(self, symbol):
        text = self.stamp_text(symbol)
        return None if text is None else parse_stamp(text)


def sync_actions(collector, store, symbol):
    """Fetch splits then dividends, write the splits file then the dividends file."""
    splits = collector.get_splits(symbol)
    dividends = collector.get_dividends(symbol)
    store.save_splits(symbol, "eodhd", splits)
    store.save_dividends(symbol, "eodhd", dividends)
    return len(splits), len(dividends)

"""The corporate-actions store: one JSON file per symbol and kind."""
import datetime as _dt
import json
from pathlib import Path

from .collectors import SplitEvent

KINDS = ("splits", "dividends")


def _path(store, kind, symbol):
    return Path(store) / "corporate_actions" / kind / (symbol.replace("/", "_") + ".json")


def wall_clock_stamp():
    """Real wall-clock UTC time, naive ISO 8601 plus Z."""
    now = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    return now.isoformat() + "Z"


def _write(store, kind, symbol, items, exchange="eodhd"):
    path = _path(store, kind, symbol)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"symbol": symbol, "exchange": exchange, "last_updated": wall_clock_stamp(),
           kind: items}
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(doc, indent=2) + "\n")


def _split_item(event):
    split = event.split if event.split else f"{event.ratio:g}/1"
    return {"date": event.date, "split": split, "ratio": event.ratio}


def write_splits(store, symbol, events):
    items = sorted((_split_item(e) for e in events), key=lambda item: item["date"])
    _write(store, "splits", symbol, items)


def write_dividends(store, symbol, dividends):
    _write(store, "dividends", symbol, list(dividends))


def sync_actions(collector, store, symbol):
    """Fetch splits then dividends, write splits then dividends; return the counts."""
    splits = collector.splits(symbol)
    dividends = collector.dividends(symbol)
    write_splits(store, symbol, splits)
    write_dividends(store, symbol, dividends)
    return len(splits), len(dividends)


def _read(store, kind, symbol):
    path = _path(store, kind, symbol)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def read_splits(store, symbol):
    doc = _read(store, "splits", symbol)
    if doc is None:
        return []
    return [SplitEvent(item["date"], item["ratio"], item.get("split"))
            for item in doc.get("splits") or []]


def read_dividends(store, symbol):
    doc = _read(store, "dividends", symbol)
    if doc is None:
        return []
    return list(doc.get("dividends") or [])


def read_stamp_text(store, symbol):
    doc = _read(store, "splits", symbol)
    if doc is None:
        return None
    return doc.get("last_updated")


def parse_stamp(text):
    moment = _dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=_dt.timezone.utc)
    return moment.astimezone(_dt.timezone.utc)


def stamp_date(store, symbol):
    """UTC calendar date of the splits file's stamp, or None."""
    text = read_stamp_text(store, symbol)
    if text is None:
        return None
    return parse_stamp(text).date()


def state(store, symbol):
    splits = _read(store, "splits", symbol)
    dividends = _read(store, "dividends", symbol)
    return {"splits": list((splits or {}).get("splits") or []),
            "dividends": list((dividends or {}).get("dividends") or []),
            "last_updated": None if splits is None else splits.get("last_updated")}

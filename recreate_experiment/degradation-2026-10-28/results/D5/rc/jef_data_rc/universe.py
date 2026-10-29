"""The declarative universe: strict loader and normaliser of universe.toml."""
from __future__ import annotations

import datetime as _dt
import tomllib
from importlib import resources
from pathlib import Path

PROVIDERS = ("eodhd", "binance", "yahoo-csv")
COLLECTOR_PROVIDERS = ("eodhd", "binance")
ASSET_TYPE_BY_CLASS = {"stock": "stock", "crypto": "crypto", "bond_etf": "etf"}
ASSET_TYPES = sorted(set(ASSET_TYPE_BY_CLASS.values()))
EXCHANGE_BY_PROVIDER = {"eodhd": "eodhd", "binance": "binance", "yahoo-csv": "yahoo"}
KINDS = ["eod"]

TOP_KEYS = ("asset", "defaults")
DEFAULT_KEYS = ("currency", "store")
ASSET_KEYS = ("asset_class", "currency", "enabled", "name", "source", "threshold")
SOURCE_KEYS = ("enabled", "end", "exchange", "kind", "modeled", "note", "path",
               "provider", "start", "symbol")

DEFAULT_STORE = "data"
DEFAULT_CURRENCY = "USD"
DEFAULT_THRESHOLD = -0.05

PACKAGED_ORIGIN = "packaged universe.toml"


class UniverseError(ValueError):
    """A universe document that violates the grammar."""


class DeclarationRefused(ValueError):
    """A hand-run declaration that cannot be trusted."""


def packaged_text() -> str:
    return resources.files(__package__).joinpath("universe.toml").read_text(encoding="utf-8")


def _unknown(table, allowed, where):
    unknown = sorted(k for k in table if k not in allowed)
    if unknown:
        raise UniverseError(
            f"{where}: unknown key(s) {unknown}; allowed: {sorted(allowed)}")


def _string(table, key, where, *, required=False):
    if key not in table:
        if required:
            raise UniverseError(f"{where}: missing required key '{key}'")
        return None
    value = table[key]
    if not isinstance(value, str) or not value:
        raise UniverseError(f"{where}: {key} must be a non-empty string, got {value!r}")
    return value


def _boolean(table, key, where, default):
    if key not in table:
        return default
    value = table[key]
    if not isinstance(value, bool):
        raise UniverseError(f"{where}: {key} must be a boolean, got {value!r}")
    return value


def _iso_date(table, key, where):
    if key not in table:
        return None
    value = table[key]
    if isinstance(value, _dt.datetime):
        return value.isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            return _dt.date.fromisoformat(value).isoformat()
        except ValueError:
            pass
    raise UniverseError(f"{where}: {key} must be an ISO date (YYYY-MM-DD), got {value!r}")


def _parse_source(src, n, asset_name, currency):
    where = f"asset '{asset_name}' source #{n}"
    if not isinstance(src, dict):
        raise UniverseError(f"{where}: must be a table")
    _unknown(src, SOURCE_KEYS, where)
    provider = _string(src, "provider", where, required=True)
    if provider not in PROVIDERS:
        raise UniverseError(
            f"{where}: unknown provider {provider!r}; allowed: {list(PROVIDERS)}")
    kind = src.get("kind", "eod")
    if kind not in KINDS:
        raise UniverseError(
            f"{where}: kind {kind!r} is not supported - only {KINDS}; "
            "a non-EOD load is a new data contract, not a config value")
    symbol = _string(src, "symbol", where, required=True)
    if provider == "eodhd" and "." not in symbol:
        raise UniverseError(
            f"{where}: eodhd symbols must be canonical TICKER.EXCHANGE "
            f"(e.g. AAPL.US, BTC-USD.CC), got {symbol!r} - bare tickers would "
            "blur store coordinates and the crypto/raw basis split")
    if "modeled" in src and not isinstance(src["modeled"], bool):
        raise UniverseError(f"{where}: modeled must be a boolean, got {src['modeled']!r}")
    modeled = src.get("modeled", False)
    enabled = _boolean(src, "enabled", where, True)
    exchange = _string(src, "exchange", where)
    if exchange is None:
        exchange = EXCHANGE_BY_PROVIDER[provider]
    note = _string(src, "note", where)
    path = _string(src, "path", where, required=(provider == "yahoo-csv"))
    start = _iso_date(src, "start", where)
    end = _iso_date(src, "end", where)
    if provider == "yahoo-csv":
        if "start" in src or "end" in src:
            raise UniverseError(
                f"{where}: start/end apply to collector sources only; "
                "a CSV import is whole-file")
    elif "path" in src:
        raise UniverseError(f"{where}: path applies to yahoo-csv sources only")
    if start is not None and end is not None and start > end:
        raise UniverseError(f"{where}: start {start} is after end {end}")
    out = {"provider": provider, "kind": kind, "enabled": enabled, "modeled": modeled,
           "exchange": exchange, "symbol": symbol, "currency": currency}
    if note is not None:
        out["note"] = note
    if provider == "yahoo-csv":
        out["path"] = path
    else:
        out["start"] = start
        out["end"] = end
    return out


def _parse_asset(entry, n, default_currency):
    if not isinstance(entry, dict):
        raise UniverseError(f"asset #{n}: must be a table")
    _unknown(entry, ASSET_KEYS, f"asset #{n}")
    name = _string(entry, "name", f"asset #{n}", required=True)
    where = f"asset '{name}'"
    asset_class = _string(entry, "asset_class", where, required=True)
    if asset_class not in ASSET_TYPE_BY_CLASS:
        raise UniverseError(
            f"{where}: unknown asset_class {asset_class!r}; "
            f"allowed: {sorted(ASSET_TYPE_BY_CLASS)}")
    threshold = DEFAULT_THRESHOLD
    if "threshold" in entry:
        value = entry["threshold"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise UniverseError(
                f"{where}: threshold must be a number (documentation only), got {value!r}")
        threshold = float(value)
    currency = _string(entry, "currency", where)
    if currency is None:
        currency = default_currency
    sources = entry.get("source")
    if not isinstance(sources, list) or not sources:
        raise UniverseError(f"{where}: needs at least one [[asset.source]]")
    enabled = _boolean(entry, "enabled", where, True)
    parsed = [_parse_source(src, i, name, currency) for i, src in enumerate(sources, 1)]

    if any(s["modeled"] and not s["enabled"] for s in parsed):
        raise UniverseError(f"{where}: a modeled source must be enabled")
    live = [s for s in parsed if s["enabled"]]
    modeled = sum(1 for s in live if s["modeled"])
    if modeled > 1:
        raise UniverseError(
            f"{where}: exactly one enabled source may be modeled = true, got {modeled}")
    if enabled:
        if len(live) >= 2 and modeled == 0:
            raise UniverseError(
                f"{where}: {len(live)} enabled sources but none marked modeled = true - "
                "the binning's feeder must be deterministic (docs/DATA_CONTRACT.md SS7.7)")
        if not live:
            raise UniverseError(
                f"{where}: enabled but has no enabled source - nothing would feed the "
                "binning; to pause the asset, set enabled = false on the asset itself")
    return {"name": name, "asset_class": asset_class,
            "asset_type": ASSET_TYPE_BY_CLASS[asset_class], "currency": currency,
            "threshold": threshold, "enabled": enabled, "sources": parsed}


def parse_universe(text: str, origin: str) -> dict:
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise UniverseError(f"{origin}: not valid TOML: {exc}") from None
    _unknown(doc, TOP_KEYS, origin)
    defaults = doc.get("defaults", {})
    if not isinstance(defaults, dict):
        raise UniverseError(f"{origin}: [defaults] must be a table")
    _unknown(defaults, DEFAULT_KEYS, f"{origin} [defaults]")
    store = _string(defaults, "store", "[defaults]")
    currency = _string(defaults, "currency", "[defaults]")
    resolved = {"store": DEFAULT_STORE if store is None else store,
                "currency": DEFAULT_CURRENCY if currency is None else currency}
    entries = doc.get("asset")
    if not isinstance(entries, list) or not entries:
        raise UniverseError(f"{origin}: no [[asset]] entries")
    assets = [_parse_asset(entry, i, resolved["currency"])
              for i, entry in enumerate(entries, 1)]

    names = [a["name"] for a in assets]
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        raise UniverseError(f"{origin}: duplicate asset name(s) {dupes}")
    owners = {}
    for asset in assets:
        for src in asset["sources"]:
            coord = (src["exchange"], src["symbol"])
            owner = owners.setdefault(coord, asset["name"])
            if owner != asset["name"]:
                raise UniverseError(
                    f"{origin}: store series {coord[0]}/{coord[1]} is claimed by both "
                    f"{owner!r} and {asset['name']!r} - two assets may never write the "
                    "same partition")
    return {"defaults": resolved, "assets": assets}


def load_universe(path=None) -> dict:
    """Load and normalise a universe file; None reads the packaged one."""
    if path is None:
        return parse_universe(packaged_text(), PACKAGED_ORIGIN)
    text = Path(path).read_text(encoding="utf-8")
    return parse_universe(text, str(path))


def listing(universe: dict) -> list[str]:
    lines = []
    for asset in universe["assets"]:
        lines.append(f"{asset['name']} ({asset['asset_class']}, {asset['currency']}, "
                     f"threshold {asset['threshold']})")
        for src in asset["sources"]:
            target = src["path"] if src["provider"] == "yahoo-csv" else src["symbol"]
            line = f"  {src['provider']}: {target}"
            if not src["enabled"]:
                line += " [disabled]"
            if src.get("note"):
                line += f" - {src['note']}"
            lines.append(line)
    return lines

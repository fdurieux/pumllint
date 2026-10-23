"""The declarative universe: strict loader and normaliser."""
from __future__ import annotations

import datetime as _dt
import tomllib
from importlib import resources

PACKAGED_ORIGIN = "packaged universe.toml"

ASSET_TYPE_BY_CLASS = {"stock": "stock", "crypto": "crypto", "bond_etf": "etf"}
ASSET_TYPES = sorted(set(ASSET_TYPE_BY_CLASS.values()))
PROVIDERS = ["eodhd", "binance", "yahoo-csv"]
DEFAULT_EXCHANGE = {"eodhd": "eodhd", "binance": "binance", "yahoo-csv": "yahoo"}
KINDS = ["eod"]
COLLECTOR_PROVIDERS = ("eodhd", "binance")

TOP_KEYS = ["asset", "defaults"]
DEFAULTS_KEYS = ["currency", "store"]
ASSET_KEYS = ["asset_class", "currency", "enabled", "name", "source", "threshold"]
SOURCE_KEYS = ["enabled", "end", "exchange", "kind", "modeled", "note", "path",
               "provider", "start", "symbol"]

DEFAULT_STORE = "data"
DEFAULT_CURRENCY = "USD"
DEFAULT_THRESHOLD = -0.05


class UniverseError(ValueError):
    """A universe document that violates the grammar."""


def _unknown_keys(where, table, allowed):
    unknown = sorted(k for k in table if k not in allowed)
    if unknown:
        raise UniverseError(
            f"{where}: unknown key(s) {unknown}; allowed: {sorted(allowed)}")


def _non_empty_string(where, key, value):
    if not isinstance(value, str) or not value:
        raise UniverseError(f"{where}: {key} must be a non-empty string, got {value!r}")
    return value


def _required_string(where, table, key):
    if key not in table:
        raise UniverseError(f"{where}: missing required key '{key}'")
    return _non_empty_string(where, key, table[key])


def _boolean(where, key, value):
    if not isinstance(value, bool):
        raise UniverseError(f"{where}: {key} must be a boolean, got {value!r}")
    return value


def _iso_date(where, key, value):
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


def _read(path):
    if path is None:
        text = resources.files(__package__).joinpath("universe.toml").read_text(
            encoding="utf-8")
        return text, PACKAGED_ORIGIN
    with open(path, "rb") as handle:
        raw = handle.read()
    return raw.decode("utf-8"), str(path)


def load_universe(path=None):
    """Read, validate and normalise a universe file (packaged one when path is None)."""
    text, origin = _read(path)
    return parse_universe(text, origin)


def parse_universe(text, origin):
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise UniverseError(f"{origin}: not valid TOML: {exc}") from None

    _unknown_keys(origin, doc, TOP_KEYS)

    defaults_table = doc.get("defaults", {})
    if not isinstance(defaults_table, dict):
        raise UniverseError(f"{origin}: [defaults] must be a table")
    _unknown_keys(f"{origin} [defaults]", defaults_table, DEFAULTS_KEYS)
    store = DEFAULT_STORE
    if "store" in defaults_table:
        store = _non_empty_string("[defaults]", "store", defaults_table["store"])
    currency = DEFAULT_CURRENCY
    if "currency" in defaults_table:
        currency = _non_empty_string("[defaults]", "currency", defaults_table["currency"])
    defaults = {"store": store, "currency": currency}

    raw_assets = doc.get("asset")
    if not isinstance(raw_assets, list) or not raw_assets:
        raise UniverseError(f"{origin}: no [[asset]] entries")

    assets = [_asset(n, table, defaults) for n, table in enumerate(raw_assets, start=1)]

    names = [a["name"] for a in assets]
    dupes = sorted({name for name in names if names.count(name) > 1})
    if dupes:
        raise UniverseError(f"{origin}: duplicate asset name(s) {dupes}")

    owners = {}
    for asset in assets:
        for source in asset["sources"]:
            coord = (source["exchange"], source["symbol"])
            owner = owners.setdefault(coord, asset["name"])
            if owner != asset["name"]:
                raise UniverseError(
                    f"{origin}: store series {coord[0]}/{coord[1]} is claimed by both "
                    f"{owner!r} and {asset['name']!r} - two assets may never write the "
                    f"same partition")

    return {"defaults": defaults, "assets": assets}


def _asset(n, table, defaults):
    if not isinstance(table, dict):
        raise UniverseError(f"asset #{n}: must be a table")
    _unknown_keys(f"asset #{n}", table, ASSET_KEYS)
    name = _required_string(f"asset #{n}", table, "name")
    where = f"asset '{name}'"

    asset_class = _required_string(where, table, "asset_class")
    if asset_class not in ASSET_TYPE_BY_CLASS:
        raise UniverseError(
            f"{where}: unknown asset_class {asset_class!r}; allowed: "
            f"{sorted(ASSET_TYPE_BY_CLASS)}")

    threshold = DEFAULT_THRESHOLD
    if "threshold" in table:
        value = table["threshold"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise UniverseError(
                f"{where}: threshold must be a number (documentation only), got {value!r}")
        threshold = float(value)

    currency = defaults["currency"]
    if "currency" in table:
        currency = _non_empty_string(where, "currency", table["currency"])

    raw_sources = table.get("source")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise UniverseError(f"{where}: needs at least one [[asset.source]]")

    enabled = True
    if "enabled" in table:
        enabled = _boolean(where, "enabled", table["enabled"])

    sources = [_source(name, m, src, currency)
               for m, src in enumerate(raw_sources, start=1)]

    if any(s["modeled"] and not s["enabled"] for s in sources):
        raise UniverseError(f"{where}: a modeled source must be enabled")
    live = [s for s in sources if s["enabled"]]
    modeled = sum(1 for s in live if s["modeled"])
    if modeled > 1:
        raise UniverseError(
            f"{where}: exactly one enabled source may be modeled = true, got {modeled}")
    if enabled:
        if len(live) >= 2 and modeled == 0:
            raise UniverseError(
                f"{where}: {len(live)} enabled sources but none marked modeled = true - "
                f"the binning's feeder must be deterministic (docs/DATA_CONTRACT.md SS7.7)")
        if not live:
            raise UniverseError(
                f"{where}: enabled but has no enabled source - nothing would feed the "
                f"binning; to pause the asset, set enabled = false on the asset itself")

    return {"name": name, "asset_class": asset_class,
            "asset_type": ASSET_TYPE_BY_CLASS[asset_class], "currency": currency,
            "threshold": threshold, "enabled": enabled, "sources": sources}


def _source(asset_name, m, table, currency):
    where = f"asset '{asset_name}' source #{m}"
    if not isinstance(table, dict):
        raise UniverseError(f"{where}: must be a table")
    _unknown_keys(where, table, SOURCE_KEYS)

    provider = _required_string(where, table, "provider")
    if provider not in PROVIDERS:
        raise UniverseError(f"{where}: unknown provider {provider!r}; allowed: {PROVIDERS}")

    kind = table.get("kind", "eod")
    if kind not in KINDS or not isinstance(kind, str):
        raise UniverseError(
            f"{where}: kind {kind!r} is not supported - only {KINDS}; a non-EOD load is "
            f"a new data contract, not a config value")

    symbol = _required_string(where, table, "symbol")
    if provider == "eodhd" and "." not in symbol:
        raise UniverseError(
            f"{where}: eodhd symbols must be canonical TICKER.EXCHANGE (e.g. AAPL.US, "
            f"BTC-USD.CC), got {symbol!r} - bare tickers would blur store coordinates and "
            f"the crypto/raw basis split")

    modeled = False
    if "modeled" in table:
        value = table["modeled"]
        if not isinstance(value, bool):
            raise UniverseError(f"{where}: modeled must be a boolean, got {value!r}")
        modeled = value

    enabled = True
    if "enabled" in table:
        enabled = _boolean(where, "enabled", table["enabled"])

    exchange = DEFAULT_EXCHANGE[provider]
    if "exchange" in table:
        exchange = _non_empty_string(where, "exchange", table["exchange"])

    note = None
    if "note" in table:
        note = _non_empty_string(where, "note", table["note"])

    path = None
    if "path" in table:
        path = _non_empty_string(where, "path", table["path"])
    elif provider == "yahoo-csv":
        raise UniverseError(f"{where}: missing required key 'path'")

    start = _iso_date(where, "start", table["start"]) if "start" in table else None
    end = _iso_date(where, "end", table["end"]) if "end" in table else None

    if provider == "yahoo-csv":
        if "start" in table or "end" in table:
            raise UniverseError(
                f"{where}: start/end apply to collector sources only; a CSV import is "
                f"whole-file")
    elif "path" in table:
        raise UniverseError(f"{where}: path applies to yahoo-csv sources only")

    if start is not None and end is not None and start > end:
        raise UniverseError(f"{where}: start {start} is after end {end}")

    source = {"provider": provider, "kind": kind, "enabled": enabled, "modeled": modeled,
              "exchange": exchange, "symbol": symbol, "currency": currency}
    if note is not None:
        source["note"] = note
    if provider == "yahoo-csv":
        source["path"] = path
    else:
        source["start"] = start
        source["end"] = end
    return source


def listing_lines(universe):
    """The `universe` command's listing."""
    lines = []
    for asset in universe["assets"]:
        line = (f"{asset['name']} ({asset['asset_class']}, {asset['currency']}, "
                f"threshold {asset['threshold']})")
        if not asset["enabled"]:
            line += " [disabled]"
        lines.append(line)
        for source in asset["sources"]:
            target = source["path"] if source["provider"] == "yahoo-csv" else source["symbol"]
            line = f"  {source['provider']}: {target}"
            if not source["enabled"]:
                line += " [disabled]"
            if "note" in source:
                line += f" - {source['note']}"
            lines.append(line)
    return lines

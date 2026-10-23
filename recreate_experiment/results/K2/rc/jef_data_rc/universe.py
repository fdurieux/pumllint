"""The declarative asset universe: strict TOML parsing into one normalised document."""
from __future__ import annotations

import datetime as _dt
import tomllib
from importlib import resources

PROVIDERS = ["eodhd", "binance", "yahoo-csv"]
COLLECTOR_PROVIDERS = ("eodhd", "binance")
ASSET_TYPE_BY_CLASS = {"stock": "stock", "crypto": "crypto", "bond_etf": "etf"}
ASSET_CLASSES = sorted(ASSET_TYPE_BY_CLASS)
ASSET_TYPES = sorted(set(ASSET_TYPE_BY_CLASS.values()))
DEFAULT_EXCHANGE = {"eodhd": "eodhd", "binance": "binance", "yahoo-csv": "yahoo"}
KINDS = ["eod"]
DEFAULT_THRESHOLD = -0.05

TOP_KEYS = ["asset", "defaults"]
DEFAULTS_KEYS = ["currency", "store"]
ASSET_KEYS = ["asset_class", "currency", "enabled", "name", "source", "threshold"]
SOURCE_KEYS = ["enabled", "end", "exchange", "kind", "modeled", "note", "path",
               "provider", "start", "symbol"]

PACKAGED_LABEL = "packaged universe.toml"


class UniverseError(ValueError):
    """A universe file that violates the grammar."""


def _unknown_keys(where, table, allowed):
    unknown = sorted(k for k in table if k not in allowed)
    if unknown:
        raise UniverseError(f"{where}: unknown key(s) {unknown}; allowed: {sorted(allowed)}")


def _non_empty_string(where, key, value):
    if not isinstance(value, str) or value == "":
        raise UniverseError(f"{where}: {key} must be a non-empty string, got {value!r}")
    return value


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


def packaged_text():
    return resources.files(__package__).joinpath("universe.toml").read_text(encoding="utf-8")


def load_universe(path=None):
    """Parse a universe file (the packaged one when `path` is None)."""
    if path is None:
        text = packaged_text()
        origin = PACKAGED_LABEL
    else:
        with open(path, "rb") as handle:
            raw = handle.read()
        text = raw.decode("utf-8")
        origin = str(path)
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
    store = "data"
    currency_default = "USD"
    if "store" in defaults_table:
        store = _non_empty_string("[defaults]", "store", defaults_table["store"])
    if "currency" in defaults_table:
        currency_default = _non_empty_string("[defaults]", "currency", defaults_table["currency"])
    defaults = {"store": store, "currency": currency_default}

    asset_list = doc.get("asset")
    if not isinstance(asset_list, list) or not asset_list:
        raise UniverseError(f"{origin}: no [[asset]] entries")

    assets = []
    for n, entry in enumerate(asset_list, start=1):
        assets.append(_parse_asset(n, entry, defaults))

    names = [a["name"] for a in assets]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise UniverseError(f"{origin}: duplicate asset name(s) {duplicates}")

    owners = {}
    for asset in assets:
        for source in asset["sources"]:
            coordinate = (source["exchange"], source["symbol"])
            owner = owners.get(coordinate)
            if owner is None:
                owners[coordinate] = asset["name"]
            elif owner != asset["name"]:
                raise UniverseError(
                    f"{origin}: store series {coordinate[0]}/{coordinate[1]} is claimed by "
                    f"both {owner!r} and {asset['name']!r} - two assets may never write the "
                    f"same partition")

    return {"defaults": defaults, "assets": assets}


def _parse_asset(n, entry, defaults):
    if not isinstance(entry, dict):
        raise UniverseError(f"asset #{n}: must be a table")
    _unknown_keys(f"asset #{n}", entry, ASSET_KEYS)
    if "name" not in entry:
        raise UniverseError(f"asset #{n}: missing required key 'name'")
    name = _non_empty_string(f"asset #{n}", "name", entry["name"])
    where = f"asset '{name}'"

    if "asset_class" not in entry:
        raise UniverseError(f"{where}: missing required key 'asset_class'")
    asset_class = _non_empty_string(where, "asset_class", entry["asset_class"])
    if asset_class not in ASSET_TYPE_BY_CLASS:
        raise UniverseError(
            f"{where}: unknown asset_class {asset_class!r}; allowed: {ASSET_CLASSES}")

    threshold = DEFAULT_THRESHOLD
    if "threshold" in entry:
        value = entry["threshold"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise UniverseError(
                f"{where}: threshold must be a number (documentation only), got {value!r}")
        threshold = float(value)

    currency = defaults["currency"]
    if "currency" in entry:
        currency = _non_empty_string(where, "currency", entry["currency"])

    source_list = entry.get("source")
    if not isinstance(source_list, list) or not source_list:
        raise UniverseError(f"{where}: needs at least one [[asset.source]]")

    enabled = True
    if "enabled" in entry:
        enabled = _boolean(where, "enabled", entry["enabled"])

    sources = []
    for m, src in enumerate(source_list, start=1):
        sources.append(_parse_source(name, m, src, currency))

    for src in sources:
        if src["modeled"] and not src["enabled"]:
            raise UniverseError(f"{where}: a modeled source must be enabled")
    enabled_sources = [s for s in sources if s["enabled"]]
    modeled = [s for s in enabled_sources if s["modeled"]]
    if len(modeled) > 1:
        raise UniverseError(
            f"{where}: exactly one enabled source may be modeled = true, got {len(modeled)}")
    if enabled:
        if len(enabled_sources) >= 2 and not modeled:
            raise UniverseError(
                f"{where}: {len(enabled_sources)} enabled sources but none marked modeled = "
                f"true - the binning's feeder must be deterministic (docs/DATA_CONTRACT.md SS7.7)")
        if not enabled_sources:
            raise UniverseError(
                f"{where}: enabled but has no enabled source - nothing would feed the binning; "
                f"to pause the asset, set enabled = false on the asset itself")

    return {"name": name, "asset_class": asset_class,
            "asset_type": ASSET_TYPE_BY_CLASS[asset_class], "currency": currency,
            "threshold": threshold, "enabled": enabled, "sources": sources}


def _parse_source(asset_name, m, src, currency):
    where = f"asset '{asset_name}' source #{m}"
    if not isinstance(src, dict):
        raise UniverseError(f"{where}: must be a table")
    _unknown_keys(where, src, SOURCE_KEYS)

    if "provider" not in src:
        raise UniverseError(f"{where}: missing required key 'provider'")
    provider = _non_empty_string(where, "provider", src["provider"])
    if provider not in PROVIDERS:
        raise UniverseError(f"{where}: unknown provider {provider!r}; allowed: {PROVIDERS}")

    kind = src.get("kind", "eod")
    if kind not in KINDS:
        raise UniverseError(
            f"{where}: kind {kind!r} is not supported - only {KINDS}; a non-EOD load is a new "
            f"data contract, not a config value")

    if "symbol" not in src:
        raise UniverseError(f"{where}: missing required key 'symbol'")
    symbol = _non_empty_string(where, "symbol", src["symbol"])
    if provider == "eodhd" and "." not in symbol:
        raise UniverseError(
            f"{where}: eodhd symbols must be canonical TICKER.EXCHANGE (e.g. AAPL.US, "
            f"BTC-USD.CC), got {symbol!r} - bare tickers would blur store coordinates and the "
            f"crypto/raw basis split")

    modeled = False
    if "modeled" in src:
        value = src["modeled"]
        if not isinstance(value, bool):
            raise UniverseError(f"{where}: modeled must be a boolean, got {value!r}")
        modeled = value

    enabled = True
    if "enabled" in src:
        enabled = _boolean(where, "enabled", src["enabled"])

    exchange = DEFAULT_EXCHANGE[provider]
    if "exchange" in src:
        exchange = _non_empty_string(where, "exchange", src["exchange"])

    note = None
    if "note" in src:
        note = _non_empty_string(where, "note", src["note"])

    path = None
    if "path" in src:
        path = _non_empty_string(where, "path", src["path"])

    start = None
    end = None
    if "start" in src:
        start = _iso_date(where, "start", src["start"])
    if "end" in src:
        end = _iso_date(where, "end", src["end"])

    if provider == "yahoo-csv":
        if "path" not in src:
            raise UniverseError(f"{where}: missing required key 'path'")
        if "start" in src or "end" in src:
            raise UniverseError(
                f"{where}: start/end apply to collector sources only; a CSV import is whole-file")
    else:
        if "path" in src:
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

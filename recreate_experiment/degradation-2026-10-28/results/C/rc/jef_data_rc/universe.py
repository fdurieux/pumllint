"""The declarative asset universe: strict TOML grammar, normalised into one document."""
import tomllib
from datetime import date, datetime
from importlib import resources

ASSET_TYPE_BY_CLASS = {"stock": "stock", "crypto": "crypto", "bond_etf": "etf"}
ASSET_TYPES = sorted(set(ASSET_TYPE_BY_CLASS.values()))
PROVIDERS = ["eodhd", "binance", "yahoo-csv"]
COLLECTOR_PROVIDERS = ("eodhd", "binance")
DEFAULT_EXCHANGE = {"eodhd": "eodhd", "binance": "binance", "yahoo-csv": "yahoo"}
KINDS = ["eod"]
DEFAULT_THRESHOLD = -0.05
DEFAULT_STORE = "data"
DEFAULT_CURRENCY = "USD"

TOP_KEYS = ["asset", "defaults"]
DEFAULTS_KEYS = ["currency", "store"]
ASSET_KEYS = ["asset_class", "currency", "enabled", "name", "source", "threshold"]
SOURCE_KEYS = ["enabled", "end", "exchange", "kind", "modeled", "note", "path",
               "provider", "start", "symbol"]

PACKAGED_ORIGIN = "packaged universe.toml"


class UniverseError(ValueError):
    """A universe document that violates the grammar."""


def packaged_text():
    return resources.files("jef_data_rc").joinpath("universe.toml").read_text(encoding="utf-8")


def load_universe(path=None):
    """Load and normalise a universe file; None reads the packaged one."""
    if path is None:
        return parse_universe(packaged_text(), PACKAGED_ORIGIN)
    with open(path, "rb") as handle:
        raw = handle.read()
    return parse_universe(raw.decode("utf-8"), str(path))


def _unknown(table, allowed, where):
    unknown = sorted(set(table) - set(allowed))
    if unknown:
        raise UniverseError(f"{where}: unknown key(s) {unknown}; allowed: {sorted(allowed)}")


def _required_str(table, key, where):
    if key not in table:
        raise UniverseError(f"{where}: missing required key '{key}'")
    return _str_value(table[key], key, where)


def _str_value(value, key, where):
    if not isinstance(value, str) or not value:
        raise UniverseError(f"{where}: {key} must be a non-empty string, got {value!r}")
    return value


def _optional_str(table, key, where, default=None):
    if key not in table:
        return default
    return _str_value(table[key], key, where)


def _optional_bool(table, key, where, default):
    if key not in table:
        return default
    value = table[key]
    if not isinstance(value, bool):
        raise UniverseError(f"{where}: {key} must be a boolean, got {value!r}")
    return value


def _date_value(value, key, where):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError:
            pass
    raise UniverseError(f"{where}: {key} must be an ISO date (YYYY-MM-DD), got {value!r}")


def parse_universe(text, origin):
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise UniverseError(f"{origin}: not valid TOML: {exc}") from None

    _unknown(doc, TOP_KEYS, origin)

    defaults_raw = doc.get("defaults", {})
    if not isinstance(defaults_raw, dict):
        raise UniverseError(f"{origin}: [defaults] must be a table")
    _unknown(defaults_raw, DEFAULTS_KEYS, f"{origin} [defaults]")
    store = _optional_str(defaults_raw, "store", "[defaults]", DEFAULT_STORE)
    currency = _optional_str(defaults_raw, "currency", "[defaults]", DEFAULT_CURRENCY)
    defaults = {"store": store, "currency": currency}

    assets_raw = doc.get("asset")
    if not isinstance(assets_raw, list) or not assets_raw:
        raise UniverseError(f"{origin}: no [[asset]] entries")

    assets = [_parse_asset(raw, n, defaults) for n, raw in enumerate(assets_raw, start=1)]

    names = [a["name"] for a in assets]
    dupes = sorted({name for name in names if names.count(name) > 1})
    if dupes:
        raise UniverseError(f"{origin}: duplicate asset name(s) {dupes}")

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
                    f"both {owner!r} and {asset['name']!r} - two assets may never write "
                    f"the same partition")
    return {"defaults": defaults, "assets": assets}


def _parse_asset(raw, n, defaults):
    where = f"asset #{n}"
    if not isinstance(raw, dict):
        raise UniverseError(f"{where}: must be a table")
    _unknown(raw, ASSET_KEYS, where)
    name = _required_str(raw, "name", where)
    where = f"asset '{name}'"
    asset_class = _required_str(raw, "asset_class", where)
    if asset_class not in ASSET_TYPE_BY_CLASS:
        raise UniverseError(
            f"{where}: unknown asset_class {asset_class!r}; "
            f"allowed: {sorted(ASSET_TYPE_BY_CLASS)}")
    threshold = DEFAULT_THRESHOLD
    if "threshold" in raw:
        value = raw["threshold"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise UniverseError(
                f"{where}: threshold must be a number (documentation only), got {value!r}")
        threshold = float(value)
    currency = _optional_str(raw, "currency", where, defaults["currency"])
    sources_raw = raw.get("source")
    if not isinstance(sources_raw, list) or not sources_raw:
        raise UniverseError(f"{where}: needs at least one [[asset.source]]")
    enabled = _optional_bool(raw, "enabled", where, True)

    sources = [_parse_source(src, m, name, currency)
               for m, src in enumerate(sources_raw, start=1)]

    if any(s["modeled"] and not s["enabled"] for s in sources):
        raise UniverseError(f"{where}: a modeled source must be enabled")
    live = [s for s in sources if s["enabled"]]
    modeled = [s for s in live if s["modeled"]]
    if len(modeled) > 1:
        raise UniverseError(
            f"{where}: exactly one enabled source may be modeled = true, got {len(modeled)}")
    if enabled:
        if len(live) >= 2 and not modeled:
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


def _parse_source(raw, m, asset_name, currency):
    where = f"asset '{asset_name}' source #{m}"
    if not isinstance(raw, dict):
        raise UniverseError(f"{where}: must be a table")
    _unknown(raw, SOURCE_KEYS, where)
    provider = _required_str(raw, "provider", where)
    if provider not in PROVIDERS:
        raise UniverseError(f"{where}: unknown provider {provider!r}; allowed: {PROVIDERS}")
    kind = raw.get("kind", "eod")
    if kind not in KINDS:
        raise UniverseError(
            f"{where}: kind {kind!r} is not supported - only {KINDS}; a non-EOD load is a "
            f"new data contract, not a config value")
    symbol = _required_str(raw, "symbol", where)
    if provider == "eodhd" and "." not in symbol:
        raise UniverseError(
            f"{where}: eodhd symbols must be canonical TICKER.EXCHANGE (e.g. AAPL.US, "
            f"BTC-USD.CC), got {symbol!r} - bare tickers would blur store coordinates and "
            f"the crypto/raw basis split")
    modeled = False
    if "modeled" in raw:
        value = raw["modeled"]
        if not isinstance(value, bool):
            raise UniverseError(f"{where}: modeled must be a boolean, got {value!r}")
        modeled = value
    enabled = _optional_bool(raw, "enabled", where, True)
    exchange = _optional_str(raw, "exchange", where, DEFAULT_EXCHANGE[provider])
    note = _optional_str(raw, "note", where)
    path = _optional_str(raw, "path", where)
    start = _date_value(raw["start"], "start", where) if "start" in raw else None
    end = _date_value(raw["end"], "end", where) if "end" in raw else None
    if provider == "yahoo-csv":
        if path is None:
            raise UniverseError(f"{where}: missing required key 'path'")
        if "start" in raw or "end" in raw:
            raise UniverseError(
                f"{where}: start/end apply to collector sources only; a CSV import is whole-file")
    elif path is not None:
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

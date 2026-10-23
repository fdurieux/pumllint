"""Strict loader for the declarative asset universe (universe.toml)."""
import datetime as _dt
import tomllib
from importlib import resources

PACKAGED_ORIGIN = "packaged universe.toml"

ASSET_TYPE_BY_CLASS = {"stock": "stock", "crypto": "crypto", "bond_etf": "etf"}
ASSET_TYPES = sorted(set(ASSET_TYPE_BY_CLASS.values()))
ASSET_CLASSES = sorted(ASSET_TYPE_BY_CLASS)
PROVIDERS = ["eodhd", "binance", "yahoo-csv"]
COLLECTOR_PROVIDERS = ("eodhd", "binance")
EXCHANGE_BY_PROVIDER = {"eodhd": "eodhd", "binance": "binance", "yahoo-csv": "yahoo"}
KINDS = ["eod"]

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
    unknown = sorted(set(table) - set(allowed))
    if unknown:
        raise UniverseError(
            f"{where}: unknown key(s) {unknown}; allowed: {sorted(allowed)}")


def _non_empty_string(where, key, value):
    if not isinstance(value, str) or not value:
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


def _read_text(path):
    if path is None:
        data = resources.files(__package__).joinpath("universe.toml").read_bytes()
        return PACKAGED_ORIGIN, data
    with open(path, "rb") as handle:
        data = handle.read()
    return str(path), data


def load_universe(path=None):
    """Parse and validate a universe file; None reads the packaged one."""
    origin, data = _read_text(path)
    return parse_universe(data.decode("utf-8"), origin)


def parse_universe(text, origin):
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise UniverseError(f"{origin}: not valid TOML: {exc}") from None

    _unknown_keys(origin, doc, TOP_KEYS)

    defaults = doc.get("defaults", {})
    if not isinstance(defaults, dict):
        raise UniverseError(f"{origin}: [defaults] must be a table")
    _unknown_keys(f"{origin} [defaults]", defaults, DEFAULTS_KEYS)
    store = DEFAULT_STORE
    if "store" in defaults:
        store = _non_empty_string("[defaults]", "store", defaults["store"])
    currency = DEFAULT_CURRENCY
    if "currency" in defaults:
        currency = _non_empty_string("[defaults]", "currency", defaults["currency"])

    raw_assets = doc.get("asset")
    if not isinstance(raw_assets, list) or not raw_assets:
        raise UniverseError(f"{origin}: no [[asset]] entries")

    assets = [_parse_asset(n, raw, currency) for n, raw in enumerate(raw_assets, 1)]

    names = [a["name"] for a in assets]
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        raise UniverseError(f"{origin}: duplicate asset name(s) {dupes}")

    owners = {}
    for asset in assets:
        for source in asset["sources"]:
            coord = (source["exchange"], source["symbol"])
            owner = owners.get(coord)
            if owner is None:
                owners[coord] = asset["name"]
            elif owner != asset["name"]:
                raise UniverseError(
                    f"{origin}: store series {coord[0]}/{coord[1]} is claimed by both "
                    f"{owner!r} and {asset['name']!r} - two assets may never write "
                    f"the same partition")

    return {"defaults": {"store": store, "currency": currency}, "assets": assets}


def _parse_asset(n, raw, default_currency):
    if not isinstance(raw, dict):
        raise UniverseError(f"asset #{n}: must be a table")
    _unknown_keys(f"asset #{n}", raw, ASSET_KEYS)
    if "name" not in raw:
        raise UniverseError(f"asset #{n}: missing required key 'name'")
    name = _non_empty_string(f"asset #{n}", "name", raw["name"])
    where = f"asset '{name}'"

    if "asset_class" not in raw:
        raise UniverseError(f"{where}: missing required key 'asset_class'")
    asset_class = _non_empty_string(where, "asset_class", raw["asset_class"])
    if asset_class not in ASSET_TYPE_BY_CLASS:
        raise UniverseError(
            f"{where}: unknown asset_class {asset_class!r}; allowed: {ASSET_CLASSES}")

    threshold = DEFAULT_THRESHOLD
    if "threshold" in raw:
        value = raw["threshold"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise UniverseError(
                f"{where}: threshold must be a number (documentation only), got {value!r}")
        threshold = float(value)

    currency = default_currency
    if "currency" in raw:
        currency = _non_empty_string(where, "currency", raw["currency"])

    raw_sources = raw.get("source")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise UniverseError(f"{where}: needs at least one [[asset.source]]")

    enabled = True
    if "enabled" in raw:
        enabled = _boolean(where, "enabled", raw["enabled"])

    sources = [_parse_source(name, m, src, currency)
               for m, src in enumerate(raw_sources, 1)]

    if any(s["modeled"] and not s["enabled"] for s in sources):
        raise UniverseError(f"{where}: a modeled source must be enabled")
    modeled = sum(1 for s in sources if s["enabled"] and s["modeled"])
    if modeled > 1:
        raise UniverseError(
            f"{where}: exactly one enabled source may be modeled = true, got {modeled}")
    if enabled:
        live = sum(1 for s in sources if s["enabled"])
        if live >= 2 and modeled == 0:
            raise UniverseError(
                f"{where}: {live} enabled sources but none marked modeled = true - the "
                f"binning's feeder must be deterministic (docs/DATA_CONTRACT.md SS7.7)")
        if live == 0:
            raise UniverseError(
                f"{where}: enabled but has no enabled source - nothing would feed the "
                f"binning; to pause the asset, set enabled = false on the asset itself")

    return {"name": name, "asset_class": asset_class,
            "asset_type": ASSET_TYPE_BY_CLASS[asset_class], "currency": currency,
            "threshold": threshold, "enabled": enabled, "sources": sources}


def _parse_source(name, m, raw, currency):
    where = f"asset '{name}' source #{m}"
    if not isinstance(raw, dict):
        raise UniverseError(f"{where}: must be a table")
    _unknown_keys(where, raw, SOURCE_KEYS)

    if "provider" not in raw:
        raise UniverseError(f"{where}: missing required key 'provider'")
    provider = _non_empty_string(where, "provider", raw["provider"])
    if provider not in PROVIDERS:
        raise UniverseError(f"{where}: unknown provider {provider!r}; allowed: {PROVIDERS}")

    kind = raw.get("kind", "eod")
    if kind not in KINDS:
        raise UniverseError(
            f"{where}: kind {kind!r} is not supported - only {KINDS}; a non-EOD load "
            f"is a new data contract, not a config value")

    if "symbol" not in raw:
        raise UniverseError(f"{where}: missing required key 'symbol'")
    symbol = _non_empty_string(where, "symbol", raw["symbol"])
    if provider == "eodhd" and "." not in symbol:
        raise UniverseError(
            f"{where}: eodhd symbols must be canonical TICKER.EXCHANGE (e.g. AAPL.US, "
            f"BTC-USD.CC), got {symbol!r} - bare tickers would blur store coordinates "
            f"and the crypto/raw basis split")

    modeled = False
    if "modeled" in raw:
        modeled = _boolean(where, "modeled", raw["modeled"])
    enabled = True
    if "enabled" in raw:
        enabled = _boolean(where, "enabled", raw["enabled"])

    exchange = EXCHANGE_BY_PROVIDER[provider]
    if "exchange" in raw:
        exchange = _non_empty_string(where, "exchange", raw["exchange"])

    note = None
    if "note" in raw:
        note = _non_empty_string(where, "note", raw["note"])

    path = None
    if provider == "yahoo-csv" and "path" not in raw:
        raise UniverseError(f"{where}: missing required key 'path'")
    if "path" in raw:
        path = _non_empty_string(where, "path", raw["path"])

    start = _iso_date(where, "start", raw["start"]) if "start" in raw else None
    end = _iso_date(where, "end", raw["end"]) if "end" in raw else None

    if provider == "yahoo-csv":
        if "start" in raw or "end" in raw:
            raise UniverseError(
                f"{where}: start/end apply to collector sources only; a CSV import is "
                f"whole-file")
    elif "path" in raw:
        raise UniverseError(f"{where}: path applies to yahoo-csv sources only")

    if start is not None and end is not None and start > end:
        raise UniverseError(f"{where}: start {start} is after end {end}")

    source = {"provider": provider, "kind": kind, "enabled": enabled,
              "modeled": modeled, "exchange": exchange, "symbol": symbol,
              "currency": currency}
    if note is not None:
        source["note"] = note
    if provider == "yahoo-csv":
        source["path"] = path
    else:
        source["start"] = start
        source["end"] = end
    return source

"""The declarative asset universe: strict TOML loader and normaliser."""
import datetime as _dt
import tomllib
from importlib import resources
from pathlib import Path

PACKAGED_ORIGIN = "packaged universe.toml"

ASSET_TYPE_BY_CLASS = {"stock": "stock", "crypto": "crypto", "bond_etf": "etf"}
ASSET_TYPES = sorted(set(ASSET_TYPE_BY_CLASS.values()))
PROVIDERS = ["eodhd", "binance", "yahoo-csv"]
COLLECTOR_PROVIDERS = ("eodhd", "binance")
DEFAULT_EXCHANGE = {"eodhd": "eodhd", "binance": "binance", "yahoo-csv": "yahoo"}
KINDS = ["eod"]
DEFAULT_THRESHOLD = -0.05

TOP_KEYS = ["asset", "defaults"]
DEFAULTS_KEYS = ["currency", "store"]
ASSET_KEYS = ["asset_class", "currency", "enabled", "name", "source", "threshold"]
SOURCE_KEYS = ["enabled", "end", "exchange", "kind", "modeled", "note", "path",
               "provider", "start", "symbol"]


class UniverseError(ValueError):
    """A universe document that violates the grammar."""


class DeclarationRefused(ValueError):
    """A hand-run load whose asset_type declaration cannot be trusted."""


def packaged_text():
    return resources.files(__package__).joinpath("universe.toml").read_text(encoding="utf-8")


def _unknown(where, table, allowed):
    extra = sorted(k for k in table if k not in allowed)
    if extra:
        raise UniverseError(f"{where}: unknown key(s) {extra}; allowed: {sorted(allowed)}")


def _nonempty_str(where, key, value):
    if not isinstance(value, str) or not value:
        raise UniverseError(f"{where}: {key} must be a non-empty string, got {value!r}")
    return value


def _bool(where, key, value):
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


def _parse_source(name, n, raw, currency):
    where = f"asset '{name}' source #{n}"
    if not isinstance(raw, dict):
        raise UniverseError(f"{where}: must be a table")
    _unknown(where, raw, SOURCE_KEYS)
    if "provider" not in raw:
        raise UniverseError(f"{where}: missing required key 'provider'")
    provider = _nonempty_str(where, "provider", raw["provider"])
    if provider not in PROVIDERS:
        raise UniverseError(f"{where}: unknown provider {provider!r}; allowed: {PROVIDERS}")
    kind = raw.get("kind", "eod")
    if kind not in KINDS:
        raise UniverseError(
            f"{where}: kind {kind!r} is not supported - only {KINDS}; a non-EOD load is "
            "a new data contract, not a config value")
    if "symbol" not in raw:
        raise UniverseError(f"{where}: missing required key 'symbol'")
    symbol = _nonempty_str(where, "symbol", raw["symbol"])
    if provider == "eodhd" and "." not in symbol:
        raise UniverseError(
            f"{where}: eodhd symbols must be canonical TICKER.EXCHANGE (e.g. AAPL.US, "
            f"BTC-USD.CC), got {symbol!r} - bare tickers would blur store coordinates and "
            "the crypto/raw basis split")
    modeled = raw.get("modeled", False)
    if not isinstance(modeled, bool):
        raise UniverseError(f"{where}: modeled must be a boolean, got {modeled!r}")
    enabled = _bool(where, "enabled", raw.get("enabled", True))
    if "exchange" in raw:
        exchange = _nonempty_str(where, "exchange", raw["exchange"])
    else:
        exchange = DEFAULT_EXCHANGE[provider]
    note = None
    if "note" in raw:
        note = _nonempty_str(where, "note", raw["note"])
    path = None
    if provider == "yahoo-csv" and "path" not in raw:
        raise UniverseError(f"{where}: missing required key 'path'")
    if "path" in raw:
        path = _nonempty_str(where, "path", raw["path"])
    start = _iso_date(where, "start", raw["start"]) if "start" in raw else None
    end = _iso_date(where, "end", raw["end"]) if "end" in raw else None
    if provider == "yahoo-csv":
        if "start" in raw or "end" in raw:
            raise UniverseError(
                f"{where}: start/end apply to collector sources only; a CSV import is whole-file")
    elif "path" in raw:
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


def _parse_asset(n, raw, default_currency):
    if not isinstance(raw, dict):
        raise UniverseError(f"asset #{n}: must be a table")
    _unknown(f"asset #{n}", raw, ASSET_KEYS)
    if "name" not in raw:
        raise UniverseError(f"asset #{n}: missing required key 'name'")
    name = _nonempty_str(f"asset #{n}", "name", raw["name"])
    where = f"asset '{name}'"
    if "asset_class" not in raw:
        raise UniverseError(f"{where}: missing required key 'asset_class'")
    asset_class = _nonempty_str(where, "asset_class", raw["asset_class"])
    if asset_class not in ASSET_TYPE_BY_CLASS:
        raise UniverseError(
            f"{where}: unknown asset_class {asset_class!r}; allowed: {sorted(ASSET_TYPE_BY_CLASS)}")
    threshold = raw.get("threshold", DEFAULT_THRESHOLD)
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise UniverseError(
            f"{where}: threshold must be a number (documentation only), got {threshold!r}")
    currency = default_currency
    if "currency" in raw:
        currency = _nonempty_str(where, "currency", raw["currency"])
    raw_sources = raw.get("source")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise UniverseError(f"{where}: needs at least one [[asset.source]]")
    enabled = _bool(where, "enabled", raw.get("enabled", True))
    sources = [_parse_source(name, i, s, currency) for i, s in enumerate(raw_sources, 1)]
    if any(s["modeled"] and not s["enabled"] for s in sources):
        raise UniverseError(f"{where}: a modeled source must be enabled")
    live = [s for s in sources if s["enabled"]]
    modeled = sum(1 for s in live if s["modeled"])
    if modeled > 1:
        raise UniverseError(f"{where}: exactly one enabled source may be modeled = true, got {modeled}")
    if enabled:
        if len(live) >= 2 and modeled == 0:
            raise UniverseError(
                f"{where}: {len(live)} enabled sources but none marked modeled = true - the "
                "binning's feeder must be deterministic (docs/DATA_CONTRACT.md SS7.7)")
        if not live:
            raise UniverseError(
                f"{where}: enabled but has no enabled source - nothing would feed the binning; "
                "to pause the asset, set enabled = false on the asset itself")
    return {"name": name, "asset_class": asset_class,
            "asset_type": ASSET_TYPE_BY_CLASS[asset_class], "currency": currency,
            "threshold": float(threshold), "enabled": enabled, "sources": sources}


def parse_universe(text, origin):
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise UniverseError(f"{origin}: not valid TOML: {exc}") from None
    _unknown(origin, doc, TOP_KEYS)
    defaults_raw = doc.get("defaults", {})
    if not isinstance(defaults_raw, dict):
        raise UniverseError(f"{origin}: [defaults] must be a table")
    _unknown(f"{origin} [defaults]", defaults_raw, DEFAULTS_KEYS)
    store = "data"
    if "store" in defaults_raw:
        store = _nonempty_str("[defaults]", "store", defaults_raw["store"])
    currency = "USD"
    if "currency" in defaults_raw:
        currency = _nonempty_str("[defaults]", "currency", defaults_raw["currency"])
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
            owner = owners.setdefault(coord, asset["name"])
            if owner != asset["name"]:
                raise UniverseError(
                    f"{origin}: store series {coord[0]}/{coord[1]} is claimed by both "
                    f"{owner!r} and {asset['name']!r} - two assets may never write the same partition")
    return {"defaults": {"store": store, "currency": currency}, "assets": assets}


def load_universe(path=None):
    if path is None:
        return parse_universe(packaged_text(), PACKAGED_ORIGIN)
    text = Path(path).read_text(encoding="utf-8")
    return parse_universe(text, str(path))


def listing(universe):
    lines = []
    for asset in universe["assets"]:
        line = f"{asset['name']} ({asset['asset_class']}, {asset['currency']}, threshold {asset['threshold']})"
        if not asset["enabled"]:
            line += " [disabled]"
        lines.append(line)
        for source in asset["sources"]:
            target = source.get("path") or source["symbol"]
            line = f"  {source['provider']}: {target}"
            if not source["enabled"]:
                line += " [disabled]"
            if source.get("note"):
                line += f" - {source['note']}"
            lines.append(line)
    return lines


def declare_asset_type(symbol, asset_type):
    """Resolve a hand-run load's asset_type from its declaration and the symbol."""
    crypto_namespace = symbol.endswith(".CC")
    if asset_type is None:
        if crypto_namespace:
            return "crypto"
        raise DeclarationRefused(
            f"{symbol}: asset_type is required (one of {ASSET_TYPES}). The ticker carries no "
            "instrument-type signal - SPY, TLT, GLD and IBIT are ETFs spelled exactly like "
            "equities - so the old 'stock' default was a guess written into the store as a "
            "fact, and TLT is in this repo's universe as an explicit override because that "
            "guess got it wrong. Only EODHD's .CC crypto namespace is evidence enough to infer from")
    if asset_type not in ASSET_TYPES:
        raise DeclarationRefused(
            f"unknown asset_type {asset_type!r}; the store vocabulary is {ASSET_TYPES} (derived "
            "from the universe's own asset_class map, jef.data.universe.ASSET_TYPE_BY_CLASS)")
    if crypto_namespace and asset_type != "crypto":
        raise DeclarationRefused(
            f"{symbol} is in EODHD's .CC crypto namespace but was declared asset_type="
            f"{asset_type!r}; that combination cannot be true, and guessing either way decides "
            "whether split adjustment runs on pre-adjusted prices (docs/DATA_CONTRACT.md §2)")
    return asset_type

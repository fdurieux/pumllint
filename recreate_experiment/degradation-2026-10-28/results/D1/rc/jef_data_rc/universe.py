"""The declarative asset universe: strict parser, normalised form, listing."""
import tomllib
from datetime import date, datetime
from importlib import resources

ASSET_TYPE_BY_CLASS = {"stock": "stock", "crypto": "crypto", "bond_etf": "etf"}
ASSET_TYPES = sorted(set(ASSET_TYPE_BY_CLASS.values()))
PROVIDERS = ["eodhd", "binance", "yahoo-csv"]
DEFAULT_EXCHANGE = {"eodhd": "eodhd", "binance": "binance", "yahoo-csv": "yahoo"}
KINDS = ["eod"]
DEFAULT_STORE = "data"
DEFAULT_CURRENCY = "USD"
DEFAULT_THRESHOLD = -0.05
PACKAGED_ORIGIN = "packaged universe.toml"

TOP_KEYS = frozenset({"defaults", "asset"})
DEFAULTS_KEYS = frozenset({"store", "currency"})
ASSET_KEYS = frozenset({"name", "asset_class", "currency", "threshold", "enabled", "source"})
SOURCE_KEYS = frozenset({"provider", "symbol", "path", "exchange", "start", "end", "kind",
                         "enabled", "modeled", "note"})


class UniverseError(ValueError):
    """A universe document that violates the grammar."""


class DeclarationRefused(ValueError):
    """A hand-run load whose instrument-type declaration cannot be trusted."""


def packaged_text():
    return resources.files(__package__).joinpath("universe.toml").read_text(encoding="utf-8")


def load_universe(path=None):
    """Parse the universe at `path` (or the packaged one) into its normalised form."""
    if path is None:
        return parse_universe(packaged_text(), PACKAGED_ORIGIN)
    with open(path, "rb") as handle:
        raw = handle.read()
    return parse_universe(raw.decode("utf-8"), str(path))


def _unknown_keys(where, table, allowed):
    unknown = sorted(set(table) - set(allowed))
    if unknown:
        raise UniverseError(f"{where}: unknown key(s) {unknown}; allowed: {sorted(allowed)}")


def _string(where, table, key, required=False):
    if key not in table:
        if required:
            raise UniverseError(f"{where}: missing required key '{key}'")
        return None
    value = table[key]
    if not isinstance(value, str) or not value:
        raise UniverseError(f"{where}: {key} must be a non-empty string, got {value!r}")
    return value


def _boolean(where, table, key, default):
    if key not in table:
        return default
    value = table[key]
    if not isinstance(value, bool):
        raise UniverseError(f"{where}: {key} must be a boolean, got {value!r}")
    return value


def _iso_date(where, table, key):
    if key not in table:
        return None
    value = table[key]
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
    _unknown_keys(origin, doc, TOP_KEYS)
    defaults = doc.get("defaults", {})
    if not isinstance(defaults, dict):
        raise UniverseError(f"{origin}: [defaults] must be a table")
    _unknown_keys(f"{origin} [defaults]", defaults, DEFAULTS_KEYS)
    store = _string("[defaults]", defaults, "store")
    currency = _string("[defaults]", defaults, "currency")
    store = DEFAULT_STORE if store is None else store
    currency = DEFAULT_CURRENCY if currency is None else currency

    entries = doc.get("asset")
    if not isinstance(entries, list) or not entries:
        raise UniverseError(f"{origin}: no [[asset]] entries")
    assets = [_parse_asset(n, entry, currency) for n, entry in enumerate(entries, 1)]

    names = [asset["name"] for asset in assets]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise UniverseError(f"{origin}: duplicate asset name(s) {duplicates}")
    owners = {}
    for asset in assets:
        for source in asset["sources"]:
            coordinate = (source["exchange"], source["symbol"])
            owner = owners.setdefault(coordinate, asset["name"])
            if owner != asset["name"]:
                raise UniverseError(
                    f"{origin}: store series {coordinate[0]}/{coordinate[1]} is claimed by both "
                    f"{owner!r} and {asset['name']!r} - two assets may never write the same partition")
    return {"defaults": {"store": store, "currency": currency}, "assets": assets}


def _parse_asset(n, entry, default_currency):
    where = f"asset #{n}"
    if not isinstance(entry, dict):
        raise UniverseError(f"{where}: must be a table")
    _unknown_keys(where, entry, ASSET_KEYS)
    name = _string(where, entry, "name", required=True)
    where = f"asset '{name}'"
    asset_class = _string(where, entry, "asset_class", required=True)
    if asset_class not in ASSET_TYPE_BY_CLASS:
        raise UniverseError(f"{where}: unknown asset_class {asset_class!r}; "
                            f"allowed: {sorted(ASSET_TYPE_BY_CLASS)}")
    if "threshold" in entry:
        threshold = entry["threshold"]
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
            raise UniverseError(f"{where}: threshold must be a number (documentation only), "
                                f"got {threshold!r}")
        threshold = float(threshold)
    else:
        threshold = DEFAULT_THRESHOLD
    currency = _string(where, entry, "currency")
    currency = default_currency if currency is None else currency
    raw_sources = entry.get("source")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise UniverseError(f"{where}: needs at least one [[asset.source]]")
    enabled = _boolean(where, entry, "enabled", True)
    sources = [_parse_source(where, m, raw, currency) for m, raw in enumerate(raw_sources, 1)]

    if any(source["modeled"] and not source["enabled"] for source in sources):
        raise UniverseError(f"{where}: a modeled source must be enabled")
    live = [source for source in sources if source["enabled"]]
    modeled = sum(1 for source in live if source["modeled"])
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
            "threshold": threshold, "enabled": enabled, "sources": sources}


def _parse_source(asset_where, m, entry, currency):
    where = f"{asset_where} source #{m}"
    if not isinstance(entry, dict):
        raise UniverseError(f"{where}: must be a table")
    _unknown_keys(where, entry, SOURCE_KEYS)
    provider = _string(where, entry, "provider", required=True)
    if provider not in PROVIDERS:
        raise UniverseError(f"{where}: unknown provider {provider!r}; allowed: {PROVIDERS}")
    kind = entry.get("kind", "eod")
    if kind not in KINDS:
        raise UniverseError(f"{where}: kind {kind!r} is not supported - only {KINDS}; a non-EOD "
                            "load is a new data contract, not a config value")
    symbol = _string(where, entry, "symbol", required=True)
    if provider == "eodhd" and "." not in symbol:
        raise UniverseError(
            f"{where}: eodhd symbols must be canonical TICKER.EXCHANGE (e.g. AAPL.US, BTC-USD.CC), "
            f"got {symbol!r} - bare tickers would blur store coordinates and the crypto/raw "
            "basis split")
    modeled = _boolean(where, entry, "modeled", False)
    enabled = _boolean(where, entry, "enabled", True)
    exchange = _string(where, entry, "exchange")
    exchange = DEFAULT_EXCHANGE[provider] if exchange is None else exchange
    note = _string(where, entry, "note")
    path = _string(where, entry, "path", required=provider == "yahoo-csv")
    start = _iso_date(where, entry, "start")
    end = _iso_date(where, entry, "end")
    if provider == "yahoo-csv":
        if "start" in entry or "end" in entry:
            raise UniverseError(f"{where}: start/end apply to collector sources only; "
                                "a CSV import is whole-file")
    elif "path" in entry:
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


def render_listing(universe):
    """The `universe` command's listing, one string per line."""
    lines = []
    for asset in universe["assets"]:
        line = f"{asset['name']} ({asset['asset_class']}, {asset['currency']}, " \
               f"threshold {float(asset['threshold'])!r})"
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


def resolve_declaration(symbol, asset_type):
    """The store asset_type of a hand-run EODHD load of the normalised `symbol`."""
    crypto_namespace = symbol.endswith(".CC")
    if asset_type is None:
        if not crypto_namespace:
            raise DeclarationRefused(
                f"{symbol}: asset_type is required (one of {ASSET_TYPES}). The ticker carries no "
                "instrument-type signal - SPY, TLT, GLD and IBIT are ETFs spelled exactly like "
                "equities - so the old 'stock' default was a guess written into the store as a "
                "fact, and TLT is in this repo's universe as an explicit override because that "
                "guess got it wrong. Only EODHD's .CC crypto namespace is evidence enough to "
                "infer from")
        return "crypto"
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

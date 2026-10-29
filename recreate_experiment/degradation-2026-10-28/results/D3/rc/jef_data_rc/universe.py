"""The declarative universe: strict TOML parsing into one normalised document."""
from __future__ import annotations

import tomllib
from datetime import date, datetime
from importlib import resources

PACKAGED_LABEL = "packaged universe.toml"

ASSET_TYPE_BY_CLASS = {"stock": "stock", "crypto": "crypto", "bond_etf": "etf"}
ASSET_TYPES = sorted(set(ASSET_TYPE_BY_CLASS.values()))
PROVIDERS = ["eodhd", "binance", "yahoo-csv"]
COLLECTOR_PROVIDERS = ("eodhd", "binance")
EXCHANGE_BY_PROVIDER = {"eodhd": "eodhd", "binance": "binance", "yahoo-csv": "yahoo"}
KINDS = ["eod"]
DEFAULT_THRESHOLD = -0.05

TOP_KEYS = ["asset", "defaults"]
DEFAULTS_KEYS = ["currency", "store"]
ASSET_KEYS = ["asset_class", "currency", "enabled", "name", "source", "threshold"]
SOURCE_KEYS = ["enabled", "end", "exchange", "kind", "modeled", "note", "path",
               "provider", "start", "symbol"]


class UniverseError(ValueError):
    """A universe document that violates the grammar."""


def packaged_text() -> str:
    return resources.files(__package__).joinpath("universe.toml").read_text(encoding="utf-8")


def load_universe(path=None) -> dict:
    """Load and normalise a universe file; None reads the packaged one."""
    if path is None:
        return parse_universe(packaged_text(), PACKAGED_LABEL)
    with open(path, "rb") as handle:
        raw = handle.read()
    return parse_universe(raw.decode("utf-8"), str(path))


def _check_keys(table: dict, allowed: list, where: str) -> None:
    unknown = sorted(k for k in table if k not in allowed)
    if unknown:
        raise UniverseError(f"{where}: unknown key(s) {unknown}; allowed: {sorted(allowed)}")


def _nonempty_str(value, key: str, where: str) -> str:
    if not isinstance(value, str) or value == "":
        raise UniverseError(f"{where}: {key} must be a non-empty string, got {value!r}")
    return value


def _required_str(table: dict, key: str, where: str) -> str:
    if key not in table:
        raise UniverseError(f"{where}: missing required key '{key}'")
    return _nonempty_str(table[key], key, where)


def _bool(table: dict, key: str, where: str, default: bool) -> bool:
    if key not in table:
        return default
    value = table[key]
    if not isinstance(value, bool):
        raise UniverseError(f"{where}: {key} must be a boolean, got {value!r}")
    return value


def _iso_date(value, key: str, where: str) -> str:
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


def parse_universe(text: str, origin: str) -> dict:
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise UniverseError(f"{origin}: not valid TOML: {exc}") from None

    _check_keys(doc, TOP_KEYS, origin)

    defaults_in = doc.get("defaults", {})
    if not isinstance(defaults_in, dict):
        raise UniverseError(f"{origin}: [defaults] must be a table")
    _check_keys(defaults_in, DEFAULTS_KEYS, f"{origin} [defaults]")
    store = "data"
    currency = "USD"
    if "store" in defaults_in:
        store = _nonempty_str(defaults_in["store"], "store", "[defaults]")
    if "currency" in defaults_in:
        currency = _nonempty_str(defaults_in["currency"], "currency", "[defaults]")
    defaults = {"store": store, "currency": currency}

    assets_in = doc.get("asset")
    if not isinstance(assets_in, list) or not assets_in:
        raise UniverseError(f"{origin}: no [[asset]] entries")

    assets = []
    for n, asset_in in enumerate(assets_in, start=1):
        assets.append(_parse_asset(asset_in, n, defaults))

    names = [a["name"] for a in assets]
    dupes = sorted({name for name in names if names.count(name) > 1})
    if dupes:
        raise UniverseError(f"{origin}: duplicate asset name(s) {dupes}")

    owners: dict = {}
    for asset in assets:
        for source in asset["sources"]:
            coord = (source["exchange"], source["symbol"])
            owner = owners.get(coord)
            if owner is None:
                owners[coord] = asset["name"]
            elif owner != asset["name"]:
                raise UniverseError(
                    f"{origin}: store series {coord[0]}/{coord[1]} is claimed by both "
                    f"{owner!r} and {asset['name']!r} - two assets may never write the same partition")

    return {"defaults": defaults, "assets": assets}


def _parse_asset(asset_in, n: int, defaults: dict) -> dict:
    if not isinstance(asset_in, dict):
        raise UniverseError(f"asset #{n}: must be a table")
    _check_keys(asset_in, ASSET_KEYS, f"asset #{n}")
    name = _required_str(asset_in, "name", f"asset #{n}")
    where = f"asset '{name}'"
    asset_class = _required_str(asset_in, "asset_class", where)
    if asset_class not in ASSET_TYPE_BY_CLASS:
        raise UniverseError(
            f"{where}: unknown asset_class {asset_class!r}; allowed: {sorted(ASSET_TYPE_BY_CLASS)}")
    threshold = DEFAULT_THRESHOLD
    if "threshold" in asset_in:
        value = asset_in["threshold"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise UniverseError(f"{where}: threshold must be a number (documentation only), got {value!r}")
        threshold = float(value)
    currency = defaults["currency"]
    if "currency" in asset_in:
        currency = _nonempty_str(asset_in["currency"], "currency", where)
    sources_in = asset_in.get("source")
    if not isinstance(sources_in, list) or not sources_in:
        raise UniverseError(f"{where}: needs at least one [[asset.source]]")
    enabled = _bool(asset_in, "enabled", where, True)

    sources = []
    for m, source_in in enumerate(sources_in, start=1):
        sources.append(_parse_source(source_in, f"{where} source #{m}", currency))

    if any(s["modeled"] and not s["enabled"] for s in sources):
        raise UniverseError(f"{where}: a modeled source must be enabled")
    live = [s for s in sources if s["enabled"]]
    modeled = [s for s in live if s["modeled"]]
    if len(modeled) > 1:
        raise UniverseError(f"{where}: exactly one enabled source may be modeled = true, got {len(modeled)}")
    if enabled:
        if len(live) >= 2 and not modeled:
            raise UniverseError(
                f"{where}: {len(live)} enabled sources but none marked modeled = true - the binning's "
                f"feeder must be deterministic (docs/DATA_CONTRACT.md SS7.7)")
        if not live:
            raise UniverseError(
                f"{where}: enabled but has no enabled source - nothing would feed the binning; "
                f"to pause the asset, set enabled = false on the asset itself")

    return {"name": name, "asset_class": asset_class,
            "asset_type": ASSET_TYPE_BY_CLASS[asset_class], "currency": currency,
            "threshold": threshold, "enabled": enabled, "sources": sources}


def _parse_source(source_in, where: str, currency: str) -> dict:
    if not isinstance(source_in, dict):
        raise UniverseError(f"{where}: must be a table")
    _check_keys(source_in, SOURCE_KEYS, where)
    provider = _required_str(source_in, "provider", where)
    if provider not in PROVIDERS:
        raise UniverseError(f"{where}: unknown provider {provider!r}; allowed: {PROVIDERS}")
    kind = source_in.get("kind", "eod")
    if kind not in KINDS:
        raise UniverseError(
            f"{where}: kind {kind!r} is not supported - only {KINDS}; a non-EOD load is a new "
            f"data contract, not a config value")
    symbol = _required_str(source_in, "symbol", where)
    if provider == "eodhd" and "." not in symbol:
        raise UniverseError(
            f"{where}: eodhd symbols must be canonical TICKER.EXCHANGE (e.g. AAPL.US, BTC-USD.CC), "
            f"got {symbol!r} - bare tickers would blur store coordinates and the crypto/raw basis split")
    if "modeled" in source_in and not isinstance(source_in["modeled"], bool):
        raise UniverseError(f"{where}: modeled must be a boolean, got {source_in['modeled']!r}")
    modeled = source_in.get("modeled", False)
    enabled = _bool(source_in, "enabled", where, True)
    exchange = EXCHANGE_BY_PROVIDER[provider]
    if "exchange" in source_in:
        exchange = _nonempty_str(source_in["exchange"], "exchange", where)
    note = None
    if "note" in source_in:
        note = _nonempty_str(source_in["note"], "note", where)
    path = None
    if "path" in source_in:
        path = _nonempty_str(source_in["path"], "path", where)
    elif provider == "yahoo-csv":
        raise UniverseError(f"{where}: missing required key 'path'")
    start = _iso_date(source_in["start"], "start", where) if "start" in source_in else None
    end = _iso_date(source_in["end"], "end", where) if "end" in source_in else None
    if provider == "yahoo-csv":
        if "start" in source_in or "end" in source_in:
            raise UniverseError(f"{where}: start/end apply to collector sources only; a CSV import is whole-file")
    elif "path" in source_in:
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


def listing(universe: dict) -> list:
    """The `universe` command's lines."""
    lines = []
    for asset in universe["assets"]:
        line = f"{asset['name']} ({asset['asset_class']}, {asset['currency']}, threshold {asset['threshold']})"
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

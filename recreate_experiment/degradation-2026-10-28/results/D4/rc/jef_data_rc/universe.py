"""The declarative universe: strict loader and normaliser."""
from __future__ import annotations

import datetime as _dt
import tomllib
from importlib import resources

PACKAGED_LABEL = "packaged universe.toml"

PROVIDERS = ("eodhd", "binance", "yahoo-csv")
KINDS = ("eod",)
ASSET_TYPE_BY_CLASS = {"stock": "stock", "crypto": "crypto", "bond_etf": "etf"}
ASSET_TYPES = sorted(set(ASSET_TYPE_BY_CLASS.values()))
DEFAULT_EXCHANGE = {"eodhd": "eodhd", "binance": "binance", "yahoo-csv": "yahoo"}
DEFAULT_THRESHOLD = -0.05

TOP_KEYS = ("defaults", "asset")
DEFAULTS_KEYS = ("store", "currency")
ASSET_KEYS = ("name", "asset_class", "currency", "threshold", "enabled", "source")
SOURCE_KEYS = ("provider", "symbol", "path", "exchange", "start", "end",
               "kind", "enabled", "modeled", "note")


class UniverseError(ValueError):
    """A universe document that violates the grammar."""


def packaged_text() -> str:
    return resources.files("jef_data_rc").joinpath("universe.toml").read_text(encoding="utf-8")


def _unknown_keys(table: dict, allowed, where: str) -> None:
    unknown = sorted(k for k in table if k not in allowed)
    if unknown:
        raise UniverseError(f"{where}: unknown key(s) {unknown}; allowed: {sorted(allowed)}")


def _nonempty_str(value, key: str, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise UniverseError(f"{where}: {key} must be a non-empty string, got {value!r}")
    return value


def _required(table: dict, key: str, where: str):
    if key not in table:
        raise UniverseError(f"{where}: missing required key '{key}'")
    return table[key]


def _boolean(table: dict, key: str, where: str, default: bool) -> bool:
    if key not in table:
        return default
    value = table[key]
    if not isinstance(value, bool):
        raise UniverseError(f"{where}: {key} must be a boolean, got {value!r}")
    return value


def _iso_date(value, key: str, where: str):
    if value is None:
        return None
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


def _parse_source(src, n: int, asset_name: str, currency: str) -> dict:
    where = f"asset '{asset_name}' source #{n}"
    if not isinstance(src, dict):
        raise UniverseError(f"{where}: must be a table")
    _unknown_keys(src, SOURCE_KEYS, where)
    provider = _nonempty_str(_required(src, "provider", where), "provider", where)
    if provider not in PROVIDERS:
        raise UniverseError(f"{where}: unknown provider {provider!r}; allowed: {list(PROVIDERS)}")
    kind = src.get("kind", "eod")
    if kind not in KINDS:
        raise UniverseError(
            f"{where}: kind {kind!r} is not supported - only {list(KINDS)}; "
            "a non-EOD load is a new data contract, not a config value")
    symbol = _nonempty_str(_required(src, "symbol", where), "symbol", where)
    if provider == "eodhd" and "." not in symbol:
        raise UniverseError(
            f"{where}: eodhd symbols must be canonical TICKER.EXCHANGE (e.g. AAPL.US, "
            f"BTC-USD.CC), got {symbol!r} - bare tickers would blur store coordinates "
            "and the crypto/raw basis split")
    if "modeled" in src and not isinstance(src["modeled"], bool):
        raise UniverseError(f"{where}: modeled must be a boolean, got {src['modeled']!r}")
    modeled = src.get("modeled", False)
    enabled = _boolean(src, "enabled", where, True)
    if "exchange" in src:
        exchange = _nonempty_str(src["exchange"], "exchange", where)
    else:
        exchange = DEFAULT_EXCHANGE[provider]
    note = None
    if "note" in src:
        note = _nonempty_str(src["note"], "note", where)
    path = None
    if provider == "yahoo-csv":
        path = _nonempty_str(_required(src, "path", where), "path", where)
    elif "path" in src:
        _nonempty_str(src["path"], "path", where)
    start = _iso_date(src.get("start"), "start", where)
    end = _iso_date(src.get("end"), "end", where)
    if provider == "yahoo-csv":
        if "start" in src or "end" in src:
            raise UniverseError(
                f"{where}: start/end apply to collector sources only; a CSV import is whole-file")
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


def _modeled_rules(name: str, enabled: bool, sources: list) -> None:
    if any(s["modeled"] and not s["enabled"] for s in sources):
        raise UniverseError(f"asset '{name}': a modeled source must be enabled")
    live = [s for s in sources if s["enabled"]]
    modeled = [s for s in live if s["modeled"]]
    if len(modeled) >= 2:
        raise UniverseError(
            f"asset '{name}': exactly one enabled source may be modeled = true, got {len(modeled)}")
    if not enabled:
        return
    if len(live) >= 2 and not modeled:
        raise UniverseError(
            f"asset '{name}': {len(live)} enabled sources but none marked modeled = true - "
            "the binning's feeder must be deterministic (docs/DATA_CONTRACT.md SS7.7)")
    if not live:
        raise UniverseError(
            f"asset '{name}': enabled but has no enabled source - nothing would feed the "
            "binning; to pause the asset, set enabled = false on the asset itself")


def _parse_asset(raw, n: int, defaults: dict) -> dict:
    if not isinstance(raw, dict):
        raise UniverseError(f"asset #{n}: must be a table")
    _unknown_keys(raw, ASSET_KEYS, f"asset #{n}")
    name = _nonempty_str(_required(raw, "name", f"asset #{n}"), "name", f"asset #{n}")
    where = f"asset '{name}'"
    asset_class = _nonempty_str(_required(raw, "asset_class", where), "asset_class", where)
    if asset_class not in ASSET_TYPE_BY_CLASS:
        raise UniverseError(
            f"{where}: unknown asset_class {asset_class!r}; allowed: {sorted(ASSET_TYPE_BY_CLASS)}")
    threshold = DEFAULT_THRESHOLD
    if "threshold" in raw:
        value = raw["threshold"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise UniverseError(
                f"{where}: threshold must be a number (documentation only), got {value!r}")
        threshold = float(value)
    currency = defaults["currency"]
    if "currency" in raw:
        currency = _nonempty_str(raw["currency"], "currency", where)
    sources_raw = raw.get("source")
    if not isinstance(sources_raw, list) or not sources_raw:
        raise UniverseError(f"{where}: needs at least one [[asset.source]]")
    enabled = _boolean(raw, "enabled", where, True)
    sources = [_parse_source(src, i, name, currency) for i, src in enumerate(sources_raw, 1)]
    _modeled_rules(name, enabled, sources)
    return {"name": name, "asset_class": asset_class,
            "asset_type": ASSET_TYPE_BY_CLASS[asset_class], "currency": currency,
            "threshold": threshold, "enabled": enabled, "sources": sources}


def parse_universe(text: str, origin: str) -> dict:
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise UniverseError(f"{origin}: not valid TOML: {exc}") from None
    _unknown_keys(doc, TOP_KEYS, origin)
    defaults_raw = doc.get("defaults", {})
    if not isinstance(defaults_raw, dict):
        raise UniverseError(f"{origin}: [defaults] must be a table")
    _unknown_keys(defaults_raw, DEFAULTS_KEYS, f"{origin} [defaults]")
    defaults = {"store": "data", "currency": "USD"}
    for key in DEFAULTS_KEYS:
        if key in defaults_raw:
            defaults[key] = _nonempty_str(defaults_raw[key], key, "[defaults]")
    assets_raw = doc.get("asset")
    if not isinstance(assets_raw, list) or not assets_raw:
        raise UniverseError(f"{origin}: no [[asset]] entries")
    assets = [_parse_asset(raw, n, defaults) for n, raw in enumerate(assets_raw, 1)]
    names = [a["name"] for a in assets]
    dupes = sorted({x for x in names if names.count(x) > 1})
    if dupes:
        raise UniverseError(f"{origin}: duplicate asset name(s) {dupes}")
    owners: dict = {}
    for asset in assets:
        for src in asset["sources"]:
            coord = (src["exchange"], src["symbol"])
            owner = owners.setdefault(coord, asset["name"])
            if owner != asset["name"]:
                raise UniverseError(
                    f"{origin}: store series {coord[0]}/{coord[1]} is claimed by both "
                    f"{owner!r} and {asset['name']!r} - two assets may never write the same partition")
    return {"defaults": defaults, "assets": assets}


def load_universe(path=None) -> dict:
    if path is None:
        return parse_universe(packaged_text(), PACKAGED_LABEL)
    with open(path, "rb") as handle:
        raw = handle.read()
    return parse_universe(raw.decode("utf-8"), str(path))


def listing(universe: dict) -> list:
    lines = []
    for asset in universe["assets"]:
        line = f"{asset['name']} ({asset['asset_class']}, {asset['currency']}, threshold {asset['threshold']})"
        if not asset["enabled"]:
            line += " [disabled]"
        lines.append(line)
        for src in asset["sources"]:
            target = src["path"] if src["provider"] == "yahoo-csv" else src["symbol"]
            line = f"  {src['provider']}: {target}"
            if not src["enabled"]:
                line += " [disabled]"
            if "note" in src:
                line += f" - {src['note']}"
            lines.append(line)
    return lines

"""Declarative EOD acquisition universe: the single strict parser.

``load_universe()`` reads the packaged ``universe.toml`` (or an explicit
file) and returns one normalized document ``{"defaults", "assets"}`` with
every default resolved, so selection never re-interprets raw TOML.

The declared ``asset_class`` is authoritative configuration: it maps to the
store ``asset_type`` that drives price basis, corporate-action eligibility,
the crypto completed-day guard and the health calendar.
"""
from __future__ import annotations

import datetime as _dt
import re
import tomllib
from importlib import resources
from pathlib import Path

PROVIDERS = ("eodhd", "binance", "yahoo-csv")
COLLECTOR_PROVIDERS = ("eodhd", "binance")
DEFAULT_EXCHANGE = {"eodhd": "eodhd", "binance": "binance", "yahoo-csv": "yahoo"}
KINDS = ("eod",)
ASSET_TYPE_BY_CLASS = {"stock": "stock", "bond_etf": "etf", "crypto": "crypto"}

DEFAULT_STORE = "data"
DEFAULT_CURRENCY = "USD"

_TOP_KEYS = frozenset({"defaults", "asset"})
_DEFAULTS_KEYS = frozenset({"store", "currency"})
_ASSET_KEYS = frozenset(
    {"name", "asset_class", "currency", "threshold", "enabled", "source"}
)
_SOURCE_KEYS = frozenset(
    {
        "provider",
        "symbol",
        "path",
        "exchange",
        "start",
        "end",
        "kind",
        "enabled",
        "modeled",
        "note",
    }
)

_CANONICAL_EODHD = re.compile(r"^[^\s.][^\s]*\.[A-Za-z0-9]+$")


class UniverseError(ValueError):
    """A universe declaration is malformed or inconsistent."""


def packaged_universe_path() -> Path:
    return Path(str(resources.files("jef_data_rc").joinpath("universe.toml")))


def _unknown(where: str, table: dict, allowed: frozenset) -> None:
    extra = sorted(set(table) - allowed)
    if extra:
        raise UniverseError(f"{where}: unknown key(s): {', '.join(extra)}")


def _string(where: str, table: dict, key: str, *, required: bool) -> str | None:
    if key not in table:
        if required:
            raise UniverseError(f"{where}: missing required key '{key}'")
        return None
    value = table[key]
    if not isinstance(value, str) or not value.strip():
        raise UniverseError(f"{where}: '{key}' must be a non-empty string")
    return value


def _flag(where: str, table: dict, key: str, default: bool) -> bool:
    if key not in table:
        return default
    value = table[key]
    if not isinstance(value, bool):
        raise UniverseError(f"{where}: '{key}' must be a boolean")
    return value


def _iso_date(where: str, table: dict, key: str) -> str | None:
    if key not in table:
        return None
    value = table[key]
    if isinstance(value, _dt.datetime):
        raise UniverseError(f"{where}: '{key}' must be a date, not a datetime")
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError(value)
            return _dt.date.fromisoformat(value).isoformat()
        except ValueError:
            pass
    raise UniverseError(f"{where}: '{key}' must be an ISO date (YYYY-MM-DD)")


def _parse_source(where: str, raw, asset_currency: str) -> dict:
    if not isinstance(raw, dict):
        raise UniverseError(f"{where}: must be a table")
    _unknown(where, raw, _SOURCE_KEYS)
    provider = _string(where, raw, "provider", required=True)
    if provider not in PROVIDERS:
        raise UniverseError(
            f"{where}: unsupported provider '{provider}' "
            f"(supported: {', '.join(PROVIDERS)})"
        )
    symbol = _string(where, raw, "symbol", required=True)
    exchange = _string(where, raw, "exchange", required=False)
    if exchange is None:
        exchange = DEFAULT_EXCHANGE[provider]
    kind = _string(where, raw, "kind", required=False) or "eod"
    if kind not in KINDS:
        raise UniverseError(f"{where}: unsupported kind '{kind}' (only 'eod')")
    path = _string(where, raw, "path", required=False)
    start = _iso_date(where, raw, "start")
    end = _iso_date(where, raw, "end")
    if provider == "yahoo-csv":
        if path is None:
            raise UniverseError(f"{where}: a yahoo-csv source requires 'path'")
        if start is not None or end is not None:
            raise UniverseError(
                f"{where}: a yahoo-csv source cannot have 'start' or 'end'"
            )
    else:
        if path is not None:
            raise UniverseError(f"{where}: a {provider} source cannot have 'path'")
        if start is not None and end is not None and start > end:
            raise UniverseError(f"{where}: start {start} is after end {end}")
    if provider == "eodhd" and not _CANONICAL_EODHD.match(symbol):
        raise UniverseError(
            f"{where}: eodhd symbol '{symbol}' must be canonical TICKER.EXCHANGE"
        )
    note = _string(where, raw, "note", required=False)
    return {
        "provider": provider,
        "exchange": exchange,
        "symbol": symbol,
        "path": path,
        "start": start,
        "end": end,
        "kind": kind,
        "enabled": _flag(where, raw, "enabled", True),
        "modeled": _flag(where, raw, "modeled", False),
        "note": note,
        "currency": asset_currency,
    }


def _parse_asset(where: str, raw, default_currency: str) -> dict:
    if not isinstance(raw, dict):
        raise UniverseError(f"{where}: must be a table")
    _unknown(where, raw, _ASSET_KEYS)
    name = _string(where, raw, "name", required=True)
    where = f"{where} '{name}'"
    asset_class = _string(where, raw, "asset_class", required=True)
    if asset_class not in ASSET_TYPE_BY_CLASS:
        raise UniverseError(
            f"{where}: unsupported asset_class '{asset_class}' "
            f"(supported: {', '.join(ASSET_TYPE_BY_CLASS)})"
        )
    currency = _string(where, raw, "currency", required=False) or default_currency
    threshold = None
    if "threshold" in raw:
        value = raw["threshold"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise UniverseError(f"{where}: 'threshold' must be numeric")
        threshold = float(value)
    enabled = _flag(where, raw, "enabled", True)
    sources_raw = raw.get("source")
    if not sources_raw:
        raise UniverseError(f"{where}: missing [[asset.source]] tables")
    if not isinstance(sources_raw, list):
        raise UniverseError(f"{where}: 'source' must be an array of tables")
    sources = [
        _parse_source(f"{where} source[{i}]", src, currency)
        for i, src in enumerate(sources_raw)
    ]
    for i, src in enumerate(sources):
        if src["modeled"] and not src["enabled"]:
            raise UniverseError(
                f"{where} source[{i}]: a disabled source cannot be modeled"
            )
    live = [s for s in sources if s["enabled"]]
    modeled = [s for s in live if s["modeled"]]
    if len(modeled) > 1:
        raise UniverseError(f"{where}: more than one enabled source is modeled")
    if enabled:
        if not live:
            raise UniverseError(f"{where}: an enabled asset needs an enabled source")
        if len(live) > 1 and not modeled:
            raise UniverseError(
                f"{where}: {len(live)} enabled sources but none is marked "
                "modeled = true"
            )
    return {
        "name": name,
        "asset_class": asset_class,
        "asset_type": ASSET_TYPE_BY_CLASS[asset_class],
        "currency": currency,
        "threshold": threshold,
        "enabled": enabled,
        "sources": sources,
    }


def parse_universe(document: dict, label: str = "universe") -> dict:
    """Normalize an already-decoded TOML document."""
    if not isinstance(document, dict):
        raise UniverseError(f"{label}: must be a TOML table")
    _unknown(label, document, _TOP_KEYS)
    defaults_raw = document.get("defaults", {})
    if not isinstance(defaults_raw, dict):
        raise UniverseError(f"{label}: [defaults] must be a table")
    where = f"{label}: defaults"
    _unknown(where, defaults_raw, _DEFAULTS_KEYS)
    defaults = {
        "store": _string(where, defaults_raw, "store", required=False)
        or DEFAULT_STORE,
        "currency": _string(where, defaults_raw, "currency", required=False)
        or DEFAULT_CURRENCY,
    }
    assets_raw = document.get("asset")
    if not assets_raw:
        raise UniverseError(f"{label}: no [[asset]] tables")
    if not isinstance(assets_raw, list):
        raise UniverseError(f"{label}: 'asset' must be an array of tables")
    assets = [
        _parse_asset(f"{label}: asset[{i}]", raw, defaults["currency"])
        for i, raw in enumerate(assets_raw)
    ]
    seen_names: set[str] = set()
    owners: dict[tuple[str, str], str] = {}
    for asset in assets:
        if asset["name"] in seen_names:
            raise UniverseError(f"{label}: duplicate asset name '{asset['name']}'")
        seen_names.add(asset["name"])
        for src in asset["sources"]:
            coord = (src["exchange"], src["symbol"])
            if coord in owners:
                raise UniverseError(
                    f"{label}: store coordinate {coord[0]}:{coord[1]} is claimed "
                    f"by both '{owners[coord]}' and '{asset['name']}'"
                )
            owners[coord] = asset["name"]
    return {"defaults": defaults, "assets": assets}


def load_universe(path: str | Path | None = None) -> dict:
    """Load and normalize the packaged universe, or the file at ``path``."""
    if path is None:
        source = packaged_universe_path()
        label = "universe.toml"
    else:
        source = Path(path)
        label = str(path)
    try:
        data = source.read_bytes()
    except OSError as exc:
        raise UniverseError(f"{label}: cannot read: {exc.strerror or exc}") from exc
    try:
        document = tomllib.loads(data.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise UniverseError(f"{label}: invalid TOML: {exc}") from exc
    return parse_universe(document, label)


def modeled_source(universe: dict, name: str) -> tuple[dict, dict]:
    """The ``(asset, source)`` pair that feeds the model for asset ``name``."""
    for asset in universe["assets"]:
        if asset["name"] != name:
            continue
        if not asset["enabled"]:
            raise UniverseError(f"asset '{name}' is disabled")
        live = [s for s in asset["sources"] if s["enabled"]]
        if len(live) == 1:
            return asset, live[0]
        for src in live:
            if src["modeled"]:
                return asset, src
        raise UniverseError(f"asset '{name}' has no modeled source")
    raise UniverseError(f"unknown asset '{name}'")

"""The declarative EOD acquisition universe.

`load_universe()` is the only parser. It reads the packaged `universe.toml`
(or an explicit path), rejects unknown keys at every level, and returns a
normalized `{"defaults": ..., "assets": [...]}` document whose sources carry
resolved store coordinates, currency and ISO dates.
"""

from __future__ import annotations

import datetime as _dt
import re
import tomllib
from importlib import resources
from pathlib import Path
from typing import Any

PROVIDERS = ("eodhd", "binance", "yahoo-csv")
COLLECTOR_PROVIDERS = ("eodhd", "binance")
DEFAULT_EXCHANGE = {"eodhd": "eodhd", "binance": "binance", "yahoo-csv": "yahoo"}
ASSET_TYPE_BY_CLASS = {"stock": "stock", "bond_etf": "etf", "crypto": "crypto"}
KINDS = ("eod",)

DEFAULT_STORE = "data"
DEFAULT_CURRENCY = "USD"

TOP_KEYS = ("defaults", "asset")
DEFAULTS_KEYS = ("store", "currency")
ASSET_KEYS = ("name", "asset_class", "currency", "threshold", "enabled", "source")
SOURCE_KEYS = (
    "provider", "symbol", "path", "exchange", "start", "end",
    "kind", "enabled", "modeled", "note",
)

_EODHD_SYMBOL = re.compile(r"^[^.\s]+\.[A-Za-z0-9]+$")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class UniverseError(ValueError):
    """A universe declaration is malformed or inconsistent."""


def _check_keys(table: dict, allowed: tuple[str, ...], where: str) -> None:
    unknown = sorted(k for k in table if k not in allowed)
    if unknown:
        raise UniverseError(f"{where}: unknown key(s): {', '.join(unknown)}")


def _string(value: Any, where: str, key: str, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise UniverseError(f"{where}: missing required key '{key}'")
        return None
    if not isinstance(value, str) or not value.strip():
        raise UniverseError(f"{where}: '{key}' must be a non-empty string")
    return value


def _bool(value: Any, where: str, key: str, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise UniverseError(f"{where}: '{key}' must be a boolean")
    return value


def _date(value: Any, where: str, key: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, _dt.datetime):
        raise UniverseError(f"{where}: '{key}' must be a date, not a datetime")
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, str) and _ISO_DATE.match(value):
        try:
            return _dt.date.fromisoformat(value).isoformat()
        except ValueError:
            pass
    raise UniverseError(f"{where}: '{key}' must be an ISO date (YYYY-MM-DD), got {value!r}")


def _normalize_source(raw: Any, asset_where: str, index: int, currency: str) -> dict:
    where = f"{asset_where} source[{index}]"
    if not isinstance(raw, dict):
        raise UniverseError(f"{where}: must be a table")
    _check_keys(raw, SOURCE_KEYS, where)
    provider = _string(raw.get("provider"), where, "provider", required=True)
    if provider not in PROVIDERS:
        raise UniverseError(
            f"{where}: unsupported provider {provider!r} (supported: {', '.join(PROVIDERS)})"
        )
    symbol = _string(raw.get("symbol"), where, "symbol", required=True)
    kind = raw.get("kind", "eod")
    if kind not in KINDS:
        raise UniverseError(f"{where}: unsupported kind {kind!r} (only 'eod' is supported)")
    exchange = _string(raw.get("exchange"), where, "exchange") or DEFAULT_EXCHANGE[provider]
    path = _string(raw.get("path"), where, "path")
    start = _date(raw.get("start"), where, "start")
    end = _date(raw.get("end"), where, "end")
    note = raw.get("note")
    if note is not None and not isinstance(note, str):
        raise UniverseError(f"{where}: 'note' must be a string")
    if provider == "yahoo-csv":
        if path is None:
            raise UniverseError(f"{where}: a yahoo-csv source requires 'path'")
        if start is not None or end is not None:
            raise UniverseError(f"{where}: a yahoo-csv source cannot have 'start' or 'end'")
    else:
        if path is not None:
            raise UniverseError(f"{where}: a {provider} source cannot have 'path'")
        if start is not None and end is not None and start > end:
            raise UniverseError(f"{where}: start {start} follows end {end}")
    if provider == "eodhd" and not _EODHD_SYMBOL.match(symbol):
        raise UniverseError(
            f"{where}: EODHD symbol {symbol!r} must be canonical TICKER.EXCHANGE (e.g. AAPL.US)"
        )
    return {
        "provider": provider,
        "symbol": symbol,
        "exchange": exchange,
        "path": path,
        "start": start,
        "end": end,
        "kind": kind,
        "enabled": _bool(raw.get("enabled"), where, "enabled", True),
        "modeled": _bool(raw.get("modeled"), where, "modeled", False),
        "note": note,
        "currency": currency,
    }


def _normalize_asset(raw: Any, index: int, defaults: dict) -> dict:
    where = f"asset[{index}]"
    if not isinstance(raw, dict):
        raise UniverseError(f"{where}: must be a table")
    _check_keys(raw, ASSET_KEYS, where)
    name = _string(raw.get("name"), where, "name", required=True)
    where = f"asset[{index}] {name!r}"
    asset_class = _string(raw.get("asset_class"), where, "asset_class", required=True)
    if asset_class not in ASSET_TYPE_BY_CLASS:
        raise UniverseError(
            f"{where}: unsupported asset_class {asset_class!r} "
            f"(supported: {', '.join(ASSET_TYPE_BY_CLASS)})"
        )
    currency = _string(raw.get("currency"), where, "currency") or defaults["currency"]
    threshold = raw.get("threshold")
    if threshold is not None:
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
            raise UniverseError(f"{where}: 'threshold' must be a number")
        threshold = float(threshold)
    enabled = _bool(raw.get("enabled"), where, "enabled", True)
    sources_raw = raw.get("source")
    if sources_raw is None:
        raise UniverseError(f"{where}: missing [[asset.source]] table(s)")
    if not isinstance(sources_raw, list) or not sources_raw:
        raise UniverseError(f"{where}: 'source' must be a non-empty array of tables")
    sources = [_normalize_source(s, where, i, currency) for i, s in enumerate(sources_raw)]

    for i, src in enumerate(sources):
        if src["modeled"] and not src["enabled"]:
            raise UniverseError(f"{where} source[{i}]: a disabled source cannot be modeled")
    enabled_sources = [s for s in sources if s["enabled"]]
    modeled = [s for s in enabled_sources if s["modeled"]]
    if len(modeled) > 1:
        raise UniverseError(f"{where}: more than one enabled source is marked modeled = true")
    if enabled:
        if not enabled_sources:
            raise UniverseError(f"{where}: an enabled asset needs at least one enabled source")
        if len(enabled_sources) > 1 and not modeled:
            raise UniverseError(
                f"{where}: {len(enabled_sources)} enabled sources but none is marked modeled = true"
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


def _read(path: str | Path | None) -> tuple[dict, str]:
    if path is None:
        text = resources.files("jef_data_rc").joinpath("universe.toml").read_text(encoding="utf-8")
        label = "packaged universe.toml"
    else:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            raise UniverseError(f"cannot read universe {path}: {exc}") from exc
        label = str(path)
    try:
        return tomllib.loads(text), label
    except tomllib.TOMLDecodeError as exc:
        raise UniverseError(f"{label}: invalid TOML: {exc}") from exc


def load_universe(path: str | Path | None = None) -> dict:
    """Parse and validate a universe declaration into its normalized form."""
    doc, _label = _read(path)
    _check_keys(doc, TOP_KEYS, "universe")
    defaults_raw = doc.get("defaults", {})
    if not isinstance(defaults_raw, dict):
        raise UniverseError("defaults: must be a table")
    _check_keys(defaults_raw, DEFAULTS_KEYS, "defaults")
    defaults = {
        "store": _string(defaults_raw.get("store"), "defaults", "store") or DEFAULT_STORE,
        "currency": _string(defaults_raw.get("currency"), "defaults", "currency") or DEFAULT_CURRENCY,
    }
    assets_raw = doc.get("asset", [])
    if not isinstance(assets_raw, list):
        raise UniverseError("asset: must be an array of tables ([[asset]])")
    assets = [_normalize_asset(a, i, defaults) for i, a in enumerate(assets_raw)]

    seen_names: dict[str, int] = {}
    coords: dict[tuple[str, str], str] = {}
    for i, asset in enumerate(assets):
        if asset["name"] in seen_names:
            raise UniverseError(
                f"asset[{i}] {asset['name']!r}: duplicate asset name "
                f"(also asset[{seen_names[asset['name']]}])"
            )
        seen_names[asset["name"]] = i
        for j, src in enumerate(asset["sources"]):
            coord = (src["exchange"], src["symbol"])
            if coord in coords:
                raise UniverseError(
                    f"asset[{i}] {asset['name']!r} source[{j}]: store coordinate "
                    f"{coord[0]}/{coord[1]} is already claimed by asset {coords[coord]!r}"
                )
            coords[coord] = asset["name"]
    return {"defaults": defaults, "assets": assets}


def modeled_source(universe: dict, name: str) -> tuple[dict, dict]:
    """Return the `(asset, source)` pair that feeds the model for `name`."""
    for asset in universe["assets"]:
        if asset["name"] != name:
            continue
        if not asset["enabled"]:
            raise UniverseError(f"asset {name!r} is disabled")
        enabled = [s for s in asset["sources"] if s["enabled"]]
        modeled = [s for s in enabled if s["modeled"]]
        if modeled:
            return asset, modeled[0]
        if len(enabled) == 1:
            return asset, enabled[0]
        raise UniverseError(f"asset {name!r} has no modeled source")
    raise UniverseError(f"unknown asset {name!r}")

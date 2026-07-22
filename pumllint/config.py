"""Configuration loading: pumllint.yaml / .toml / .json, or explicit path."""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_NAMES = ("pumllint.yaml", "pumllint.yml", "pumllint.toml", "pumllint.json")


def load_config(path: str | Path | None = None, cwd: str | Path = ".") -> dict:
    if path is None:
        for name in DEFAULT_NAMES:
            candidate = Path(cwd) / name
            if candidate.exists():
                path = candidate
                break
        else:
            return {}
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    suffix = p.suffix.lower()
    if suffix in (".yaml", ".yml"):
        import yaml  # optional dependency; only needed for YAML configs

        return yaml.safe_load(text) or {}
    if suffix == ".toml":
        import tomllib

        return tomllib.loads(text)
    if suffix == ".json":
        return json.loads(text)
    raise ValueError(f"Unsupported config format: {p}")

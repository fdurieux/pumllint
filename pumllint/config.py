"""Configuration loading: pumllint.yaml / .toml / .json, or explicit path."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from .textio import read_text_file

DEFAULT_NAMES = ("pumllint.yaml", "pumllint.yml", "pumllint.toml", "pumllint.json")

# Every key the product reads off the config root. `rules` is consumed in
# engine._rule_config, `profile`/`profiles` in Engine.__init__, `suppressions`
# in Engine, `scoring` in cli._run_score.
KNOWN_TOP_LEVEL = ("profile", "profiles", "rules", "scoring", "suppressions")

# Legal inside every rule table, whatever the rule declares: `severity` is
# popped by Rule.__init__, `enabled` is consumed by engine._rule_config (a
# table-form disable) and never reaches the rule.
GENERIC_RULE_KEYS = frozenset({"severity", "enabled"})


def config_warnings(cfg: dict, rules: Mapping[str, type]) -> list[str]:
    """Keys the config sets that nothing will ever read.

    Returned rather than printed so the caller routes them through ``_err``
    (all CLI output goes through the encoding-safe helpers). These are
    warnings, not errors: a typo here is worth saying out loud, but promoting
    it to exit 2 would change the hardest contract this project has, and
    nobody has asked for that. See ROADMAP "Settled questions" §6.6.

    Three disclosures, each for a key that is silently ignored otherwise:
    an unknown top-level key; a rule id or name no rule carries (`[rules]`
    accepts either, in any case); and, inside a rule's table, an option the
    rule does not take — checked against the ``option_keys`` every rule
    class carries from ``catalog.toml`` (its ``options`` plus each
    ``lexicons`` entry as ``<k>`` and ``extra_<k>``), so a typo'd cap key or
    dormancy pattern no longer reads as "the cap never binds" or "the rule
    is off". *rules* is ``discover()``'s mapping.
    """
    out: list[str] = []
    unknown_top = sorted(k for k in cfg if k not in KNOWN_TOP_LEVEL)
    if unknown_top:
        named = ", ".join(repr(k) for k in unknown_top)
        out.append(
            f"warning: config sets unknown top-level key(s) {named} — "
            f"nothing reads them (known: {', '.join(KNOWN_TOP_LEVEL)})"
        )
    rules_cfg = cfg.get("rules")
    if isinstance(rules_cfg, dict):
        by_key: dict[str, type] = {}
        for rid, cls in rules.items():
            by_key[rid.lower()] = cls
            by_key[str(cls.name).lower()] = cls
        unknown = sorted(k for k in rules_cfg if str(k).lower() not in by_key)
        if unknown:
            named = ", ".join(repr(k) for k in unknown)
            out.append(
                f"warning: config names unknown rule(s) {named} — no such rule "
                "id or name, so the entry has no effect (`pumllint --list-rules`)"
            )
        for key, value in rules_cfg.items():
            cls = by_key.get(str(key).lower())
            if cls is None or not isinstance(value, dict):
                continue
            legal = cls.option_keys | GENERIC_RULE_KEYS
            bad = sorted(str(k) for k in value if str(k) not in legal)
            if bad:
                named = ", ".join(repr(k) for k in bad)
                takes = (
                    f"this rule takes: {', '.join(sorted(cls.option_keys))}"
                    if cls.option_keys
                    else "this rule takes no options"
                )
                out.append(
                    f"warning: config sets unknown option(s) {named} for "
                    f"{cls.id} ({cls.name}) — {takes}"
                )
    return out


def _as_mapping(cfg, p: Path) -> dict:
    """A config whose root is not a mapping is a config error, not a crash.

    A YAML document that is a list, or a JSON file holding a bare array,
    otherwise reaches ``Engine.__init__`` and dies on ``.get`` — escaping as
    exit 1, which CI reads as lint findings.
    """
    if not isinstance(cfg, dict):
        raise ValueError(
            f"config file {p} must contain a mapping at the top level, "
            f"got {type(cfg).__name__}"
        )
    return cfg


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
    text = read_text_file(p, kind="config file")
    suffix = p.suffix.lower()
    if suffix in (".yaml", ".yml"):
        try:
            import yaml  # optional dependency; only needed for YAML configs
        except ImportError:
            raise ValueError(
                f"config file {p} is YAML but PyYAML is not installed — "
                f"install with `pip install pumllint[yaml]`, or use a "
                f".toml/.json config; in a pre-commit hook, add "
                f"`additional_dependencies: [PyYAML]`"
            ) from None
        return _as_mapping(yaml.safe_load(text) or {}, p)
    if suffix == ".toml":
        import tomllib

        return _as_mapping(tomllib.loads(text), p)
    if suffix == ".json":
        return _as_mapping(json.loads(text), p)
    raise ValueError(f"Unsupported config format: {p}")

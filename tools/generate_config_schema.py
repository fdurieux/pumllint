#!/usr/bin/env python3
"""Generate ``pumllint/schemas/config.schema.json`` from the rule catalog.

The configuration file (``pumllint.toml`` / ``.yaml`` / ``.json``) is the one
input whose shape the code already declares: every rule's option keys and
their types live in ``pumllint/rules/catalog.toml``, the generic keys in
``pumllint.config``, the profile and scoring keys in ``engine.py`` and
``scoring.py``. This script turns that declaration into a JSON Schema (draft
2020-12) so an editor or a CI step can reject a misspelled key, a wrong type
or a section that does not exist *before* pumllint runs — where today an
unknown key is a stderr warning at run time.

The schema is a pinned shape like the three report schemas: static, shipped
as package data, printed by ``pumllint schema config``, and drift-guarded by
``tests/test_schema.py``, which re-derives it in memory and diffs::

    python tools/generate_config_schema.py      # rewrite the shipped file

What it cannot express, on purpose: pumllint also accepts a rule key in any
letter case (``gen009``) — the schema lists the canonical id and kebab-case
name only; the dimension weights must sum to 1.0; option defaults are the
code's, not the catalog's. Null is never a legal *option* value, so no option
is nullable here; a null *rule* value is legal (it means defaults, the way a
YAML key with no value reads) and is listed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pumllint.model import Dimension, Severity  # noqa: E402
from pumllint.rules import OPTION_TYPES, discover  # noqa: E402

TARGET = ROOT / "pumllint" / "schemas" / "config.schema.json"
SCHEMA_ID = "https://raw.githubusercontent.com/fdurieux/pumllint/main/pumllint/schemas/config.schema.json"

_REGEX = {"type": "string", "description": "A Python regular expression"}
_TYPE_SCHEMAS: dict[str, dict] = {
    "boolean": {"type": "boolean"},
    "integer": {"type": "integer"},
    "number": {"type": "number"},
    "string": {"type": "string"},
    "regex": _REGEX,
    "list": {"type": "array", "items": {"type": "string"}},
    "map": {"type": "object", "additionalProperties": {"type": "string"}},
    "map-integer": {"type": "object", "additionalProperties": {"type": "integer"}},
    "map-regex": {"type": "object", "additionalProperties": dict(_REGEX)},
}
assert set(_TYPE_SCHEMAS) == set(OPTION_TYPES), "type vocabulary drifted"

_SCALAR_FORMS = ["on", "off", "enabled", "disabled"]


def _rule_def(cls) -> dict:
    props: dict[str, dict] = {
        "enabled": {
            "type": "boolean",
            "description": "false switches the rule off; the other keys are then ignored",
        },
        "severity": {"$ref": "#/$defs/severity"},
    }
    for key in sorted(cls.option_keys):
        node = dict(_TYPE_SCHEMAS[cls.option_types[key]])
        if key.startswith("extra_") and key[6:] in cls.option_keys:
            node["description"] = f"Extends the shipped '{key[6:]}' list"
        elif f"extra_{key}" in cls.option_keys:
            node["description"] = "Replaces the shipped list"
        if key in cls.dormant_unless:
            node["description"] = (
                node.get("description", "").rstrip(".")
                + (" — " if node.get("description") else "")
                + "the rule is dormant until this (or a sibling gate key) is set"
            )
        props[key] = node
    gated = f" (profile: {', '.join(cls.profiles)})" if cls.profiles else ""
    description = f"{cls.id} {cls.name}: {cls.description}{gated}"
    return {
        "description": description,
        "anyOf": [
            {"type": "boolean", "description": "true = defaults, false = off"},
            {"type": "null", "description": "Same as true (a YAML/JSON key with no value)"},
            {"type": "string", "enum": _SCALAR_FORMS},
            {"type": "object", "properties": props, "additionalProperties": False},
        ],
    }


def build_schema() -> dict:
    rules = discover()
    severities = [s.value for s in Severity]
    scored = [d.value for d in Dimension if d is not Dimension.SYNTAX]

    defs: dict[str, dict] = {
        "severity": {"type": "string", "enum": severities},
        "profile": {
            "type": "object",
            "description": "A named profile: which gated rules it pulls in and which severities it raises",
            "properties": {
                "enable": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Rule ids or kebab-case names to enable under this profile",
                },
                "escalate": {
                    "type": "object",
                    "additionalProperties": {"$ref": "#/$defs/severity"},
                    "description": "Rule id or name → severity; wins over the rule's own severity",
                },
            },
            "additionalProperties": False,
        },
        "scoring": {
            "type": "object",
            "description": "Settings read by `pumllint score` only (SCORING.md)",
            "properties": {
                "syntax_gate": {
                    "type": "boolean",
                    "description": "Run the DIM-SYN syntax gate on every score run, as --check-syntax does",
                },
                "syntax_command": {
                    "type": "string",
                    "description": (
                        "The command the syntax gate executes (default 'plantuml'). pumllint runs it: "
                        "do not run pumllint with an auto-detected config inside a checkout you do not trust"
                    ),
                },
                "k": {"type": "number", "description": "The composite's saturation constant (default 50)"},
                "severity_weights": {
                    "type": "object",
                    "properties": {s: {"type": "number"} for s in severities},
                    "additionalProperties": False,
                },
                "dimension_weights": {
                    "type": "object",
                    "description": "Must sum to 1.0 (checked at run time, not here)",
                    "properties": {d: {"type": "number"} for d in scored},
                    "additionalProperties": False,
                },
                "thresholds": {
                    "type": "object",
                    "properties": {
                        "l2_composite": {"type": "number"},
                        "l3_composite": {"type": "number"},
                        "l4_composite": {"type": "number"},
                        "l4_dim_min": {"type": "number"},
                        "l5_composite": {"type": "number"},
                        "l5_dim_min": {"type": "number"},
                        "c3_dim_floor": {"type": "number"},
                        "l4_min_elements": {"type": "integer", "minimum": 0},
                    },
                    "additionalProperties": False,
                },
                "l5_requires_profile": {
                    "type": ["string", "boolean"],
                    "description": "The profile Level 5 requires (default 'codegen'); false disables the requirement",
                },
                "c7_requires_applicable_rules": {"type": "boolean"},
                "deduplicate_findings": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
    }
    rule_props: dict[str, dict] = {}
    for rule_id in sorted(rules):
        cls = rules[rule_id]
        defs[rule_id] = _rule_def(cls)
        rule_props[rule_id] = {"$ref": f"#/$defs/{rule_id}"}
        rule_props[cls.name] = {"$ref": f"#/$defs/{rule_id}"}

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": SCHEMA_ID,
        "title": "pumllint configuration",
        "description": (
            "The shape of pumllint.toml / pumllint.yaml / pumllint.json (README § Configuration). "
            "Generated from the rule catalog by tools/generate_config_schema.py; a public contract, "
            "changes are deliberate and release-noted (drift-guarded by tests/test_schema.py). "
            "Rules are keyed by canonical id or kebab-case name — pumllint itself also accepts "
            "other letter cases, and reports an unknown key as a warning rather than an error; "
            "this schema is stricter on both counts by design. Null is never a legal option value."
        ),
        "type": "object",
        "properties": {
            "profile": {
                "type": "string",
                "description": "The active profile (built-in: codegen); --profile overrides",
            },
            "profiles": {
                "type": "object",
                "additionalProperties": {"$ref": "#/$defs/profile"},
            },
            "rules": {
                "type": "object",
                "description": "One entry per rule, by id or kebab-case name: false/off, true/on, or a table of options",
                "properties": rule_props,
                "additionalProperties": False,
            },
            "scoring": {"$ref": "#/$defs/scoring"},
            "suppressions": {
                "type": "boolean",
                "description": "Honour inline ' pumllint: disable comments (default true); --no-suppressions overrides",
            },
        },
        "additionalProperties": False,
        "$defs": defs,
    }


def render() -> str:
    return json.dumps(build_schema(), indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        print(__doc__, file=sys.stderr)
        return 2
    TARGET.write_text(render(), encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

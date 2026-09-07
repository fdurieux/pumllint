"""JSON Schemas for the machine-readable report formats and the config file.

The ``-f json`` outputs of the lint, score and trace commands are public
contracts — CI scripts and integrations parse them — and the schemas under
``schemas/`` pin those shapes the way ``tests/golden_scores.json`` pins the
scores: changes must be deliberate. The files are shipped as package data,
printed by ``pumllint schema {lint,score,trace,config}``, and drift-guarded
by tests/test_schema.py, which validates real reporter output against them.

``config`` is the one input schema: what ``pumllint.toml`` / ``.yaml`` /
``.json`` may contain, generated from the rule catalog by
``tools/generate_config_schema.py`` (regenerate after changing a rule's
declared options; the drift guard fails otherwise). It is for editors and
external validators — pumllint's own loader keeps warning on unknown keys
rather than failing.

The badge and sonar formats are deliberately not covered: those shapes are
shields.io's and SonarQube's contracts, not pumllint's.

:func:`validate` is a deliberately small JSON Schema (draft 2020-12)
validator covering exactly the keyword subset the shipped schemas use — the
zero-dependency promise rules out ``jsonschema``. It refuses schemas that
use anything outside that subset: silently ignoring an unknown keyword
would turn the drift guard into a rubber stamp.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_NAMES = ("lint", "score", "trace", "config")

_SCHEMA_DIR = Path(__file__).parent / "schemas"

# Keywords whose value is (or contains) subschemas to recurse into, vs.
# plain data-valued keywords, vs. annotations carrying no constraints.
_MAP_OF_SCHEMAS = {"properties", "$defs"}
_SINGLE_SCHEMA = {"items", "additionalProperties"}
_LIST_OF_SCHEMAS = {"anyOf"}
_DATA_KEYWORDS = {"$ref", "type", "enum", "const", "required", "minimum", "maximum"}
_ANNOTATIONS = {"$schema", "$id", "title", "description", "examples", "default"}


def load_schema(name: str) -> dict:
    """The shipped schema for ``name`` (one of :data:`SCHEMA_NAMES`)."""
    if name not in SCHEMA_NAMES:
        raise ValueError(
            f"Unknown schema '{name}'. Available: {', '.join(SCHEMA_NAMES)}"
        )
    path = _SCHEMA_DIR / f"{name}.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate(instance: Any, schema: dict) -> list[str]:
    """Validate ``instance`` against ``schema``; empty list means valid.

    Errors are human-readable strings anchored with a JSONPath-style
    location, e.g. ``$.diagrams[0].maturity.level: expected integer, ...``.
    Raises ``ValueError`` if the schema uses a keyword outside the supported
    subset (extend the validator before extending the schemas).
    """
    _assert_supported(schema)
    errors: list[str] = []
    _validate(instance, schema, schema, "$", errors)
    return errors


def _assert_supported(node: Any) -> None:
    if not isinstance(node, dict):
        return
    for key, value in node.items():
        if key in _MAP_OF_SCHEMAS:
            for sub in value.values():
                _assert_supported(sub)
        elif key in _SINGLE_SCHEMA:
            _assert_supported(value)
        elif key in _LIST_OF_SCHEMAS:
            for sub in value:
                _assert_supported(sub)
        elif key not in _DATA_KEYWORDS and key not in _ANNOTATIONS:
            raise ValueError(
                f"unsupported JSON Schema keyword '{key}' — extend "
                f"pumllint.schema.validate before using it in a schema"
            )


def _resolve(ref: str, root: dict) -> dict:
    if not ref.startswith("#/"):
        raise ValueError(f"only local '#/...' $refs are supported, got '{ref}'")
    node: Any = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _type_ok(value: Any, t: str) -> bool:
    # bool is excluded from integer/number: it subclasses int in Python but
    # is a distinct JSON type.
    if t == "null":
        return value is None
    if t == "boolean":
        return isinstance(value, bool)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "string":
        return isinstance(value, str)
    if t == "array":
        return isinstance(value, list)
    if t == "object":
        return isinstance(value, dict)
    raise ValueError(f"unsupported type '{t}' in schema")


def _validate(value: Any, schema: dict, root: dict, path: str, errors: list[str]) -> None:
    if "$ref" in schema:
        _validate(value, _resolve(schema["$ref"], root), root, path, errors)
        return

    if "anyOf" in schema:
        _validate_any_of(value, schema["anyOf"], root, path, errors)
        return

    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_ok(value, t) for t in types):
            errors.append(
                f"{path}: expected {' | '.join(types)}, got {type(value).__name__}"
            )
            return  # further keywords assume the right type

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} is not one of {schema['enum']!r}")
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: {value!r} != {schema['const']!r}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} is below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} is above maximum {schema['maximum']}")

    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}: missing required property '{req}'")
        props = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, sub in value.items():
            if key in props:
                _validate(sub, props[key], root, f"{path}.{key}", errors)
            elif additional is False:
                errors.append(f"{path}: unexpected property '{key}'")
            elif isinstance(additional, dict):
                _validate(sub, additional, root, f"{path}.{key}", errors)

    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            _validate(item, schema["items"], root, f"{path}[{i}]", errors)


def _declared_types(schema: dict, root: dict) -> list[str]:
    if "$ref" in schema:
        schema = _resolve(schema["$ref"], root)
    t = schema.get("type", [])
    return t if isinstance(t, list) else [t]


def _validate_any_of(
    value: Any, alternatives: list[dict], root: dict, path: str, errors: list[str]
) -> None:
    """``anyOf``: valid when at least one alternative accepts ``value``.

    When exactly one alternative declares the value's JSON type, its errors
    are reported verbatim — that is the branch the author meant, and "expected
    integer, got string" under it beats "matches none of the forms". Otherwise
    the single error names the allowed forms.
    """
    for alt in alternatives:
        branch: list[str] = []
        _validate(value, alt, root, path, branch)
        if not branch:
            return
    typed = [
        alt for alt in alternatives
        if any(_type_ok(value, t) for t in _declared_types(alt, root))
    ]
    if len(typed) == 1:
        _validate(value, typed[0], root, path, errors)
        return
    forms = " | ".join(
        " | ".join(_declared_types(alt, root)) or "any" for alt in alternatives
    )
    errors.append(f"{path}: {value!r} matches none of the allowed forms ({forms})")

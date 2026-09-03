"""Rule framework.

Extending the linter = dropping a new module into ``pumllint/rules/<pack>/``
containing a class decorated with ``@register``, plus an entry in
``catalog.toml``. Nothing else to wire up: ``discover()`` imports every module
under the rules package so decorators run.

A rule class carries only its ``id`` and its ``check()`` algorithm; the
declarative metadata (name, description, severity, scope, profiles) lives in
:data:`catalog.toml` and is stamped onto the class by ``@register``. A rule
receives a parsed :class:`~pumllint.model.Diagram` plus its (already merged)
configuration dict, and yields :class:`~pumllint.model.Violation`s.
"""

from __future__ import annotations

import importlib
import pkgutil
import re
import tomllib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, Sequence, Type

from ..model import Diagram, Dimension, Severity, Violation

_REGISTRY: dict[str, Type["Rule"]] = {}


def compile_option_pattern(rule_id: str, option: str, pattern: str) -> re.Pattern[str]:
    """Compile a config-supplied regex; malformed = config error, not traceback.

    Raises ``ValueError`` naming the rule and option, which the CLI reports
    as a usage/config error (exit 2) per its documented contract — a broken
    config must not surface as a crash that CI reads as lint findings.
    """
    try:
        return re.compile(pattern)
    except (re.error, TypeError) as e:
        raise ValueError(
            f"rule {rule_id}: option '{option}' is not a valid regex "
            f"({e}): {pattern!r}"
        ) from e

def _reject_null_options(rule_id: str, cfg: dict) -> None:
    """An explicitly-null option value is a config error, never a default.

    Every option in this codebase expresses "not set" by *omitting* the key —
    ``options.get(name)`` then returns ``None`` and the rule takes its own
    default or goes dormant. A key written with an explicit null (YAML
    ``pattern:``, JSON ``"pattern": null``; TOML cannot express it at all)
    looks identical at the read site but means the user tried to say
    something. Left alone it reaches the rule body and crashes there —
    ``AttributeError`` on a compiled-pattern deref, ``TypeError`` on an int
    or list option — which escapes as **exit 1** and is indistinguishable
    from "lint findings at or above --fail-on" under the exit-code contract.
    Thirteen call sites had that shape; guarding here closes all of them at
    once rather than teaching each one to re-check.

    Raises ``ValueError``, which the CLI reports as exit 2 — the same clean
    config error :func:`compile_option_pattern` already raises for a
    malformed regex.
    """
    nulls = sorted(k for k, v in cfg.items() if v is None)
    if nulls:
        named = ", ".join(repr(k) for k in nulls)
        raise ValueError(
            f"rule {rule_id}: option(s) {named} are set to null — omit the "
            "key to leave an option unset (null is never a valid value)"
        )


_CATALOG_PATH = Path(__file__).with_name("catalog.toml")


def _load_catalog() -> dict[str, dict]:
    """Rule metadata catalog, keyed by rule id (see ``catalog.toml``)."""
    with _CATALOG_PATH.open("rb") as fh:
        return tomllib.load(fh)


_CATALOG: dict[str, dict] = _load_catalog()


class Rule(ABC):
    """Base class for all lint rules.

    Only ``id`` and ``check()`` are authored on the subclass; the remaining
    attributes below are populated from ``catalog.toml`` by ``@register`` and
    are declared here purely as defaults / type hints. See the catalog for the
    authoritative metadata.

    ``profiles``: empty = base catalog (always active); non-empty = disabled by
    default, active only when one of these profiles is selected (or the rule is
    listed under the profile's ``enable:`` key).
    """

    id: str = ""  # e.g. "SEQ001" -- the catalog join key, authored on subclass
    name: str = ""  # kebab-case, e.g. "undeclared-participant"
    description: str = ""
    default_severity: Severity = Severity.MAJOR
    dimension: Dimension = Dimension.SEMANTIC  # maturity-scoring bucket (SCORING.md)
    applies_to: tuple[str, ...] = ("sequence",)  # diagram types, or ("*",)
    profiles: tuple[str, ...] = ()

    def __init__(self, config: dict | None = None):
        cfg = dict(config or {})
        _reject_null_options(self.id, cfg)
        sev = cfg.pop("severity", None)
        self.severity = Severity(sev) if sev else self.default_severity
        self.options = cfg

    @abstractmethod
    def check(self, diagram: Diagram) -> Iterable[Violation]:
        ...

    # Helpers so rules stay terse
    def pattern_option(
        self, option: str, default: str | None = None
    ) -> re.Pattern[str] | None:
        """Compiled regex from config option *option* (falling back to
        *default*; None means the option is absent). Malformed patterns
        raise the clean config error of :func:`compile_option_pattern`."""
        raw = self.options.get(option, default)
        return None if raw is None else compile_option_pattern(self.id, option, raw)

    def violation(self, diagram: Diagram, line: int, message: str) -> Violation:
        return Violation(
            rule_id=self.id,
            message=message,
            file_path=diagram.file_path,
            line=line,
            severity=self.severity,
            dimension=self.dimension,
        )


class CrossDiagramRule(Rule):
    """Base for cross-diagram rules: a symbol table across the whole batch.

    The engine activates these only when more than one diagram is linted
    (SCORING.md §6) and attributes each violation back to the diagram that
    owns its file/line. ``check`` is unused — implement :meth:`check_all`.
    """

    def check(self, diagram: Diagram) -> Iterable[Violation]:  # pragma: no cover
        return ()

    @abstractmethod
    def check_all(self, diagrams: Sequence[Diagram]) -> Iterable[Violation]:
        ...


def register(cls: Type[Rule]) -> Type[Rule]:
    """Class decorator: stamp catalog metadata onto the rule and register it."""
    if not cls.id:
        raise ValueError(f"Rule {cls.__name__} has no id")
    if cls.id in _REGISTRY:
        raise ValueError(f"Duplicate rule id {cls.id}")
    meta = _CATALOG.get(cls.id)
    if meta is None:
        raise ValueError(f"Rule {cls.id} has no entry in catalog.toml")
    cls.name = meta["name"]
    cls.description = meta["description"]
    cls.default_severity = Severity(meta["severity"])
    cls.dimension = Dimension(meta["dimension"])
    cls.applies_to = tuple(meta["applies_to"])
    cls.profiles = tuple(meta.get("profiles", ()))
    _REGISTRY[cls.id] = cls
    return cls


def discover() -> dict[str, Type[Rule]]:
    """Import all rule modules (so @register decorators execute)."""
    import pumllint.rules as pkg

    for _, modname, ispkg in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
        if not ispkg:
            importlib.import_module(modname)
    return dict(_REGISTRY)

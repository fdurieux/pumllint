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
import tomllib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, Type

from ..model import Diagram, Severity, Violation

_REGISTRY: dict[str, Type["Rule"]] = {}

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
    applies_to: tuple[str, ...] = ("sequence",)  # diagram types, or ("*",)
    profiles: tuple[str, ...] = ()

    def __init__(self, config: dict | None = None):
        cfg = dict(config or {})
        sev = cfg.pop("severity", None)
        self.severity = Severity(sev) if sev else self.default_severity
        self.options = cfg

    @abstractmethod
    def check(self, diagram: Diagram) -> Iterable[Violation]:
        ...

    # Helper so rules stay terse
    def violation(self, diagram: Diagram, line: int, message: str) -> Violation:
        return Violation(
            rule_id=self.id,
            message=message,
            file_path=diagram.file_path,
            line=line,
            severity=self.severity,
        )


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

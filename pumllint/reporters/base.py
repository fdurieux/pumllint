"""Reporters turn violations into output. Register new ones with @reporter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Iterable, Type

from ..model import Violation

if TYPE_CHECKING:  # annotation-only imports; avoids a runtime reporters->scoring edge
    from ..model import Diagram
    from ..scoring import MaturityResult

_REPORTERS: dict[str, Type["Reporter"]] = {}


class Reporter(ABC):
    format_name: str = ""

    @abstractmethod
    def render(self, violations: Iterable[Violation]) -> str:
        ...

    def render_maturity(self, results: Iterable[tuple["Diagram", "MaturityResult"]]) -> str:
        """Render maturity scores for the ``score`` command. Optional: reporters
        that don't support it (default) raise a clear error."""
        raise NotImplementedError(
            f"Reporter '{self.format_name}' does not support maturity output"
        )


def reporter(cls: Type[Reporter]) -> Type[Reporter]:
    _REPORTERS[cls.format_name] = cls
    return cls


def get_reporter(name: str) -> Reporter:
    try:
        return _REPORTERS[name]()
    except KeyError:
        raise ValueError(f"Unknown format '{name}'. Available: {', '.join(sorted(_REPORTERS))}")

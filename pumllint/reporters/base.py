"""Reporters turn violations into output. Register new ones with @reporter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Type

from ..model import Violation

_REPORTERS: dict[str, Type["Reporter"]] = {}


class Reporter(ABC):
    format_name: str = ""

    @abstractmethod
    def render(self, violations: Iterable[Violation]) -> str:
        ...


def reporter(cls: Type[Reporter]) -> Type[Reporter]:
    _REPORTERS[cls.format_name] = cls
    return cls


def get_reporter(name: str) -> Reporter:
    try:
        return _REPORTERS[name]()
    except KeyError:
        raise ValueError(f"Unknown format '{name}'. Available: {', '.join(sorted(_REPORTERS))}")

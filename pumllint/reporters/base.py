"""Reporters turn violations into output. Register new ones with @reporter."""

from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, Iterable, Type

from ..model import Violation
from ..scoring import format_score  # noqa: F401  (re-export for reporters)

# C0 controls (except tab), DEL, and C1 controls — everything a terminal or
# CI log viewer might interpret (ESC/CSI/OSC sequences, line-spoofing CR/LF).
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0a-\x1f\x7f-\x9f]")


def sanitize_terminal(text: str) -> str:
    """Neutralize control characters in one line of terminal-bound output.

    Diagram content (labels, participant names, file paths) flows verbatim
    into lint messages; embedded escape sequences or bare CR/LF could spoof
    log lines or retitle terminals. Replaced with U+FFFD so tampering stays
    visible instead of being interpreted. Must be applied per logical line,
    before lines are joined — after joining, an injected newline is
    indistinguishable from a structural one. The structured formats need no
    such step: json/sonar/badge escape via ``json.dumps``, html via
    ``html.escape``.
    """
    return _CONTROL_CHARS.sub("�", text)


# Decorative glyphs the text reports use, and their ASCII stand-ins. Applied
# per character, and only to characters the destination stream cannot encode
# (see cli._encode_safely) — a Windows console redirected to a file runs in
# the ANSI code page, where printing U+2714 raises UnicodeEncodeError and
# destroys the whole report. U+FFFD is deliberately absent: sanitize_terminal
# uses it to mark tampering, and an escape sequence keeps that visible.
ASCII_GLYPHS = {
    "\u2714": "OK",    # heavy check mark
    "\u2716": "FAIL",  # heavy multiplication x
    "\u2192": "->",
    "\u2190": "<-",
    "\u2022": "*",
    "\u2014": "--",
    "\u2013": "-",
    "\u2026": "...",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
}


def ascii_glyphs(text: str) -> str:
    """Replace pumllint's own decorative glyphs with ASCII equivalents."""
    for glyph, plain in ASCII_GLYPHS.items():
        text = text.replace(glyph, plain)
    return text

if TYPE_CHECKING:  # annotation-only imports; avoids a runtime reporters->scoring edge
    from ..baseline import BaselineEntry
    from ..model import Diagram
    from ..scoring import MaturityResult
    from ..trace import TraceResult

_REPORTERS: dict[str, Type["Reporter"]] = {}


class Reporter(ABC):
    format_name: str = ""

    def render(self, violations: Iterable[Violation]) -> str:
        """Render lint findings. Optional, like the two methods below: a
        score-only reporter (badge, html) simply doesn't override it. Which
        methods a class overrides is what `formats_supporting` — and thus
        each command's `-f` choices — is derived from."""
        raise NotImplementedError(
            f"Reporter '{self.format_name}' does not support lint output"
        )

    def render_maturity(
        self,
        results: Iterable[tuple["Diagram", "MaturityResult"]],
        *,
        baseline: "dict[str, BaselineEntry] | None" = None,
        syntax_gate_ran: bool = False,
    ) -> str:
        """Render maturity scores for the ``score`` command. Optional: reporters
        that don't support it (default) raise a clear error.

        ``baseline`` is the loaded ratchet baseline (``--baseline`` compare
        runs only); reporters that receive one add trend/delta annotations.
        """
        raise NotImplementedError(
            f"Reporter '{self.format_name}' does not support maturity output"
        )

    def render_trace(self, result: "TraceResult") -> str:
        """Render a requirement-coverage matrix for the ``trace`` command.
        Optional, like :meth:`render_maturity` — text and json implement it."""
        raise NotImplementedError(
            f"Reporter '{self.format_name}' does not support trace output"
        )


def reporter(cls: Type[Reporter]) -> Type[Reporter]:
    _REPORTERS[cls.format_name] = cls
    return cls


def get_reporter(name: str) -> Reporter:
    try:
        return _REPORTERS[name]()
    except KeyError:
        raise ValueError(f"Unknown format '{name}'. Available: {', '.join(sorted(_REPORTERS))}")


def formats_supporting(method: str) -> list[str]:
    """Registered format names whose reporter implements ``method`` —
    'render' (lint), 'render_maturity' (score) or 'render_trace' (trace).
    Drives each CLI command's `-f` choices, so custom @reporter
    registrations become selectable exactly where they add support."""
    return sorted(
        name
        for name, cls in _REPORTERS.items()
        if getattr(cls, method) is not getattr(Reporter, method)
    )

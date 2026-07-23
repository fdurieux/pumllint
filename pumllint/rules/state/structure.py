"""Structural rules for state diagrams."""

from __future__ import annotations

from typing import Iterable

from ...model import Diagram, Violation
from .. import Rule, register


@register
class SingleInitialState(Rule):
    """Exactly one top-level ``[*] -->`` initial transition.

    A machine without one does not define where execution begins; with two,
    it defines it twice. Initial transitions inside composite-state bodies
    are those composites' own entry points and do not count.
    """

    id = "STA001"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        initial = [
            t for t in diagram.transitions if t.is_initial and t.container is None
        ]
        if not initial:
            yield self.violation(
                diagram,
                diagram.start_line,
                "State machine has no top-level '[*] -->' initial transition",
            )
        for t in initial[1:]:
            yield self.violation(
                diagram,
                t.line,
                f"Duplicate initial transition '[*] --> {t.target}' — "
                f"the machine already starts at '{initial[0].target}'",
            )


@register
class UnreachableState(Rule):
    """State with no incoming transition — dead model content.

    Typically a leftover from refactoring. Self-transitions do not count as
    incoming (a state only reachable from itself is still unreachable).
    """

    id = "STA002"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        targeted = {
            t.target for t in diagram.transitions if t.source != t.target
        }
        for s in diagram.states.values():
            if s.name not in targeted:
                yield self.violation(
                    diagram,
                    s.line,
                    f"State '{s.name}' has no incoming transition — unreachable",
                )


@register
class UnlabelledTransition(Rule):
    """State-to-state transitions carry an ``event [guard] / action`` label.

    An unlabelled transition says a state change can occur but not what
    triggers it. Initial and final transitions (``[*]`` endpoints) are
    conventionally unlabelled and exempt.
    """

    id = "STA003"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        for t in diagram.transitions:
            if t.is_initial or t.is_final or t.label:
                continue
            yield self.violation(
                diagram,
                t.line,
                f"Transition '{t.source} --> {t.target}' has no label — "
                'write "event [guard] / action"',
            )

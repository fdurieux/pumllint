"""Participant hygiene rules for sequence diagrams."""

from __future__ import annotations

from typing import Iterable

from ...model import Diagram, Violation
from .. import Rule, register


@register
class UndeclaredParticipant(Rule):
    """Participant used in a message but never declared.

    PlantUML silently auto-creates lifelines on first mention, so a typo
    (``Custmer -> Bank``) renders a phantom participant instead of failing.
    Requiring explicit declaration turns typos into lint errors.

    Option ``only_if_any_declared`` (default True): stay quiet in files that
    declare nothing at all, so quick ad-hoc sketches aren't punished.
    """

    id = "SEQ001"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        only_if_any = self.options.get("only_if_any_declared", True)
        declared = [p for p in diagram.participants.values() if p.declared]
        if only_if_any and not declared:
            return
        for p in diagram.participants.values():
            if not p.declared:
                yield self.violation(
                    diagram,
                    p.line,
                    f"Participant '{p.name}' is used but never declared "
                    f"(possible typo — PlantUML silently creates a new lifeline)",
                )


@register
class UnusedParticipant(Rule):
    """Participant declared but never involved in any message or activation."""

    id = "SEQ002"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        if not diagram.messages:
            return  # declaration-only stubs are fine
        used = diagram.used_participant_names()
        for p in diagram.participants.values():
            if p.declared and p.kind != "usecase" and p.name not in used:
                yield self.violation(
                    diagram,
                    p.line,
                    f"{p.kind.capitalize()} '{p.name}' is declared but never used",
                )


@register
class ExplicitParticipantOrdering(Rule):
    """Participants should be declared up front, not created on first use.

    When lifeline order is implied by first use, an innocent message reordering
    reshuffles the whole diagram; explicit declaration pins the layout. Off by
    default (``require_explicit_order``): this overlaps SEQ001 and exists for
    configurations that relax SEQ001 but still want ordering pinned.
    """

    id = "SEQ010"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        if self.dormant:
            return
        for p in diagram.participants.values():
            if not p.declared:
                yield self.violation(
                    diagram,
                    p.line,
                    f"Participant '{p.name}' is introduced by first use; "
                    "declare it up front to pin lifeline order",
                )

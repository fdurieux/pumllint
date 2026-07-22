"""XD: cross-diagram consistency rules (DIM-CON).

A participant symbol table across every sequence diagram in the lint batch:
the same entity must keep one identity — one declaration kind, one stereotype,
one spelling. Active only when more than one diagram is linted (see Engine);
single-diagram runs score DIM-CON from naming rules alone (SCORING.md §6).
"""

from __future__ import annotations

from typing import Iterable, Sequence

from ...model import Diagram, Participant, Violation
from .. import CrossDiagramRule, register


def _majority(values: list[str]) -> str:
    """The most frequent value; ties resolve to the first-seen value so the
    earliest declaration stays authoritative."""
    return max(set(values), key=lambda v: (values.count(v), -values.index(v)))


def _conflicts(diagrams, value_of):
    """The shared symbol-table walk behind XD001/XD002.

    Groups declared participants by name via ``value_of`` (returning None to
    skip an occurrence), and for every name whose values disagree yields
    ``(name, majority_value, (ref_diagram, ref_participant), minority_sites)``
    — majority wins, ties resolve to the first-seen value, and the reference
    site is the first majority occurrence.
    """
    occurrences: dict[str, list[tuple[Diagram, Participant]]] = {}
    for d in diagrams:
        for name, p in d.participants.items():
            if value_of(p) is not None:
                occurrences.setdefault(name, []).append((d, p))
    for name, occs in occurrences.items():
        values = [value_of(p) for _, p in occs]
        if len(set(values)) < 2:
            continue
        majority = _majority(values)
        ref = next((d, p) for d, p in occs if value_of(p) == majority)
        minority = [(d, p) for d, p in occs if value_of(p) != majority]
        yield name, majority, ref, minority


@register
class ConflictingParticipantKind(CrossDiagramRule):
    id = "XD001"

    def check_all(self, diagrams: Sequence[Diagram]) -> Iterable[Violation]:
        # implicit lifelines have no authored kind
        value_of = lambda p: p.kind if p.declared else None  # noqa: E731
        for name, majority, (ref_d, ref_p), minority in _conflicts(diagrams, value_of):
            for d, p in minority:
                yield self.violation(
                    d, p.line,
                    f"Participant '{name}' is declared as '{p.kind}' here but as "
                    f"'{majority}' at {ref_d.file_path}:{ref_p.line} — one entity, one kind",
                )


@register
class ConflictingParticipantStereotype(CrossDiagramRule):
    id = "XD002"

    def check_all(self, diagrams: Sequence[Diagram]) -> Iterable[Violation]:
        # absent stereotypes are SEQ102's concern, not a conflict
        value_of = lambda p: (p.stereotype or None) if p.declared else None  # noqa: E731
        for name, majority, (ref_d, ref_p), minority in _conflicts(diagrams, value_of):
            for d, p in minority:
                yield self.violation(
                    d, p.line,
                    f"Participant '{name}' is stereotyped <<{p.stereotype}>> here but "
                    f"<<{majority}>> at {ref_d.file_path}:{ref_p.line}",
                )


@register
class ParticipantNameCaseCollision(CrossDiagramRule):
    id = "XD003"

    def check_all(self, diagrams: Sequence[Diagram]) -> Iterable[Violation]:
        # Implicit participants included: spelling drift usually enters via arrows.
        first: dict[str, tuple[str, Diagram, Participant]] = {}
        for d in diagrams:
            for name, p in d.participants.items():
                key = name.lower()
                if key not in first:
                    first[key] = (name, d, p)
                    continue
                name0, d0, p0 = first[key]
                if name != name0:
                    yield self.violation(
                        d, p.line,
                        f"Participant '{name}' collides case-insensitively with '{name0}' "
                        f"({d0.file_path}:{p0.line}) — likely the same entity spelled differently",
                    )

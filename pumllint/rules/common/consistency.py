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


@register
class ConflictingParticipantKind(CrossDiagramRule):
    id = "XD001"

    def check_all(self, diagrams: Sequence[Diagram]) -> Iterable[Violation]:
        first: dict[str, tuple[Diagram, Participant]] = {}
        for d in diagrams:
            for name, p in d.participants.items():
                if not p.declared:
                    continue  # implicit lifelines have no authored kind
                if name not in first:
                    first[name] = (d, p)
                    continue
                d0, p0 = first[name]
                if p.kind != p0.kind:
                    yield self.violation(
                        d, p.line,
                        f"Participant '{name}' is declared as '{p.kind}' here but as "
                        f"'{p0.kind}' at {d0.file_path}:{p0.line} — one entity, one kind",
                    )


@register
class ConflictingParticipantStereotype(CrossDiagramRule):
    id = "XD002"

    def check_all(self, diagrams: Sequence[Diagram]) -> Iterable[Violation]:
        first: dict[str, tuple[Diagram, Participant]] = {}
        for d in diagrams:
            for name, p in d.participants.items():
                if not p.declared or not p.stereotype:
                    continue  # absent stereotypes are SEQ102's concern, not a conflict
                if name not in first:
                    first[name] = (d, p)
                    continue
                d0, p0 = first[name]
                if p.stereotype != p0.stereotype:
                    yield self.violation(
                        d, p.line,
                        f"Participant '{name}' is stereotyped <<{p.stereotype}>> here but "
                        f"<<{p0.stereotype}>> at {d0.file_path}:{p0.line}",
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

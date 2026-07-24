"""XD: cross-diagram consistency rules (DIM-CON).

An entity symbol table across every diagram in the lint batch: the same
entity must keep one identity — one declaration kind, one stereotype, one
spelling. XD001–003 walk the participant tables of sequence diagrams;
XD004–005 span diagram *types* (sequence participants, use-case actors,
class classifiers, activity swimlanes — state names are excluded on purpose:
states are modes of an entity, not entities). Active only when more than one
diagram is linted (see Engine); single-diagram runs score DIM-CON from
naming rules alone (SCORING.md §6).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, Sequence

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


# --- XD004/XD005: cross-*type* entity identity ------------------------------

@dataclass(frozen=True)
class _Site:
    """One occurrence of an entity in some diagram's universe."""

    name: str
    diagram: Diagram
    line: int
    role: str  # participant | actor | usecase | class | interface | ... | swimlane
    stereotype: str | None = None
    declared: bool = True


def _entity_sites(diagrams: Sequence[Diagram]) -> Iterator[_Site]:
    """Every entity occurrence across the type-specific universes.

    Sequence/use-case participants, class classifiers and activity swimlanes
    name entities; state names are modes, not entities, and stay out.
    """
    for d in diagrams:
        for name, p in d.participants.items():
            yield _Site(name, d, p.line, p.kind, p.stereotype, p.declared)
        for name, c in d.classes.items():
            yield _Site(name, d, c.line, c.kind, c.stereotype, c.declared)
        for n in d.activity_nodes:
            if n.kind == "swimlane" and n.label:
                yield _Site(n.label, d, n.line, "swimlane")


@register
class CrossTypeNameCollision(CrossDiagramRule):
    """One entity, one spelling — across diagram *types*.

    A class ``OrderService`` next to a sequence lifeline ``orderService`` is
    almost certainly the same entity drifting apart. First-seen spelling is
    authoritative (as in XD003); pairs where both sites are sequence
    participants are XD003's territory and skipped here.
    """

    id = "XD004"

    def check_all(self, diagrams: Sequence[Diagram]) -> Iterable[Violation]:
        first: dict[str, _Site] = {}
        for site in _entity_sites(diagrams):
            key = site.name.lower()
            ref = first.setdefault(key, site)
            if site is ref or site.name == ref.name:
                continue
            if site.diagram.diagram_type == ref.diagram.diagram_type == "sequence":
                continue  # XD003 reports sequence-internal collisions
            yield self.violation(
                site.diagram, site.line,
                f"{site.role.capitalize()} '{site.name}' collides case-insensitively "
                f"with {ref.role} '{ref.name}' ({ref.diagram.file_path}:{ref.line}) "
                "— likely the same entity spelled differently",
            )


@register
class CrossTypeStereotypeConflict(CrossDiagramRule):
    """An entity's stereotype must agree between the class model and the
    interaction models.

    ``class OrderService <<service>>`` versus ``participant OrderService
    <<gateway>>`` is one entity with two contracts. Majority wins (ties to
    first-seen, as in XD002); conflicts confined to sequence diagrams are
    XD002's territory and skipped here.
    """

    id = "XD005"

    def check_all(self, diagrams: Sequence[Diagram]) -> Iterable[Violation]:
        occurrences: dict[str, list[_Site]] = {}
        for site in _entity_sites(diagrams):
            if site.declared and site.stereotype:
                occurrences.setdefault(site.name, []).append(site)
        for name, sites in occurrences.items():
            values = [s.stereotype for s in sites]
            if len(set(values)) < 2:
                continue
            if all(s.diagram.diagram_type == "sequence" for s in sites):
                continue  # XD002 reports sequence-internal conflicts
            majority = _majority(values)
            ref = next(s for s in sites if s.stereotype == majority)
            for s in sites:
                if s.stereotype == majority:
                    continue
                yield self.violation(
                    s.diagram, s.line,
                    f"{s.role.capitalize()} '{name}' is stereotyped <<{s.stereotype}>> "
                    f"here but <<{majority}>> as {ref.role} at "
                    f"{ref.diagram.file_path}:{ref.line}",
                )

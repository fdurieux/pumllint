"""XD: cross-diagram consistency rules (DIM-CON).

An entity symbol table across every diagram in the lint batch: the same
entity must keep one identity — one declaration kind, one stereotype, one
spelling. XD001–003 walk the participant tables of sequence diagrams;
XD004–005 span diagram *types* (sequence participants, use-case actors,
class classifiers, activity swimlanes — state names are excluded on purpose:
states are modes of an entity, not entities). Active only when more than one
diagram is linted (see Engine); single-diagram runs score DIM-CON from
naming rules alone (SCORING.md §6).

Value conflicts (XD001/XD002/XD005) are reported symmetrically at every
conflicted site — the tool cannot know which side is right, and electing a
majority indicts the conforming sites once a drift has spread (issue #36).
The per-entity ``authoritative`` option pins the intended value; with it set,
only non-conforming sites are reported.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, Sequence

from ...model import Diagram, Participant, Violation
from .. import CrossDiagramRule, register


def _variant_summary(values: list[str], fmt) -> str:
    """Every distinct value with its occurrence count, most frequent first,
    count ties broken alphabetically — never by batch order, so the message
    reads the same whichever file sorts first: ``<<sink>> ×3, <<store>> ×2``."""
    ranked = sorted(set(values), key=lambda v: (-values.count(v), v))
    return ", ".join(f"{fmt(v)} ×{values.count(v)}" for v in ranked)


def _authoritative(options) -> dict[str, str]:
    """The per-entity ``authoritative`` pick: {entity name -> pinned value}.

    A conflict-resolution pin, not a vocabulary check: an entity whose sites
    all agree is never compared against it.
    """
    raw = options.get("authoritative", {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def _conflict_sets(diagrams, value_of):
    """The shared symbol-table walk behind XD001/XD002.

    Groups declared participants by name via ``value_of`` (returning None to
    skip an occurrence), and for every name whose values disagree yields
    ``(name, sites)`` with every occurrence in batch order. No side is
    elected: a conflict is symmetric evidence, and which value is *correct*
    is the ``authoritative`` option's call, never a vote's (issue #36).
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
        yield name, occs


@register
class ConflictingParticipantKind(CrossDiagramRule):
    id = "XD001"

    def check_all(self, diagrams: Sequence[Diagram]) -> Iterable[Violation]:
        # implicit lifelines have no authored kind
        value_of = lambda p: p.kind if p.declared else None  # noqa: E731
        authoritative = _authoritative(self.options)
        for name, occs in _conflict_sets(diagrams, value_of):
            auth = authoritative.get(name)
            if auth is not None:
                for d, p in occs:
                    if p.kind != auth:
                        yield self.violation(
                            d, p.line,
                            f"Participant '{name}' is declared '{p.kind}' here but "
                            f"'{auth}' is the configured kind for this entity",
                        )
                continue
            summary = _variant_summary([p.kind for _, p in occs], lambda v: f"'{v}'")
            for d, p in occs:
                yield self.violation(
                    d, p.line,
                    f"Participant '{name}' is declared '{p.kind}' here and the set "
                    f"disagrees ({summary}) — one entity, one kind",
                )


@register
class ConflictingParticipantStereotype(CrossDiagramRule):
    id = "XD002"

    def check_all(self, diagrams: Sequence[Diagram]) -> Iterable[Violation]:
        # absent stereotypes are SEQ102's concern, not a conflict
        value_of = lambda p: (p.stereotype or None) if p.declared else None  # noqa: E731
        authoritative = _authoritative(self.options)
        for name, occs in _conflict_sets(diagrams, value_of):
            auth = authoritative.get(name)
            if auth is not None:
                for d, p in occs:
                    if p.stereotype != auth:
                        yield self.violation(
                            d, p.line,
                            f"Participant '{name}' is stereotyped <<{p.stereotype}>> "
                            f"here but <<{auth}>> is the configured stereotype for "
                            "this entity",
                        )
                continue
            summary = _variant_summary(
                [p.stereotype for _, p in occs], lambda v: f"<<{v}>>"
            )
            for d, p in occs:
                yield self.violation(
                    d, p.line,
                    f"Participant '{name}' is stereotyped <<{p.stereotype}>> here "
                    f"and the set disagrees ({summary}) — one entity, one stereotype",
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
    <<gateway>>`` is one entity with two contracts. Every conflicted site is
    reported symmetrically (no vote — the ``authoritative`` option pins the
    intended value, as in XD001/XD002); conflicts confined to sequence
    diagrams are XD002's territory and skipped here.
    """

    id = "XD005"

    def check_all(self, diagrams: Sequence[Diagram]) -> Iterable[Violation]:
        occurrences: dict[str, list[_Site]] = {}
        for site in _entity_sites(diagrams):
            if site.declared and site.stereotype:
                occurrences.setdefault(site.name, []).append(site)
        authoritative = _authoritative(self.options)
        for name, sites in occurrences.items():
            values = [s.stereotype for s in sites]
            if len(set(values)) < 2:
                continue
            if all(s.diagram.diagram_type == "sequence" for s in sites):
                continue  # XD002 reports sequence-internal conflicts
            auth = authoritative.get(name)
            if auth is not None:
                for s in sites:
                    if s.stereotype != auth:
                        yield self.violation(
                            s.diagram, s.line,
                            f"{s.role.capitalize()} '{name}' is stereotyped "
                            f"<<{s.stereotype}>> here but <<{auth}>> is the "
                            "configured stereotype for this entity",
                        )
                continue
            summary = _variant_summary(values, lambda v: f"<<{v}>>")
            for s in sites:
                yield self.violation(
                    s.diagram, s.line,
                    f"{s.role.capitalize()} '{name}' is stereotyped "
                    f"<<{s.stereotype}>> here and the set disagrees across "
                    f"diagram types ({summary}) — one entity, one stereotype",
                )

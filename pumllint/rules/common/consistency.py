"""XD: cross-diagram consistency rules (DIM-CON).

An entity symbol table across every diagram in the lint batch: the same
entity must keep one identity — one declaration kind, one stereotype, one
spelling. XD001–003 walk the participant tables of sequence diagrams;
XD004–005 span diagram *types* (sequence participants, use-case actors,
class classifiers, activity swimlanes — state names are excluded on purpose:
states are modes of an entity, not entities). Active only when more than one
diagram is linted (see Engine); single-diagram runs score DIM-CON from
naming rules alone (SCORING.md §6).

Every conflict — value (XD001/XD002/XD005) and spelling (XD003/XD004) — is
reported symmetrically at every conflicted site: the tool cannot know which
side is right, and electing one indicts the conforming sites once a drift has
spread (issue #36). XD003/XD004 elected the *first-seen* spelling until
2026-09-03, which made per-diagram scores depend on the order files were
passed in — pre-commit hands the hooks changed files in git's order, so the
same content scored differently commit to commit. The per-entity
``authoritative`` option pins the intended value (or spelling); with it set,
only non-conforming sites are reported. The ``distinct`` option is its
negative form: names listed there are deliberately different entities that
happen to share a spelling (bounded contexts), so no XD rule joins them.

Batch order must not change which findings exist or which diagram owns
them. Every rule groups the whole batch before it yields anything, so the
reference a site is compared against is the whole group, never whichever
site came first; ``_variant_summary`` orders by count then alphabetically;
emission order is normalised downstream by the engine's sort. The guard is
``tests/test_crossfile.py``, which asserts per-diagram findings, levels and
composites identical under every permutation of the batch.
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


def _authoritative(options, *, casefold: bool = False) -> dict[str, str]:
    """The per-entity ``authoritative`` pick: {entity name -> pinned value}.

    A conflict-resolution pin, not a vocabulary check: an entity whose sites
    all agree is never compared against it. XD003/XD004 join names
    case-insensitively, so they look the pin up by the lowercased name
    (``casefold=True``); the pinned *value* keeps its case, since for those
    two rules the value is the spelling itself.
    """
    raw = options.get("authoritative", {})
    if not isinstance(raw, dict):
        return {}
    return {
        (str(k).lower() if casefold else str(k)): str(v) for k, v in raw.items()
    }


def _distinct(options) -> set[str]:
    """The ``distinct`` name list: entities that are deliberately *different*
    things despite sharing a spelling (a bounded-context ``Order`` here, a
    work-order ``Order`` there).

    The negative form of ``authoritative``: where that option resolves a
    conflict to one intended value, this one declares the premise of every
    XD join false for the name — same spelling is not the same entity, so no
    cross-diagram comparison applies. XD001/XD002/XD005 match the name
    exactly; XD003/XD004 join case-insensitively, so they match a distinct
    name case-insensitively too.
    """
    raw = options.get("distinct", [])
    if not isinstance(raw, (list, tuple)):
        return set()
    return {str(v) for v in raw}


def _conflict_sets(diagrams, value_of, skip: set[str] = frozenset()):
    """The shared symbol-table walk behind XD001/XD002.

    Groups declared participants by name via ``value_of`` (returning None to
    skip an occurrence), and for every name whose values disagree yields
    ``(name, sites)`` with every occurrence in batch order. No side is
    elected: a conflict is symmetric evidence, and which value is *correct*
    is the ``authoritative`` option's call, never a vote's (issue #36).
    Names in ``skip`` (the ``distinct`` option) are never grouped at all.
    """
    occurrences: dict[str, list[tuple[Diagram, Participant]]] = {}
    for d in diagrams:
        for name, p in d.participants.items():
            if name in skip:
                continue
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
        for name, occs in _conflict_sets(diagrams, value_of, _distinct(self.options)):
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
        for name, occs in _conflict_sets(diagrams, value_of, _distinct(self.options)):
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
    """One entity, one spelling — across sequence diagrams.

    ``OrderSvc`` here and ``Ordersvc`` there are almost certainly one entity;
    PlantUML treats them as two lifelines and the model silently forks. Every
    site in a case-variant group is reported, each message listing every
    spelling with its count. Implicit participants are included: spelling
    drift usually enters via arrows.

    Until 2026-09-03 this rule kept the first spelling it met as the reference
    and flagged only the sites that differed from it — so which diagram was
    blamed, and how many findings existed, depended on the order files were
    passed in. Same defect class as issue #36, which had already made
    XD001/XD002/XD005 symmetric and left these two "untouched".
    """

    id = "XD003"

    def check_all(self, diagrams: Sequence[Diagram]) -> Iterable[Violation]:
        distinct = {v.lower() for v in _distinct(self.options)}
        authoritative = _authoritative(self.options, casefold=True)
        groups: dict[str, list[tuple[str, Diagram, Participant]]] = {}
        for d in diagrams:
            for name, p in d.participants.items():
                key = name.lower()
                if key in distinct:
                    continue
                groups.setdefault(key, []).append((name, d, p))
        for key, occs in groups.items():
            spellings = [name for name, _, _ in occs]
            if len(set(spellings)) < 2:
                continue
            auth = authoritative.get(key)
            if auth is not None:
                for name, d, p in occs:
                    if name != auth:
                        yield self.violation(
                            d, p.line,
                            f"Participant '{name}' is spelled so here but '{auth}' "
                            "is the configured spelling for this entity",
                        )
                continue
            summary = _variant_summary(spellings, lambda v: f"'{v}'")
            for name, d, p in occs:
                yield self.violation(
                    d, p.line,
                    f"Participant '{name}' collides case-insensitively with the set "
                    f"({summary}) — one entity, one spelling",
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
    almost certainly the same entity drifting apart. Every site in a
    case-variant group is reported symmetrically (no spelling is elected —
    the ``authoritative`` option pins the intended one, as in XD001/XD002);
    groups confined to sequence diagrams are XD003's territory and skipped
    here, the same set-wise test XD005 applies for XD002.

    Until 2026-09-03 the first-seen spelling was the reference and the
    sequence-internal skip was evaluated pairwise against it — so a group
    with a class site and two sequence sites produced one finding or two
    depending on which site the batch happened to yield first. Same defect
    class as issue #36.
    """

    id = "XD004"

    def check_all(self, diagrams: Sequence[Diagram]) -> Iterable[Violation]:
        distinct = {v.lower() for v in _distinct(self.options)}
        authoritative = _authoritative(self.options, casefold=True)
        groups: dict[str, list[_Site]] = {}
        for site in _entity_sites(diagrams):
            key = site.name.lower()
            if key in distinct:
                continue
            groups.setdefault(key, []).append(site)
        for key, sites in groups.items():
            spellings = [s.name for s in sites]
            if len(set(spellings)) < 2:
                continue
            if all(s.diagram.diagram_type == "sequence" for s in sites):
                continue  # XD003 reports sequence-internal collisions
            auth = authoritative.get(key)
            if auth is not None:
                for s in sites:
                    if s.name != auth:
                        yield self.violation(
                            s.diagram, s.line,
                            f"{s.role.capitalize()} '{s.name}' is spelled so here but "
                            f"'{auth}' is the configured spelling for this entity",
                        )
                continue
            summary = _variant_summary(spellings, lambda v: f"'{v}'")
            for s in sites:
                yield self.violation(
                    s.diagram, s.line,
                    f"{s.role.capitalize()} '{s.name}' collides case-insensitively "
                    f"across diagram types with the set ({summary}) — one entity, "
                    "one spelling",
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
        distinct = _distinct(self.options)
        occurrences: dict[str, list[_Site]] = {}
        for site in _entity_sites(diagrams):
            if site.name in distinct:
                continue
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

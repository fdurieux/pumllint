"""Governance rules applying to any diagram type."""

from __future__ import annotations

import re
from typing import Iterable

from ...model import Diagram, Violation
from .. import Rule, register


@register
class MissingTitle(Rule):
    id = "GEN001"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        if diagram.title is None:
            yield self.violation(diagram, diagram.start_line, "Diagram has no title")


@register
class UnnamedDiagram(Rule):
    id = "GEN002"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        if not diagram.name:
            yield self.violation(
                diagram,
                diagram.start_line,
                "@startuml has no name (use '@startuml my-diagram-name' for stable export filenames)",
            )


@register
class InlineSkinparam(Rule):
    """Central theming beats per-diagram styling drift.

    Option ``allowed`` — list of skinparam prefixes tolerated inline.
    """

    id = "GEN003"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        allowed = tuple(s.lower() for s in self.options.get("allowed", []))
        for d in diagram.skinparams:
            if allowed and d.value.lower().startswith(allowed):
                continue
            yield self.violation(
                diagram,
                d.line,
                f"Inline 'skinparam {d.value}' — move styling to the shared theme include",
            )


@register
class ParticipantNaming(Rule):
    """Declared participant names must match a configurable pattern.

    Options: ``pattern`` (regex, default PascalCase-with-dots),
    ``per_kind`` (dict of kind -> regex overriding the default).
    """

    id = "GEN004"

    DEFAULT_PATTERN = r"^[A-Z][A-Za-z0-9]*(\.[A-Z][A-Za-z0-9]*)*$"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        default = self.options.get("pattern", self.DEFAULT_PATTERN)
        per_kind = self.options.get("per_kind", {})
        for p in diagram.participants.values():
            if not p.declared:
                continue
            pattern = per_kind.get(p.kind, default)
            if not re.match(pattern, p.name):
                yield self.violation(
                    diagram,
                    p.line,
                    f"{p.kind.capitalize()} name '{p.name}' does not match pattern {pattern!r}",
                )


@register
class MaxParticipants(Rule):
    """Too many lifelines = diagram doing too much. Option: ``max`` (default 9)."""

    id = "GEN005"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        limit = int(self.options.get("max", 9))
        count = len(diagram.participants)
        if count > limit:
            yield self.violation(
                diagram,
                diagram.start_line,
                f"Diagram has {count} participants (max {limit}) — consider splitting per phase or using 'ref over'",
            )


def _prose_directives(diagram: Diagram) -> list:
    """Directives whose value is free text an owner/requirement tag can live in."""
    kinds = ("title", "header", "footer", "caption", "note")
    return [d for d in diagram.directives if d.kind in kinds]


@register
class OwnerTag(Rule):
    """Diagrams must declare ownership (team, maintainer) somewhere findable.

    There is no universal ownership convention, so the rule is dormant until
    the project configures one: option ``pattern`` (regex, e.g.
    ``(?i)owner\\s*:``) is matched against the title, header, footer, caption
    and note texts.
    """

    id = "GEN006"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        pattern = self.options.get("pattern")
        if not pattern:
            return
        if any(re.search(pattern, d.value) for d in _prose_directives(diagram)):
            return
        yield self.violation(
            diagram,
            diagram.start_line,
            f"No ownership tag matching {pattern!r} in title/header/footer/caption/notes",
        )


@register
class RequirementLink(Rule):
    """Diagrams must reference the requirement/ADR they realize.

    Reference schemes are project-specific (``REQ-123``, ``ADR-0007``,
    ticket keys, URLs), so the rule is dormant until option ``pattern``
    (regex, e.g. ``REQ-\\d+|ADR-\\d+``) supplies the project's scheme; it is
    matched against the diagram name plus title/header/footer/caption/notes.
    """

    id = "GEN007"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        pattern = self.options.get("pattern")
        if not pattern:
            return
        haystacks = [d.value for d in _prose_directives(diagram)]
        if diagram.name:
            haystacks.append(diagram.name)
        if any(re.search(pattern, h) for h in haystacks):
            return
        yield self.violation(
            diagram,
            diagram.start_line,
            f"No requirement/ADR reference matching {pattern!r} in name/title/header/footer/caption/notes",
        )


@register
class NoteDensity(Rule):
    """Structure drowning in prose: too many notes for the diagram's size.

    Notes annotate; they should not carry the model. Options: ``min_notes``
    (default 4 — smaller counts never fire) and ``max_ratio`` (default 0.5
    notes per element).
    """

    id = "GEN008"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        notes = [d for d in diagram.directives if d.kind == "note"]
        min_notes = int(self.options.get("min_notes", 4))
        max_ratio = float(self.options.get("max_ratio", 0.5))
        if len(notes) < min_notes:
            return
        elements = max(1, diagram.element_count)
        if len(notes) > max_ratio * elements:
            yield self.violation(
                diagram,
                notes[0].line,
                f"{len(notes)} notes on {elements} element(s) — model the structure "
                "instead of narrating it in notes",
            )


@register
class MaxElements(Rule):
    """Diagram grown past readable size, whatever its type.

    Option: ``max`` (default 60 semantic elements — the same count the
    maturity scorer uses as its density denominator).
    """

    id = "GEN009"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        limit = int(self.options.get("max", 60))
        count = diagram.element_count
        if count > limit:
            yield self.violation(
                diagram,
                diagram.start_line,
                f"Diagram has {count} elements (max {limit}) — split it along "
                "phases, subsystems or scenarios",
            )


@register
class OrphanUseCaseActor(Rule):
    """Use-case diagram: actor linked to zero use cases, or vice versa."""

    id = "UC001"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        if not diagram.usecase_links:
            return
        linked: set[str] = set()
        for link in diagram.usecase_links:
            linked.add(link.source)
            linked.add(link.target)
        for p in diagram.participants.values():
            if p.declared and p.name not in linked:
                yield self.violation(
                    diagram,
                    p.line,
                    f"{p.kind.capitalize()} '{p.name}' is not linked to anything",
                )


@register
class IncludeExtendDirection(Rule):
    """``<<include>>``/``<<extend>>`` arrows point the right way.

    ``<<include>>`` points from base to included case; ``<<extend>>`` from
    extension to base. Both relate use cases only — an actor endpoint is
    always wrong. Direction is judged against actor connectivity (the base
    case is the one an actor reaches through a plain association) and only
    when that evidence is unambiguous: exactly one endpoint actor-connected.
    """

    id = "UC003"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        stereo = [
            link for link in diagram.usecase_links
            if link.stereotype in ("include", "extend")
        ]
        if not stereo:
            return
        actors = {
            p.name for p in diagram.participants.values() if p.kind == "actor"
        }
        connected: set[str] = set()  # use cases an actor reaches via plain links
        for link in diagram.usecase_links:
            if link.stereotype in ("include", "extend"):
                continue
            if link.source in actors and link.target not in actors:
                connected.add(link.target)
            elif link.target in actors and link.source not in actors:
                connected.add(link.source)
        for link in stereo:
            st = link.stereotype
            actor_end = next(
                (n for n in (link.source, link.target) if n in actors), None
            )
            if actor_end:
                yield self.violation(
                    diagram,
                    link.line,
                    f"<<{st}>> must relate two use cases — '{actor_end}' is an actor",
                )
                continue
            src_conn = link.source in connected
            if src_conn == (link.target in connected):
                continue  # neither or both actor-connected: no verdict
            if st == "include" and not src_conn:
                yield self.violation(
                    diagram,
                    link.line,
                    f"<<include>> points from base to included case — "
                    f"'{link.target}' is the actor-facing base, so the arrow appears reversed",
                )
            elif st == "extend" and src_conn:
                yield self.violation(
                    diagram,
                    link.line,
                    f"<<extend>> points from extension to base — "
                    f"'{link.source}' is the actor-facing base, so the arrow appears reversed",
                )


@register
class UseCaseActorNaming(Rule):
    """Use cases as verb–object phrases ("Place order"), actors as nouns.

    Mixing forms confuses reading. Option ``verbs`` supplies the accepted leading
    verbs for use-case names; with no whitelist the rule is dormant (there is no
    language-agnostic verb oracle).
    """

    id = "UC002"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        verbs = {v.lower() for v in self.options.get("verbs", [])}
        if not verbs:
            return
        for p in diagram.participants.values():
            if p.kind != "usecase" or not p.declared or not p.name:
                continue
            if p.name.split()[0].lower() not in verbs:
                yield self.violation(
                    diagram,
                    p.line,
                    f"Use case '{p.name}' is not verb-first — name it "
                    '"verb + object" (e.g. "Place order")',
                )

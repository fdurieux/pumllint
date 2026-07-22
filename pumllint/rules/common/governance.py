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


@register
class OrphanUseCaseActor(Rule):
    """Use-case diagram: actor linked to zero use cases, or vice versa."""

    id = "UC001"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        if not diagram.usecase_links:
            return
        linked: set[str] = set()
        for src, dst, _ in diagram.usecase_links:
            linked.add(src)
            linked.add(dst)
        for p in diagram.participants.values():
            if p.declared and p.name not in linked:
                yield self.violation(
                    diagram,
                    p.line,
                    f"{p.kind.capitalize()} '{p.name}' is not linked to anything",
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

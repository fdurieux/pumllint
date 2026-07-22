"""Structural and design rules for class diagrams."""

from __future__ import annotations

import re
from typing import Iterable

from ...model import ClassRelation, Diagram, Violation
from .. import Rule, register

# Relation kinds that model a structural "has-a" link and therefore carry
# cardinality; generalization/realization/dependency edges do not.
_STRUCTURAL_KINDS = ("association", "aggregation", "composition")


@register
class ClassNaming(Rule):
    """Class and member names must follow the project convention.

    Options: ``class_pattern`` (regex, default PascalCase) and
    ``member_pattern`` (regex, default camelCase/snake_case start). Enum
    members are exempt (constant conventions vary too much to default).
    """

    id = "CLS001"

    DEFAULT_CLASS_PATTERN = r"^[A-Z][A-Za-z0-9]*$"
    DEFAULT_MEMBER_PATTERN = r"^[a-z_][A-Za-z0-9_]*$"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        class_pattern = self.options.get("class_pattern", self.DEFAULT_CLASS_PATTERN)
        member_pattern = self.options.get("member_pattern", self.DEFAULT_MEMBER_PATTERN)
        for c in diagram.classes.values():
            if c.declared and not re.match(class_pattern, c.name):
                yield self.violation(
                    diagram,
                    c.line,
                    f"{c.kind.capitalize()} name '{c.name}' does not match pattern {class_pattern!r}",
                )
            if c.kind == "enum":
                continue
            for m in c.members:
                if not re.match(member_pattern, m.name):
                    yield self.violation(
                        diagram,
                        m.line,
                        f"Member '{m.name}' of '{c.name}' does not match pattern {member_pattern!r}",
                    )


@register
class AssociationMultiplicity(Rule):
    """Associations (and aggregations/compositions) declare both multiplicities.

    An association without cardinalities omits the very constraint the diagram
    exists to record ('Order "1..*" -- "1" Customer').
    """

    id = "CLS002"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        for r in diagram.class_relations:
            if r.kind not in _STRUCTURAL_KINDS:
                continue
            missing = [
                end
                for end, card in ((r.left, r.left_card), (r.right, r.right_card))
                if not card
            ]
            if missing:
                yield self.violation(
                    diagram,
                    r.line,
                    f"{r.kind.capitalize()} between '{r.left}' and '{r.right}' has no "
                    f"multiplicity on {' or '.join(repr(e) for e in missing)} "
                    '— write e.g. \'Order "1..*" -- "1" Customer\'',
                )


@register
class AssociationLabel(Rule):
    """Plain associations carry a role or verb label ('places', 'owns').

    An unlabelled association states that two classes relate without saying
    how. Aggregation/composition/generalization already carry semantics in the
    arrow itself and are exempt.
    """

    id = "CLS003"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        for r in diagram.class_relations:
            if r.kind == "association" and not r.label:
                yield self.violation(
                    diagram,
                    r.line,
                    f"Association between '{r.left}' and '{r.right}' has no label "
                    "— name the relationship (e.g. ': places')",
                )


@register
class InheritanceCycle(Rule):
    """No cycles in the generalization/realization hierarchy.

    A cyclic hierarchy is semantically invalid UML and uncompilable in any
    target language, yet PlantUML renders it without complaint.
    """

    id = "CLS004"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        edges: dict[str, list[ClassRelation]] = {}
        for r in diagram.class_relations:
            if r.kind in ("extension", "realization"):
                edges.setdefault(r.child, []).append(r)

        reported: set[frozenset[str]] = set()
        for start in sorted(edges):
            path: list[str] = []
            on_path: set[str] = set()

            def visit(node: str) -> Iterable[Violation]:
                if node in on_path:
                    cycle = path[path.index(node):] + [node]
                    key = frozenset(cycle)
                    if key not in reported:
                        reported.add(key)
                        closing = next(
                            r for r in edges[path[-1]] if r.parent == node
                        )
                        yield self.violation(
                            diagram,
                            closing.line,
                            "Inheritance cycle: " + " -> ".join(cycle),
                        )
                    return
                path.append(node)
                on_path.add(node)
                for r in edges.get(node, ()):
                    yield from visit(r.parent)
                on_path.discard(node)
                path.pop()

            yield from visit(start)


@register
class MaxMembers(Rule):
    """A class box with dozens of members is a god-class smell in the model
    just as in code, and unreadable when rendered. Option: ``max`` (default 15).
    """

    id = "CLS005"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        limit = int(self.options.get("max", 15))
        for c in diagram.classes.values():
            if len(c.members) > limit:
                yield self.violation(
                    diagram,
                    c.line,
                    f"{c.kind.capitalize()} '{c.name}' has {len(c.members)} members "
                    f"(max {limit}) — split responsibilities or elide detail",
                )

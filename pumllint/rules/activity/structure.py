"""Structural rules for activity diagrams (new-style syntax)."""

from __future__ import annotations

from typing import Iterable

from ...model import Diagram, Violation
from .. import Rule, register


@register
class MissingStart(Rule):
    """Activity diagram with actions but no ``start`` node.

    Without an explicit entry point the reader cannot tell where the flow
    begins; PlantUML renders it anyway.
    """

    id = "ACT001"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        actions = [n for n in diagram.activity_nodes if n.kind == "action"]
        if not actions:
            return
        if not any(n.kind == "start" for n in diagram.activity_nodes):
            yield self.violation(
                diagram,
                actions[0].line,
                "Activity flow has no 'start' node — entry point is implicit",
            )


@register
class MissingStop(Rule):
    """Activity diagram whose flow never reaches an explicit terminal.

    ``kill``/``detach`` count as terminals (the parser folds them into
    ``stop``/``end``).
    """

    id = "ACT002"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        actions = [n for n in diagram.activity_nodes if n.kind == "action"]
        if not actions:
            return
        if not any(n.kind in ("stop", "end") for n in diagram.activity_nodes):
            yield self.violation(
                diagram,
                actions[-1].line,
                "Activity flow never terminates with 'stop' or 'end' (unterminated flow)",
            )


@register
class UnlabelledDecisionBranch(Rule):
    """``if (...) then`` / ``else`` without a branch label like ``(yes)``.

    Unlabelled branches force the reader to guess which side is which.
    Option ``require_else_label`` (default True) also flags bare ``else``.
    """

    id = "ACT003"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        require_else = self.options.get("require_else_label", True)
        for n in diagram.activity_nodes:
            if n.kind == "decision" and not n.branch_label:
                yield self.violation(
                    diagram,
                    n.line,
                    f"Decision '({n.label})' has an unlabelled 'then' branch — write \"then (yes)\"",
                )
            elif n.kind == "branch" and require_else and not n.branch_label:
                yield self.violation(
                    diagram,
                    n.line,
                    "Unlabelled 'else' branch — write \"else (no)\"",
                )


@register
class UnterminatedConstruct(Rule):
    """if/while/repeat/fork/switch/partition never closed.

    The activity twin of SEQ004: PlantUML errors on some of these but
    silently tolerates others (notably unclosed ``partition`` braces).
    """

    id = "ACT004"

    _CLOSERS = {
        "if": "endif",
        "while": "endwhile",
        "repeat": "repeat while (...)",
        "fork": "end fork",
        "switch": "endswitch",
        "partition": "}",
    }

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        for b in diagram.blocks:
            if b.kind in self._CLOSERS and not b.terminated:
                label = f" ({b.label})" if b.label else ""
                yield self.violation(
                    diagram,
                    b.start_line,
                    f"'{b.kind}'{label} opened here is never closed with '{self._CLOSERS[b.kind]}'",
                )


@register
class SwimlaneNaming(Rule):
    """Swimlane names must follow a consistent convention.

    Swimlanes represent organizational responsibility; inconsistent lane names
    ("billing", "Billing dept.", "BILLING") fragment ownership mapping. Option
    ``pattern`` (regex, default: Capitalized words) sets the convention.
    """

    id = "ACT005"

    DEFAULT_PATTERN = r"^[A-Z][A-Za-z ]+$"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        pattern = self.pattern_option("pattern", self.DEFAULT_PATTERN)
        for n in diagram.activity_nodes:
            if n.kind == "swimlane" and not pattern.match(n.label):
                yield self.violation(
                    diagram,
                    n.line,
                    f"Swimlane '{n.label}' does not match pattern {pattern.pattern!r}",
                )


@register
class VerbFirstActivity(Rule):
    """Activities should be phrased verb-first ("Validate order").

    The classic ARIS/EPC function convention keeps models action-oriented and
    uniform. Option ``verbs`` supplies the accepted leading verbs; with no
    whitelist the rule is dormant (there is no language-agnostic verb oracle).
    """

    id = "ACT006"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        verbs = {v.lower() for v in self.options.get("verbs", [])}
        if not verbs:
            return
        for n in diagram.activity_nodes:
            if n.kind != "action" or not n.label:
                continue
            first = n.label.split()[0].lower()
            if first not in verbs:
                yield self.violation(
                    diagram,
                    n.line,
                    f"Activity '{n.label}' is not verb-first — name it "
                    '"verb + object" (e.g. "Validate order")',
                )

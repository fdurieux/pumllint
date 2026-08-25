"""Flow-integrity rules: activations, blocks, message labels."""

from __future__ import annotations

from typing import Iterable

from ...model import Diagram, GROUP_KEYWORDS, Violation
from .. import Rule, register


@register
class UnbalancedActivation(Rule):
    """activate without matching deactivate/return, or vice versa.

    A lifeline left activated at @enduml renders "open-ended" — usually a
    forgotten deactivate/return, i.e. an unterminated flow.
    """

    id = "SEQ003"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        depth: dict[str, list[int]] = {}  # participant -> stack of activate lines
        order: list[str] = []  # activation order, for attributing bare `return`

        for ev in diagram.activations:
            if ev.kind == "activate" and ev.participant:
                depth.setdefault(ev.participant, []).append(ev.line)
                order.append(ev.participant)
            elif ev.kind == "deactivate" and ev.participant:
                stack = depth.get(ev.participant, [])
                if stack:
                    stack.pop()
                    if ev.participant in order:
                        order.reverse()
                        order.remove(ev.participant)
                        order.reverse()
                else:
                    yield self.violation(
                        diagram,
                        ev.line,
                        f"deactivate '{ev.participant}' without a prior activate",
                    )
            elif ev.kind == "return":
                # return closes the most recent activation
                if order:
                    who = order.pop()
                    stack = depth.get(who, [])
                    if stack:
                        stack.pop()
                else:
                    yield self.violation(
                        diagram, ev.line, "return without any active lifeline"
                    )
            elif ev.kind == "destroy" and ev.participant:
                depth.pop(ev.participant, None)
                order = [o for o in order if o != ev.participant]

        for who, stack in depth.items():
            for line in stack:
                yield self.violation(
                    diagram,
                    line,
                    f"Lifeline '{who}' is activated here but never deactivated "
                    f"(unterminated flow)",
                )


@register
class UnterminatedBlock(Rule):
    """alt/opt/loop/par/group/box without a closing end."""

    id = "SEQ004"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        for b in diagram.blocks:
            if not b.terminated:
                label = f" \"{b.label}\"" if b.label else ""
                yield self.violation(
                    diagram,
                    b.start_line,
                    f"'{b.kind}'{label} block opened here is never terminated with 'end'",
                )


@register
class UnlabelledMessage(Rule):
    """Message arrows without a text label document nothing."""

    id = "SEQ005"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        allow_returns = self.options.get("allow_unlabelled_returns", True)
        for m in diagram.messages:
            if m.label:
                continue
            if allow_returns and m.is_return_arrow:
                continue
            src = m.source or "["
            dst = m.target or "]"
            yield self.violation(
                diagram, m.line, f"Message {src} {m.arrow} {dst} has no label"
            )


@register
class NoSelfMessage(Rule):
    """Self-messages usually hide logic that belongs in a note or 'ref over'.

    Option ``allowed`` — list of participant names for which self-messages
    are tolerated (e.g. batch schedulers that legitimately self-trigger).
    """

    id = "SEQ006"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        allowed = set(self.options.get("allowed", []))
        for m in diagram.messages:
            if m.source and m.source == m.target and m.source not in allowed:
                yield self.violation(
                    diagram,
                    m.line,
                    f"Self-message on '{m.source}' — consider a note or 'ref over' instead",
                )


@register
class UnlabelledBlockCondition(Rule):
    """alt/opt/loop/break/critical without a condition label reads as noise.

    A reader cannot tell *when* the branch applies. Option ``kinds`` overrides
    which block kinds require a label (default: alt, opt, loop, break,
    critical — 'group' and 'box' may legitimately be bare).
    """

    id = "SEQ007"

    DEFAULT_KINDS = ("alt", "opt", "loop", "break", "critical")

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        kinds = tuple(self.options.get("kinds", self.DEFAULT_KINDS))
        for b in diagram.blocks:
            if b.kind in kinds and not b.label:
                yield self.violation(
                    diagram,
                    b.start_line,
                    f"'{b.kind}' block has no condition label — state when this branch applies",
                )


@register
class FragmentNestingDepth(Rule):
    """Combined fragments nested beyond a readable depth.

    Deeply nested fragments (alt inside loop inside par …) are a readability
    cliff; beyond ``max_nesting_depth`` (default 3) the interaction should be
    extracted into a referenced sub-diagram. Only combined-fragment kinds
    (``GROUP_KEYWORDS``) count toward depth — a ``box`` is layout, not control.
    """

    id = "SEQ008"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        # `max` is the cap-family convention; the historical key wins when both are set.
        limit = int(self.options.get("max_nesting_depth", self.options.get("max", 3)))
        fragments = [b for b in diagram.blocks if b.kind in GROUP_KEYWORDS]
        for b in fragments:
            depth = 1 + sum(1 for a in fragments if a.contains_line(b.start_line))
            if depth > limit:
                yield self.violation(
                    diagram,
                    b.start_line,
                    f"'{b.kind}' fragment is nested {depth} levels deep "
                    f"(max {limit}) — extract it into a referenced sub-diagram",
                )


@register
class UnpairedReturn(Rule):
    """Dashed return arrow with no preceding call in the opposite direction.

    A dotted reply (``B --> A``) that answers no open ``A -> B`` call is usually
    arrow-style misuse or a modelling error. This base rule flags *orphans only*;
    strict reply discipline (naming the returned value) is the codegen-profile
    rule SEQ109.
    """

    id = "SEQ009"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        # A return B --> A pairs with an earlier call A -> B (the opposite
        # direction). Existence, not one-to-one consumption: within an alt each
        # mutually-exclusive branch may reply to the same preceding call.
        prior_calls: set[tuple[str, str]] = set()
        for m in sorted(diagram.messages, key=lambda m: m.line):
            src, dst = m.effective_source, m.effective_target
            if m.is_return_arrow:
                if src is None or dst is None or src == dst:
                    continue  # edge stubs / self returns are not call/reply pairs
                if (dst, src) not in prior_calls:
                    yield self.violation(
                        diagram,
                        m.line,
                        f"Return '{m.label or '<unlabelled>'}' from '{src}' to "
                        f"'{dst}' pairs with no preceding call",
                    )
                continue
            if m.is_async or src is None or dst is None or src == dst:
                continue
            prior_calls.add((src, dst))


@register
class MaxMessages(Rule):
    """Too many messages = the scenario is doing too much on one page.

    The message-count twin of GEN005's participant limit. Option: ``max``
    (default 30).
    """

    id = "SEQ011"

    def check(self, diagram: Diagram) -> Iterable[Violation]:
        limit = int(self.options.get("max", 30))
        count = len(diagram.messages)
        if count > limit:
            yield self.violation(
                diagram,
                diagram.messages[limit].line,
                f"Diagram has {count} messages (max {limit}) — split per phase "
                "or extract a 'ref over' sub-diagram",
            )

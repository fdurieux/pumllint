"""Core domain model shared by parser, rules and reporters.

The parser produces a :class:`Diagram` (a lightweight semantic model of a
PlantUML source file). Rules inspect the model and emit :class:`Violation`
objects. Reporters serialize violations for humans or machines (SonarQube).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(Enum):
    """Linter severities, mapped by reporters onto tool-specific scales."""

    INFO = "info"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"
    BLOCKER = "blocker"


@dataclass(frozen=True)
class Violation:
    """A single rule finding at a location in a source file."""

    rule_id: str
    message: str
    file_path: str
    line: int
    severity: Severity
    column: Optional[int] = None


# ---------------------------------------------------------------------------
# Parsed semantic model
# ---------------------------------------------------------------------------

PARTICIPANT_KEYWORDS = (
    "participant",
    "actor",
    "boundary",
    "control",
    "entity",
    "database",
    "collections",
    "queue",
)

GROUP_KEYWORDS = ("alt", "opt", "loop", "par", "break", "critical", "group")


@dataclass
class Participant:
    """A lifeline: declared explicitly, or implicitly created by first use."""

    name: str  # canonical identifier used in arrows
    kind: str  # participant / actor / ... / "implicit"
    line: int  # line of declaration, or of first use if implicit
    declared: bool
    display_name: Optional[str] = None  # long name when `as` alias is used
    stereotype: Optional[str] = None  # e.g. "service" for <<service>>


@dataclass
class Message:
    """A message between two lifelines (or an incoming/outgoing stub)."""

    source: Optional[str]  # None for incoming from '[' edge
    target: Optional[str]  # None for outgoing to ']' edge
    label: str
    line: int
    arrow: str
    activates_target: bool = False  # trailing ++ shortcut
    deactivates_source: bool = False  # trailing -- shortcut
    is_return_arrow: bool = False  # dotted arrow (visual return convention)

    # -- direction / synchrony helpers -----------------------------------
    @property
    def is_reversed(self) -> bool:
        """True for left-pointing arrows (``A <-- B``: flow is B → A)."""
        return self.arrow.lstrip("o").startswith("<")

    @property
    def is_async(self) -> bool:
        """True for explicitly asynchronous arrows (``->>`` / ``<<-``)."""
        return ">>" in self.arrow or "<<" in self.arrow

    @property
    def effective_source(self) -> Optional[str]:
        """Semantic sender, normalizing reversed arrows."""
        return self.target if self.is_reversed else self.source

    @property
    def effective_target(self) -> Optional[str]:
        """Semantic receiver, normalizing reversed arrows."""
        return self.source if self.is_reversed else self.target


@dataclass
class ActivationEvent:
    """Explicit activate/deactivate/return/destroy statement."""

    kind: str  # activate | deactivate | return | destroy
    participant: Optional[str]
    line: int
    label: Optional[str] = None  # returned value on `return <label>`


@dataclass
class BlockBranch:
    """An ``else`` branch inside an alt (or similar) fragment."""

    label: str
    line: int


@dataclass
class Block:
    """A grouping construct: alt/opt/loop/par/break/critical/group or box."""

    kind: str
    label: str
    start_line: int
    end_line: Optional[int] = None  # None => unterminated
    else_branches: list[BlockBranch] = field(default_factory=list)

    @property
    def terminated(self) -> bool:
        return self.end_line is not None

    def contains_line(self, line: int) -> bool:
        """True when *line* falls inside this fragment's span."""
        end = self.end_line if self.end_line is not None else float("inf")
        return self.start_line < line < end


@dataclass
class Directive:
    """Miscellaneous statement of interest to governance rules."""

    kind: str  # skinparam | title | autonumber | header | footer ...
    value: str
    line: int


@dataclass
class ActivityNode:
    """A node in an activity diagram (new-style syntax).

    kind: start | stop | end | action | decision | branch | swimlane
    For ``swimlane`` nodes ``label`` is the lane name (``|Lane|``).
    For decisions (``if``/``elseif``) ``label`` is the condition and
    ``branch_label`` the ``then (yes)`` annotation; for ``branch`` (``else``)
    ``branch_label`` is the ``(no)`` annotation.
    """

    kind: str
    label: str
    line: int
    branch_label: Optional[str] = None


@dataclass(frozen=True)
class Suppression:
    """Inline suppression parsed from a ``' pumllint: disable...`` comment.

    ``rule_keys`` holds lowercase rule ids and/or kebab-case names; ``("*",)``
    means all rules. ``line`` is the target source line, or ``None`` for a
    file-wide suppression (``disable-file``).
    """

    rule_keys: tuple[str, ...]
    line: Optional[int]
    source_line: int


@dataclass
class Diagram:
    """Semantic model of one @startuml..@enduml block."""

    file_path: str
    name: Optional[str]  # name after @startuml, if any
    start_line: int
    end_line: Optional[int]
    diagram_type: str = "unknown"  # sequence | usecase | activity | unknown
    participants: dict[str, Participant] = field(default_factory=dict)
    messages: list[Message] = field(default_factory=list)
    activations: list[ActivationEvent] = field(default_factory=list)
    blocks: list[Block] = field(default_factory=list)
    directives: list[Directive] = field(default_factory=list)
    usecase_links: list[tuple[str, str, int]] = field(default_factory=list)
    activity_nodes: list[ActivityNode] = field(default_factory=list)
    suppressions: list[Suppression] = field(default_factory=list)

    # -- convenience accessors -------------------------------------------
    @property
    def title(self) -> Optional[Directive]:
        return next((d for d in self.directives if d.kind == "title"), None)

    @property
    def skinparams(self) -> list[Directive]:
        return [d for d in self.directives if d.kind == "skinparam"]

    def used_participant_names(self) -> set[str]:
        used: set[str] = set()
        for m in self.messages:
            if m.source:
                used.add(m.source)
            if m.target:
                used.add(m.target)
        for a in self.activations:
            if a.participant:
                used.add(a.participant)
        return used


# ---------------------------------------------------------------------------
# Semantic helpers: call/reply pairing and activation stack
# ---------------------------------------------------------------------------


@dataclass
class CallReturn:
    """A synchronous call paired with its (possibly missing) return.

    ``reply`` is the dotted reply arrow when one was found;
    ``returned_via_keyword`` marks calls closed by a ``return`` statement
    (whose label, if any, lands in ``return_label``).
    """

    call: Message
    reply: Optional[Message] = None
    returned_via_keyword: bool = False
    return_label: Optional[str] = None

    @property
    def answered(self) -> bool:
        return self.reply is not None or self.returned_via_keyword


def pair_calls_and_replies(diagram: Diagram) -> list[CallReturn]:
    """Pair synchronous calls with their replies along the message timeline.

    A *call* is a solid, non-dotted, non-async arrow between two distinct
    lifelines. A *reply* is a dotted arrow flowing back (target → source of an
    open call), or a ``return`` statement (which closes the most recent open
    call, mirroring PlantUML's own semantics). Self-messages, async arrows
    (``->>``) and edge stubs (``[->`` / ``->]``) never open a call.
    """
    events: list[tuple[int, str, object]] = [(m.line, "msg", m) for m in diagram.messages]
    events.extend((a.line, "ret", a) for a in diagram.activations if a.kind == "return")
    events.sort(key=lambda e: e[0])

    open_calls: list[CallReturn] = []
    all_calls: list[CallReturn] = []
    for _line, kind, obj in events:
        if kind == "ret":
            if open_calls:
                cr = open_calls.pop()
                cr.returned_via_keyword = True
                cr.return_label = obj.label  # type: ignore[union-attr]
            continue
        m: Message = obj  # type: ignore[assignment]
        src, dst = m.effective_source, m.effective_target
        if m.is_return_arrow:
            for cr in reversed(open_calls):
                if cr.call.effective_source == dst and cr.call.effective_target == src:
                    cr.reply = m
                    open_calls.remove(cr)
                    break
            continue
        if m.is_async or src is None or dst is None or src == dst:
            continue
        cr = CallReturn(call=m)
        open_calls.append(cr)
        all_calls.append(cr)
    return all_calls


def walk_activation_stack(
    diagram: Diagram,
) -> tuple[list[ActivationEvent], list[tuple[str, int]]]:
    """Replay activation events as per-lifeline stacks.

    Returns ``(orphan_closes, dangling_opens)``: ``deactivate`` statements
    with no open activation to close, and ``(participant, line)`` frames still
    open at ``@enduml``. ``return`` closes the most recently opened frame
    (any lifeline); ``destroy`` closes silently when nothing is open.
    """
    stack: list[tuple[str, int]] = []
    orphans: list[ActivationEvent] = []
    for a in diagram.activations:
        if a.kind == "activate" and a.participant:
            stack.append((a.participant, a.line))
        elif a.kind in ("deactivate", "destroy") and a.participant:
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][0] == a.participant:
                    del stack[i]
                    break
            else:
                if a.kind == "deactivate":
                    orphans.append(a)
        elif a.kind == "return":
            if stack:
                stack.pop()
    return orphans, list(stack)

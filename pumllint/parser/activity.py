"""Activity-diagram statement handling (new-style syntax).

Called from the main line-oriented parser. Recognizes the governance-relevant
subset of the *new* activity syntax (``start``/``stop``/``:action;``/``if``/
``while``/``repeat``/``fork``/``switch``/``partition``) and, like the rest of
the parser, deliberately ignores anything it does not understand.

Control constructs are recorded as :class:`~pumllint.model.Block` objects on
the diagram (kinds ``if``/``while``/``repeat``/``fork``/``switch``/
``partition``) so unterminated-construct rules work the same way as for
sequence diagrams. Nodes and decision branches land in
``Diagram.activity_nodes``.
"""

from __future__ import annotations

import re
from typing import Optional

from ..model import ActivityNode, Block, Diagram

# --- regexes ---------------------------------------------------------------

RE_ACT_TERMINAL = re.compile(r"^(?P<kw>start|stop|end|kill|detach)\s*;?\s*$", re.IGNORECASE)
RE_ACT_ACTION = re.compile(r"^:(?P<label>.*?)(?P<term>[;|<>/\]}]?)\s*$")
RE_ACT_IF = re.compile(
    r"^(?P<kw>if|elseif)\s*\((?P<cond>[^)]*)\)\s*then(?:\s*\((?P<branch>[^)]*)\))?\s*$",
    re.IGNORECASE,
)
RE_ACT_ELSE = re.compile(r"^else(?:\s*\((?P<branch>[^)]*)\))?\s*$", re.IGNORECASE)
RE_ACT_ENDIF = re.compile(r"^endif\s*$", re.IGNORECASE)
RE_ACT_WHILE = re.compile(
    r"^while\s*\((?P<cond>[^)]*)\)(?:\s*is\s*\((?P<branch>[^)]*)\))?\s*$", re.IGNORECASE
)
RE_ACT_ENDWHILE = re.compile(r"^endwhile(?:\s*\((?P<branch>[^)]*)\))?\s*$", re.IGNORECASE)
RE_ACT_REPEAT = re.compile(r"^repeat\s*$", re.IGNORECASE)
RE_ACT_REPEAT_WHILE = re.compile(
    r"^repeat\s*while\s*\((?P<cond>[^)]*)\).*$", re.IGNORECASE
)
RE_ACT_BACKWARD = re.compile(
    r"^backward\s*:(?P<label>.*?)(?P<term>[;|<>/\]}]?)\s*$", re.IGNORECASE
)
RE_ACT_FORK = re.compile(r"^fork\s*$", re.IGNORECASE)
RE_ACT_FORK_AGAIN = re.compile(r"^fork\s+again\s*$", re.IGNORECASE)
RE_ACT_END_FORK = re.compile(r"^(?:end\s*fork|end\s*merge)\s*$", re.IGNORECASE)
RE_ACT_SWITCH = re.compile(r"^switch\s*\((?P<cond>[^)]*)\)\s*$", re.IGNORECASE)
RE_ACT_CASE = re.compile(r"^case\s*\((?P<label>[^)]*)\)\s*$", re.IGNORECASE)
RE_ACT_ENDSWITCH = re.compile(r"^endswitch\s*$", re.IGNORECASE)
RE_ACT_PARTITION = re.compile(
    r'^partition\s+(?P<label>"[^"]+"|\S+)\s*\{?\s*$', re.IGNORECASE
)
RE_ACT_PARTITION_END = re.compile(r"^\}\s*$")
# Swimlane: |Lane| or |#color|Lane|  (does not match the |||... delay token,
# which carries no lane name between a single pair of pipes).
RE_ACT_SWIMLANE = re.compile(r"^\|(?:#\w+\|)?(?P<name>[^|]*)\|\s*$")

# Lines that *identify* a diagram as an activity diagram when its type is
# still unknown. ``end`` and ``stop`` are excluded on purpose: they are too
# ambiguous ('end' terminates sequence blocks).
_TYPE_MARKERS = (RE_ACT_IF, RE_ACT_WHILE, RE_ACT_SWITCH, RE_ACT_FORK)


def _close(stack: list[Block], kinds: tuple[str, ...], lineno: int) -> Optional[Block]:
    """Close the innermost open block of one of the given kinds."""
    for b in reversed(stack):
        if b.kind in kinds and not b.terminated:
            b.end_line = lineno
            stack.remove(b)
            return b
    return None


def try_parse(d: Diagram, act_stack: list[Block], lineno: int, line: str):
    """Attempt to interpret ``line`` as an activity-diagram statement.

    Returns ``"handled"`` when consumed, ``"action_open"`` when the line
    starts a multi-line ``:action`` whose terminator is on a later line
    (the caller should swallow lines until one ends with ``;``, ``|`` etc.),
    or ``False`` when the line is not an activity statement.
    """
    if d.diagram_type not in ("unknown", "activity"):
        return False  # never re-type a sequence/usecase diagram
    is_activity = d.diagram_type == "activity"

    # --- actions: :label;  (the ; | < > / ] } terminators all occur) -------
    m = RE_ACT_ACTION.match(line)
    if m:
        # In not-yet-typed diagrams only a single-line ':action;' identifies an
        # activity diagram — this keeps use-case inline actors (:Name: [as X])
        # from being mistaken for actions.
        if is_activity or m.group("term") == ";":
            d.diagram_type = "activity"
            d.activity_nodes.append(
                ActivityNode(kind="action", label=m.group("label").strip(), line=lineno)
            )
            return "handled" if m.group("term") else "action_open"

    # --- start/stop/end terminals -----------------------------------------
    m = RE_ACT_TERMINAL.match(line)
    if m:
        kw = m.group("kw").lower()
        if kw == "start":
            d.diagram_type = "activity"
            d.activity_nodes.append(ActivityNode(kind="start", label="", line=lineno))
            return "handled"
        if is_activity and kw in ("stop", "end", "kill", "detach"):
            kind = "stop" if kw in ("stop", "kill", "detach") else "end"
            d.activity_nodes.append(ActivityNode(kind=kind, label="", line=lineno))
            return "handled"
        return False

    # --- swimlanes: |Lane| (a type-discriminating marker, like start) -----
    m = RE_ACT_SWIMLANE.match(line)
    if m:
        d.diagram_type = "activity"
        d.activity_nodes.append(
            ActivityNode(kind="swimlane", label=m.group("name").strip(), line=lineno)
        )
        return "handled"

    # --- everything below only fires for known-activity or marker lines ---
    if not is_activity and not any(r.match(line) for r in _TYPE_MARKERS):
        return False

    m = RE_ACT_IF.match(line)
    if m:
        d.diagram_type = "activity"
        d.activity_nodes.append(
            ActivityNode(
                kind="decision",
                label=m.group("cond").strip(),
                line=lineno,
                branch_label=(m.group("branch") or "").strip() or None,
            )
        )
        if m.group("kw").lower() == "if":
            b = Block(kind="if", label=m.group("cond").strip(), start_line=lineno)
            d.blocks.append(b)
            act_stack.append(b)
        return "handled"
    m = RE_ACT_ELSE.match(line)
    if m and is_activity:
        d.activity_nodes.append(
            ActivityNode(
                kind="branch",
                label="else",
                line=lineno,
                branch_label=(m.group("branch") or "").strip() or None,
            )
        )
        return "handled"
    if RE_ACT_ENDIF.match(line) and is_activity:
        _close(act_stack, ("if",), lineno)
        return "handled"

    m = RE_ACT_WHILE.match(line)
    if m:
        d.diagram_type = "activity"
        b = Block(kind="while", label=m.group("cond").strip(), start_line=lineno)
        d.blocks.append(b)
        act_stack.append(b)
        return "handled"
    if RE_ACT_ENDWHILE.match(line) and is_activity:
        _close(act_stack, ("while",), lineno)
        return "handled"

    if RE_ACT_REPEAT_WHILE.match(line) and is_activity:  # before bare 'repeat'
        _close(act_stack, ("repeat",), lineno)
        return "handled"
    if RE_ACT_REPEAT.match(line) and is_activity:
        b = Block(kind="repeat", label="", start_line=lineno)
        d.blocks.append(b)
        act_stack.append(b)
        return "handled"
    # --- backward :label;  the action on a loop's return path -------------
    m = RE_ACT_BACKWARD.match(line)
    if m and is_activity:
        # Recorded under its own kind, not "action": ACT001 and ACT002 pick
        # the first and last *action* to report on, and a backward line is
        # neither the start nor the end of the flow. `backward` is not a type
        # marker either, so it never types an unknown diagram.
        d.activity_nodes.append(
            ActivityNode(kind="backward", label=m.group("label").strip(), line=lineno)
        )
        return "handled" if m.group("term") else "action_open"

    if RE_ACT_FORK_AGAIN.match(line) and is_activity:
        return "handled"
    if RE_ACT_END_FORK.match(line) and is_activity:
        _close(act_stack, ("fork",), lineno)
        return "handled"
    m = RE_ACT_FORK.match(line)
    if m:
        d.diagram_type = "activity"
        b = Block(kind="fork", label="", start_line=lineno)
        d.blocks.append(b)
        act_stack.append(b)
        return "handled"

    m = RE_ACT_SWITCH.match(line)
    if m:
        d.diagram_type = "activity"
        b = Block(kind="switch", label=m.group("cond").strip(), start_line=lineno)
        d.blocks.append(b)
        act_stack.append(b)
        return "handled"
    if is_activity and RE_ACT_CASE.match(line):
        return "handled"
    if RE_ACT_ENDSWITCH.match(line) and is_activity:
        _close(act_stack, ("switch",), lineno)
        return "handled"

    m = RE_ACT_PARTITION.match(line)
    if m and (is_activity or line.rstrip().endswith("{")):
        d.diagram_type = "activity"
        b = Block(kind="partition", label=m.group("label").strip('"'), start_line=lineno)
        d.blocks.append(b)
        act_stack.append(b)
        return "handled"
    if RE_ACT_PARTITION_END.match(line) and is_activity:
        _close(act_stack, ("partition",), lineno)
        return "handled"

    return False

"""Line-oriented PlantUML parser.

Deliberately *not* a full grammar: it recognizes the governance-relevant
subset (participant declarations, message arrows, activations, grouping
blocks, titles, skinparams, use-case links) and ignores the rest. This keeps
the linter robust against PlantUML language evolution: unknown lines are
simply skipped, never fatal.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator, Optional

from ..model import (
    ActivationEvent,
    Block,
    BlockBranch,
    ClassEntity,
    Diagram,
    Directive,
    GROUP_KEYWORDS,
    Message,
    PARTICIPANT_KEYWORDS,
    Participant,
    StateNode,
    Suppression,
    UseCaseLink,
)
from . import activity, class_, state

# ---------------------------------------------------------------------------
# Regexes
# ---------------------------------------------------------------------------

_IDENT = r'(?:"[^"]+"|[\w.]+)'

RE_STARTUML = re.compile(r"^@startuml\s*(?P<name>\S.*)?$")
RE_ENDUML = re.compile(r"^@enduml\b")

RE_DECLARATION = re.compile(
    r"^(?P<kw>" + "|".join(PARTICIPANT_KEYWORDS) + r")\s+"
    r"(?P<first>" + _IDENT + r")"
    r"(?:\s+as\s+(?P<alias>" + _IDENT + r"))?"
    r"(?P<rest>.*)$",
    re.IGNORECASE,
)

# Sequence arrow: A -> B : label   (with many arrow variants, ++/-- shortcuts,
# incoming '[' / outgoing ']' stubs, reverse arrows)
_ARROW = r"(?P<arrow>[<o\\/x]*[-.]{1,2}(?:\[[^\]]*\])?[-.]*[>o\\/x]*[+*!]*)"
RE_MESSAGE = re.compile(
    r"^(?P<src>\[|" + _IDENT + r")?\s*"
    + _ARROW
    + r"\s*(?P<dst>\]|" + _IDENT + r")?\s*"
    r"(?P<mods>(?:\+\+|--|\*\*|!!)\s*)?"
    r"(?::\s*(?P<label>.*))?$"
)

RE_ACTIVATE = re.compile(
    r"^(?P<kw>activate|deactivate|destroy|create)\s+(?P<who>" + _IDENT + r")",
    re.IGNORECASE,
)
RE_RETURN = re.compile(r"^return\b\s*(?P<label>.*)$", re.IGNORECASE)

RE_GROUP_START = re.compile(
    r"^(?P<kw>" + "|".join(GROUP_KEYWORDS) + r")\b\s*(?P<label>.*)$",
    re.IGNORECASE,
)
RE_GROUP_ELSE = re.compile(r"^else\b\s*(?P<label>.*)$", re.IGNORECASE)
RE_STEREOTYPE = re.compile(r"<<\s*(?P<st>[^<>]+?)\s*>>")
RE_GROUP_END = re.compile(r"^end\s*$", re.IGNORECASE)
RE_BOX_START = re.compile(r'^box\b\s*(?P<label>.*)$', re.IGNORECASE)
RE_BOX_END = re.compile(r"^end\s*box\s*$", re.IGNORECASE)

RE_TITLE = re.compile(r"^title\b\s*(?P<v>.*)$", re.IGNORECASE)
RE_SKINPARAM = re.compile(r"^skinparam\b\s*(?P<v>.*)$", re.IGNORECASE)
RE_AUTONUMBER = re.compile(r"^autonumber\b\s*(?P<v>.*)$", re.IGNORECASE)
RE_HEADER = re.compile(r"^(?:center\s+|left\s+|right\s+)?header\b\s*(?P<v>.*)$", re.IGNORECASE)
RE_FOOTER = re.compile(r"^(?:center\s+|left\s+|right\s+)?footer\b\s*(?P<v>.*)$", re.IGNORECASE)
RE_CAPTION = re.compile(r"^caption\b\s*(?P<v>.*)$", re.IGNORECASE)
RE_NOTE_START = re.compile(r"^[hr]?note\b(?!.*:\s*\S).*$", re.IGNORECASE)
RE_NOTE_END = re.compile(r"^end\s*[hr]?note\s*$", re.IGNORECASE)
RE_NOTE_INLINE = re.compile(r"^[hr]?note\b[^:]*:\s*(?P<v>.+)$", re.IGNORECASE)

# Use-case diagram elements
RE_USECASE_DECL = re.compile(
    r"^usecase\s+(?P<first>" + _IDENT + r"|\([^)]+\))"
    r"(?:\s+as\s+(?P<alias>" + _IDENT + r"|\([^)]+\)))?",
    re.IGNORECASE,
)
RE_UC_LINK = re.compile(
    r"^(?P<src>:" + r"[^:]+" + r":|\([^)]+\)|" + _IDENT + r")\s*"
    r"(?P<arrow>[<]?[-.]{1,4}[>]?)\s*"
    r"(?P<dst>:" + r"[^:]+" + r":|\([^)]+\)|" + _IDENT + r")\s*"
    r"(?::\s*(?P<label>.*))?$"
)
RE_UC_ACTOR_INLINE = re.compile(r"^:(?P<name>[^:]+):(?:\s+as\s+(?P<alias>" + _IDENT + r"))?\s*$")

_LIKELY_KEYWORD_SOURCES = {
    "activate", "deactivate", "destroy", "create", "return", "note", "ref",
    "alt", "opt", "loop", "par", "break", "critical", "group", "else", "end",
    "box", "title", "skinparam", "autonumber", "hide", "show", "header",
    "footer", "legend", "endlegend", "newpage", "participant", "actor",
    "boundary", "control", "entity", "database", "collections", "queue",
    "usecase", "rectangle", "package", "left", "right", "top", "bottom",
    "caption", "delay", "endnote", "endrnote", "endhnote", "mainframe",
    "endbox", "hnote", "rnote", "ignore", "set",
}


# Inline suppression comments, e.g.
#   ' pumllint: disable=SEQ001, unlabelled-message   (suppresses on next line)
#   ' pumllint: disable-file=GEN003                  (whole file)
#   ' pumllint: disable                              (all rules, next line)
RE_SUPPRESSION = re.compile(
    r"^(?:/')?\s*'*\s*pumllint:\s*(?P<scope>disable(?:-file)?)"
    r"(?:\s*=\s*(?P<keys>[\w\-*,\s]+?))?\s*(?:'/)?\s*$",
    re.IGNORECASE,
)


def _collect_suppressions(text: str) -> list[Suppression]:
    """Pre-pass extracting ``pumllint: disable`` comments from raw source."""
    raw_lines = text.splitlines()
    suppressions: list[Suppression] = []
    for i, raw in enumerate(raw_lines, start=1):
        line = raw.strip()
        if not (line.startswith("'") or line.startswith("/'")):
            continue
        m = RE_SUPPRESSION.match(line)
        if not m:
            continue
        keys_raw = m.group("keys")
        keys = (
            tuple(k.strip().lower() for k in keys_raw.split(",") if k.strip())
            if keys_raw
            else ("*",)
        )
        if m.group("scope").lower() == "disable-file":
            suppressions.append(Suppression(rule_keys=keys, line=None, source_line=i))
            continue
        # next-line scope: find the next effective source line
        target: Optional[int] = None
        for j in range(i, len(raw_lines)):
            nxt = raw_lines[j].strip()
            if not nxt or nxt.startswith("'") or nxt.startswith("/'") or nxt.startswith("!"):
                continue
            target = j + 1
            break
        if target is not None:
            suppressions.append(Suppression(rule_keys=keys, line=target, source_line=i))
    return suppressions


def _strip_ident(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    return raw.strip().strip('"')


def _iter_logical_lines(text: str) -> Iterator[tuple[int, str]]:
    """Yield (line_number, stripped_line), skipping comments/preprocessor."""
    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("'") or line.startswith("/'"):
            continue
        if line.startswith("!"):  # preprocessor: !include, !define, ...
            continue
        yield i, line


def parse_source(text: str, file_path: str = "<string>") -> list[Diagram]:
    """Parse a .puml source that may contain multiple @startuml blocks."""
    text = text.lstrip("\ufeff")  # tolerate a UTF-8 BOM before @startuml
    diagrams: list[Diagram] = []
    current: Optional[Diagram] = None
    block_stack: list[Block] = []
    act_stack: list[Block] = []
    cls_stack: list[ClassEntity] = []
    sta_stack: list[StateNode] = []
    in_note = False
    note_buf: list[str] = []
    note_start = 0
    in_action = False
    suppressions = _collect_suppressions(text)

    for lineno, line in _iter_logical_lines(text):
        m = RE_STARTUML.match(line)
        if m:
            current = Diagram(
                file_path=file_path,
                name=(m.group("name") or "").strip() or None,
                start_line=lineno,
                end_line=None,
            )
            current.suppressions = list(suppressions)
            diagrams.append(current)
            block_stack = []
            act_stack = []
            cls_stack = []
            sta_stack = []
            in_note = False
            in_action = False
            continue
        if current is None:
            continue
        if RE_ENDUML.match(line):
            current.end_line = lineno
            current = None
            continue

        # Multi-line activity actions: swallow until a terminator line
        if in_action:
            if line.rstrip()[-1:] in ";|<>/]}":
                in_action = False
            continue

        # Multi-line notes: swallow content until 'end note' (text kept as a
        # note directive so completeness rules can inspect it)
        if in_note:
            if RE_NOTE_END.match(line):
                in_note = False
                current.directives.append(
                    Directive(kind="note", value=" ".join(note_buf), line=note_start)
                )
            else:
                note_buf.append(line)
            continue
        if RE_NOTE_END.match(line):
            continue
        if RE_NOTE_START.match(line):
            in_note = True
            note_buf = []
            note_start = lineno
            continue
        m = RE_NOTE_INLINE.match(line)
        if m:
            current.directives.append(
                Directive(kind="note", value=m.group("v").strip(), line=lineno)
            )
            continue

        outcome = _parse_statement(
            current, block_stack, act_stack, cls_stack, sta_stack, lineno, line
        )
        if outcome == "action_open":
            in_action = True

    return diagrams


def _parse_statement(
    d: Diagram,
    block_stack: list[Block],
    act_stack: list[Block],
    cls_stack: list[ClassEntity],
    sta_stack: list[StateNode],
    lineno: int,
    line: str,
):
    # --- activity diagrams --------------------------------------------------
    handled = activity.try_parse(d, act_stack, lineno, line)
    if handled:
        return handled if handled == "action_open" else None
    # --- class diagrams -----------------------------------------------------
    if class_.try_parse(d, cls_stack, lineno, line):
        return None
    # --- state diagrams -----------------------------------------------------
    if state.try_parse(d, sta_stack, lineno, line):
        return None
    # --- declarations --------------------------------------------------
    m = RE_DECLARATION.match(line)
    if m:
        first = _strip_ident(m.group("first"))
        alias = _strip_ident(m.group("alias"))
        name = alias or first
        st = RE_STEREOTYPE.search(m.group("rest") or "")
        d.participants.setdefault(
            name,
            Participant(
                name=name,
                kind=m.group("kw").lower(),
                line=lineno,
                declared=True,
                display_name=first if alias else None,
                stereotype=st.group("st") if st else None,
            ),
        )
        if d.diagram_type == "unknown" and m.group("kw").lower() != "actor":
            d.diagram_type = "sequence"
        return

    m = RE_USECASE_DECL.match(line)
    if m:
        first = _strip_ident(m.group("alias") or m.group("first"))
        name = first.strip("()") if first else first
        d.participants.setdefault(
            name, Participant(name=name, kind="usecase", line=lineno, declared=True)
        )
        d.diagram_type = "usecase"
        return

    m = RE_UC_ACTOR_INLINE.match(line)
    if m:
        name = _strip_ident(m.group("alias")) or m.group("name").strip()
        d.participants.setdefault(
            name, Participant(name=name, kind="actor", line=lineno, declared=True)
        )
        d.diagram_type = "usecase"
        return

    # --- directives -----------------------------------------------------
    for regex, kind in (
        (RE_TITLE, "title"),
        (RE_SKINPARAM, "skinparam"),
        (RE_AUTONUMBER, "autonumber"),
        (RE_HEADER, "header"),
        (RE_FOOTER, "footer"),
        (RE_CAPTION, "caption"),
    ):
        m = regex.match(line)
        if m:
            d.directives.append(Directive(kind=kind, value=m.group("v").strip(), line=lineno))
            return

    # --- activations ------------------------------------------------------
    m = RE_ACTIVATE.match(line)
    if m:
        d.activations.append(
            ActivationEvent(kind=m.group("kw").lower(), participant=_strip_ident(m.group("who")), line=lineno)
        )
        return
    m = RE_RETURN.match(line)
    if m:
        d.activations.append(
            ActivationEvent(
                kind="return",
                participant=None,
                line=lineno,
                label=m.group("label").strip() or None,
            )
        )
        return

    # --- blocks -----------------------------------------------------------
    if RE_BOX_END.match(line):
        for b in reversed(block_stack):
            if b.kind == "box" and not b.terminated:
                b.end_line = lineno
                block_stack.remove(b)
                break
        return
    if RE_GROUP_END.match(line):
        if block_stack:
            b = block_stack.pop()
            b.end_line = lineno
        return
    m = RE_GROUP_ELSE.match(line)
    if m:
        if block_stack:
            block_stack[-1].else_branches.append(
                BlockBranch(label=m.group("label").strip(), line=lineno)
            )
        return
    m = RE_BOX_START.match(line)
    if m:
        b = Block(kind="box", label=m.group("label").strip(), start_line=lineno)
        d.blocks.append(b)
        block_stack.append(b)
        return
    m = RE_GROUP_START.match(line)
    if m:
        b = Block(kind=m.group("kw").lower(), label=m.group("label").strip(), start_line=lineno)
        d.blocks.append(b)
        block_stack.append(b)
        return

    # --- use-case links (before sequence arrows: shapes differ) ----------
    if d.diagram_type == "usecase":
        m = RE_UC_LINK.match(line)
        if m:
            src_raw, dst_raw = m.group("src"), m.group("dst")
            arrow = m.group("arrow")
            if arrow.startswith("<") and not arrow.endswith(">"):
                src_raw, dst_raw = dst_raw, src_raw  # normalize A <.. B to B → A
            src = _uc_name(src_raw)
            dst = _uc_name(dst_raw)
            if src and dst:
                for name, raw in ((src, src_raw), (dst, dst_raw)):
                    # The endpoint syntax reveals the kind: (X) draws a
                    # use-case ellipse, :X: a stick-figure actor.
                    d.participants.setdefault(
                        name,
                        Participant(
                            name=name, kind=_uc_kind(raw), line=lineno, declared=False
                        ),
                    )
                d.usecase_links.append(
                    UseCaseLink(
                        source=src,
                        target=dst,
                        line=lineno,
                        label=(m.group("label") or "").strip(),
                        arrow=arrow,
                    )
                )
            return

    # --- sequence messages ------------------------------------------------
    m = RE_MESSAGE.match(line)
    if m and m.group("arrow") and (m.group("src") or m.group("dst")):
        src = _strip_ident(m.group("src"))
        dst = _strip_ident(m.group("dst"))
        if src == "[":
            src = None
        if dst == "]":
            dst = None
        # Guard against keyword lines mis-matched as messages
        if (src or "").lower() in _LIKELY_KEYWORD_SOURCES:
            return
        if src is None and dst is None:
            return
        arrow = m.group("arrow")
        mods = (m.group("mods") or "").strip()
        msg = Message(
            source=src,
            target=dst,
            label=(m.group("label") or "").strip(),
            line=lineno,
            arrow=arrow,
            activates_target="++" in mods or arrow.endswith("+"),
            deactivates_source="--" in mods,
            is_return_arrow="--" in arrow or ".." in arrow,  # dotted line = return convention
        )
        d.messages.append(msg)
        if d.diagram_type == "unknown":
            d.diagram_type = "sequence"
        for name in (src, dst):
            if name and name not in d.participants:
                d.participants[name] = Participant(
                    name=name, kind="implicit", line=lineno, declared=False
                )
        # ++/-- shortcuts also count as activation events
        if msg.activates_target and dst:
            d.activations.append(ActivationEvent(kind="activate", participant=dst, line=lineno))
        if msg.deactivates_source and src:
            d.activations.append(ActivationEvent(kind="deactivate", participant=src, line=lineno))
        return


def _uc_name(raw: str) -> Optional[str]:
    raw = raw.strip()
    if raw.startswith(":") and raw.endswith(":"):
        return raw.strip(":").strip()
    if raw.startswith("(") and raw.endswith(")"):
        return raw.strip("()").strip()
    return _strip_ident(raw)


def _uc_kind(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith(":") and raw.endswith(":"):
        return "actor"
    if raw.startswith("(") and raw.endswith(")"):
        return "usecase"
    return "implicit"


def parse_file(path: str | Path) -> list[Diagram]:
    p = Path(path)
    return parse_source(p.read_text(encoding="utf-8"), file_path=str(p))

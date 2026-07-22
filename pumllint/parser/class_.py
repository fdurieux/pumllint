"""Class-diagram statement handling.

Called from the main line-oriented parser. Recognizes the governance-relevant
subset of PlantUML class-diagram syntax (``class``/``abstract class``/
``interface``/``enum`` declarations, brace bodies with members, ``X : member``
shorthand, and relation arrows with multiplicities and labels) and, like the
rest of the parser, deliberately ignores anything it does not understand.

Type discrimination: a classifier declaration or a generalization arrow
(``<|--`` and friends — no other diagram form uses ``<|``) identifies a class
diagram. Per the parser contract, parsing only engages while the diagram type
is ``unknown``/``class`` — a sequence/activity/usecase diagram is never
re-typed, so plain ``A --> B`` arrows keep their sequence meaning.

Classifiers land in ``Diagram.classes``, edges in ``Diagram.class_relations``.
"""

from __future__ import annotations

import re
from typing import Optional

from ..model import ClassEntity, ClassMember, ClassRelation, Diagram

# --- regexes ---------------------------------------------------------------

_IDENT = r'(?:"[^"]+"|[\w.]+)'
_CARD = r'"[^"]*"'

RE_CLS_DECL = re.compile(
    r"^(?P<kw>abstract\s+class|abstract|interface|enum|class)\s+"
    r"(?P<first>" + _IDENT + r")"
    r"(?:\s+as\s+(?P<alias>" + _IDENT + r"))?"
    r"(?P<rest>[^{]*?)\s*(?P<brace>\{)?\s*$",
    re.IGNORECASE,
)

# Relation: Left "card"? arrow "card"? Right : label?  — the arrow accepts an
# optional embedded direction hint (-left->, -up-|>, …).
_REL_ARROW = (
    r"(?P<arrow><\|[-.]+|[*o<][-.]+|[-.]+"
    r"(?:(?:left|right|up|down)[-.]+)?"
    r"(?:\|>|[*o>])?|[-.]{2,})"
)
RE_CLS_REL = re.compile(
    r"^(?P<left>" + _IDENT + r")\s*(?:(?P<lcard>" + _CARD + r")\s*)?"
    + _REL_ARROW
    + r"\s*(?:(?P<rcard>" + _CARD + r")\s*)?(?P<right>" + _IDENT + r")"
    r"\s*(?::\s*(?P<label>.*))?$"
)

# X : +placeOrder()  — member added to a classifier from outside a body
RE_CLS_MEMBER_SHORTHAND = re.compile(
    r"^(?P<cls>" + _IDENT + r")\s*:\s*(?P<member>\S.*)$"
)

RE_STEREOTYPE = re.compile(r"<<\s*(?P<st>[^<>]+?)\s*>>")

# Body separator lines (-- == .. __ with optional embedded label) are visual
# grouping only, not members.
RE_BODY_SEPARATOR = re.compile(r"^([-=._])\1.*$")

# Member name: after stripping visibility (+ - # ~) and {modifier} prefixes,
# the leading identifier before '(' / ':' / whitespace.
RE_MEMBER_NAME = re.compile(r"^(?P<name>[\w]+)")

_TYPE_MARKER_ARROW = re.compile(r"<\||\|>")


def _classify(arrow: str) -> str:
    if "<|" in arrow or "|>" in arrow:
        return "realization" if "." in arrow else "extension"
    if arrow.startswith("*") or arrow.endswith("*"):
        return "composition"
    if arrow.startswith("o") or arrow.endswith("o"):
        return "aggregation"
    if "." in arrow:
        return "dependency"
    return "association"


def _strip_ident(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    return raw.strip().strip('"')


def _ensure_entity(d: Diagram, name: str, lineno: int) -> ClassEntity:
    if name not in d.classes:
        d.classes[name] = ClassEntity(
            name=name, kind="implicit", line=lineno, declared=False
        )
    return d.classes[name]


def _add_member(entity: ClassEntity, lineno: int, raw: str) -> None:
    text = raw.strip()
    text = re.sub(r"^[+\-#~]\s*", "", text)  # visibility prefix
    text = re.sub(r"^(?:\{[^}]*\}\s*)+", "", text)  # {static} / {abstract} …
    m = RE_MEMBER_NAME.match(text)
    entity.members.append(
        ClassMember(
            name=m.group("name") if m else text,
            raw=raw.strip(),
            line=lineno,
            is_method="(" in text,
        )
    )


def try_parse(d: Diagram, cls_stack: list[ClassEntity], lineno: int, line: str):
    """Attempt to interpret ``line`` as a class-diagram statement.

    ``cls_stack`` holds the classifier whose brace body is currently open (the
    class-diagram twin of the activity parser's ``act_stack``). Returns
    ``"handled"`` when consumed, ``False`` otherwise.
    """
    if d.diagram_type not in ("unknown", "class"):
        return False  # never re-type a sequence/usecase/activity diagram
    is_class = d.diagram_type == "class"

    # --- inside an open brace body: members until '}' ----------------------
    if cls_stack:
        if line == "}":
            cls_stack.pop()
            return "handled"
        if RE_BODY_SEPARATOR.match(line):
            return "handled"
        _add_member(cls_stack[-1], lineno, line)
        return "handled"

    # --- classifier declarations ------------------------------------------
    m = RE_CLS_DECL.match(line)
    if m:
        d.diagram_type = "class"
        kw = re.sub(r"\s+", " ", m.group("kw").lower())
        kind = "abstract" if kw.startswith("abstract") else kw
        first = _strip_ident(m.group("first"))
        alias = _strip_ident(m.group("alias"))
        name = alias or first
        st = RE_STEREOTYPE.search(m.group("rest") or "")
        entity = d.classes.get(name)
        if entity is None or not entity.declared:
            entity = ClassEntity(
                name=name,
                kind=kind,
                line=lineno,
                declared=True,
                display_name=first if alias else None,
                stereotype=st.group("st") if st else None,
            )
            d.classes[name] = entity
        if m.group("brace"):
            cls_stack.append(entity)
        return "handled"

    # --- relations ---------------------------------------------------------
    # A generalization arrow types the diagram; other arrows are ambiguous
    # (sequence messages) and only bind once the diagram is known to be class.
    m = RE_CLS_REL.match(line)
    if m and (is_class or _TYPE_MARKER_ARROW.search(m.group("arrow"))):
        d.diagram_type = "class"
        left = _strip_ident(m.group("left"))
        right = _strip_ident(m.group("right"))
        arrow = m.group("arrow")
        _ensure_entity(d, left, lineno)
        _ensure_entity(d, right, lineno)
        d.class_relations.append(
            ClassRelation(
                left=left,
                right=right,
                kind=_classify(arrow),
                arrow=arrow,
                line=lineno,
                left_card=_strip_ident(m.group("lcard")),
                right_card=_strip_ident(m.group("rcard")),
                label=(m.group("label") or "").strip(),
            )
        )
        return "handled"

    # --- member shorthand: X : +member -------------------------------------
    # Bound to already-known classifiers only, so directive lines whose text
    # happens to contain a colon (title, captions, …) are never consumed.
    if is_class:
        m = RE_CLS_MEMBER_SHORTHAND.match(line)
        if m:
            name = _strip_ident(m.group("cls"))
            if name in d.classes:
                _add_member(d.classes[name], lineno, m.group("member"))
                return "handled"

    return False

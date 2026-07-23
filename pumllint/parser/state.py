"""State-diagram statement handling.

Called from the main line-oriented parser. Recognizes the governance-relevant
subset of PlantUML state-machine syntax (``state`` declarations with alias and
stereotype, composite ``state Foo { ... }`` bodies with concurrent-region
separators, ``[*]`` pseudo-state endpoints, and transition arrows with
labels) and, like the rest of the parser, deliberately ignores anything it
does not understand.

Type discrimination: the ``state`` keyword and the ``[*]`` pseudo-state are
used by no other diagram form (the sequence message regex cannot match
``[*]``), so both are safe markers. Per the parser contract, parsing only
engages while the diagram type is ``unknown``/``state`` — other forms are
never re-typed.

States land in ``Diagram.states``, edges in ``Diagram.transitions``. A
transition written inside a composite body records that composite as its
``container`` (STA001 counts only top-level initial transitions).
"""

from __future__ import annotations

import re

from ..model import Diagram, StateNode, StateTransition

# --- regexes ---------------------------------------------------------------

_IDENT = r'(?:"[^"]+"|[\w.]+)'

RE_STA_DECL = re.compile(
    r"^state\s+(?P<first>" + _IDENT + r")"
    r"(?:\s+as\s+(?P<alias>" + _IDENT + r"))?"
    r"(?P<rest>[^{]*?)\s*(?P<brace>\{)?\s*$",
    re.IGNORECASE,
)

# Transition: Src -[#style]-> Dst : label  (direction hints tolerated;
# endpoints may be the [*] pseudo-state, kept literal).
RE_STA_TRANSITION = re.compile(
    r"^(?P<src>\[\*\]|" + _IDENT + r")\s*"
    r"-+(?:\[[^\]]*\]-*|(?:left|right|up|down)-+)?>\s*"
    r"(?P<dst>\[\*\]|" + _IDENT + r")\s*"
    r"(?::\s*(?P<label>.*))?$",
    re.IGNORECASE,
)

# State : description  (adds prose to a state box; consumed, not modelled)
RE_STA_DESCRIPTION = re.compile(r"^(?P<state>" + _IDENT + r")\s*:\s*\S.*$")

# Concurrent-region separator inside a composite body: -- or ||
RE_REGION_SEPARATOR = re.compile(r"^(?:-{2,}|\|{2,})\s*$")

RE_STEREOTYPE = re.compile(r"<<\s*(?P<st>[^<>]+?)\s*>>")


def _strip_ident(raw: str) -> str:
    return raw.strip().strip('"')


def _endpoint(d: Diagram, raw: str, container: str | None, lineno: int) -> str:
    """Normalize a transition endpoint, creating implicit states on first use."""
    if raw == "[*]":
        return raw
    name = _strip_ident(raw)
    if name not in d.states:
        d.states[name] = StateNode(
            name=name, kind="implicit", line=lineno, declared=False,
            container=container,
        )
    return name


def try_parse(d: Diagram, sta_stack: list[StateNode], lineno: int, line: str):
    """Attempt to interpret ``line`` as a state-diagram statement.

    ``sta_stack`` holds the composite states whose brace bodies are open.
    Returns ``"handled"`` when consumed, ``False`` otherwise.
    """
    if d.diagram_type not in ("unknown", "state"):
        return False  # never re-type a sequence/usecase/activity/class diagram
    is_state = d.diagram_type == "state"
    container = sta_stack[-1].name if sta_stack else None

    # --- declarations ------------------------------------------------------
    m = RE_STA_DECL.match(line)
    if m:
        d.diagram_type = "state"
        first = _strip_ident(m.group("first"))
        alias = m.group("alias")
        name = _strip_ident(alias) if alias else first
        st = RE_STEREOTYPE.search(m.group("rest") or "")
        node = d.states.get(name)
        if node is None or not node.declared:
            node = StateNode(
                name=name,
                kind="state",
                line=lineno,
                declared=True,
                display_name=first if alias else None,
                stereotype=st.group("st") if st else None,
                container=container,
            )
            d.states[name] = node
        if m.group("brace"):
            node.composite = True
            sta_stack.append(node)
        return "handled"

    # --- transitions -------------------------------------------------------
    # A [*] endpoint types the diagram; plain A --> B arrows are ambiguous
    # (sequence messages) and only bind once the diagram is known to be state.
    m = RE_STA_TRANSITION.match(line)
    if m and (is_state or "[*]" in (m.group("src"), m.group("dst"))):
        d.diagram_type = "state"
        d.transitions.append(
            StateTransition(
                source=_endpoint(d, m.group("src"), container, lineno),
                target=_endpoint(d, m.group("dst"), container, lineno),
                label=(m.group("label") or "").strip(),
                line=lineno,
                container=container,
            )
        )
        return "handled"

    # --- composite bodies --------------------------------------------------
    if sta_stack:
        if line == "}":
            sta_stack.pop()
            return "handled"
        if RE_REGION_SEPARATOR.match(line):
            return "handled"

    # --- state descriptions: State : prose ---------------------------------
    # Bound to already-known states only, so directive lines whose text
    # happens to contain a colon (title, captions, …) are never consumed.
    if is_state:
        m = RE_STA_DESCRIPTION.match(line)
        if m and _strip_ident(m.group("state")) in d.states:
            return "handled"

    return False

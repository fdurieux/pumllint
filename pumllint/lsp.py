"""Language Server Protocol front-end — pumllint's diagnostics, at authoring time.

The seven-note Ilograph survey (docs/ilograph-*.md) ended on a measured
asymmetry: that ecosystem has good *editor-time* checking and no way to fail a
build, and pumllint was its mirror image — a gate with nothing at authoring
time. This module is the missing half. It does not add a rule, a dimension or
a score; it re-delivers the existing engine over stdio so an editor can show
the findings while the diagram is being written.

**The severity mapping is the point, and it is derived, not invented.**
``pumllint lint --fail-on`` (default ``major``) decides which findings return
exit code 1; ``pumllint lsp --fail-on`` takes the same flag, the same choices
and the same default, and maps *at or above that threshold* to LSP ``Error``
with everything below to ``Warning``/``Information``. So the squiggles in the
editor are exactly the findings that would fail CI, and pointing both at the
same threshold is a one-word change. Editor-time and build-time checking
disagree in most tools; here they agree by construction.

(``fail_on`` is deliberately *not* read from the config file: it is a CLI flag
everywhere else in this tool, and inventing a config key the lint path does
not honour would create exactly the editor/gate divergence this module
exists to prevent.)

**Protocol ownership of stdout is a hazard, not a detail.** LSP frames
JSON-RPC on stdout, and ``pumllint.cli._out`` prints there. A single stray
write corrupts the stream and the session dies with a parse error that names
nothing. :func:`serve` therefore takes the real stdout buffer once and
*rebinds* ``sys.stdout`` to stderr for the server's lifetime, so a stray
``print`` anywhere in the process degrades to a log line instead of breaking
the protocol.

**Code actions re-deliver ``pumllint fix``, they do not reimplement it.**
The fixer already returns per-finding, line-numbered edits, so the server
converts them to LSP ``TextEdit``\\s and applying those must produce bytes
identical to what ``pumllint fix`` writes — asserted by a differential test
over LF, CRLF, missing-trailing-newline, astral-character and
two-participants-on-one-line buffers, not assumed.

Zero third-party dependencies, in keeping with the rest of the package.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, BinaryIO, Optional, Sequence
from urllib.parse import unquote, urlparse

from .config import load_config
from .engine import Engine
from .fixer import Fix, apply_fixes, compute_fixes
from .model import SEVERITY_ORDER, Severity, Violation
from .parser import parse_source

# LSP DiagnosticSeverity. 1=Error, 2=Warning, 3=Information, 4=Hint.
_LSP_ERROR = 1
_LSP_WARNING = 2
_LSP_INFORMATION = 3

# textDocument/didChange sync kind: 1 = full document text each time. Full
# sync costs a reparse per keystroke-batch and buys exact agreement with the
# CLI, which is the property this server exists to preserve.
_SYNC_FULL = 1

SOURCE = "pumllint"

# CodeActionKinds. The fix-all kind is namespaced: an editor's generic
# "source.fixAll" on-save setting must not silently author diagram names and
# titles for someone who never named this tool. `context.only` matching is
# hierarchical, so a client asking for "source.fixAll" still gets this one.
_KIND_QUICKFIX = "quickfix"
_KIND_FIX_ALL = "source.fixAll.pumllint"

# Editors split lines on exactly these three separators. `str.splitlines()`
# also splits on \v, \f, \x1c-\x1e, \x85, \u2028 and \u2029, so a buffer
# containing any of them numbers its lines differently in Python than in the
# editor — one form feed shifts every subsequent line by one.
_LINE_SPLIT = re.compile(r"\r\n|\r|\n")


def _split_lines(text: str) -> list[str]:
    """*text* split the way an editor splits it — never ``str.splitlines()``.

    Used for every line index that crosses the protocol boundary. A wrong
    line number is a misplaced squiggle for a diagnostic; for a ``replace``
    edit it overwrites the wrong line, so the two must not disagree.
    """
    return _LINE_SPLIT.split(text)


def _has_exotic_separators(text: str) -> bool:
    """Whether *text* holds a separator the editor and the parser disagree on.

    Compared after dropping the empty element a trailing newline leaves in the
    editor-style split — ``"a\nb\n"`` is two lines to ``str.splitlines()``
    and three to ``re.split``, and that difference is universal rather than a
    signal. What remains is a genuine disagreement: a form feed, a vertical
    tab, U+2028 and friends, each of which shifts every later line number.
    """
    if not text:
        return False
    editor = _split_lines(text)
    if text.endswith(("\n", "\r")):
        editor = editor[:-1]
    return len(editor) != len(text.splitlines())


def _u16(text: str) -> int:
    """Length of *text* in UTF-16 code units.

    LSP measures ``Position.character`` in UTF-16 code units, not code
    points, unless ``positionEncoding`` is negotiated (3.17) — which this
    server does not do, so UTF-16 is the contract. ``len()`` is short by one
    for every astral character: ``"@startuml \U0001f680"`` is 11 code points
    and 12 UTF-16 units. As a range end that truncates mid-character and
    writes a lone surrogate into the file.
    """
    return len(text.encode("utf-16-le")) // 2


# ---------------------------------------------------------------------------
# URIs
# ---------------------------------------------------------------------------


def uri_to_path(uri: str) -> str:
    """``file://`` *uri* as a filesystem path, forward-slashed.

    Reported paths use forward slashes on every platform (the repository's
    stated contract), so this returns ``Path.as_posix()`` rather than
    ``str(path)``. Percent-escapes are decoded, and the leading slash Windows
    URIs carry before a drive letter (``/C:/x``) is stripped.
    """
    parsed = urlparse(uri)
    if parsed.scheme and parsed.scheme != "file":
        return uri  # untitled: and friends have no filesystem path; pass through
    path = unquote(parsed.path)
    if len(path) > 2 and path[0] == "/" and path[2] == ":":
        path = path[1:]  # /C:/dir/x.puml -> C:/dir/x.puml
    return Path(path).as_posix()


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


def lsp_severity(severity: Severity, fail_on: Severity = Severity.MAJOR) -> int:
    """LSP severity for a pumllint *severity*, keyed to the CI threshold.

    At or above *fail_on* is an ``Error`` — those are the findings that make
    ``pumllint`` exit 1. Below the threshold the mapping falls back to the
    finding's own severity: ``info`` is an ``Information`` and everything else
    a ``Warning``. (That second clause matters when the gate is raised: a
    ``major`` finding under ``--fail-on blocker`` is still worth a warning,
    not a footnote.) Deriving the red line from the same threshold the gate
    uses is what keeps the editor honest — nothing is underlined as an error
    that CI would accept, and nothing CI rejects is shown as a hint.
    """
    if SEVERITY_ORDER.index(severity) >= SEVERITY_ORDER.index(fail_on):
        return _LSP_ERROR
    return _LSP_INFORMATION if severity is Severity.INFO else _LSP_WARNING


def _range_for(violation: Violation, lines: list[str]) -> dict:
    """The document range to underline for *violation*.

    ``Violation.line`` is 1-based and ``column`` is optional. With a column,
    underline from it to end of line; without one, underline the whole line —
    a zero-width range renders as an invisible squiggle in most editors, which
    is worse than a slightly wide one. A line number past the end of the
    buffer (a stale diagnostic racing an edit) is clamped rather than dropped.
    """
    index = max(0, violation.line - 1)
    index = min(index, max(0, len(lines) - 1))
    text = lines[index] if lines else ""
    start = min(max(0, (violation.column or 1) - 1), len(text))
    return {
        "start": {"line": index, "character": _u16(text[:start])},
        "end": {"line": index, "character": max(_u16(text), _u16(text[:start]))},
    }


def diagnostics_for(
    text: str,
    path: str,
    engine: Engine,
    fail_on: Severity = Severity.MAJOR,
) -> list[dict]:
    """LSP diagnostics for buffer *text* attributed to *path*.

    The whole server reduces to this function: it is pure, it takes the
    unsaved buffer rather than a file, and it runs the same
    :class:`~pumllint.engine.Engine` the CLI runs. A buffer with no
    ``@startuml`` block parses to no diagrams and yields no diagnostics —
    matching the CLI, which reports such a file as not checked rather than as
    clean.
    """
    diagrams = parse_source(text, file_path=path)
    if not diagrams:
        return []
    lines = _split_lines(text) or [""]
    out: list[dict] = []
    for violation in engine.lint_diagrams(diagrams):
        out.append(
            {
                "range": _range_for(violation, lines),
                "severity": lsp_severity(violation.severity, fail_on),
                "code": violation.rule_id,
                "source": SOURCE,
                "message": violation.message,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Code actions
# ---------------------------------------------------------------------------


def _newline_of(text: str) -> str:
    """The newline :func:`~pumllint.fixer.apply_fixes` would use for *text*."""
    return "\r\n" if "\r\n" in text else "\n"


def text_edits_for(fixes: Sequence[Fix], text: str) -> list[dict]:
    """LSP text edits equivalent to applying *fixes* to *text*.

    Reproduces :func:`~pumllint.fixer.apply_fixes` exactly — that equivalence
    is the whole point of the surface and is asserted by a differential test,
    not assumed. Three properties carry it:

    * **One edit per affected line**, so the ranges are disjoint and no client
      has to arbitrate overlaps.
    * **Insert-only lines produce a zero-width edit at end of line** rather
      than a whole-line rewrite. A rewrite would restate the original text,
      so a keystroke landing on that line between the offer and the click
      would be reverted; a zero-width insert touches no existing character.
    * **List order within a line is preserved** — ``compute_fixes`` emits
      GEN002, then GEN001, then the SEQ declarations, and the title-first
      layout depends on that order surviving.

    Last replace on a line wins, matching ``apply_fixes``'s dict build.
    """
    if not fixes:
        return []
    lines = _split_lines(text)
    newline = _newline_of(text)
    replace: dict[int, Fix] = {f.line: f for f in fixes if f.kind == "replace"}
    inserts: dict[int, list[Fix]] = {}
    for f in fixes:
        if f.kind == "insert_after":
            inserts.setdefault(f.line, []).append(f)

    edits: list[dict] = []
    for line in sorted(set(replace) | set(inserts)):
        index = line - 1
        if not (0 <= index < len(lines)):
            continue  # a fix for a line this buffer no longer has
        original = lines[index]
        added = [f.content for f in inserts.get(line, ())]
        if line in replace:
            body = newline.join([replace[line].content] + added)
            start, end = 0, _u16(original)
        else:
            body = "".join(newline + c for c in added)
            start = end = _u16(original)
        edits.append(
            {
                "range": {
                    "start": {"line": index, "character": start},
                    "end": {"line": index, "character": end},
                },
                "newText": body,
            }
        )
    return edits


_SEQ_UNDECLARED = frozenset({"SEQ001", "SEQ101"})


def _diagnostic_for(violation: Violation, offered: Sequence[dict]) -> dict | None:
    """The client's own diagnostic dict matching *violation*, if it sent one.

    Diagnostics carry no ``data`` field, so correlation is by value. Two
    SEQ001 findings on one line share a code *and* a range — the range spans
    the whole line, since violations carry no column — so ``message`` is the
    only discriminator, and it round-trips byte-identically because this
    server generated it. Falls back to code-and-line when the message does
    not match, which is what happens if a client normalises text.
    """
    for prefer_message in (True, False):
        for d in offered:
            if d.get("source") != SOURCE or d.get("code") != violation.rule_id:
                continue
            if (d.get("range") or {}).get("start", {}).get("line") != violation.line - 1:
                continue
            if prefer_message and d.get("message") != violation.message:
                continue
            return d
    return None


def code_actions_for(
    text: str,
    path: str,
    engine: Engine,
    uri: str,
    *,
    offered: Sequence[dict] = (),
    only: Sequence[str] | None = None,
    line_range: tuple[int, int] | None = None,
    version: int | None = None,
    document_changes: bool = False,
    fail_on: Severity = Severity.MAJOR,
) -> list[dict]:
    """Code actions offering pumllint's mechanical fixes for *text*.

    Fixes are computed **once** for the whole buffer and then sliced by
    output, never by re-running :func:`~pumllint.fixer.compute_fixes` over a
    filtered violation list. That is not a shortcut, it is a correctness
    requirement: ``compute_fixes`` collapses its input to the *set of lines*
    carrying undeclared participants, so asking it about one participant on a
    line returns the fixes for every participant on that line. Filtering the
    input would produce two menu entries with identical edits and
    contradictory titles.

    For the same reason the SEQ declarations for one diagram are offered as a
    *single* action naming all of them, rather than one action per
    participant: they share one anchor and one edit, so separate entries
    would be a fiction.
    """
    diagrams = parse_source(text, file_path=path)
    if not diagrams:
        return []
    if _has_exotic_separators(text):
        # The buffer holds a separator the parser splits on and the editor
        # does not, so every line number below this point is suspect. A
        # misplaced squiggle is survivable; a misplaced `replace` overwrites
        # a line the user did not touch, so offer nothing at all.
        print(
            f"pumllint-lsp: {uri} contains non-editor line separators; "
            f"code actions suppressed",
            file=sys.stderr,
        )
        return []

    violations = engine.lint_diagrams(diagrams)
    stem = Path(path).stem if urlparse(uri).scheme in ("", "file") else ""
    fixes = compute_fixes(text, diagrams, violations, stem=stem)
    if not fixes:
        return []

    def edit(subset: Sequence[Fix]) -> dict:
        edits = text_edits_for(subset, text)
        if document_changes:
            return {
                "documentChanges": [
                    {"textDocument": {"uri": uri, "version": version}, "edits": edits}
                ]
            }
        return {"changes": {uri: edits}}

    def in_range(line: int) -> bool:
        if line_range is None:
            return True
        return line_range[0] <= line - 1 <= line_range[1]

    actions: list[dict] = []
    if _kind_matches(_KIND_QUICKFIX, only):
        for group, resolved in _quickfix_groups(fixes, violations, diagrams):
            if not any(in_range(v.line) for v in resolved):
                continue
            attached = [d for d in (_diagnostic_for(v, offered) for v in resolved) if d]
            if not attached:
                # Invoked from a keybinding rather than a lightbulb: the
                # client sends no diagnostics, so synthesise rather than
                # claiming the action resolves nothing.
                attached = [
                    d
                    for d in diagnostics_for(text, path, engine, fail_on)
                    for v in resolved
                    if d.get("code") == v.rule_id
                    and d["range"]["start"]["line"] == v.line - 1
                    and d.get("message") == v.message
                ]
            actions.append(
                {
                    "title": _title_for(group),
                    "kind": _KIND_QUICKFIX,
                    "diagnostics": attached,
                    "edit": edit(group),
                }
            )

    if len(actions) == 1:
        # isPreferred designates *the* auto-fix; with several offered, marking
        # them all makes Ctrl-. Enter pick arbitrarily.
        actions[0]["isPreferred"] = True

    if _kind_matches(_KIND_FIX_ALL, only):
        n = len(fixes)
        actions.append(
            {
                "title": f"Fix all {n} pumllint finding{'s' if n != 1 else ''}",
                "kind": _KIND_FIX_ALL,
                "edit": edit(fixes),
            }
        )
    return actions


def _quickfix_groups(
    fixes: Sequence[Fix], violations: Sequence[Violation], diagrams: Sequence
) -> list[tuple[list[Fix], list[Violation]]]:
    """Fixes grouped into one offer each, with the violations each resolves.

    GEN001 and GEN002 are one fix per diagram and match their violation by
    line. The SEQ declarations for a diagram are one group however many
    participants they cover, because they share an anchor and an edit.
    """
    groups: list[tuple[list[Fix], list[Violation]]] = []
    for rule in ("GEN002", "GEN001"):
        for f in (f for f in fixes if f.rule_id == rule):
            matched = [v for v in violations if v.rule_id == rule and v.line == f.line]
            if matched:
                groups.append(([f], matched))

    seq = [f for f in fixes if f.rule_id in _SEQ_UNDECLARED]
    if seq:
        # `Fix.line` is the anchor, never the violation's own line, so the
        # violations are gathered by rule rather than by position.
        resolved = [v for v in violations if v.rule_id in _SEQ_UNDECLARED]
        if resolved:
            groups.append((seq, resolved))
    return groups


def _title_for(group: Sequence[Fix]) -> str:
    """A title that names exactly what the group's edit does."""
    if len(group) == 1:
        return group[0].description[0].upper() + group[0].description[1:]
    names = ", ".join(
        f.content.split(maxsplit=1)[1] if " " in f.content else f.content for f in group
    )
    return f"Declare {len(group)} missing participants ({names})"


def _kind_matches(kind: str, only: Sequence[str] | None) -> bool:
    """Whether *kind* satisfies a ``context.only`` filter.

    CodeActionKinds are hierarchical: a client asking for ``source.fixAll``
    must be given ``source.fixAll.pumllint``. Comparing for equality would
    silently return nothing to the commonest fix-on-save configuration there
    is.
    """
    return not only or any(kind == o or kind.startswith(o + ".") for o in only)


# ---------------------------------------------------------------------------
# Hover and completion
# ---------------------------------------------------------------------------
#
# Both are deliberately narrow. This is a linter's language server, not a
# PlantUML one: it surfaces what pumllint already knows — its rule catalogue
# and the participants it parsed out of *this* buffer — and completes no
# PlantUML syntax at all. A keyword list would be a second product, would go
# stale against upstream, and nothing in the engine backs it.


def _rule_docs(rule_id: str) -> str | None:
    """Markdown for *rule_id* from the shipped catalogue, or ``None``.

    Every field here is declared metadata (``rules/catalog.toml``, stamped
    onto the class by ``@register``) — nothing is composed for display, so
    hover cannot drift from what the linter actually enforces.
    """
    from .rules import discover

    cls = discover().get(rule_id.upper())
    if cls is None:
        return None
    scope = "all diagram types" if "*" in cls.applies_to else ", ".join(cls.applies_to)
    lines = [
        f"**{cls.id}** \u00b7 `{cls.name}`",
        "",
        cls.description,
        "",
        f"- severity `{cls.default_severity.value}` \u00b7 dimension `{cls.dimension.value}`",
        f"- applies to {scope}",
    ]
    if cls.profiles:
        lines.append(
            f"- **profile-gated**: only active under `--profile "
            f"{'` / `'.join(cls.profiles)}`"
        )
    lines.append("")
    lines.append(f"Silence one line with `' pumllint: disable={cls.name}`.")
    return "\n".join(lines)


def hover_for(
    text: str,
    path: str,
    engine: Engine,
    line: int,
    character: int,
    fail_on: Severity = Severity.MAJOR,
) -> dict | None:
    """Hover content at a position, or ``None`` where there is nothing to say.

    Two things carry documentation: a finding (hover the squiggle, get the
    rule behind it) and a rule key inside a ``pumllint: disable`` comment
    (hover a suppression, see what you switched off). Everything else returns
    ``None`` rather than something invented.
    """
    lines = _split_lines(text)
    if not (0 <= line < len(lines)):
        return None
    source = lines[line]

    key = _suppression_key_at(source, character)
    if key is not None:
        docs = _rule_docs(key) or _rule_docs_by_name(key)
        if docs:
            return {"contents": {"kind": "markdown", "value": docs}}
        return None

    seen: list[str] = []
    for diag in diagnostics_for(text, path, engine, fail_on):
        if diag["range"]["start"]["line"] == line and diag["code"] not in seen:
            seen.append(diag["code"])
    if not seen:
        return None
    blocks = [d for d in (_rule_docs(rule) for rule in seen) if d]
    if not blocks:
        return None
    return {"contents": {"kind": "markdown", "value": "\n\n---\n\n".join(blocks)}}


def _rule_docs_by_name(key: str) -> str | None:
    """Rule docs looked up by kebab-case name rather than id."""
    from .rules import discover

    for rule_id, cls in discover().items():
        if cls.name.lower() == key.lower():
            return _rule_docs(rule_id)
    return None


def _suppression_key_at(source: str, character: int) -> str | None:
    """The suppression rule key under *character*, if this is such a comment."""
    stripped = source.strip()
    if not (stripped.startswith("'") or stripped.startswith("/'")):
        return None
    if "pumllint:" not in stripped.lower():
        return None
    for m in re.finditer(r"[\w-]+", source):
        if m.start() <= character <= m.end():
            word = m.group(0)
            if word.lower() in ("pumllint", "disable", "disable-file"):
                return None
            return word
    return None


def completions_for(
    text: str, path: str, line: int, character: int
) -> list[dict]:
    """Completion items at a position — participants, or rule keys.

    Inside a ``pumllint: disable`` comment the candidates are the rule
    catalogue (id and kebab name both, since either is accepted). Anywhere
    else they are the participants *this buffer* already mentions, which is
    the one vocabulary the linter genuinely knows. No PlantUML keywords: the
    parser is deliberately partial and line-oriented, so a keyword list would
    be invented rather than derived.
    """
    lines = _split_lines(text)
    if not (0 <= line < len(lines)):
        return []
    source = lines[line]
    stripped = source.strip()

    if (stripped.startswith("'") or stripped.startswith("/'")) and "pumllint:" in stripped.lower():
        from .rules import discover

        items: list[dict] = []
        for rule_id, cls in sorted(discover().items()):
            items.append(
                {
                    "label": cls.name,
                    "kind": 21,  # Constant
                    "detail": f"{rule_id} \u00b7 {cls.default_severity.value}",
                    "documentation": {"kind": "markdown", "value": cls.description},
                }
            )
            items.append(
                {
                    "label": rule_id,
                    "kind": 21,
                    "detail": f"{cls.name} \u00b7 {cls.default_severity.value}",
                    "documentation": {"kind": "markdown", "value": cls.description},
                }
            )
        return items

    diagrams = parse_source(text, file_path=path)
    names: dict[str, str] = {}
    for d in diagrams:
        for participant in d.participants.values():
            detail = participant.kind
            if participant.display_name:
                detail = f"{participant.kind} \u00b7 {participant.display_name}"
            if not participant.declared:
                detail += " (implicit)"
            names.setdefault(participant.name, detail)
    return [
        {"label": name, "kind": 6, "detail": detail}  # Variable
        for name, detail in sorted(names.items())
    ]


# ---------------------------------------------------------------------------
# Rename
# ---------------------------------------------------------------------------
#
# Renaming a participant is the one refactor pumllint's model can support, and
# only because the parser's own regexes expose *named group spans*: the
# message pattern captures ``src`` and ``dst`` separately from ``label``, so an
# identifier can be located without touching the prose beside it. Renaming
# ``A`` in ``A -> B : notify A's owner`` must not touch the label, and this is
# why it does not.
#
# The model does NOT record note or ref targets — ``note over A`` is parsed as
# prose — so a rename that left such a line behind would half-rename the
# diagram. Rather than guess, :func:`rename_edits` verifies its own work by
# re-parsing and refuses when the result would not be exactly right.


class _Error:
    """A JSON-RPC error to return in place of a result."""

    def __init__(self, code: int, message: str):
        self.code, self.message = code, message


def _error(code: int, message: str) -> _Error:
    return _Error(code, message)


class RenameUnsafe(Exception):
    """Raised when a rename cannot be completed correctly, with a reason."""


def _ident_spans(source: str) -> list[tuple[int, int, str]]:
    """``(start, end, name)`` for every participant identifier in *source*.

    Derived from the parser's own patterns rather than a fresh regex, so the
    two cannot disagree about what an identifier is. Spans are offset back to
    the raw line, since the parser matches against the stripped form.
    """
    from .parser.sequence import RE_ACTIVATE, RE_DECLARATION, RE_MESSAGE

    stripped = source.strip()
    if not stripped:
        return []
    offset = source.index(stripped)
    spans: list[tuple[int, int, str]] = []

    def take(match, *groups: str) -> None:
        for group in groups:
            raw = match.group(group)
            if raw is None or raw in ("[", "]"):
                continue  # incoming/outgoing edge stubs are not participants
            start, end = match.span(group)
            spans.append((start + offset, end + offset, raw.strip().strip('"')))

    m = RE_DECLARATION.match(stripped)
    if m:
        take(m, "first", "alias")
        return spans
    m = RE_ACTIVATE.match(stripped)
    if m:
        take(m, "who")
        return spans
    m = RE_MESSAGE.match(stripped)
    if m and m.group("arrow"):
        take(m, "src", "dst")
    return spans


def participant_at(text: str, line: int, character: int) -> tuple[str, dict] | None:
    """The participant name and its range at a position, or ``None``."""
    lines = _split_lines(text)
    if not (0 <= line < len(lines)):
        return None
    source = lines[line]
    for start, end, name in _ident_spans(source):
        if start <= character <= end:
            return name, {
                "start": {"line": line, "character": _u16(source[:start])},
                "end": {"line": line, "character": _u16(source[:end])},
            }
    return None


def rename_edits(text: str, path: str, old: str, new: str) -> list[dict]:
    """Text edits renaming participant *old* to *new* across the buffer.

    Raises :class:`RenameUnsafe` rather than returning a partial rename. The
    check is not a heuristic: the edits are applied to a copy, the result is
    re-parsed, and the participant set must come back as the original with
    exactly one name swapped. Anything else — a name the parser tracks
    somewhere this function does not rewrite, a collision with an existing
    participant, a ``note over`` mentioning the old name — is a refusal with a
    reason the editor shows.
    """
    from .fixer import _quote

    if not new.strip():
        raise RenameUnsafe("the new name is empty")
    lines = _split_lines(text)
    before = {p for d in parse_source(text, file_path=path) for p in d.participants}
    if old not in before:
        raise RenameUnsafe(f"{old!r} is not a participant in this diagram")
    if new in before:
        raise RenameUnsafe(f"{new!r} is already a participant — rename would merge two lifelines")

    edits: list[dict] = []
    for index, source in enumerate(lines):
        for start, end, name in _ident_spans(source):
            if name != old:
                continue
            edits.append(
                {
                    "range": {
                        "start": {"line": index, "character": _u16(source[:start])},
                        "end": {"line": index, "character": _u16(source[:end])},
                    },
                    "newText": _quote(new),
                }
            )
    if not edits:
        raise RenameUnsafe(f"found no references to {old!r} to rename")

    # Verify by re-parsing, rather than trusting the span scan.
    renamed = _apply_locally(text, edits)
    after = {p for d in parse_source(renamed, file_path=path) for p in d.participants}
    expected = (before - {old}) | {new}
    if after != expected:
        raise RenameUnsafe(
            f"rename would change the diagram in ways this refactor cannot verify "
            f"(expected participants {sorted(expected)}, got {sorted(after)})"
        )
    residual = _residual_mentions(renamed, old)
    if residual:
        raise RenameUnsafe(
            f"{old!r} still appears on line(s) "
            f"{', '.join(str(n) for n in residual)} — pumllint does not track "
            f"note or ref targets, so renaming there is not safe to automate"
        )
    return edits


def _apply_locally(text: str, edits: Sequence[dict]) -> str:
    """Apply *edits* to *text* the way a client would — for verification only."""
    starts = [0] + [m.end() for m in _LINE_SPLIT.finditer(text)]
    lines = _split_lines(text)

    def offset(pos: dict) -> int:
        row = min(pos["line"], len(lines) - 1)
        line, units, i = lines[row], pos["character"], 0
        seen = 0
        while i < len(line) and seen < units:
            seen += 2 if ord(line[i]) > 0xFFFF else 1
            i += 1
        return starts[row] + i

    for e in sorted(edits, key=lambda e: offset(e["range"]["start"]), reverse=True):
        a, b = offset(e["range"]["start"]), offset(e["range"]["end"])
        text = text[:a] + e["newText"] + text[b:]
    return text


def _checkable_part(source: str) -> str:
    """*source* with its prose removed — the part that names participants.

    A message label and a declaration's display text are prose: the ``A`` in
    ``A -> B : notify A owner`` is a word in a sentence, not a reference, and
    treating it as one would refuse almost every rename. What remains is the
    structural part, where a surviving identifier really is dangling.
    """
    from .parser.sequence import RE_DECLARATION, RE_MESSAGE

    stripped = source.strip()
    if not stripped:
        return ""
    m = RE_DECLARATION.match(stripped)
    if m:
        return stripped[: m.start("rest")] if m.group("rest") else stripped
    m = RE_MESSAGE.match(stripped)
    if m and m.group("arrow"):
        return stripped[: m.start("label")] if m.group("label") is not None else stripped
    return stripped


def _residual_mentions(text: str, old: str) -> list[int]:
    """1-based lines where *old* survives as a real reference after renaming.

    Catches the constructs the model does not track — ``note over A``,
    ``ref over A``, ``box`` groupings — where a silent half-rename would leave
    a dangling reference PlantUML happily renders as a brand-new lifeline.
    Prose is excluded (see :func:`_checkable_part`), as are comments and note
    bodies, so the refusal fires on references rather than on mentions.
    """
    from .parser.sequence import RE_NOTE_END, RE_NOTE_INLINE, RE_NOTE_START

    pattern = re.compile(r"(?<![\w.])" + re.escape(old) + r"(?![\w.])")
    hits: list[int] = []
    in_note_body = False
    for i, source in enumerate(_split_lines(text), start=1):
        stripped = source.strip()
        if in_note_body:
            if RE_NOTE_END.match(stripped):
                in_note_body = False
            continue  # a note's text is prose
        if stripped.startswith("'") or stripped.startswith("/'"):
            continue  # comments are not diagram references
        if RE_NOTE_START.match(stripped) and not RE_NOTE_INLINE.match(stripped):
            # The header of a multi-line note names participants, so it is
            # checked; the body that follows is prose and is not.
            in_note_body = True
            if pattern.search(stripped):
                hits.append(i)
            continue
        if pattern.search(_checkable_part(source)):
            hits.append(i)
    return hits


# ---------------------------------------------------------------------------
# Document symbols
# ---------------------------------------------------------------------------
#
# An outline of what the parser understood, and nothing else. The root of each
# diagram is backed by its ``@startuml`` line, which always parses; the
# children are backed by type-specific parsing, which may not have. That split
# is why an ``unknown`` diagram still gets a named, navigable row: the six C4
# diagrams in this repository's own `dynamics.puml` all type `unknown` and all
# carry real names, and six named roots is the most useful outline available
# for that file.
#
# Two structural facts drive the shape of the code below, and both were
# measured rather than assumed:
#
# * **Blocks can cross.** `if / while / endif / endwhile` yields spans [2,4]
#   and [3,5] — neither contains the other, because the parser closes blocks
#   out of the middle of its stack. So nesting clamps rather than trusting
#   containment, and `Block.contains_line` is deliberately unused (its
#   ``None -> infinity`` makes one unterminated block swallow its siblings).
# * **Leaves carry a line, never a span.** A class's members sit on lines
#   after its declaration, so a parent's range has to be the envelope of its
#   descendants or every child falls outside it.
#
# Rather than make five per-type builders individually correct, the tree is
# built loosely and then put through one type-agnostic normalizer that
# guarantees the invariants LSP requires. The property test over the whole
# .puml corpus is what keeps that honest.

# LSP SymbolKind. NOT the CompletionItemKind values used further up this file:
# 21 is Constant there and Null here, 6 is Variable there and Method here.
_SYM_MODULE = 2
_SYM_NAMESPACE = 3
_SYM_CLASS = 5
_SYM_METHOD = 6
_SYM_FIELD = 8
_SYM_INTERFACE = 11
_SYM_OBJECT = 19

# Above this many symbols the leaves are dropped and the root says so. A
# 1438-message diagram costs ~19 ms and 384 KB to serialise, which is fine;
# this is a guard against a pathological buffer (an unterminated `class Foo {`
# turns every following line into a member while you type), not a budget.
_SYMBOL_CAP = 2000

_FRAGMENT_KINDS = frozenset(
    {"alt", "opt", "loop", "par", "break", "critical", "group",
     "if", "while", "repeat", "fork", "switch"}
)


def _clamp_line(line: int, lines: Sequence[str]) -> int:
    """A 1-based model line as a 0-based buffer index, clamped."""
    return max(0, min(line - 1, max(0, len(lines) - 1)))


def _whole_line(line: int, lines: Sequence[str]) -> dict:
    index = _clamp_line(line, lines)
    text = lines[index] if lines else ""
    return {
        "start": {"line": index, "character": 0},
        "end": {"line": index, "character": _u16(text)},
    }


def _span(start_line: int, end_line: int, lines: Sequence[str]) -> dict:
    a, b = _clamp_line(start_line, lines), _clamp_line(end_line, lines)
    if b < a:
        b = a
    text = lines[b] if lines else ""
    return {
        "start": {"line": a, "character": 0},
        "end": {"line": b, "character": _u16(text)},
    }


def _selection_for(name: str, line: int, lines: Sequence[str]) -> dict:
    """The identifier's own span when the parser can locate it.

    Two implicit participants on one arrow (``Alice -> Bob : hi``) share a
    line, so whole-line selection ranges would make them indistinguishable —
    two rows with the same jump target. ``_ident_spans`` already returns exact
    per-identifier spans derived from the parser's own patterns.
    """
    index = _clamp_line(line, lines)
    source = lines[index] if lines else ""
    for start, end, found in _ident_spans(source):
        if found == name:
            return {
                "start": {"line": index, "character": _u16(source[:start])},
                "end": {"line": index, "character": _u16(source[:end])},
            }
    return _whole_line(line, lines)


def _symbol(name: str, kind: int, rng: dict, selection: dict, detail: str = "") -> dict:
    sym = {
        "name": name or "(unnamed)",
        "kind": kind,
        "range": rng,
        "selectionRange": selection,
        "children": [],
    }
    if detail:
        sym["detail"] = detail
    return sym


def _block_name(block) -> str:
    """A block always gets a name — ``repeat`` and ``fork`` never have labels."""
    label = (block.label or "").strip().strip('"')  # `box "Team"` keeps its quotes
    return f"{block.kind} {label}".strip() if label else block.kind


def _block_kind(block) -> int:
    return _SYM_NAMESPACE if block.kind in ("box", "partition") else _SYM_OBJECT


def _block_tree(blocks, floor: int, lines: Sequence[str]):
    """``(roots, spans)`` for *blocks* — nested, with crossing spans clamped.

    ``Diagram.blocks`` is one flat list in source order with no parent
    pointers, already ascending by ``start_line``. A stack walk nests it, but
    two corrections are needed and both are reachable:

    * ``end_line`` is ``None`` for an unterminated block — permanent for a
      real defect (SEQ004/ACT004) and the normal transient state while typing.
      It is floored rather than treated as infinity, or one unclosed ``alt``
      adopts every later sibling.
    * Spans genuinely **cross**: the parser closes out of the middle of its
      stack, so ``if/while/endif/endwhile`` gives [2,4] and [3,5]. A crossing
      child is clamped into its parent instead of being allowed to stick out.
    """
    roots: list[dict] = []
    spans: list[tuple[int, int, dict]] = []
    stack: list[tuple[int, dict]] = []
    for block in blocks:
        end = min(block.end_line or floor, floor)
        start = block.start_line
        while stack and stack[-1][0] < start:
            stack.pop()
        if stack:
            end = min(end, stack[-1][0])
        if end < start:
            end = start
        node = _symbol(
            _block_name(block),
            _block_kind(block),
            _span(start, end, lines),
            _whole_line(start, lines),
        )
        (stack[-1][1]["children"] if stack else roots).append(node)
        stack.append((end, node))
        spans.append((start, end, node))
    return roots, spans


def _place(line: int, spans, roots: list[dict]) -> list[dict]:
    """The child list for a leaf on *line* — innermost containing block, else root.

    An implicit participant is created at its first use, which is often inside
    a block, so leaves cannot simply be siblings of the block tree.
    """
    best: tuple[int, int, dict] | None = None
    for start, end, node in spans:
        if start <= line <= end and (best is None or start > best[0]):
            best = (start, end, node)
    return best[2]["children"] if best else roots


def _entity_symbol(entity, kind: int, lines: Sequence[str], detail: str = "") -> dict:
    name = entity.display_name or entity.name
    bits = [detail or entity.kind]
    if getattr(entity, "stereotype", None):
        bits.append(f"<<{entity.stereotype}>>")
    if not getattr(entity, "declared", True):
        bits.append("(implicit)")
    return _symbol(
        name,
        kind,
        _whole_line(entity.line, lines),
        _selection_for(entity.name, entity.line, lines),
        " ".join(b for b in bits if b),
    )


def _state_children(diagram, lines: Sequence[str]) -> list[dict]:
    """States nested by inverting ``StateNode.container``.

    ``container`` is set at first creation only, so a state re-opened inside a
    composite keeps its original parent — which can leave two siblings whose
    envelopes overlap. Cycles and orphans are unreachable in the current
    parser (the container is always an earlier, declared node), but the guard
    costs three lines and a future parser change should degrade rather than
    hang. **When the inverted tree is positionally inconsistent the states are
    returned flat**: a flat correct list beats a nested wrong one.
    """
    states = sorted(diagram.states.values(), key=lambda s: (s.line, s.name))
    nodes = {
        s.name: _entity_symbol(
            s, _SYM_NAMESPACE if s.composite else _SYM_CLASS, lines, "state"
        )
        for s in states
    }
    roots: list[dict] = []
    for s in states:
        parent = nodes.get(s.container) if s.container else None
        if parent is None or parent is nodes[s.name]:
            roots.append(nodes[s.name])
        else:
            parent["children"].append(nodes[s.name])
    # Positional sanity: a parent declared after its child means the inversion
    # disagrees with the source, so fall back to flat.
    for s in states:
        if s.container and s.container in diagram.states:
            if diagram.states[s.container].line > s.line:
                return [nodes[s.name] for s in states]
    return roots


def _diagram_children(diagram, lines: Sequence[str], floor: int) -> list[dict]:
    """The outline under one diagram, by type."""
    kind = diagram.diagram_type
    if kind == "unknown":
        return []  # nothing was modelled; the root alone is the honest answer

    if kind == "class":
        out: list[dict] = []
        for entity in sorted(diagram.classes.values(), key=lambda c: (c.line, c.name)):
            node = _entity_symbol(
                entity,
                _SYM_INTERFACE if entity.kind == "interface" else _SYM_CLASS,
                lines,
            )
            for member in entity.members:
                node["children"].append(
                    _symbol(
                        member.name or member.raw.strip(),
                        _SYM_METHOD if member.is_method else _SYM_FIELD,
                        _whole_line(member.line, lines),
                        _whole_line(member.line, lines),
                    )
                )
            out.append(node)
        return out

    if kind == "state":
        return _state_children(diagram, lines)

    roots, spans = _block_tree(diagram.blocks, floor, lines)

    if kind == "activity":
        # An `if` emits BOTH a Block and a `decision` ActivityNode with the
        # same label on the same line; showing both is two indistinguishable
        # rows with one jump target.
        block_starts = {b.start_line for b in diagram.blocks}
        for node in diagram.activity_nodes:
            if node.kind == "decision" and node.line in block_starts:
                continue
            label = node.label or node.kind
            _place(node.line, spans, roots).append(
                _symbol(
                    label,
                    _SYM_OBJECT,
                    _whole_line(node.line, lines),
                    _whole_line(node.line, lines),
                    node.kind,
                )
            )
        return roots

    # sequence / usecase
    for participant in sorted(diagram.participants.values(), key=lambda p: (p.line, p.name)):
        _place(participant.line, spans, roots).append(
            _entity_symbol(participant, _SYM_CLASS, lines)
        )
    for message in diagram.messages:
        arrow = f"{message.source or '['} → {message.target or ']'}"
        _place(message.line, spans, roots).append(
            _symbol(
                message.label.strip() or arrow,
                _SYM_METHOD,
                _whole_line(message.line, lines),
                _whole_line(message.line, lines),
                arrow if message.label.strip() else "",
            )
        )
    return roots


def _normalise(symbols: list[dict], bounds: dict | None, lines: Sequence[str]) -> list[dict]:
    """Enforce the invariants LSP requires, whatever the builders produced.

    One type-agnostic pass is the safeguard: five per-type builders each
    individually correct is a standard nobody sustains, and a malformed tree
    costs the *whole* document's outline in most clients. Guarantees, in
    order: siblings sorted and non-overlapping, every range inside its
    parent's, no degenerate spans, ``selectionRange`` contained in ``range``,
    and a non-empty name.
    """
    out: list[dict] = []
    for sym in sorted(symbols, key=lambda s: (s["range"]["start"]["line"], s["range"]["end"]["line"])):
        rng = sym["range"]
        if bounds is not None:  # clamp into the parent
            if rng["start"]["line"] < bounds["start"]["line"]:
                rng["start"] = dict(bounds["start"])
            if rng["end"]["line"] > bounds["end"]["line"]:
                rng["end"] = dict(bounds["end"])
        if rng["end"]["line"] < rng["start"]["line"]:
            continue  # degenerate after clamping

        if out:
            previous = out[-1]["range"]
            if rng["start"]["line"] <= previous["end"]["line"]:
                if rng["end"]["line"] <= previous["end"]["line"]:
                    # Fully inside the previous sibling — it belongs under it.
                    out[-1]["children"] = _normalise(
                        out[-1]["children"] + [sym], out[-1]["range"], lines
                    )
                    continue
                # Merely crossing: trim the start so siblings stay disjoint.
                rng["start"] = {"line": previous["end"]["line"] + 1, "character": 0}
                if rng["end"]["line"] < rng["start"]["line"]:
                    continue

        selection = sym["selectionRange"]
        if not (
            rng["start"]["line"] <= selection["start"]["line"]
            and selection["end"]["line"] <= rng["end"]["line"]
        ):
            # Widening beats dropping: the row still jumps to the right line.
            rng["start"] = min(rng["start"], selection["start"], key=lambda p: p["line"])
            rng["end"] = max(rng["end"], selection["end"], key=lambda p: p["line"])
        if not sym["name"]:
            sym["name"] = "(unnamed)"
        sym["children"] = _normalise(sym["children"], rng, lines)
        out.append(sym)
    return out


def _envelope(symbol: dict) -> None:
    """Widen every range to cover its descendants, depth first.

    Participants, classes, states and members carry a *line*, never a span, so
    a parent whose range is its declaration line has every child outside it —
    which breaks `examples/shop_classes_good.puml`, the file this project
    ships as the good example.
    """
    for child in symbol["children"]:
        _envelope(child)
    for child in symbol["children"]:
        rng, sub = symbol["range"], child["range"]
        if sub["start"]["line"] < rng["start"]["line"]:
            rng["start"] = dict(sub["start"])
        if sub["end"]["line"] > rng["end"]["line"]:
            rng["end"] = dict(sub["end"])


def _count(symbols: Sequence[dict]) -> int:
    return sum(1 + _count(s["children"]) for s in symbols)


def document_symbols_for(text: str, path: str) -> list[dict]:
    """An outline of *text* as LSP ``DocumentSymbol``\\u200bs.

    Parse-only — it takes no :class:`~pumllint.engine.Engine`, so it is
    strictly cheaper than :func:`diagnostics_for` and cannot be affected by
    rule configuration. Unlike the code-action path this does **not** refuse a
    buffer with exotic line separators: it is read-only navigation, so it sits
    on the diagnostics side of that line, and clamping every index is enough
    (a wrong squiggle or a wrong jump target costs a click; only a wrong
    *edit* costs a file).
    """
    diagrams = parse_source(text, file_path=path)
    if not diagrams:
        return []
    lines = _split_lines(text)
    last = max(1, len(lines))

    roots: list[dict] = []
    for index, diagram in enumerate(diagrams):
        following = diagrams[index + 1].start_line - 1 if index + 1 < len(diagrams) else last
        floor = min(diagram.end_line or last, following, last)
        floor = max(floor, diagram.start_line)

        declared = [p for p in diagram.participants.values() if p.declared]
        detail = diagram.diagram_type
        if diagram.diagram_type == "sequence" and diagram.participants and not declared:
            # Every lifeline was manufactured from an arrow — which is what a
            # component diagram looks like after the type-fallback. Say so
            # rather than suppress: the engine already reports findings on
            # this buffer as a sequence diagram.
            detail = "sequence (inferred)"

        title = next(
            (d.value for d in diagram.directives if d.kind == "title" and d.value), None
        )
        name = diagram.name or title or f"diagram {index + 1}"
        node = _symbol(
            name,
            _SYM_MODULE,
            _span(diagram.start_line, floor, lines),
            _whole_line(diagram.start_line, lines),
            detail,
        )
        node["children"] = _diagram_children(diagram, lines, floor)
        roots.append(node)

    for root in roots:
        _envelope(root)
    roots = _normalise(roots, None, lines)

    if _count(roots) > _SYMBOL_CAP:
        # A pathological buffer (an unterminated `class Foo {` turns every
        # later line into a member while you type). Keep the roots, say why.
        for root in roots:
            root["children"] = []
            root["detail"] = f"{root.get('detail', '')} — outline truncated".strip(" —")
    return roots


def _flatten(symbols: Sequence[dict], uri: str, container: str = "") -> list[dict]:
    """``SymbolInformation[]`` for clients without hierarchical support."""
    out: list[dict] = []
    for sym in symbols:
        entry = {
            "name": sym["name"],
            "kind": sym["kind"],
            "location": {"uri": uri, "range": sym["range"]},
        }
        if container:
            entry["containerName"] = container
        out.append(entry)
        out.extend(_flatten(sym["children"], uri, sym["name"]))
    return out


# ---------------------------------------------------------------------------
# JSON-RPC framing
# ---------------------------------------------------------------------------


def read_message(stream: BinaryIO) -> Optional[dict]:
    """The next LSP message from *stream*, or ``None`` at end of input.

    Headers are ASCII, terminated by a blank line; only ``Content-Length``
    matters. A truncated body at end of stream returns ``None`` rather than
    raising: an editor that dies mid-write should stop the server, not crash
    it.
    """
    length = 0
    while True:
        line = stream.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            break  # end of headers
        name, _, value = line.partition(b":")
        if name.strip().lower() == b"content-length":
            try:
                length = int(value.strip())
            except ValueError:
                return None
    if length <= 0:
        return None
    body = stream.read(length)
    if body is None or len(body) < length:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def write_message(stream: BinaryIO, payload: dict) -> None:
    """Frame and write *payload*, flushing so the editor sees it immediately."""
    body = json.dumps(payload).encode("utf-8")
    stream.write(b"Content-Length: %d\r\n\r\n" % len(body))
    stream.write(body)
    stream.flush()


# ---------------------------------------------------------------------------
# The server
# ---------------------------------------------------------------------------


class LspServer:
    """A minimal, synchronous LSP server publishing pumllint diagnostics.

    Deliberately narrow rather than small: full-document sync, diagnostics,
    the three mechanical fixes as code actions, rule documentation on hover,
    completion over what the buffer already contains, participant rename, and
    a document outline of what the parser understood.
    Every one of those is backed by something the engine already knows — the
    rule catalogue, the parsed model, the fixer. Nothing completes PlantUML
    syntax and nothing renames a symbol the model does not track, because
    that would be a second product rather than a delivery surface.
    """

    def __init__(
        self,
        out: BinaryIO,
        config_path: str | None = None,
        fail_on: Severity = Severity.MAJOR,
        profile: str | None = None,
        no_suppressions: bool = False,
    ):
        self._out = out
        self._config_path = config_path
        self._profile = profile
        self._no_suppressions = no_suppressions
        self._documents: dict[str, str] = {}
        self._versions: dict[str, int | None] = {}
        # Set from the client's initialize params; decides whether edits can
        # carry a document version for the client to reject if stale.
        self._document_changes = False
        self._hierarchical_symbols = False
        self._engine: Engine | None = None
        # Deliberately no analysis cache. Editors request code actions on
        # every selection change, so re-linting per request was the obvious
        # worry — but measured on a 403-line diagram (far larger than a
        # hand-authored one) parse+lint is ~4 ms and compute_fixes ~7 ms, and
        # a cache keyed on buffer text would buy that back at the price of a
        # staleness bug class. Re-measure before adding one.
        self._fail_on = fail_on
        self._root = "."
        self.shutdown_requested = False

    # -- engine ----------------------------------------------------------
    def _ensure_engine(self) -> Engine:
        """The engine for this workspace, built once and reused.

        Config discovery matches the CLI: an explicit ``--config`` wins,
        otherwise the workspace root is searched for ``pumllint.toml`` and its
        siblings. A malformed or unreadable config must not take the server
        down — it falls back to defaults and says so on stderr, because an
        editor with default checks is far more useful than one that died on
        startup.
        """
        if self._engine is None:
            config: dict[str, Any] = {}
            try:
                config = load_config(self._config_path, cwd=self._root)
            except (FileNotFoundError, ValueError, OSError) as exc:
                print(f"pumllint-lsp: using defaults, config unreadable: {exc}", file=sys.stderr)
            # Same overrides `pumllint lint`/`fix` apply, so the editor and
            # the CLI cannot be pointed at different rule sets.
            if self._no_suppressions:
                config = {**config, "suppressions": False}
            if self._profile:
                config = {**config, "profile": self._profile}
            self._engine = Engine(config)
        return self._engine

    # -- protocol --------------------------------------------------------
    def _notify(self, method: str, params: dict) -> None:
        write_message(self._out, {"jsonrpc": "2.0", "method": method, "params": params})

    def _respond(self, msg_id: Any, result: Any) -> None:
        if isinstance(result, _Error):
            write_message(
                self._out,
                {"jsonrpc": "2.0", "id": msg_id, "error": {"code": result.code, "message": result.message}},
            )
            return
        write_message(self._out, {"jsonrpc": "2.0", "id": msg_id, "result": result})

    def _publish(self, uri: str) -> None:
        """Re-lint *uri*'s buffer and publish its diagnostics.

        Always publishes, including an empty list — that is how a client is
        told the previous findings are resolved. A rule that raises is
        reported on stderr and treated as no diagnostics for that buffer,
        rather than being allowed to kill the session mid-edit.
        """
        text = self._documents.get(uri)
        if text is None:
            return
        try:
            diagnostics = diagnostics_for(
                text, uri_to_path(uri), self._ensure_engine(), self._fail_on
            )
        except Exception as exc:  # a rule bug must not end the editing session
            print(f"pumllint-lsp: lint failed for {uri}: {exc!r}", file=sys.stderr)
            diagnostics = []
        self._notify(
            "textDocument/publishDiagnostics", {"uri": uri, "diagnostics": diagnostics}
        )

    def _code_actions(self, params: dict) -> list[dict]:
        """Code actions for a ``textDocument/codeAction`` request.

        Returns ``[]`` rather than ``null`` on every failure path, including
        an unexpected exception: ``serve`` has no ``except``, so letting one
        escape here would end the editing session, and a client that gets no
        response at all blocks forever.
        """
        uri = (params.get("textDocument") or {}).get("uri")
        if not isinstance(uri, str):
            return []
        text = self._documents.get(uri)  # a request can race didClose
        if text is None:
            return []
        rng = params.get("range") or {}
        start = (rng.get("start") or {}).get("line")
        end = (rng.get("end") or {}).get("line")
        line_range = None
        if isinstance(start, int) and isinstance(end, int):
            # A selection ending at column 0 does not include that line.
            if end > start and (rng.get("end") or {}).get("character") == 0:
                end -= 1
            line_range = (start, end)
        context = params.get("context") or {}
        try:
            return code_actions_for(
                text,
                uri_to_path(uri),
                self._ensure_engine(),
                uri,
                offered=context.get("diagnostics") or (),
                only=context.get("only"),
                line_range=line_range,
                version=self._versions.get(uri),
                document_changes=self._document_changes,
                fail_on=self._fail_on,
            )
        except Exception as exc:  # a fixer bug must not end the session
            print(f"pumllint-lsp: code actions failed for {uri}: {exc!r}", file=sys.stderr)
            return []

    def _position(self, params: dict) -> tuple[str, str, int, int] | None:
        """``(uri, text, line, character)`` for a positional request."""
        uri = (params.get("textDocument") or {}).get("uri")
        if not isinstance(uri, str):
            return None
        text = self._documents.get(uri)
        if text is None:
            return None
        pos = params.get("position") or {}
        line, char = pos.get("line"), pos.get("character")
        if not isinstance(line, int) or not isinstance(char, int):
            return None
        return uri, text, line, char

    def _hover(self, params: dict) -> dict | None:
        where = self._position(params)
        if where is None:
            return None
        uri, text, line, char = where
        try:
            return hover_for(
                text, uri_to_path(uri), self._ensure_engine(), line, char, self._fail_on
            )
        except Exception as exc:
            print(f"pumllint-lsp: hover failed for {uri}: {exc!r}", file=sys.stderr)
            return None

    def _completion(self, params: dict) -> list[dict]:
        where = self._position(params)
        if where is None:
            return []
        uri, text, line, char = where
        try:
            return completions_for(text, uri_to_path(uri), line, char)
        except Exception as exc:
            print(f"pumllint-lsp: completion failed for {uri}: {exc!r}", file=sys.stderr)
            return []

    def _prepare_rename(self, params: dict) -> dict | None:
        """The range of the participant under the cursor, or ``None``.

        ``None`` makes the editor say the position cannot be renamed, which is
        the honest answer everywhere except on a participant — pumllint models
        no other renameable symbol.
        """
        where = self._position(params)
        if where is None:
            return None
        _, text, line, char = where
        try:
            found = participant_at(text, line, char)
        except Exception:
            return None
        return found[1] if found else None

    def _rename(self, params: dict) -> Any:
        """A workspace edit renaming a participant, or an error the editor shows.

        A refusal is returned as a JSON-RPC *error* rather than an empty edit:
        an editor that gets no edits reports "nothing to rename", which hides
        the reason, and the reasons here are the interesting part.
        """
        where = self._position(params)
        if where is None:
            return None
        uri, text, line, char = where
        new_name = params.get("newName")
        if not isinstance(new_name, str):
            return None
        found = participant_at(text, line, char)
        if found is None:
            return _error(-32803, "Only participants can be renamed")
        try:
            edits = rename_edits(text, uri_to_path(uri), found[0], new_name)
        except RenameUnsafe as exc:
            return _error(-32803, str(exc))
        except Exception as exc:
            print(f"pumllint-lsp: rename failed for {uri}: {exc!r}", file=sys.stderr)
            return _error(-32803, "Rename failed")
        if self._document_changes:
            return {
                "documentChanges": [
                    {
                        "textDocument": {"uri": uri, "version": self._versions.get(uri)},
                        "edits": edits,
                    }
                ]
            }
        return {"changes": {uri: edits}}

    def _document_symbols(self, params: dict) -> list[dict]:
        """The outline for a document, hierarchical or flat as the client asked.

        Fires on every change, so the happy path logs nothing.
        """
        uri = (params.get("textDocument") or {}).get("uri")
        if not isinstance(uri, str):
            return []
        text = self._documents.get(uri)
        if text is None:
            return []
        try:
            symbols = document_symbols_for(text, uri_to_path(uri))
        except Exception as exc:  # a parser bug must not end the session
            print(f"pumllint-lsp: symbols failed for {uri}: {exc!r}", file=sys.stderr)
            return []
        return symbols if self._hierarchical_symbols else _flatten(symbols, uri)

    def handle(self, message: dict) -> None:
        """Dispatch one decoded message. Unknown methods are ignored.

        Ignoring is required rather than merely polite: clients send
        capability and workspace notifications a diagnostics-only server has
        no opinion on, and replying with an error to those makes some clients
        disconnect.
        """
        method = message.get("method")
        params = message.get("params") or {}
        msg_id = message.get("id")

        if method == "initialize":
            root_uri = params.get("rootUri")
            if isinstance(root_uri, str):
                self._root = uri_to_path(root_uri)
            caps = params.get("capabilities") or {}
            self._document_changes = bool(
                ((caps.get("workspace") or {}).get("workspaceEdit") or {}).get(
                    "documentChanges"
                )
            )
            # Clients without hierarchical support must be sent the flat
            # SymbolInformation[] form, not a nested tree.
            self._hierarchical_symbols = bool(
                ((caps.get("textDocument") or {}).get("documentSymbol") or {}).get(
                    "hierarchicalDocumentSymbolSupport"
                )
            )
            self._respond(
                msg_id,
                {
                    "capabilities": {
                        "textDocumentSync": _SYNC_FULL,
                        "codeActionProvider": {
                            "codeActionKinds": [_KIND_QUICKFIX, _KIND_FIX_ALL]
                        },
                        "hoverProvider": True,
                        "completionProvider": {},
                        "renameProvider": {"prepareProvider": True},
                        "documentSymbolProvider": True,
                    },
                    "serverInfo": {"name": "pumllint", "version": _version()},
                },
            )
        elif method == "textDocument/didOpen":
            doc = params.get("textDocument") or {}
            uri = doc.get("uri")
            if isinstance(uri, str):
                self._documents[uri] = doc.get("text") or ""
                self._versions[uri] = doc.get("version")
                self._publish(uri)
        elif method == "textDocument/didChange":
            uri = (params.get("textDocument") or {}).get("uri")
            changes = params.get("contentChanges") or []
            if isinstance(uri, str) and changes:
                # Full sync: the last change carries the whole document.
                self._documents[uri] = changes[-1].get("text") or ""
                self._versions[uri] = (params.get("textDocument") or {}).get("version")
                self._publish(uri)
        elif method == "textDocument/didSave":
            uri = (params.get("textDocument") or {}).get("uri")
            if isinstance(uri, str):
                text = params.get("text")
                if isinstance(text, str):
                    self._documents[uri] = text
                self._publish(uri)
        elif method == "textDocument/didClose":
            uri = (params.get("textDocument") or {}).get("uri")
            if isinstance(uri, str):
                self._documents.pop(uri, None)
                self._versions.pop(uri, None)
                # Clear the client's squiggles for a file we no longer track.
                self._notify(
                    "textDocument/publishDiagnostics", {"uri": uri, "diagnostics": []}
                )
        elif method == "textDocument/codeAction":
            self._respond(msg_id, self._code_actions(params))
        elif method == "textDocument/hover":
            self._respond(msg_id, self._hover(params))
        elif method == "textDocument/completion":
            self._respond(msg_id, self._completion(params))
        elif method == "textDocument/prepareRename":
            self._respond(msg_id, self._prepare_rename(params))
        elif method == "textDocument/rename":
            self._respond(msg_id, self._rename(params))
        elif method == "textDocument/documentSymbol":
            self._respond(msg_id, self._document_symbols(params))
        elif method == "shutdown":
            self.shutdown_requested = True
            self._respond(msg_id, None)
        elif msg_id is not None:
            # An unknown *request* still needs a reply or the client blocks.
            self._respond(msg_id, None)


def _version() -> str:
    from . import __version__

    return __version__


def serve(
    stdin: BinaryIO | None = None,
    stdout: BinaryIO | None = None,
    config_path: str | None = None,
    fail_on: Severity = Severity.MAJOR,
    profile: str | None = None,
    no_suppressions: bool = False,
) -> int:
    """Run the server until ``exit``. Returns the process exit code.

    Per the LSP specification, ``exit`` after ``shutdown`` is a clean stop (0)
    and ``exit`` without one is an error (1) — which keeps even this
    long-running surface inside the repository's exit-code contract.

    ``sys.stdout`` is rebound to stderr for the duration: the protocol owns
    the real stdout, and ``cli._out`` writes to ``sys.stdout``. Rebinding
    turns a corrupted session into a harmless log line.
    """
    raw_in = stdin if stdin is not None else sys.stdin.buffer
    raw_out = stdout if stdout is not None else sys.stdout.buffer

    saved_stdout = sys.stdout
    sys.stdout = sys.stderr  # protocol owns the real stdout; see the docstring
    try:
        server = LspServer(
            raw_out,
            config_path=config_path,
            fail_on=fail_on,
            profile=profile,
            no_suppressions=no_suppressions,
        )
        while True:
            message = read_message(raw_in)
            if message is None:
                return 0 if server.shutdown_requested else 1
            if message.get("method") == "exit":
                return 0 if server.shutdown_requested else 1
            server.handle(message)
    finally:
        sys.stdout = saved_stdout

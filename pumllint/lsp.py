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

    Deliberately small: full-document sync, diagnostics and the three
    mechanical fixes as code actions. No completion, no hover, no rename. It
    is a delivery surface for the existing engine and fixer, not a second
    product with its own behaviour.
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
            self._respond(
                msg_id,
                {
                    "capabilities": {
                        "textDocumentSync": _SYNC_FULL,
                        "codeActionProvider": {
                            "codeActionKinds": [_KIND_QUICKFIX, _KIND_FIX_ALL]
                        },
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

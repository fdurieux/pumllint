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

Zero third-party dependencies, in keeping with the rest of the package.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, BinaryIO, Optional
from urllib.parse import unquote, urlparse

from .config import load_config
from .engine import Engine
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
    start = max(0, (violation.column or 1) - 1)
    start = min(start, len(text))
    return {
        "start": {"line": index, "character": start},
        "end": {"line": index, "character": max(len(text), start)},
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
    lines = text.splitlines() or [""]
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

    Deliberately small: full-document sync, diagnostics only, no completion,
    hover or code actions. It is a delivery surface for the existing engine,
    not a second product with its own behaviour.
    """

    def __init__(
        self,
        out: BinaryIO,
        config_path: str | None = None,
        fail_on: Severity = Severity.MAJOR,
    ):
        self._out = out
        self._config_path = config_path
        self._documents: dict[str, str] = {}
        self._engine: Engine | None = None
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
            self._respond(
                msg_id,
                {
                    "capabilities": {"textDocumentSync": _SYNC_FULL},
                    "serverInfo": {"name": "pumllint", "version": _version()},
                },
            )
        elif method == "textDocument/didOpen":
            doc = params.get("textDocument") or {}
            uri = doc.get("uri")
            if isinstance(uri, str):
                self._documents[uri] = doc.get("text") or ""
                self._publish(uri)
        elif method == "textDocument/didChange":
            uri = (params.get("textDocument") or {}).get("uri")
            changes = params.get("contentChanges") or []
            if isinstance(uri, str) and changes:
                # Full sync: the last change carries the whole document.
                self._documents[uri] = changes[-1].get("text") or ""
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
                # Clear the client's squiggles for a file we no longer track.
                self._notify(
                    "textDocument/publishDiagnostics", {"uri": uri, "diagnostics": []}
                )
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
        server = LspServer(raw_out, config_path=config_path, fail_on=fail_on)
        while True:
            message = read_message(raw_in)
            if message is None:
                return 0 if server.shutdown_requested else 1
            if message.get("method") == "exit":
                return 0 if server.shutdown_requested else 1
            server.handle(message)
    finally:
        sys.stdout = saved_stdout

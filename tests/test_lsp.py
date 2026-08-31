"""LSP front-end tests (the authoring-time surface).

Plain assert functions with no fixtures and no third-party imports, so the
zero-dependency runner exercises them too. The load-bearing test is
:func:`test_lsp_diagnostics_agree_with_the_engine`: the whole point of this
surface is that the editor and the gate cannot disagree, so it is checked
rather than assumed.
"""

import io
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from pumllint.engine import Engine
from pumllint.fixer import apply_fixes, compute_fixes
from pumllint.lsp import (
    LspServer,
    RenameUnsafe,
    diagnostics_for,
    lsp_severity,
    read_message,
    serve,
    text_edits_for,
    uri_to_path,
    write_message,
)
from pumllint.parser import parse_source
from pumllint.model import Severity

# No title (GEN001), no diagram name (GEN002), unlabelled message (SEQ005).
_DOC = "@startuml\nparticipant A\nparticipant B\nA -> B\n@enduml\n"


def _frame(obj: dict) -> bytes:
    body = json.dumps(obj).encode("utf-8")
    return b"Content-Length: %d\r\n\r\n" % len(body) + body


def _decode_all(raw: bytes) -> list[dict]:
    """Every framed message in *raw*, decoded."""
    out, i = [], 0
    while True:
        j = raw.find(b"\r\n\r\n", i)
        if j == -1:
            return out
        header = raw[i:j].decode("ascii")
        length = int(
            [l for l in header.split("\r\n") if l.lower().startswith("content-length")][0]
            .split(":")[1]
            .strip()
        )
        out.append(json.loads(raw[j + 4 : j + 4 + length].decode("utf-8")))
        i = j + 4 + length


def _drive(messages: list[dict]) -> tuple[int, list[dict]]:
    """Run the server over *messages*, returning (exit code, replies).

    An ``initialize`` carrying an empty temp directory as ``rootUri`` is
    prepended unless the caller sent one, so config discovery finds nothing
    and the defaults apply. Without it these tests would silently pick up the
    repository's own ``pumllint.toml`` and assert against its severities —
    the config contamination this project has been bitten by before.
    """
    with tempfile.TemporaryDirectory() as tmp:
        if not any(m.get("method") == "initialize" for m in messages):
            messages = [
                {
                    "jsonrpc": "2.0",
                    "id": 0,
                    "method": "initialize",
                    "params": {"rootUri": Path(tmp).as_uri()},
                }
            ] + messages
        else:
            messages = [
                {**m, "params": {**(m.get("params") or {}), "rootUri": Path(tmp).as_uri()}}
                if m.get("method") == "initialize"
                else m
                for m in messages
            ]
        out = io.BytesIO()
        code = serve(io.BytesIO(b"".join(_frame(m) for m in messages)), out)
    return code, _decode_all(out.getvalue())


# -- URIs -------------------------------------------------------------------


def test_lsp_uri_to_path_is_forward_slashed():
    assert uri_to_path("file:///home/user/a/b.puml") == "/home/user/a/b.puml"


def test_lsp_uri_to_path_strips_the_windows_drive_slash():
    # file:///C:/x/y.puml — the leading slash before the drive must go, and the
    # result stays forward-slashed on every platform (the reporting contract).
    assert uri_to_path("file:///C:/x/y.puml") == "C:/x/y.puml"


def test_lsp_uri_to_path_decodes_percent_escapes():
    assert uri_to_path("file:///tmp/my%20diagrams/a.puml") == "/tmp/my diagrams/a.puml"


def test_lsp_uri_to_path_passes_through_non_file_schemes():
    # untitled: buffers have no filesystem path; they must not become "".
    assert uri_to_path("untitled:Untitled-1") == "untitled:Untitled-1"


# -- severity mapping -------------------------------------------------------


def test_lsp_severity_maps_the_fail_threshold_to_error():
    # Default threshold is major, matching `pumllint lint --fail-on`.
    assert lsp_severity(Severity.BLOCKER) == 1
    assert lsp_severity(Severity.CRITICAL) == 1
    assert lsp_severity(Severity.MAJOR) == 1
    assert lsp_severity(Severity.MINOR) == 2
    assert lsp_severity(Severity.INFO) == 3


def test_lsp_severity_follows_a_raised_threshold():
    # Raising the gate must raise the squiggles with it, or the editor starts
    # underlining things CI accepts — the divergence this surface prevents.
    assert lsp_severity(Severity.MAJOR, fail_on=Severity.BLOCKER) == 2
    assert lsp_severity(Severity.BLOCKER, fail_on=Severity.BLOCKER) == 1


# -- diagnostics ------------------------------------------------------------


def test_lsp_diagnostics_agree_with_the_engine():
    """The editor reports exactly what the engine reports — same rule ids.

    This is the contract the whole module exists for. If it ever fails, the
    editor and the gate have diverged and the surface is worse than useless.
    """
    engine = Engine({})
    from pumllint.parser import parse_source

    expected = {v.rule_id for v in engine.lint_diagrams(parse_source(_DOC, "d.puml"))}
    got = {d["code"] for d in diagnostics_for(_DOC, "d.puml", engine)}
    assert got == expected, (got, expected)
    assert expected, "fixture should produce findings"


def test_lsp_diagnostics_carry_source_and_rule_id():
    diags = diagnostics_for(_DOC, "d.puml", Engine({}))
    assert all(d["source"] == "pumllint" for d in diags)
    assert all(d["code"] and d["code"][:3].isalpha() for d in diags)


def test_lsp_diagnostic_ranges_are_zero_based_and_span_the_line():
    diags = diagnostics_for(_DOC, "d.puml", Engine({}))
    gen001 = [d for d in diags if d["code"] == "GEN001"][0]
    # Violation.line is 1-based; LSP is 0-based.
    assert gen001["range"]["start"]["line"] == 0
    # A zero-width range renders as an invisible squiggle — span the line.
    assert gen001["range"]["end"]["character"] > gen001["range"]["start"]["character"]


def test_lsp_no_startuml_yields_no_diagnostics():
    # Matches the CLI, which reports such a file as not checked, not as clean.
    assert diagnostics_for("just prose\n", "notes.md", Engine({})) == []


def test_lsp_range_is_clamped_past_the_end_of_the_buffer():
    # A diagnostic can race an edit that shortened the file; clamp, don't crash.
    from pumllint.lsp import _range_for
    from pumllint.model import Dimension, Violation

    v = Violation("GEN001", "m", "d.puml", 999, Severity.MAJOR, Dimension.SEMANTIC)
    r = _range_for(v, ["only one line"])
    assert r["start"]["line"] == 0


# -- framing ----------------------------------------------------------------


def test_lsp_framing_round_trips():
    buf = io.BytesIO()
    write_message(buf, {"jsonrpc": "2.0", "id": 1, "result": None})
    buf.seek(0)
    assert read_message(buf) == {"jsonrpc": "2.0", "id": 1, "result": None}


def test_lsp_read_message_returns_none_at_end_of_stream():
    assert read_message(io.BytesIO(b"")) is None


def test_lsp_read_message_survives_a_truncated_body():
    # An editor that dies mid-write should stop the server, not crash it.
    assert read_message(io.BytesIO(b"Content-Length: 999\r\n\r\n{}")) is None


# -- lifecycle --------------------------------------------------------------


def test_lsp_initialize_advertises_full_sync():
    _, replies = _drive(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "shutdown"},
            {"jsonrpc": "2.0", "method": "exit"},
        ]
    )
    init = [r for r in replies if r.get("id") == 1][0]
    assert init["result"]["capabilities"]["textDocumentSync"] == 1
    assert init["result"]["serverInfo"]["name"] == "pumllint"


def test_lsp_did_open_publishes_diagnostics():
    _, replies = _drive(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {"textDocument": {"uri": "file:///d.puml", "text": _DOC}},
            },
            {"jsonrpc": "2.0", "id": 2, "method": "shutdown"},
            {"jsonrpc": "2.0", "method": "exit"},
        ]
    )
    published = [r for r in replies if r.get("method") == "textDocument/publishDiagnostics"]
    assert len(published) == 1
    assert published[0]["params"]["uri"] == "file:///d.puml"
    assert published[0]["params"]["diagnostics"], "expected findings for the fixture"


def test_lsp_did_change_republishes_from_the_unsaved_buffer():
    """Editing to a clean diagram clears the findings without touching disk."""
    clean = "@startuml d\ntitle T\nparticipant A\nparticipant B\nA -> B : go\n@enduml\n"
    _, replies = _drive(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {"textDocument": {"uri": "file:///d.puml", "text": _DOC}},
            },
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didChange",
                "params": {
                    "textDocument": {"uri": "file:///d.puml"},
                    "contentChanges": [{"text": clean}],
                },
            },
            {"jsonrpc": "2.0", "id": 2, "method": "shutdown"},
            {"jsonrpc": "2.0", "method": "exit"},
        ]
    )
    published = [r for r in replies if r.get("method") == "textDocument/publishDiagnostics"]
    assert len(published) == 2
    assert published[0]["params"]["diagnostics"]
    assert published[1]["params"]["diagnostics"] == []


def test_lsp_did_close_clears_the_clients_squiggles():
    _, replies = _drive(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {"textDocument": {"uri": "file:///d.puml", "text": _DOC}},
            },
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didClose",
                "params": {"textDocument": {"uri": "file:///d.puml"}},
            },
            {"jsonrpc": "2.0", "id": 2, "method": "shutdown"},
            {"jsonrpc": "2.0", "method": "exit"},
        ]
    )
    published = [r for r in replies if r.get("method") == "textDocument/publishDiagnostics"]
    assert published[-1]["params"]["diagnostics"] == []


def test_lsp_unknown_request_still_gets_a_reply():
    # An unanswered request blocks the client forever.
    _, replies = _drive(
        [
            {"jsonrpc": "2.0", "id": 7, "method": "textDocument/hover", "params": {}},
            {"jsonrpc": "2.0", "id": 8, "method": "shutdown"},
            {"jsonrpc": "2.0", "method": "exit"},
        ]
    )
    assert any(r.get("id") == 7 for r in replies)


def test_lsp_unknown_notification_is_ignored_silently():
    # Notifications have no id and must not draw a reply.
    _, replies = _drive(
        [
            {"jsonrpc": "2.0", "method": "$/setTrace", "params": {"value": "off"}},
            {"jsonrpc": "2.0", "id": 1, "method": "shutdown"},
            {"jsonrpc": "2.0", "method": "exit"},
        ]
    )
    assert [r for r in replies if r.get("id") == 1]
    assert not any(r.get("method") == "$/setTrace" for r in replies)
    # initialize (injected by _drive) + shutdown; the notification drew nothing.
    assert len(replies) == 2


# -- exit codes (the contract) ---------------------------------------------


def test_lsp_shutdown_then_exit_is_zero():
    code, _ = _drive(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "shutdown"},
            {"jsonrpc": "2.0", "method": "exit"},
        ]
    )
    assert code == 0


def test_lsp_exit_without_shutdown_is_one():
    # The LSP specification's rule, and it keeps this long-running surface
    # inside the repository's 0/1/2 exit-code contract.
    code, _ = _drive([{"jsonrpc": "2.0", "method": "exit"}])
    assert code == 1


def test_lsp_broken_pipe_without_shutdown_is_one():
    code, _ = _drive([])
    assert code == 1


# -- the stdout hazard ------------------------------------------------------


def test_lsp_serve_rebinds_stdout_so_stray_prints_cannot_corrupt_the_stream():
    """``cli._out`` prints to ``sys.stdout``; the protocol owns the real one.

    Without the rebind a single stray print produces an unparseable stream and
    the session dies naming nothing. Assert the rebind is in force *during*
    serve and restored afterwards.
    """
    seen = {}

    class Probe(io.BytesIO):
        def write(self, b):  # first protocol write happens inside serve()
            seen.setdefault("stdout_during", sys.stdout)
            return super().write(b)

    before = sys.stdout
    serve(
        io.BytesIO(
            _frame({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
            + _frame({"jsonrpc": "2.0", "id": 2, "method": "shutdown"})
            + _frame({"jsonrpc": "2.0", "method": "exit"})
        ),
        Probe(),
    )
    assert seen["stdout_during"] is sys.stderr, "stdout must be rebound during serve"
    assert sys.stdout is before, "stdout must be restored after serve"


def test_lsp_a_failing_rule_does_not_end_the_session():
    """A rule that raises degrades to no diagnostics, not a dead editor."""

    class Exploding(Engine):
        def lint_diagrams(self, diagrams):
            raise RuntimeError("boom")

    out = io.BytesIO()
    server = LspServer(out)
    server._engine = Exploding({})
    server.handle(
        {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {"textDocument": {"uri": "file:///d.puml", "text": _DOC}},
        }
    )
    published = _decode_all(out.getvalue())
    assert published[0]["params"]["diagnostics"] == []


# -- end to end -------------------------------------------------------------


def test_lsp_subcommand_rejects_a_bad_fail_on_with_exit_2():
    """Usage errors keep the 0/1/2 contract even on the streaming subcommand."""
    repo = str(Path(__file__).resolve().parent.parent)
    proc = subprocess.run(
        [sys.executable, "-m", "pumllint", "lsp", "--fail-on", "nonsense"],
        input=b"",
        capture_output=True,
        env={**os.environ, "PYTHONPATH": repo},
        timeout=120,
    )
    assert proc.returncode == 2, proc.stderr.decode()


def test_lsp_subcommand_carries_the_version_flag():
    repo = str(Path(__file__).resolve().parent.parent)
    proc = subprocess.run(
        [sys.executable, "-m", "pumllint", "lsp", "--version"],
        input=b"",
        capture_output=True,
        env={**os.environ, "PYTHONPATH": repo},
        timeout=120,
    )
    assert proc.returncode == 0
    assert b"pumllint" in proc.stdout


def test_lsp_subcommand_runs_as_a_real_process():
    """`python -m pumllint lsp` speaks the protocol on real stdio."""
    payload = b"".join(
        _frame(m)
        for m in (
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {"textDocument": {"uri": "file:///d.puml", "text": _DOC}},
            },
            {"jsonrpc": "2.0", "id": 2, "method": "shutdown"},
            {"jsonrpc": "2.0", "method": "exit"},
        )
    )
    repo = str(Path(__file__).resolve().parent.parent)
    env = {**os.environ, "PYTHONPATH": repo}
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            [sys.executable, "-m", "pumllint", "lsp"],
            input=payload,
            capture_output=True,
            cwd=tmp,  # outside the repo: default config, GEN006/GEN007 dormant
            env=env,
            timeout=120,
        )
    assert proc.returncode == 0, proc.stderr.decode()
    replies = _decode_all(proc.stdout)
    published = [r for r in replies if r.get("method") == "textDocument/publishDiagnostics"]
    assert published and published[0]["params"]["diagnostics"]


# -- code actions: the differential property --------------------------------
#
# The executable analogue of test_lsp_diagnostics_agree_with_the_engine. An
# example test would pass while the edits were subtly wrong; only applying
# them through a client that indexes the way a real editor does can show that
# the lightbulb and `pumllint fix` write the same bytes.


def _u16_to_index(line: str, units: int) -> int:
    """Python index in *line* for a UTF-16 code-unit offset."""
    i = seen = 0
    while i < len(line) and seen < units:
        seen += 2 if ord(line[i]) > 0xFFFF else 1
        i += 1
    return i


def _apply_text_edits(text: str, edits: list[dict]) -> str:
    """Apply LSP TextEdits the way an editor would.

    Splits lines on exactly \r\n / \r / \n and treats ``character`` as
    UTF-16 code units — the two things the server has to get right.
    """
    starts = [0] + [m.end() for m in re.finditer(r"\r\n|\r|\n", text)]
    lines = re.split(r"\r\n|\r|\n", text)

    def offset(pos: dict) -> int:
        line = min(pos["line"], len(lines) - 1)
        return starts[line] + _u16_to_index(lines[line], pos["character"])

    # Descending, so each splice leaves earlier offsets valid.
    for e in sorted(edits, key=lambda e: offset(e["range"]["start"]), reverse=True):
        a, b = offset(e["range"]["start"]), offset(e["range"]["end"])
        text = text[:a] + e["newText"] + text[b:]
    return text


def _differential(src: str, stem: str = "credit_check") -> None:
    """Assert the LSP edits and `pumllint fix` produce identical bytes."""
    diagrams = parse_source(src, f"{stem}.puml")
    violations = Engine({}).lint_diagrams(diagrams)
    fixes = compute_fixes(src, diagrams, violations, stem=stem)
    assert fixes, f"fixture produced no fixes: {src!r}"
    assert _apply_text_edits(src, text_edits_for(fixes, src)) == apply_fixes(src, fixes)


def test_lsp_edits_match_pumllint_fix_on_a_plain_buffer():
    _differential("@startuml\nparticipant A\nA -> B : go\n@enduml\n")


def test_lsp_edits_match_pumllint_fix_with_crlf():
    _differential("@startuml\r\nparticipant A\r\nA -> B : go\r\n@enduml\r\n")


def test_lsp_edits_match_pumllint_fix_without_a_trailing_newline():
    _differential("@startuml\nparticipant A\nA -> B : go\n@enduml")


def test_lsp_edits_match_pumllint_fix_with_replace_and_insert_on_one_line():
    # GEN002 replaces the @startuml line; GEN001 inserts a title after it.
    # Both anchor on the same line, which is where a naive builder overlaps.
    src = "@startuml\nparticipant A\nA -> A : x\n@enduml\n"
    diagrams = parse_source(src, "credit_check.puml")
    fixes = compute_fixes(src, diagrams, Engine({}).lint_diagrams(diagrams), stem="credit_check")
    kinds = {(f.rule_id, f.kind, f.line) for f in fixes}
    assert ("GEN002", "replace", 1) in kinds and ("GEN001", "insert_after", 1) in kinds
    _differential(src)


def test_lsp_edits_match_pumllint_fix_with_two_participants_on_one_line():
    # Two inserts sharing one anchor line — the case where emitting separate
    # same-position edits would leave the order to the client.
    _differential("@startuml d\ntitle T\nparticipant A\nB -> C : hop\n@enduml\n")


def test_lsp_edits_match_pumllint_fix_with_astral_characters():
    """The astral character must sit on an *edited* line, or this is vacuous.

    An emoji elsewhere in the buffer never crosses an edit offset, so the
    test would pass with the code-point bug still in place — verified by
    reintroducing it. Here the SEQ001 anchor *is* the participant line
    carrying the emoji, whose end offset is 22 code points but 23 UTF-16
    units, so a len()-based server splices one unit short.
    """
    _differential(
        '@startuml d\ntitle T\nparticipant "🚀 A" as A\nA -> B : go\n@enduml\n', stem="d"
    )


def test_lsp_edits_are_utf16_indexed_not_codepoint_indexed():
    """The end offset of a replaced line counts UTF-16 units."""
    src = "@startuml\ntitle 🚀 T\nparticipant A\nA -> A : x\n@enduml\n"
    diagrams = parse_source(src, "d.puml")
    fixes = compute_fixes(src, diagrams, Engine({}).lint_diagrams(diagrams), stem="d")
    replaces = [f for f in fixes if f.kind == "replace"]
    assert replaces, "expected a GEN002 replace"
    edit = [e for e in text_edits_for(fixes, src) if e["range"]["end"]["character"] > 0][0]
    line = re.split(r"\r\n|\r|\n", src)[edit["range"]["start"]["line"]]
    assert edit["range"]["end"]["character"] == len(line.encode("utf-16-le")) // 2


def test_lsp_edits_for_no_fixes_is_empty():
    assert text_edits_for([], "@startuml d\n@enduml\n") == []


# -- code actions: protocol behaviour ---------------------------------------


def _actions(doc: str = _DOC, uri: str = "file:///credit_check.puml", **ctx) -> list[dict]:
    """Code actions for *doc*, driven through the real server."""
    rng = ctx.pop("range", {"start": {"line": 0, "character": 0},
                            "end": {"line": 20, "character": 0}})
    _, replies = _drive(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {"textDocument": {"uri": uri, "version": 1, "text": doc}},
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "textDocument/codeAction",
                "params": {
                    "textDocument": {"uri": uri},
                    "range": rng,
                    "context": {"diagnostics": [], **ctx},
                },
            },
            {"jsonrpc": "2.0", "id": 3, "method": "shutdown"},
            {"jsonrpc": "2.0", "method": "exit"},
        ]
    )
    return [r for r in replies if r.get("id") == 2][0]["result"]


def test_lsp_initialize_advertises_code_actions():
    _, replies = _drive(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "shutdown"},
            {"jsonrpc": "2.0", "method": "exit"},
        ]
    )
    caps = [r for r in replies if r.get("id") == 1][0]["result"]["capabilities"]
    kinds = caps["codeActionProvider"]["codeActionKinds"]
    assert "quickfix" in kinds and "source.fixAll.pumllint" in kinds


def test_lsp_offers_a_quickfix_per_finding_and_one_fix_all():
    actions = _actions()
    quick = [a for a in actions if a["kind"] == "quickfix"]
    fix_all = [a for a in actions if a["kind"] == "source.fixAll.pumllint"]
    assert len(fix_all) == 1
    assert quick, "expected quick fixes for the fixture"
    # Titles name what the edit does, taken from the fixer's own descriptions.
    assert any("title" in a["title"].lower() for a in quick)


def test_lsp_declares_all_participants_on_a_line_in_one_action():
    """Two undeclared participants on one line is ONE offer, not two.

    `compute_fixes` collapses its input to the set of lines carrying
    undeclared participants, so asking about one participant returns the
    fixes for every participant on that line. Two entries would carry
    identical edits and contradictory titles.
    """
    doc = "@startuml d\ntitle T\nparticipant A\nB -> C : hop\n@enduml\n"
    quick = [a for a in _actions(doc) if a["kind"] == "quickfix"]
    declares = [a for a in quick if "articipant" in a["title"]]
    assert len(declares) == 1, [a["title"] for a in declares]
    assert "B" in declares[0]["title"] and "C" in declares[0]["title"]
    # and it claims both diagnostics it resolves
    assert len(declares[0]["diagnostics"]) == 2


def test_lsp_fix_all_matches_a_generic_source_fixall_request():
    """CodeActionKinds are hierarchical — `source.fixAll` must match ours.

    String equality here would return nothing to the commonest fix-on-save
    configuration there is.
    """
    actions = _actions(only=["source.fixAll"])
    assert [a["kind"] for a in actions] == ["source.fixAll.pumllint"]


def test_lsp_only_filter_can_select_quickfixes_alone():
    actions = _actions(only=["quickfix"])
    assert actions and all(a["kind"] == "quickfix" for a in actions)


def test_lsp_offers_nothing_when_there_is_nothing_to_fix():
    """A clean buffer must not offer an empty fix-all.

    Otherwise `codeActionsOnSave` applies an empty WorkspaceEdit every save.
    """
    clean = "@startuml d\ntitle T\nparticipant A\nparticipant B\nA -> B : go\n@enduml\n"
    assert _actions(clean) == []


def test_lsp_code_action_response_is_a_list_not_null():
    assert isinstance(_actions("no diagram here\n"), list)


def test_lsp_quickfix_is_preferred_only_when_it_is_the_only_one():
    # Several quick fixes: none may claim to be *the* auto-fix.
    many = [a for a in _actions() if a["kind"] == "quickfix"]
    assert len(many) > 1
    assert not any(a.get("isPreferred") for a in many)


def test_lsp_code_actions_respect_the_selected_range():
    # A selection ending at character 0 does not include that line, so a
    # selection of line 0 only must not offer the participant fix anchored
    # further down.
    doc = "@startuml d\ntitle T\nparticipant A\nB -> C : hop\n@enduml\n"
    narrow = _actions(doc, range={"start": {"line": 0, "character": 0},
                                  "end": {"line": 1, "character": 0}})
    assert not [a for a in narrow if a["kind"] == "quickfix"]


def test_lsp_code_actions_suppressed_on_exotic_line_separators():
    """A form feed makes Python and the editor disagree about line numbers.

    A misplaced squiggle is survivable; a misplaced `replace` overwrites a
    line the user never touched, so offer nothing at all.
    """
    doc = "@startuml\nparticipant A\nnote over A\n  see\x0cspec\nend note\nA -> B : go\n@enduml\n"
    assert _actions(doc) == []


def test_lsp_code_actions_for_untitled_buffers_skip_name_derived_fixes():
    """An untitled buffer has no file stem, so GEN002's name is meaningless."""
    actions = _actions(uri="untitled:Untitled-1")
    assert not any("Untitled" in a["title"] for a in actions)


def test_lsp_code_action_falls_back_to_changes_without_documentChanges():
    # _drive's initialize advertises no capabilities, so the server must not
    # emit documentChanges (which carries a version the client can reject).
    actions = _actions()
    assert all("changes" in a["edit"] for a in actions)


def test_lsp_a_failing_fixer_does_not_end_the_session():
    out = io.BytesIO()
    server = LspServer(out)
    server._documents["file:///d.puml"] = _DOC

    def boom(*a, **k):
        raise RuntimeError("boom")

    import pumllint.lsp as lsp_mod

    original = lsp_mod.code_actions_for
    lsp_mod.code_actions_for = boom
    try:
        server.handle(
            {
                "jsonrpc": "2.0",
                "id": 9,
                "method": "textDocument/codeAction",
                "params": {"textDocument": {"uri": "file:///d.puml"}, "context": {}},
            }
        )
    finally:
        lsp_mod.code_actions_for = original
    assert _decode_all(out.getvalue())[0]["result"] == []


def test_lsp_code_action_after_close_responds_empty():
    out = io.BytesIO()
    server = LspServer(out)
    server.handle(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "textDocument/codeAction",
            "params": {"textDocument": {"uri": "file:///gone.puml"}, "context": {}},
        }
    )
    assert _decode_all(out.getvalue())[0]["result"] == []


def test_lsp_derived_name_never_empty():
    """A stem reducing to nothing produced a fix that fixed nothing.

    `@startuml ` still trips GEN002, so the finding survived its own fix and
    the editor re-offered the same no-op forever.
    """
    from pumllint.fixer import _derived_name

    assert _derived_name("_", 1) == "diagram"
    assert _derived_name("___", 2) == "diagram-2"
    assert _derived_name("credit_check", 1) == "credit-check"


def test_lsp_honours_profile_and_no_suppressions_like_the_fix_command():
    """The editor and `pumllint fix` must see the same rule set.

    `pumllint fix --profile codegen` fixes SEQ101 findings; without these
    flags the editor could never offer them, which is the divergence this
    surface exists to prevent.
    """
    base = LspServer(io.BytesIO())
    base._root = tempfile.gettempdir()
    with_codegen = LspServer(io.BytesIO(), profile="codegen")
    with_codegen._root = tempfile.gettempdir()
    assert len(with_codegen._ensure_engine().rules) > len(base._ensure_engine().rules)
    assert with_codegen._ensure_engine().profile == "codegen"

    quiet = LspServer(io.BytesIO(), no_suppressions=True)
    quiet._root = tempfile.gettempdir()
    assert quiet._ensure_engine().config.get("suppressions") is False


# -- hover ------------------------------------------------------------------


def _hover(doc: str, line: int, character: int) -> dict | None:
    from pumllint.lsp import hover_for

    return hover_for(doc, "d.puml", Engine({}), line, character)


def test_lsp_hover_documents_the_rule_behind_a_finding():
    value = _hover(_DOC, 0, 3)["contents"]["value"]
    # Every field is declared metadata, so hover cannot drift from the rule.
    assert "GEN001" in value and "missing-title" in value
    assert "severity `minor`" in value and "DIM-TRC" in value
    assert "pumllint: disable=missing-title" in value


def test_lsp_hover_documents_a_suppression_key():
    """Hovering a rule key in a disable comment explains what was switched off."""
    doc = "@startuml d\n' pumllint: disable=missing-title\ntitle T\nA -> A : x\n@enduml\n"
    value = _hover(doc, 1, 25)["contents"]["value"]
    assert "GEN001" in value and "Diagram has no title" in value


def test_lsp_hover_on_the_suppression_keyword_itself_says_nothing():
    doc = "@startuml d\n' pumllint: disable=missing-title\ntitle T\nA -> A : x\n@enduml\n"
    assert _hover(doc, 1, 4) is None  # the word "pumllint"


def test_lsp_hover_is_none_where_there_is_no_finding():
    clean = "@startuml d\ntitle T\nparticipant A\nparticipant B\nA -> B : go\n@enduml\n"
    assert _hover(clean, 2, 0) is None
    assert _hover(clean, 99, 0) is None


def test_lsp_hover_lists_every_rule_on_a_line():
    # The @startuml line trips both GEN001 and GEN002 in the fixture.
    value = _hover(_DOC, 0, 0)["contents"]["value"]
    assert "GEN001" in value and "GEN002" in value


# -- completion -------------------------------------------------------------


def _complete(doc: str, line: int, character: int) -> list[dict]:
    from pumllint.lsp import completions_for

    return completions_for(doc, "d.puml", line, character)


def test_lsp_completion_offers_the_buffers_own_participants():
    # _DOC declares both, so nothing here is implicit.
    assert [i["label"] for i in _complete(_DOC, 3, 0)] == ["A", "B"]


def test_lsp_completion_marks_implicit_lifelines():
    """An implicit participant is worth flagging — declaring it is the fix."""
    doc = "@startuml d\ntitle T\nparticipant A\nA -> B : go\n@enduml\n"
    items = {i["label"]: i["detail"] for i in _complete(doc, 3, 0)}
    assert "implicit" in items["B"] and "implicit" not in items["A"]


def test_lsp_completion_offers_rule_keys_inside_a_disable_comment():
    labels = {i["label"] for i in _complete("' pumllint: disable=", 0, 20)}
    # Both spellings are accepted by the suppression parser, so both are offered.
    assert "missing-title" in labels and "GEN001" in labels


def test_lsp_completion_offers_no_plantuml_syntax():
    """Deliberate: pumllint's parser is partial, so a keyword list would be invented.

    Completion returns only names this buffer already contains.
    """
    labels = {i["label"] for i in _complete(_DOC, 3, 0)}
    assert not labels & {"participant", "@startuml", "actor", "note", "title"}


# -- rename -----------------------------------------------------------------


def _rename(doc: str, old: str, new: str) -> list[dict]:
    from pumllint.lsp import rename_edits

    return rename_edits(doc, "d.puml", old, new)


def test_lsp_rename_updates_declaration_and_message_endpoints():
    doc = "@startuml d\ntitle T\nparticipant A\nA -> B : go\nactivate A\n@enduml\n"
    edits = _rename(doc, "A", "Auth")
    assert len(edits) == 3  # declaration, message source, activate
    assert all(e["newText"] == "Auth" for e in edits)


def test_lsp_rename_leaves_prose_in_labels_alone():
    """`A` in `A -> B : notify A owner` is a word in a sentence, not a reference.

    The parser's message pattern captures src/dst separately from label, so
    the identifier can be located without touching the prose beside it.
    """
    doc = "@startuml d\ntitle T\nparticipant A\nA -> B : notify A owner\n@enduml\n"
    edits = _rename(doc, "A", "Auth")
    from pumllint.lsp import _apply_locally

    assert "notify A owner" in _apply_locally(doc, edits)


def test_lsp_rename_refuses_rather_than_half_renaming_a_note_target():
    """pumllint parses note bodies as prose and records no note targets.

    A rename that silently left `note over A` behind would leave PlantUML
    rendering a brand-new lifeline, so this refuses with the reason.
    """
    doc = "@startuml d\ntitle T\nparticipant A\nnote over A\n  hi\nend note\nA -> B : go\n@enduml\n"
    try:
        _rename(doc, "A", "Auth")
        raise AssertionError("expected a refusal")
    except RenameUnsafe as exc:
        assert "note" in str(exc)


def test_lsp_rename_allows_a_note_body_that_merely_mentions_the_name():
    doc = "@startuml d\ntitle T\nparticipant A\nnote over B\n  about A\nend note\nA -> B : go\n@enduml\n"
    assert _rename(doc, "A", "Auth")


def test_lsp_rename_refuses_a_collision():
    doc = "@startuml d\ntitle T\nparticipant A\nparticipant B\nA -> B : go\n@enduml\n"
    try:
        _rename(doc, "A", "B")
        raise AssertionError("expected a refusal")
    except RenameUnsafe as exc:
        assert "merge" in str(exc)


def test_lsp_rename_refuses_an_unknown_participant_or_empty_name():
    doc = "@startuml d\ntitle T\nparticipant A\nA -> B : go\n@enduml\n"
    for old, new in (("Nope", "X"), ("A", "  ")):
        try:
            _rename(doc, old, new)
            raise AssertionError(f"expected a refusal for {old!r} -> {new!r}")
        except RenameUnsafe:
            pass


def test_lsp_rename_verifies_itself_by_reparsing():
    """The result must parse back to exactly the expected participant set."""
    doc = "@startuml d\ntitle T\nparticipant A\nparticipant B\nA -> B : go\n@enduml\n"
    from pumllint.lsp import _apply_locally

    renamed = _apply_locally(doc, _rename(doc, "A", "Auth"))
    names = {p for d in parse_source(renamed, "d.puml") for p in d.participants}
    assert names == {"Auth", "B"}


def test_lsp_rename_quotes_a_name_that_needs_it():
    doc = "@startuml d\ntitle T\nparticipant A\nA -> B : go\n@enduml\n"
    assert all(e["newText"] == '"Auth Service"' for e in _rename(doc, "A", "Auth Service"))


def test_lsp_prepare_rename_only_offers_participants():
    from pumllint.lsp import participant_at

    doc = "@startuml d\ntitle T\nparticipant A\nA -> B : go\n@enduml\n"
    assert participant_at(doc, 2, 12)[0] == "A"      # on the declaration
    assert participant_at(doc, 1, 3) is None          # on `title`
    assert participant_at(doc, 0, 2) is None          # on `@startuml`


def test_lsp_rename_over_the_protocol_returns_an_error_with_the_reason():
    """A refusal must be a JSON-RPC error, not an empty edit.

    An editor given no edits says "nothing to rename", which hides exactly
    the information that makes the refusal useful.
    """
    doc = "@startuml d\ntitle T\nparticipant A\nnote over A\n  hi\nend note\nA -> B : go\n@enduml\n"
    _, replies = _drive(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {"textDocument": {"uri": "file:///d.puml", "text": doc}},
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "textDocument/rename",
                "params": {
                    "textDocument": {"uri": "file:///d.puml"},
                    "position": {"line": 2, "character": 12},
                    "newName": "Auth",
                },
            },
            {"jsonrpc": "2.0", "id": 3, "method": "shutdown"},
            {"jsonrpc": "2.0", "method": "exit"},
        ]
    )
    reply = [r for r in replies if r.get("id") == 2][0]
    assert "error" in reply and "note" in reply["error"]["message"]


def test_lsp_initialize_advertises_hover_completion_and_rename():
    _, replies = _drive(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "shutdown"},
            {"jsonrpc": "2.0", "method": "exit"},
        ]
    )
    caps = [r for r in replies if r.get("id") == 1][0]["result"]["capabilities"]
    assert caps["hoverProvider"] is True
    assert "completionProvider" in caps
    assert caps["renameProvider"]["prepareProvider"] is True


# -- document symbols: the invariant property -------------------------------
#
# LSP requires selectionRange ⊆ range, and clients drop the WHOLE document's
# outline on a malformed tree. The first draft of this feature produced 36
# violations across the repo's own corpus — including on
# examples/shop_classes_good.puml — so the invariants are asserted over every
# .puml in the tree rather than on a hand-picked fixture.

_ADVERSARIAL = {
    # Blocks whose spans cross: the parser closes out of the middle of its
    # stack, so neither contains the other.
    "crossing if/while": "@startuml\nif (c?) then (yes)\nwhile (more)\nendif\nendwhile\nstop\n@enduml\n",
    "crossing box/alt": '@startuml\nAlice -> Bob : x\nbox "Team"\nalt ok\nend box\nend\n@enduml\n',
    # An unterminated diagram must not swallow the one after it.
    "unterminated diagram": "@startuml First\nAlice -> Bob : one\n@startuml Second\nCarol -> Dan : two\n@enduml\n",
    "unterminated block": "@startuml d\ntitle T\nparticipant A\nalt happy\nA -> A : again\n@enduml\n",
    # container is set at first creation, so re-opening a composite can make
    # two states siblings whose envelopes overlap.
    "reopened composite": "@startuml\nstate Sub\nstate Top {\n  state Sub {\n    X --> Y\n  }\n}\n@enduml\n",
    # Names the model leaves empty.
    "empty member name": "@startuml\nclass Foo {\n  +\n}\n@enduml\n",
    "bare repeat": "@startuml\nstart\nrepeat\n  :work;\nrepeat while (more?)\nstop\n@enduml\n",
    "bare alt": "@startuml d\ntitle T\nparticipant A\nalt\nA -> A : x\nend\n@enduml\n",
    # Two implicit participants sharing one line.
    "two on one line": "@startuml\nAlice -> Bob : hi\n@enduml\n",
    "astral name": "@startuml 🚀-rocket\nparticipant A\nA -> B : go\n@enduml\n",
    "crlf": "@startuml d\r\ntitle T\r\nparticipant A\r\nA -> B : go\r\n@enduml\r\n",
    "empty": "",
    "no startuml": "just prose\nand more\n",
    "exotic separator": "@startuml\nparticipant A\nnote over A\n  see\x0cspec\nend note\nA -> B : go\n@enduml\n",
}


def _walk(symbols, depth=0):
    for sym in symbols:
        yield depth, sym
        yield from _walk(sym["children"], depth + 1)


def _assert_tree_is_valid(symbols, lines, where):
    """Every invariant LSP requires of a DocumentSymbol tree."""
    seen = set()

    def check(nodes, parent, path):
        previous = None
        for sym in nodes:
            rng, sel = sym["range"], sym["selectionRange"]
            assert id(sym) not in seen, f"{where}: cycle at {path}/{sym['name']}"
            seen.add(id(sym))
            assert sym["name"], f"{where}: empty name at {path}"
            assert rng["start"]["line"] <= rng["end"]["line"], f"{where}: inverted range {sym['name']}"
            assert 0 <= rng["start"]["line"] < max(1, len(lines)), f"{where}: range off buffer {sym['name']}"
            assert rng["end"]["line"] < max(1, len(lines)), f"{where}: range past buffer {sym['name']}"
            # The spec-mandatory one.
            assert (
                rng["start"]["line"] <= sel["start"]["line"]
                and sel["end"]["line"] <= rng["end"]["line"]
            ), f"{where}: selectionRange outside range at {path}/{sym['name']}"
            if parent is not None:
                assert (
                    parent["start"]["line"] <= rng["start"]["line"]
                    and rng["end"]["line"] <= parent["end"]["line"]
                ), f"{where}: child outside parent at {path}/{sym['name']}"
            if previous is not None:
                assert rng["start"]["line"] > previous["end"]["line"], (
                    f"{where}: siblings overlap at {path}/{sym['name']}"
                )
            previous = rng
            check(sym["children"], rng, f"{path}/{sym['name']}")

    check(symbols, None, "")


def test_lsp_document_symbols_are_valid_over_the_whole_corpus():
    """Every .puml in the repository, plus the adversarial buffers."""
    from pumllint.lsp import document_symbols_for

    root = Path(__file__).resolve().parent.parent
    files = sorted(p for p in root.rglob("*.puml") if ".git" not in p.parts)
    assert len(files) > 20, f"expected a real corpus, found {len(files)}"
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        _assert_tree_is_valid(
            document_symbols_for(text, path.name), re.split(r"\r\n|\r|\n", text), path.name
        )
    for label, text in _ADVERSARIAL.items():
        _assert_tree_is_valid(
            document_symbols_for(text, "d.puml"), re.split(r"\r\n|\r|\n", text), label
        )


def test_lsp_document_symbols_outline_a_sequence_diagram():
    from pumllint.lsp import document_symbols_for

    doc = "@startuml d\ntitle T\nparticipant A\nparticipant B\nalt happy\nA -> B : go\nend\n@enduml\n"
    roots = document_symbols_for(doc, "d.puml")
    assert len(roots) == 1 and roots[0]["name"] == "d"
    names = [s["name"] for _, s in _walk(roots)]
    assert "A" in names and "B" in names and "alt happy" in names
    # The message is nested inside the block it lives in, not a sibling.
    alt = [s for _, s in _walk(roots) if s["name"] == "alt happy"][0]
    assert [c["name"] for c in alt["children"]] == ["go"]


def test_lsp_document_symbols_nest_class_members():
    """Members sit on lines after the declaration, so the class range must be
    the envelope of its descendants — the defect that broke the shipped
    good-example file."""
    from pumllint.lsp import document_symbols_for

    doc = "@startuml\nclass Customer {\n  +name: String\n  +placeOrder(): Order\n}\n@enduml\n"
    cls = [s for _, s in _walk(document_symbols_for(doc, "c.puml")) if s["name"] == "Customer"][0]
    assert [c["name"] for c in cls["children"]] == ["name", "placeOrder"]
    assert cls["range"]["end"]["line"] >= cls["children"][-1]["range"]["end"]["line"]


def test_lsp_document_symbols_keep_a_root_for_an_unknown_diagram():
    """The @startuml line always parses, so the name is real even when the
    contents were not understood — six named roots is the most useful outline
    available for a C4 file."""
    from pumllint.lsp import document_symbols_for

    doc = "@startuml loan_approved\n!include <C4/C4_Sequence>\nPerson(a, \"Applicant\")\n@enduml\n"
    roots = document_symbols_for(doc, "c4.puml")
    assert len(roots) == 1
    assert roots[0]["name"] == "loan_approved"
    assert roots[0]["detail"] == "unknown"
    assert roots[0]["children"] == []


def test_lsp_document_symbols_label_an_inferred_sequence_diagram():
    """A component diagram types as *sequence* with manufactured lifelines.

    Suppressing would be incoherent — the engine already reports findings on
    this buffer as a sequence diagram — so the uncertainty goes in `detail`.
    """
    from pumllint.lsp import document_symbols_for

    inferred = document_symbols_for("@startuml\ncomponent Api\ncomponent Db\nApi --> Db\n@enduml\n", "x.puml")
    assert inferred[0]["detail"] == "sequence (inferred)"
    declared = document_symbols_for("@startuml\nparticipant A\nA -> B : go\n@enduml\n", "y.puml")
    assert declared[0]["detail"] == "sequence"


def test_lsp_document_symbols_skip_the_duplicate_decision_node():
    """An activity `if` emits both a Block and a decision ActivityNode with the
    same label on the same line — two indistinguishable rows, one target."""
    from pumllint.lsp import document_symbols_for

    doc = "@startuml\nstart\nif (Ready?) then (yes)\n  :go;\nendif\nstop\n@enduml\n"
    names = [s["name"] for _, s in _walk(document_symbols_for(doc, "a.puml"))]
    assert names.count("if Ready?") == 1
    assert "Ready?" not in names  # the bare decision node is not repeated


def test_lsp_document_symbols_distinguish_two_participants_on_one_line():
    """Whole-line selection ranges would give both the same jump target."""
    from pumllint.lsp import document_symbols_for

    roots = document_symbols_for("@startuml\nAlice -> Bob : hi\n@enduml\n", "d.puml")
    people = [s for _, s in _walk(roots) if s["name"] in ("Alice", "Bob")]
    assert len(people) == 2
    assert people[0]["selectionRange"] != people[1]["selectionRange"]


def test_lsp_document_symbols_are_offered_over_the_protocol():
    _, replies = _drive(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"capabilities": {"textDocument": {"documentSymbol":
                 {"hierarchicalDocumentSymbolSupport": True}}}}},
            {"jsonrpc": "2.0", "method": "textDocument/didOpen",
             "params": {"textDocument": {"uri": "file:///d.puml", "text": _DOC}}},
            {"jsonrpc": "2.0", "id": 2, "method": "textDocument/documentSymbol",
             "params": {"textDocument": {"uri": "file:///d.puml"}}},
            {"jsonrpc": "2.0", "id": 3, "method": "shutdown"},
            {"jsonrpc": "2.0", "method": "exit"},
        ]
    )
    caps = [r for r in replies if r.get("id") == 1][0]["result"]["capabilities"]
    assert caps["documentSymbolProvider"] is True
    result = [r for r in replies if r.get("id") == 2][0]["result"]
    assert result and "children" in result[0]  # hierarchical form


def test_lsp_document_symbols_fall_back_to_flat_for_clients_without_hierarchy():
    """A client that does not advertise hierarchical support gets
    SymbolInformation[], which carries a location and a containerName."""
    _, replies = _drive(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "textDocument/didOpen",
             "params": {"textDocument": {"uri": "file:///d.puml", "text": _DOC}}},
            {"jsonrpc": "2.0", "id": 2, "method": "textDocument/documentSymbol",
             "params": {"textDocument": {"uri": "file:///d.puml"}}},
            {"jsonrpc": "2.0", "id": 3, "method": "shutdown"},
            {"jsonrpc": "2.0", "method": "exit"},
        ]
    )
    result = [r for r in replies if r.get("id") == 2][0]["result"]
    assert result and "location" in result[0] and "children" not in result[0]
    assert any("containerName" in s for s in result)


def test_lsp_document_symbols_survive_a_parser_failure():
    out = io.BytesIO()
    server = LspServer(out)
    server._documents["file:///d.puml"] = _DOC
    import pumllint.lsp as lsp_mod

    original = lsp_mod.document_symbols_for
    lsp_mod.document_symbols_for = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        server.handle({"jsonrpc": "2.0", "id": 5, "method": "textDocument/documentSymbol",
                       "params": {"textDocument": {"uri": "file:///d.puml"}}})
    finally:
        lsp_mod.document_symbols_for = original
    assert _decode_all(out.getvalue())[0]["result"] == []


def test_lsp_document_symbols_are_complete_not_merely_valid():
    """The outline must contain what the parser modelled.

    Caught a real gap: with the descendant-envelope pass disabled, every class
    member was silently dropped (14 symbols to 6) and the tree stayed
    perfectly *valid* — so the invariant test above passed while the outline
    was wrong. Well-formedness and completeness are different properties and
    both need asserting.
    """
    from pumllint.lsp import document_symbols_for
    from pumllint.parser import parse_source

    root = Path(__file__).resolve().parent.parent
    for name in ("shop_classes_good.puml", "door_lock_state_good.puml",
                 "webshop_usecase_good.puml", "insurance_claim_good.puml"):
        path = root / "examples" / name
        text = path.read_text(encoding="utf-8")
        found = {s["name"] for _, s in _walk(document_symbols_for(text, name))}
        for diagram in parse_source(text, name):
            if diagram.diagram_type == "unknown":
                continue
            expected = set()
            for entity in list(diagram.participants.values()) + list(diagram.states.values()):
                expected.add(entity.display_name or entity.name)
            for entity in diagram.classes.values():
                expected.add(entity.display_name or entity.name)
                expected.update(m.name for m in entity.members if m.name)
            missing = expected - found
            assert not missing, f"{name}: outline dropped {sorted(missing)}"

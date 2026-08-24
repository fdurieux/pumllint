"""Dogfooding-record sync guard. docs/dogfooding.md publishes the exact
outputs of running the tool on docs/pumllint-lint-flow.puml, and
docs/pumllint-lint-flow-explained.md narrates the same numbers. Committed
prose must never drift from what the tool actually produces: these tests
re-run the documented commands and assert the documents carry the live
numbers. After a deliberate change to the diagram, the rules, or the
scoring, re-run the four commands in docs/dogfooding.md ("The runs") and
update BOTH documents to the new outputs in the same commit.

Genesis case: commit 2eca8ae removed one of three suppressed self-messages
from the diagram and neither document moved — four numbers were stale for
five releases with nothing to catch them (issue #31).
"""

import re
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_DIAGRAM = "docs/pumllint-lint-flow.puml"


def _run(*args: str) -> str:
    proc = subprocess.run(
        [sys.executable, "-m", "pumllint", *args],
        cwd=_ROOT,
        capture_output=True,
        text=True,
    )
    return proc.stdout + proc.stderr


def _doc(name: str) -> str:
    return (_ROOT / "docs" / name).read_text(encoding="utf-8")


def test_dogfooding_seq006_count_matches_the_doc():
    out = _run("--no-suppressions", _DIAGRAM)
    live = out.count("[SEQ006/")
    assert live > 0, "the honest test surface disappeared entirely"
    claim = f"{live} × SEQ006"
    assert claim in _doc("dogfooding.md"), (
        f"tool reports {live} SEQ006 findings but docs/dogfooding.md does not "
        f"say {claim!r} — update the record (see this module's docstring)"
    )


def test_dogfooding_suppressed_count_matches_both_docs():
    out = _run("score", _DIAGRAM)
    m = re.search(r"\((\d+) finding\(s\) suppressed\)", out)
    assert m, f"score output carries no suppressed count: {out!r}"
    claim = f"({m.group(1)} suppressed)"
    for name in ("dogfooding.md", "pumllint-lint-flow-explained.md"):
        assert claim in _doc(name), (
            f"tool reports {claim!r} but docs/{name} does not — "
            "update the record (see this module's docstring)"
        )


def test_dogfooding_codegen_finding_count_matches_the_doc():
    out = _run("--profile", "codegen", "--no-suppressions", _DIAGRAM)
    m = re.search(r"(\d+) issue\(s\)", out)
    assert m, f"codegen lint output carries no issue count: {out!r}"
    claim = f"{m.group(1)} findings"
    assert claim in _doc("dogfooding.md"), (
        f"tool reports {m.group(1)} codegen findings but docs/dogfooding.md "
        f"does not say {claim!r} — update the record"
    )


def test_dogfooding_scores_match_the_doc():
    doc = _doc("dogfooding.md")
    codegen = _run("score", "--profile", "codegen", _DIAGRAM)
    m = re.search(r"— (\d+(?:\.\d+)?)/100", codegen)
    assert m, f"codegen score output carries no composite: {codegen!r}"
    assert f"{m.group(1)}/100" in doc, (
        f"codegen score is {m.group(1)}/100 but docs/dogfooding.md does not "
        "carry it — update the record"
    )
    unsuppressed = _run("score", "--no-suppressions", _DIAGRAM)
    m = re.search(r"— (\d+(?:\.\d+)?)/100", unsuppressed)
    assert m, f"unsuppressed score output carries no composite: {unsuppressed!r}"
    assert f"{m.group(1)}/100" in doc, (
        f"unsuppressed score is {m.group(1)}/100 but docs/dogfooding.md does "
        "not carry it — update the record"
    )

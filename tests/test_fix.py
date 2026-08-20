"""Auto-fix tests (pumllint fix). Plain assert functions so the
zero-dependency runner exercises them too. All file operations happen in
temp dirs — the repo's own examples must never be "fixed".
"""

import contextlib
import io
import tempfile
from pathlib import Path

from pumllint.cli import main
from pumllint.engine import Engine
from pumllint.fixer import apply_fixes, compute_fixes, fix_paths
from pumllint.parser import parse_source

# One declared participant so SEQ001 engages (it deliberately stays quiet in
# files that declare nothing at all — and so does the fixer).
_MESSY = """\
@startuml
participant Customer
Customer -> credit_engine : Score applicant
credit_engine --> Customer : Risk score
@enduml
"""


def _fixed(src: str, stem: str = "credit_check", config: dict | None = None) -> str:
    diagrams = parse_source(src, f"{stem}.puml")
    violations = Engine(config or {}).lint_diagrams(diagrams)
    return apply_fixes(src, compute_fixes(src, diagrams, violations, stem=stem))


def test_fix_names_titles_and_declares_participants():
    out = _fixed(_MESSY)
    assert "@startuml credit-check" in out
    assert "title Credit check" in out
    assert "participant credit_engine" in out
    # new declaration lands after the existing one, before the first message
    assert (
        out.index("title ")
        < out.index("participant Customer")
        < out.index("participant credit_engine")
        < out.index("Customer ->")
    )


def test_fix_is_idempotent_and_removes_the_fixed_findings():
    once = _fixed(_MESSY)
    assert _fixed(once) == once
    ids = {v.rule_id for v in Engine({}).lint_diagrams(parse_source(once, "t.puml"))}
    assert not ids & {"GEN001", "GEN002", "SEQ001"}


def test_fix_anchors_declarations_after_existing_ones():
    src = (
        "@startuml flow\ntitle Flow\nparticipant Customer\n"
        "Customer -> Bank : pay()\nBank -> Ledger : book()\n@enduml\n"
    )
    out = _fixed(src, stem="flow")
    lines = out.splitlines()
    assert lines[2:5] == ["participant Customer", "participant Bank", "participant Ledger"]


def test_multiple_diagrams_in_one_file_get_ordinal_names():
    src = "@startuml\ntitle A\nAlice -> Bob : hi\n@enduml\n@startuml\ntitle B\nBob -> Eve : yo\n@enduml\n"
    out = _fixed(src, stem="pair")
    assert "@startuml pair\n" in out
    assert "@startuml pair-2\n" in out


def test_suppressed_findings_are_not_fixed():
    src = "' pumllint: disable-file=GEN001, GEN002\n" + _MESSY
    out = _fixed(src)
    assert "@startuml\n" in out  # still unnamed
    assert "title " not in out
    assert "participant credit_engine" in out  # SEQ001 still fixed


def test_disabled_rules_are_not_fixed():
    out = _fixed(_MESSY, config={"rules": {"SEQ001": False}})
    assert "participant credit_engine" not in out
    assert "title Credit check" in out


def test_fix_preserves_crlf_line_endings():
    src = _MESSY.replace("\n", "\r\n")
    out = _fixed(src)
    assert "\r\n" in out
    assert "\n" not in out.replace("\r\n", "")


def _fix_on_disk(src: str) -> bytes:
    """Bytes on disk after a real `pumllint fix` run — file layer included."""
    with tempfile.TemporaryDirectory() as tmp:
        puml = Path(tmp) / "credit_check.puml"
        puml.write_bytes(src.encode("utf-8"))
        cfg = Path(tmp) / "cfg.json"
        cfg.write_text("{}", encoding="utf-8")
        with io.StringIO() as quiet, contextlib.redirect_stdout(quiet):
            main(["fix", str(puml), "-c", str(cfg)])
        return puml.read_bytes()


def test_fix_writes_crlf_files_back_without_doubling_the_returns():
    # apply_fixes joins with \r\n, but Windows text mode re-translates every
    # \n on the way out, producing \r\r\n. Only a real write catches that,
    # which is why the assertion above (string level) stayed green while the
    # bug shipped.
    written = _fix_on_disk(_MESSY.replace("\n", "\r\n"))
    assert b"\r\r\n" not in written
    assert written.count(b"\r\n") == written.count(b"\n")


def test_fix_writes_lf_files_back_as_lf():
    written = _fix_on_disk(_MESSY)
    assert b"\r" not in written


def test_exotic_participant_names_are_quoted():
    src = (
        "@startuml x\ntitle X\nparticipant Alice\n"
        'Alice -> "Front Office" : hi\n@enduml\n'
    )
    out = _fixed(src, stem="x")
    assert 'participant "Front Office"' in out


def test_non_sequence_diagrams_get_title_fixes_too():
    src = "@startuml\nstart\n:Review application;\nstop\n@enduml\n"
    out = _fixed(src, stem="loan_flow")
    assert "@startuml loan-flow" in out
    assert "title Loan flow" in out


def test_fix_paths_only_flags_changed_files():
    with tempfile.TemporaryDirectory() as tmp:
        clean = Path(tmp) / "clean.puml"
        clean.write_text(
            "@startuml clean\ntitle Clean\nparticipant A\nparticipant B\n"
            "A -> B : go()\n@enduml\n",
            encoding="utf-8",
        )
        messy = Path(tmp) / "messy.puml"
        messy.write_text(_MESSY, encoding="utf-8")
        results = fix_paths([tmp])
        by_name = {r.path.name: r for r in results}
        assert not by_name["clean.puml"].changed
        assert by_name["messy.puml"].changed


# An explicit empty JSON config isolates CLI tests from the repo's
# pumllint.toml (tests must not inherit the repo's own rule settings).
def _cli_fixture(tmp: str) -> tuple[Path, Path]:
    f = Path(tmp) / "credit_check.puml"
    f.write_text(_MESSY, encoding="utf-8")
    cfg = Path(tmp) / "cfg.json"
    cfg.write_text("{}", encoding="utf-8")
    return f, cfg


def test_cli_fix_applies_and_second_run_is_clean():
    with tempfile.TemporaryDirectory() as tmp:
        f, cfg = _cli_fixture(tmp)
        assert main(["fix", str(f), "-c", str(cfg)]) == 0
        assert "title Credit check" in f.read_text(encoding="utf-8")
        assert main(["fix", str(f), "-c", str(cfg)]) == 0


def test_cli_fix_dry_run_writes_nothing_and_signals_pending():
    with tempfile.TemporaryDirectory() as tmp:
        f, cfg = _cli_fixture(tmp)
        assert main(["fix", str(f), "-c", str(cfg), "--dry-run"]) == 1
        assert f.read_text(encoding="utf-8") == _MESSY
        # clean tree: dry-run exits 0
        f.write_text(
            "@startuml ok\ntitle Ok\nparticipant A\nA -> A : x()\n@enduml\n",
            encoding="utf-8",
        )
        assert main(["fix", str(f), "-c", str(cfg), "--dry-run"]) == 0


def test_cli_fix_requires_paths():
    assert main(["fix"]) == 2


def test_sketches_declaring_nothing_get_no_declaration_fixes_by_default():
    # The fixer inherits SEQ001's only_if_any_declared judgment: an ad-hoc
    # sketch is not punished by the linter, so it is not "fixed" either.
    sketch = "@startuml quick\ntitle Quick\nAlice -> Bob : hi\n@enduml\n"
    assert "participant" not in _fixed(sketch, stem="quick")
    # The documented escape hatch turns the fixes on.
    cfg = {"rules": {"SEQ001": {"only_if_any_declared": False}}}
    out = _fixed(sketch, stem="quick", config=cfg)
    assert "participant Alice" in out and "participant Bob" in out

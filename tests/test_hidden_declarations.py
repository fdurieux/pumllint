"""The `!include` hidden-declarations disclosure (G3,
docs/cross-diagram-relationships-evaluation.md).

A diagram whose declarations live behind `!include` parses with only
implicit entities, silencing the XD identity checks and every
declared-entity rule — and the maturity score *rises* for it. The CLI
disclosure says so on stderr, like the "nothing was checked" warning:
never a finding, never an exit-code change. Plain assert functions for
the zero-dependency runner.
"""

import contextlib
import io
import json
import tempfile
from pathlib import Path

from pumllint.cli import main

_INCLUDED = "@startuml a\ntitle A\n!include _shared.iuml\nSvc -> Peer : go()\n@enduml\n"
_INLINE = (
    "@startuml a\ntitle A\nparticipant Svc\nparticipant Peer\n"
    "Svc -> Peer : go()\n@enduml\n"
)
_IMPLICIT_ONLY = "@startuml a\ntitle A\nSvc -> Peer : go()\n@enduml\n"


def _run(tmp: str, src: str, argv_head: list[str] | None = None):
    puml = Path(tmp) / "d.puml"
    puml.write_text(src, encoding="utf-8")
    cfg = Path(tmp) / "cfg.json"
    cfg.write_text("{}", encoding="utf-8")
    out = Path(tmp) / "report.txt"
    err = io.StringIO()
    argv = (argv_head or []) + [str(puml), "-c", str(cfg), "-o", str(out)]
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        rc = main(argv)
    return rc, err.getvalue(), out.read_text(encoding="utf-8")


def test_lint_discloses_declarations_hidden_behind_include():
    with tempfile.TemporaryDirectory() as tmp:
        rc, err, report = _run(tmp, _INCLUDED)
        assert "contain '!include' but declare nothing" in err
        assert "d.puml" in err
        # disclosure, not a finding: the report body carries no new issue
        assert "!include" not in report
        assert rc == 0  # exit code untouched


def test_score_discloses_too_and_the_score_is_untouched():
    with tempfile.TemporaryDirectory() as tmp:
        rc, err, report = _run(tmp, _INCLUDED, ["score"])
        assert "contain '!include' but declare nothing" in err
        assert rc == 0
        # same source without the include line scores identically: the
        # disclosure is a warning, never a penalty
        rc2, err2, report2 = _run(tmp, _INCLUDED.replace("!include _shared.iuml\n", ""), ["score"])
        assert "contain '!include'" not in err2
        assert report == report2


def test_inline_declarations_do_not_warn():
    with tempfile.TemporaryDirectory() as tmp:
        _, err, _ = _run(tmp, _INLINE.replace("participant Svc", "participant Svc\n!include theme.iuml"))
        # an include used alongside inline declarations is legitimate (a
        # theme, GEN003's own recommendation) — no warning
        assert "declare nothing" not in err


def test_implicit_without_include_does_not_warn():
    with tempfile.TemporaryDirectory() as tmp:
        _, err, _ = _run(tmp, _IMPLICIT_ONLY)
        assert "declare nothing" not in err


def test_json_report_shape_is_unchanged():
    with tempfile.TemporaryDirectory() as tmp:
        puml = Path(tmp) / "d.puml"
        puml.write_text(_INCLUDED, encoding="utf-8")
        cfg = Path(tmp) / "cfg.json"
        cfg.write_text("{}", encoding="utf-8")
        out = Path(tmp) / "r.json"
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            main([str(puml), "-c", str(cfg), "-f", "json", "-o", str(out)])
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "contain '!include'" in err.getvalue()
        # stderr only: nothing about includes leaks into the pinned report shape
        assert "include" not in json.dumps(data)

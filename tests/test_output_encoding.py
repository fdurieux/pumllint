"""Output must survive a console codec that cannot render ✔/✖.

On Windows, stdout is UTF-8 only while attached to a real console; redirect,
pipe or capture it (`pumllint . > report.txt`, pre-commit, most CI log
collectors) and it becomes the ANSI code page, where printing U+2714 raises
UnicodeEncodeError, loses the whole report and inverts the exit code.

`PYTHONIOENCODING=cp1252` on a subprocess reproduces that exactly on Linux.
Plain assert functions for the zero-dependency runner.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from pumllint.cli import _encode_safely
from pumllint.reporters.base import ascii_glyphs

_CLEAN = "@startuml Order\ntitle Order intake\nAlice -> Bob : hi\n@enduml\n"
_DIRTY = "@startuml\nAlice -> Bob : hi\n@enduml\n"


class _Stream:
    def __init__(self, encoding):
        self.encoding = encoding


def _run(args, tmp, encoding="cp1252"):
    """pumllint in a subprocess with stdout to a real file, as a redirect does."""
    env = {**os.environ, "PYTHONIOENCODING": encoding, "PYTHONPATH": os.getcwd()}
    out = Path(tmp) / "captured.txt"
    with out.open("wb") as fh:
        proc = subprocess.run(
            [sys.executable, "-m", "pumllint", *args],
            stdout=fh, stderr=subprocess.PIPE, cwd=tmp, env=env,
        )
    return proc.returncode, out.read_bytes(), proc.stderr.decode("utf-8", "replace")


def test_encode_safely_downgrades_glyphs_the_codec_cannot_render():
    got = _encode_safely("✔ clean ✖ 2 issues → here", _Stream("cp1252"))
    assert got == "OK clean FAIL 2 issues -> here", got


def test_encode_safely_leaves_utf8_untouched():
    text = "✔ No issues found. → ←"
    assert _encode_safely(text, _Stream("utf-8")) == text


def test_encode_safely_escapes_content_with_no_ascii_equivalent():
    got = _encode_safely("participant 参加者", _Stream("cp1252"))
    assert "\\u53c2" in got, got  # visible escape, not a crash


def test_encode_safely_tolerates_a_stream_without_an_encoding():
    text = "✔ No issues found."
    assert _encode_safely(text, _Stream(None)) == text


def test_reporters_still_emit_unicode_glyphs():
    # The downgrade belongs in the CLI chokepoint, so -o FILE and the HTML
    # reporter keep their Unicode.
    from pumllint.reporters import get_reporter

    assert "✔" in get_reporter("text").render([])


def test_ascii_glyphs_maps_every_decoration():
    assert ascii_glyphs("✔✖→←…") == "OKFAIL-><-..."


def test_clean_run_under_a_legacy_codepage_redirect():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "d.puml").write_text(_CLEAN, encoding="utf-8")
        (Path(tmp) / "cfg.json").write_text("{}", encoding="utf-8")
        rc, out, err = _run(["d.puml", "-c", "cfg.json"], tmp)
        assert rc == 0, (rc, err)
        assert out.strip(), "the report must survive the redirect"
        assert b"Traceback" not in out and "Traceback" not in err, err


def test_findings_under_a_legacy_codepage_redirect_keep_exit_one():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "d.puml").write_text(_DIRTY, encoding="utf-8")
        (Path(tmp) / "cfg.json").write_text("{}", encoding="utf-8")
        rc, out, err = _run(["d.puml", "-c", "cfg.json", "--fail-on", "info"], tmp)
        # exit 1 must still mean "findings", not "the reporter died"
        assert rc == 1, (rc, err)
        assert b"issue(s)" in out, out
        assert "Traceback" not in err, err


def test_fix_under_a_legacy_codepage_redirect_reports_success():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "d.puml").write_text(_DIRTY, encoding="utf-8")
        (Path(tmp) / "cfg.json").write_text("{}", encoding="utf-8")
        rc, out, err = _run(["fix", "d.puml", "-c", "cfg.json"], tmp)
        assert rc == 0, (rc, err)
        assert b"fix(es)" in out or b"Nothing to fix" in out, out
        assert "Traceback" not in err, err


def test_score_under_a_legacy_codepage_redirect():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "d.puml").write_text(_CLEAN, encoding="utf-8")
        (Path(tmp) / "cfg.json").write_text("{}", encoding="utf-8")
        rc, out, err = _run(["score", "d.puml", "-c", "cfg.json"], tmp)
        assert rc == 0, (rc, err)
        assert out.strip(), "the score report must survive the redirect"
        assert "Traceback" not in err, err

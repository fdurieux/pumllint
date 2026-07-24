"""Pilot-example sync guard. docs/example-maturity-report.html and
docs/example-badge.json are the *published* Phase-0 pilot artefacts — the
tool's own score run over the bundled examples/, linked from the management
docs. Committed output must never drift from what the tool actually
produces: these tests re-run the exact publishing commands and compare
bytes. After a deliberate scoring or reporter change, regenerate with:

    python -m pumllint score examples/ -f html  -o docs/example-maturity-report.html
    python -m pumllint score examples/ -f badge -o docs/example-badge.json
"""

import subprocess
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _regenerate(fmt: str, out: Path) -> None:
    subprocess.run(
        [sys.executable, "-m", "pumllint", "score", "examples/", "-f", fmt,
         "-o", str(out)],
        cwd=_ROOT,
        check=True,
        capture_output=True,
    )


def _assert_matches(fmt: str, published: str) -> None:
    committed = _ROOT / "docs" / published
    assert committed.exists(), f"docs/{published} is missing — regenerate it"
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / published
        _regenerate(fmt, fresh)
        assert fresh.read_bytes() == committed.read_bytes(), (
            f"docs/{published} no longer matches `pumllint score examples/ "
            f"-f {fmt}` — the published pilot example has drifted; "
            f"regenerate it (see this file's docstring)"
        )


def test_published_html_report_matches_a_fresh_run():
    _assert_matches("html", "example-maturity-report.html")


def test_published_badge_matches_a_fresh_run():
    _assert_matches("badge", "example-badge.json")

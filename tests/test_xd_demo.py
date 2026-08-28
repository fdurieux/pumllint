"""Drift guard for docs/xd-identity-demo.md and its committed corpus.

The walkthrough quotes live tool output (the `!include` disclosure warning,
the symmetric XD005 findings, the inline-drift contrast); these tests run
the same commands against the committed files under docs/xd-demo/ and
assert both directions — the tool still produces what the page quotes, and
the page still quotes what the tool produces. Same pact as
tests/test_pilot_example.py and tests/test_dogfooding.py: change either
side deliberately, and this file says so.

Plain assert functions; in-process ``main()`` with redirected streams so
nothing prints under the zero-dependency runner.
"""

import contextlib
import io
import tempfile
from pathlib import Path

from pumllint.cli import main

_ROOT = Path(__file__).resolve().parents[1]
_DEMO = _ROOT / "docs" / "xd-demo"
_PAGE = _ROOT / "docs" / "xd-identity-demo.md"

_WARN_PHRASE = "contain '!include' but declare nothing"


def _run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = main(argv)
    return rc, out.getvalue(), err.getvalue()


def _demo_args(*names: str, config: str = "lint.toml") -> list[str]:
    return [str(_DEMO / n) for n in names] + ["-c", str(_DEMO / config)]


def test_disclosure_fires_on_the_include_pair_exactly_as_documented():
    rc, out, err = _run(_demo_args("checkout.puml", "refund.puml"))
    assert rc == 0  # a disclosure, never a gate
    assert _WARN_PHRASE in err and "checkout.puml" in err and "refund.puml" in err
    assert "No issues found" in out  # the report itself is clean
    assert _WARN_PHRASE not in out  # stderr only — never a finding
    page = _PAGE.read_text(encoding="utf-8")
    assert _WARN_PHRASE in page  # the page quotes the live warning


def test_score_warns_too_and_the_documented_verdict_holds():
    rc, out, err = _run(["score"] + _demo_args("checkout.puml", "refund.puml"))
    assert rc == 0
    assert _WARN_PHRASE in err
    # the page's point: Level 4 100/100 on half-read files, with the warning
    assert "[checkout]: Level 4 (Precise) — 100/100" in out
    assert "[refund]: Level 4 (Precise) — 100/100" in out
    page = _PAGE.read_text(encoding="utf-8")
    assert "Level 4 (Precise) — 100/100" in page


def test_xd005_fires_symmetrically_without_distinct():
    rc, out, err = _run(_demo_args("sales.puml", "manufacturing.puml"))
    assert rc == 0  # two minors: below the default --fail-on major
    assert out.count("[XD005/minor]") == 2
    assert "sales.puml:4" in out and "manufacturing.puml:4" in out
    variants = "(<<aggregate>> ×1, <<work-order>> ×1)"
    assert variants in out
    assert _WARN_PHRASE not in err  # class pair declares inline: no disclosure
    page = _PAGE.read_text(encoding="utf-8")
    assert variants in page  # the page quotes the live variant summary


def test_distinct_config_silences_the_homonym():
    rc, out, err = _run(
        _demo_args("sales.puml", "manufacturing.puml", config="distinct.toml")
    )
    assert rc == 0
    assert "XD005" not in out
    assert "No issues found" in out


def test_inline_contrast_matches_the_documented_findings():
    # The page's contrast section: !include replaced by inline declarations,
    # refund.puml drifting the gateway to `database <<store>>`.
    inline = (
        "participant OrderService <<service>>\n"
        "participant InventoryService <<service>>\n"
        "participant PaymentGateway <<external>>"
    )
    drifted = (
        "participant OrderService <<service>>\n"
        "database PaymentGateway <<store>>"
    )
    with tempfile.TemporaryDirectory() as tmp:
        for name, decls in (("checkout.puml", inline), ("refund.puml", drifted)):
            src = (_DEMO / name).read_text(encoding="utf-8")
            (Path(tmp) / name).write_text(
                src.replace("!include _participants.iuml", decls), encoding="utf-8"
            )
        rc, out, err = _run(
            [str(Path(tmp) / "checkout.puml"), str(Path(tmp) / "refund.puml"),
             "-c", str(_DEMO / "lint.toml")]
        )
    assert rc == 1  # two majors now: the drift is visible and gates
    assert out.count("[XD001/major]") == 2 and out.count("[XD002/minor]") == 2
    assert _WARN_PHRASE not in err  # declarations inline: nothing hidden
    page = _PAGE.read_text(encoding="utf-8")
    for fragment in (
        "('database' ×1, 'participant' ×1)",
        "(<<external>> ×1, <<store>> ×1)",
    ):
        assert fragment in out and fragment in page


def test_demo_configs_and_page_agree_on_the_distinct_stanza():
    stanza = 'distinct = ["Order"]'
    assert stanza in (_DEMO / "distinct.toml").read_text(encoding="utf-8")
    assert stanza in _PAGE.read_text(encoding="utf-8")

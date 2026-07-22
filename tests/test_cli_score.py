"""CLI tests for the `score` subcommand (Phase 6). Plain assert functions; all
output is routed to a file with -o so nothing prints under the zero-dependency
runner, and an explicit empty JSON config isolates tests from the repo's
pumllint.yaml.
"""

import json
import tempfile
from pathlib import Path

from pumllint.cli import main
from pumllint.engine import Engine
from pumllint.scoring import score_groups

_SRC = "@startuml Order\nAlice -> Bob : hi\n@enduml\n"


def _fixture(tmp: str):
    puml = Path(tmp) / "d.puml"
    puml.write_text(_SRC, encoding="utf-8")
    cfg = Path(tmp) / "cfg.json"
    cfg.write_text("{}", encoding="utf-8")  # empty config -> scoring defaults
    return puml, cfg


def _expected_level(puml: Path) -> int:
    groups = Engine({}).lint_paths_grouped([str(puml)])
    return score_groups(groups)[0][1].level


def test_score_command_writes_report():
    with tempfile.TemporaryDirectory() as tmp:
        puml, cfg = _fixture(tmp)
        out = Path(tmp) / "r.txt"
        rc = main(["score", str(puml), "-c", str(cfg), "-o", str(out)])
        assert rc == 0
        assert "Level" in out.read_text(encoding="utf-8")


def test_min_level_gate_passes_at_threshold():
    with tempfile.TemporaryDirectory() as tmp:
        puml, cfg = _fixture(tmp)
        out = Path(tmp) / "r.txt"
        level = _expected_level(puml)
        rc = main(["score", str(puml), "-c", str(cfg), "--min-level", str(level), "-o", str(out)])
        assert rc == 0


def test_min_level_gate_fails_below_threshold():
    with tempfile.TemporaryDirectory() as tmp:
        puml, cfg = _fixture(tmp)
        out = Path(tmp) / "r.txt"
        level = _expected_level(puml)
        if level >= 5:
            return  # can't ask for a higher level
        rc = main(["score", str(puml), "-c", str(cfg), "--min-level", str(level + 1), "-o", str(out)])
        assert rc == 1


def test_score_json_format():
    with tempfile.TemporaryDirectory() as tmp:
        puml, cfg = _fixture(tmp)
        out = Path(tmp) / "r.json"
        rc = main(["score", str(puml), "-c", str(cfg), "-f", "json", "-o", str(out)])
        assert rc == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["diagrams"][0]["maturity"]["level"] == _expected_level(puml)
        assert data["modelSet"]["level"] == _expected_level(puml)


def test_score_requires_paths():
    assert main(["score"]) == 2


def test_check_syntax_gate_forces_level_1_on_failure():
    import sys

    with tempfile.TemporaryDirectory() as tmp:
        puml, _ = _fixture(tmp)
        cfg = Path(tmp) / "gate.json"
        cfg.write_text(json.dumps({
            "scoring": {"syntax_command": [sys.executable, "-c", "import sys; sys.exit(1)"]}
        }), encoding="utf-8")
        out = Path(tmp) / "r.txt"
        rc = main(["score", str(puml), "-c", str(cfg), "--check-syntax",
                   "--min-level", "2", "-o", str(out)])
        assert rc == 1  # gate failure -> Level 1 -> below --min-level 2
        assert "syntax gate" in out.read_text(encoding="utf-8")


def test_syntax_gate_enabled_via_config_and_passing():
    import sys

    with tempfile.TemporaryDirectory() as tmp:
        puml, _ = _fixture(tmp)
        cfg = Path(tmp) / "gate.json"
        cfg.write_text(json.dumps({
            "scoring": {
                "syntax_gate": True,
                "syntax_command": [sys.executable, "-c", "import sys; sys.exit(0)"],
            }
        }), encoding="utf-8")
        out = Path(tmp) / "r.txt"
        rc = main(["score", str(puml), "-c", str(cfg), "--min-level", "2", "-o", str(out)])
        assert rc == 0
        assert "syntax gate" not in out.read_text(encoding="utf-8")


def test_min_level_with_no_diagrams_exits_2():
    # Regression: an empty (or mistyped-but-existing) directory must not
    # silently pass the CI gate.
    with tempfile.TemporaryDirectory() as tmp:
        _, cfg = _fixture(tmp)
        empty = Path(tmp) / "nodiagrams"
        empty.mkdir()
        out = Path(tmp) / "r.txt"
        rc = main(["score", str(empty), "-c", str(cfg), "--min-level", "2", "-o", str(out)])
        assert rc == 2


def test_reporter_without_maturity_support_exits_2():
    # Regression: NotImplementedError from render_maturity must map to a clean
    # config error, not a traceback.
    from pumllint.reporters import Reporter, reporter

    @reporter
    class _NoMaturity(Reporter):
        format_name = "nomat-test"

        def render(self, violations):
            return ""

    with tempfile.TemporaryDirectory() as tmp:
        puml, cfg = _fixture(tmp)
        out = Path(tmp) / "r.txt"
        rc = main(["score", str(puml), "-c", str(cfg), "-f", "nomat-test", "-o", str(out)])
        assert rc == 2


def test_default_command_still_lints():
    with tempfile.TemporaryDirectory() as tmp:
        puml, cfg = _fixture(tmp)
        out = Path(tmp) / "lint.txt"
        rc = main([str(puml), "-c", str(cfg), "-o", str(out)])
        txt = out.read_text(encoding="utf-8")
        assert rc in (0, 1)  # lint exit code, not a score gate
        assert "To reach Level" not in txt  # lint output, not maturity


# --- baseline / ratchet (0.6.0) --------------------------------------------

def _main_quiet(argv: list[str]) -> tuple[int, str]:
    """Run the CLI with stderr captured (keeps the runner's output clean)."""
    import contextlib
    import io

    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rc = main(argv)
    return rc, err.getvalue()


def _bootstrap_baseline(tmp: str):
    """Run score once with a fresh --baseline file; return its path + report."""
    puml, cfg = _fixture(tmp)
    out = Path(tmp) / "r.txt"
    base = Path(tmp) / "maturity.json"
    rc, err = _main_quiet(
        ["score", str(puml), "-c", str(cfg), "--baseline", str(base), "-o", str(out)]
    )
    assert "baseline: recorded" in err
    return rc, puml, cfg, out, base


def test_baseline_bootstrap_records_current_levels_and_passes():
    with tempfile.TemporaryDirectory() as tmp:
        rc, puml, _, _, base = _bootstrap_baseline(tmp)
        assert rc == 0
        data = json.loads(base.read_text(encoding="utf-8"))
        assert data["version"] == 1
        (entry,) = data["diagrams"].values()
        assert entry["level"] == _expected_level(puml)


def test_baseline_second_run_without_regression_passes():
    with tempfile.TemporaryDirectory() as tmp:
        rc, puml, cfg, out, base = _bootstrap_baseline(tmp)
        assert rc == 0
        rc, err = _main_quiet(
            ["score", str(puml), "-c", str(cfg), "--baseline", str(base), "-o", str(out)]
        )
        assert rc == 0
        assert err == ""  # no regressions, nothing to report


def _raise_baseline_levels(base: Path, delta: int = 1) -> None:
    data = json.loads(base.read_text(encoding="utf-8"))
    for entry in data["diagrams"].values():
        entry["level"] += delta
    base.write_text(json.dumps(data), encoding="utf-8")


def test_baseline_regression_exits_1():
    with tempfile.TemporaryDirectory() as tmp:
        rc, puml, cfg, out, base = _bootstrap_baseline(tmp)
        _raise_baseline_levels(base)  # pretend the diagram used to score higher
        rc, err = _main_quiet(
            ["score", str(puml), "-c", str(cfg), "--baseline", str(base), "-o", str(out)]
        )
        assert rc == 1
        assert "regression:" in err and "::Order" in err


def test_update_baseline_accepts_the_status_quo():
    with tempfile.TemporaryDirectory() as tmp:
        rc, puml, cfg, out, base = _bootstrap_baseline(tmp)
        _raise_baseline_levels(base)
        rc, err = _main_quiet(
            ["score", str(puml), "-c", str(cfg), "--baseline", str(base),
             "--update-baseline", "-o", str(out)]
        )
        assert rc == 0  # rewriting the baseline, not comparing against it
        assert "baseline: updated" in err
        data = json.loads(base.read_text(encoding="utf-8"))
        (entry,) = data["diagrams"].values()
        assert entry["level"] == _expected_level(puml)
        # and the ratchet is green again afterwards
        rc, _ = _main_quiet(
            ["score", str(puml), "-c", str(cfg), "--baseline", str(base), "-o", str(out)]
        )
        assert rc == 0


def test_update_baseline_without_baseline_is_a_usage_error():
    rc, err = _main_quiet(["score", "whatever.puml", "--update-baseline"])
    assert rc == 2
    assert "--update-baseline requires --baseline" in err


def test_corrupt_baseline_is_a_config_error():
    with tempfile.TemporaryDirectory() as tmp:
        puml, cfg = _fixture(tmp)
        out = Path(tmp) / "r.txt"
        base = Path(tmp) / "maturity.json"
        base.write_text("{not json", encoding="utf-8")
        rc, err = _main_quiet(
            ["score", str(puml), "-c", str(cfg), "--baseline", str(base), "-o", str(out)]
        )
        assert rc == 2
        assert "not valid JSON" in err


def test_baseline_and_min_level_gates_combine():
    with tempfile.TemporaryDirectory() as tmp:
        rc, puml, cfg, out, base = _bootstrap_baseline(tmp)
        level = _expected_level(puml)
        if level >= 5:
            return  # can't ask for a higher level
        # baseline is green but --min-level still trips
        rc, _ = _main_quiet(
            ["score", str(puml), "-c", str(cfg), "--baseline", str(base),
             "--min-level", str(level + 1), "-o", str(out)]
        )
        assert rc == 1


# --- trend/delta + badge (0.7.0) --------------------------------------------

def test_ratchet_compare_report_shows_delta():
    with tempfile.TemporaryDirectory() as tmp:
        rc, puml, cfg, out, base = _bootstrap_baseline(tmp)
        _raise_baseline_levels(base)  # old baseline is one level higher
        rc, _ = _main_quiet(
            ["score", str(puml), "-c", str(cfg), "--baseline", str(base), "-o", str(out)]
        )
        assert rc == 1
        level = _expected_level(puml)
        txt = out.read_text(encoding="utf-8")
        assert f"(Level {level + 1} → {level} since last baseline)" in txt


def test_bootstrap_run_has_no_delta_annotations():
    with tempfile.TemporaryDirectory() as tmp:
        rc, _, _, out, _ = _bootstrap_baseline(tmp)
        assert rc == 0
        assert "baseline)" not in out.read_text(encoding="utf-8")


def test_update_baseline_report_still_shows_delta_vs_old():
    with tempfile.TemporaryDirectory() as tmp:
        rc, puml, cfg, out, base = _bootstrap_baseline(tmp)
        _raise_baseline_levels(base)
        rc, _ = _main_quiet(
            ["score", str(puml), "-c", str(cfg), "--baseline", str(base),
             "--update-baseline", "-o", str(out)]
        )
        assert rc == 0  # accepting the status quo...
        assert "since last baseline" in out.read_text(encoding="utf-8")  # ...but shown


def test_json_report_carries_baseline_delta():
    with tempfile.TemporaryDirectory() as tmp:
        rc, puml, cfg, out, base = _bootstrap_baseline(tmp)
        _raise_baseline_levels(base)
        outj = Path(tmp) / "r.json"
        rc, _ = _main_quiet(
            ["score", str(puml), "-c", str(cfg), "--baseline", str(base),
             "-f", "json", "-o", str(outj)]
        )
        assert rc == 1
        level = _expected_level(puml)
        data = json.loads(outj.read_text(encoding="utf-8"))
        assert data["diagrams"][0]["baseline"] == {"level": level + 1, "delta": -1}
        assert data["modelSet"]["baseline"] == {"level": level + 1, "delta": -1}


def test_badge_format_writes_shields_endpoint_json():
    with tempfile.TemporaryDirectory() as tmp:
        puml, cfg = _fixture(tmp)
        out = Path(tmp) / "badge.json"
        rc = main(["score", str(puml), "-c", str(cfg), "-f", "badge", "-o", str(out)])
        assert rc == 0
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["schemaVersion"] == 1
        assert payload["message"].startswith(f"Level {_expected_level(puml)} — ")
        assert payload["color"]


def test_badge_format_is_rejected_for_lint():
    with tempfile.TemporaryDirectory() as tmp:
        puml, cfg = _fixture(tmp)
        out = Path(tmp) / "badge.json"
        rc, err = _main_quiet([str(puml), "-c", str(cfg), "-f", "badge", "-o", str(out)])
        assert rc == 2
        assert "score command" in err

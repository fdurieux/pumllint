"""CLI tests for the `score` subcommand (Phase 6). Plain assert functions; all
output is routed to a file with -o so nothing prints under the zero-dependency
runner, and an explicit empty JSON config isolates tests from the repo's
pumllint.toml.
"""

import json
import os
import shutil
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


def test_reporter_without_maturity_support_is_rejected_at_parse_time():
    # A custom @reporter that only implements render() must be selectable for
    # lint but rejected by score's -f choices — argparse now refuses the
    # format up front instead of failing at render_maturity time.
    import contextlib
    import io

    from pumllint.cli import build_parser, build_score_parser
    from pumllint.reporters import Reporter, reporter

    @reporter
    class _NoMaturity(Reporter):
        format_name = "nomat-test"

        def render(self, violations):
            return ""

    def _format_choices(parser):
        return next(a.choices for a in parser._actions if "-f" in a.option_strings)

    assert "nomat-test" in _format_choices(build_parser())
    assert "nomat-test" not in _format_choices(build_score_parser())

    with tempfile.TemporaryDirectory() as tmp:
        puml, cfg = _fixture(tmp)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            try:
                main(["score", str(puml), "-c", str(cfg), "-f", "nomat-test"])
            except SystemExit as e:
                assert e.code == 2
            else:
                raise AssertionError("score accepted a format without maturity support")
        assert "invalid choice: 'nomat-test'" in err.getvalue()


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
        assert data["version"] == 2
        # keyed relative to the baseline file's directory, forward slashes
        assert list(data["diagrams"]) == ["d.puml::Order"], data
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
    # badge has no lint render(), so -f badge fails at parse time now —
    # before any file is read — instead of at render time.
    import contextlib
    import io

    with tempfile.TemporaryDirectory() as tmp:
        puml, cfg = _fixture(tmp)
        out = Path(tmp) / "badge.json"
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            try:
                main([str(puml), "-c", str(cfg), "-f", "badge", "-o", str(out)])
            except SystemExit as e:
                assert e.code == 2
            else:
                raise AssertionError("lint accepted -f badge")
        assert "invalid choice: 'badge'" in err.getvalue()


# --- suppressed-findings disclosure (0.19.0) --------------------------------

_SUPPRESSED_SRC = (
    "@startuml Flow\n"
    "title Flow\n"
    "participant Alice\n"
    "' pumllint: disable=SEQ006\n"
    "Alice -> Alice : tick()\n"
    "@enduml\n"
)


def _suppressed_fixture(tmp: str):
    puml = Path(tmp) / "s.puml"
    puml.write_text(_SUPPRESSED_SRC, encoding="utf-8")
    cfg = Path(tmp) / "cfg.json"
    cfg.write_text("{}", encoding="utf-8")
    return puml, cfg


def test_score_reports_disclose_suppressed_findings_end_to_end():
    with tempfile.TemporaryDirectory() as tmp:
        puml, cfg = _suppressed_fixture(tmp)
        txt, js = Path(tmp) / "r.txt", Path(tmp) / "r.json"
        assert main(["score", str(puml), "-c", str(cfg), "-o", str(txt)]) == 0
        assert "(1 suppressed)" in txt.read_text(encoding="utf-8")
        assert main(["score", str(puml), "-c", str(cfg), "-f", "json", "-o", str(js)]) == 0
        data = json.loads(js.read_text(encoding="utf-8"))
        assert data["diagrams"][0]["maturity"]["suppressedCount"] == 1
        assert data["modelSet"]["suppressedCount"] == 1


def test_no_suppressions_surfaces_the_finding_instead_of_the_count():
    with tempfile.TemporaryDirectory() as tmp:
        puml, cfg = _suppressed_fixture(tmp)
        js = Path(tmp) / "r.json"
        assert main(["score", str(puml), "-c", str(cfg), "--no-suppressions",
                     "-f", "json", "-o", str(js)]) == 0
        data = json.loads(js.read_text(encoding="utf-8"))
        assert data["diagrams"][0]["maturity"]["suppressedCount"] == 0


def _stderr_of(argv: list[str], tmp: str) -> tuple[int, str]:
    """Exit code and stderr of a CLI run, stdout parked in a file."""
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        rc = main(argv + ["-o", str(Path(tmp) / "report.txt")])
    return rc, buf.getvalue()


def test_zero_files_warns_on_stderr_and_still_exits_zero():
    # A linter that says "no issues" because it looked at nothing is worse
    # than one that fails — but the 0/1/2 exit contract stays put.
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "cfg.json").write_text("{}", encoding="utf-8")
        (Path(tmp) / "notes.md").write_text("# not a diagram\n", encoding="utf-8")
        rc, err = _stderr_of([tmp, "-c", str(Path(tmp) / "cfg.json")], tmp)
        assert rc == 0, rc
        assert "no PlantUML files found" in err, err
        assert "nothing was checked" in err, err


def test_file_without_a_startuml_block_warns_but_does_not_fail():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "cfg.json").write_text("{}", encoding="utf-8")
        mind = Path(tmp) / "mind.puml"
        mind.write_text("@startmindmap\n* root\n@endmindmap\n", encoding="utf-8")
        rc, err = _stderr_of([str(mind), "-c", str(Path(tmp) / "cfg.json")], tmp)
        assert rc == 0, rc
        assert "no @startuml block" in err, err
        assert "mind.puml" in err, err


def test_iuml_include_fragment_is_not_warned_about():
    # .iuml is the include-fragment extension: having no @startuml of its own
    # is the point of such a file, so warning about it would be noise on
    # every run of a repo that uses includes.
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "cfg.json").write_text("{}", encoding="utf-8")
        frag = Path(tmp) / "shared.iuml"
        frag.write_text("participant Alice\n", encoding="utf-8")
        rc, err = _stderr_of([str(frag), "-c", str(Path(tmp) / "cfg.json")], tmp)
        assert rc == 0, rc
        assert "no @startuml block" not in err, err


def test_score_without_syntax_gate_discloses_it():
    with tempfile.TemporaryDirectory() as tmp:
        puml, _ = _fixture(tmp)
        out = Path(tmp) / "r.txt"
        main(["score", str(puml), "-o", str(out)])
        text = out.read_text(encoding="utf-8")
        assert "Syntax gate: not run" in text
        assert "DIM-SYN unchecked" in text


def test_score_with_syntax_gate_run_omits_the_disclosure():
    import sys

    with tempfile.TemporaryDirectory() as tmp:
        puml, _ = _fixture(tmp)
        cfg = Path(tmp) / "gate.json"
        cfg.write_text(json.dumps({
            "scoring": {"syntax_command": [sys.executable, "-c", "import sys; sys.exit(0)"]}
        }), encoding="utf-8")
        out = Path(tmp) / "r.txt"
        main(["score", str(puml), "-c", str(cfg), "--check-syntax", "-o", str(out)])
        assert "Syntax gate: not run" not in out.read_text(encoding="utf-8")


def test_json_score_report_is_unchanged_by_the_disclosure():
    with tempfile.TemporaryDirectory() as tmp:
        puml, _ = _fixture(tmp)
        out = Path(tmp) / "r.json"
        main(["score", str(puml), "-f", "json", "-o", str(out)])
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "syntaxGateRan" not in json.dumps(data)  # schema untouched


# --- anchored baseline keys (2026-09-04) -------------------------------------
#
# The file keys on paths relative to its own directory, so the ratchet matches
# from any working directory and under any spelling. The cases below are the
# ones that used to match nothing and pass everything.


def _project(tmp: str) -> Path:
    """proj/diagrams/a.puml + proj/cfg.json — the README's shape."""
    proj = Path(tmp) / "proj"
    (proj / "diagrams").mkdir(parents=True)
    (proj / "diagrams" / "a.puml").write_text(_SRC, encoding="utf-8")
    (proj / "cfg.json").write_text("{}", encoding="utf-8")
    return proj


def _run_from(cwd: Path, argv: list[str]) -> tuple[int, str]:
    old = os.getcwd()
    os.chdir(cwd)
    try:
        return _main_quiet(argv)
    finally:
        os.chdir(old)  # before the temp dir goes: Windows cannot delete a cwd


def _record(tmp: str, proj: Path) -> tuple[Path, list[str]]:
    """Record the canonical way (from proj, relative paths); return the file
    and the argv tail that pins config and report output to absolute paths."""
    common = ["-c", str(proj / "cfg.json"), "-o", str(Path(tmp) / "r.txt")]
    rc, err = _run_from(
        proj, ["score", "diagrams", "--baseline", "maturity.json", *common]
    )
    assert rc == 0 and "baseline: recorded" in err, err
    base = proj / "maturity.json"
    data = json.loads(base.read_text(encoding="utf-8"))
    assert data["version"] == 2, data
    assert list(data["diagrams"]) == ["diagrams/a.puml::Order"], data
    return base, common


def test_ratchet_matches_under_every_spelling_and_cwd():
    with tempfile.TemporaryDirectory() as tmp:
        proj = _project(tmp)
        base, common = _record(tmp, proj)
        _raise_baseline_levels(base)  # the diagram "used to" score higher
        for cwd, paths, baseline in (
            (proj, str(proj / "diagrams"), "maturity.json"),  # absolute
            (proj / "diagrams", ".", "../maturity.json"),  # from inside the tree
            (Path(tmp), "proj/diagrams", "proj/maturity.json"),  # from the parent
            (proj, "./diagrams/", "maturity.json"),  # the always-safe spelling
        ):
            rc, err = _run_from(cwd, ["score", paths, "--baseline", baseline, *common])
            assert rc == 1, (cwd, paths, err)
            assert "regression:" in err and "warning" not in err, (cwd, paths, err)


def test_ratchet_survives_the_tree_moving():
    # Recorded on one machine, compared on another: the whole tree moves and
    # the baseline moves with it.
    with tempfile.TemporaryDirectory() as tmp:
        proj = _project(tmp)
        base, common = _record(tmp, proj)
        _raise_baseline_levels(base)
        moved = Path(tmp) / "elsewhere" / "checkout"
        shutil.copytree(proj, moved)
        rc, err = _run_from(
            moved, ["score", "diagrams", "--baseline", "maturity.json", *common]
        )
        assert rc == 1 and "regression:" in err, err


def test_version_1_baseline_still_ratchets_and_is_upgraded():
    with tempfile.TemporaryDirectory() as tmp:
        proj = _project(tmp)
        common = ["-c", str(proj / "cfg.json"), "-o", str(Path(tmp) / "r.txt")]
        base = proj / "maturity.json"
        level = _expected_level(proj / "diagrams" / "a.puml")
        base.write_text(
            json.dumps(
                {
                    "version": 1,
                    "diagrams": {
                        "diagrams/a.puml::Order": {"level": level + 1, "composite": 0}
                    },
                }
            ),
            encoding="utf-8",
        )
        # Recorded the canonical way, so its keys already are the anchored
        # ones: it ratchets under the absolute spelling too, before any
        # rewrite — and says how to upgrade.
        for paths in ("diagrams", str(proj / "diagrams")):
            rc, err = _run_from(
                proj, ["score", paths, "--baseline", "maturity.json", *common]
            )
            assert rc == 1 and "regression:" in err, (paths, err)
            assert "version 1" in err and "--update-baseline" in err, err
        rc, err = _run_from(
            proj,
            ["score", "diagrams", "--baseline", "maturity.json", "--update-baseline", *common],
        )
        assert rc == 0 and "baseline: updated" in err, err
        data = json.loads(base.read_text(encoding="utf-8"))
        assert data["version"] == 2, data
        assert list(data["diagrams"]) == ["diagrams/a.puml::Order"], data
        rc, err = _run_from(
            proj, ["score", "diagrams", "--baseline", "maturity.json", *common]
        )
        assert rc == 0 and err == "", err


def test_moved_baseline_warns_that_nothing_matched():
    with tempfile.TemporaryDirectory() as tmp:
        proj = _project(tmp)
        base, common = _record(tmp, proj)
        _raise_baseline_levels(base)
        (proj / "sub").mkdir()
        shutil.move(str(base), str(proj / "sub" / "maturity.json"))
        rc, err = _run_from(
            proj, ["score", "diagrams", "--baseline", "sub/maturity.json", *common]
        )
        assert rc == 0, err  # nothing matched, so nothing could regress
        assert "has been moved" in err, err


# --- update merges by file (2026-09-04) ---------------------------------------
#
# --update-baseline replaces the entries of every file the run scored and
# keeps the entries of files it did not score while they exist: a one-file
# or staged-list update no longer shrinks the baseline to the run.

_ALL = ["diagrams/a.puml::Order", "diagrams/b.puml::Ship", "diagrams/c.puml::Bill"]


def _three_file_project(tmp: str) -> Path:
    proj = Path(tmp) / "proj"
    (proj / "diagrams").mkdir(parents=True)
    for stem, name in (("a", "Order"), ("b", "Ship"), ("c", "Bill")):
        (proj / "diagrams" / f"{stem}.puml").write_text(
            _SRC.replace("Order", name), encoding="utf-8"
        )
    (proj / "cfg.json").write_text("{}", encoding="utf-8")
    return proj


def _record_all(tmp: str, proj: Path) -> tuple[Path, list[str]]:
    common = ["-c", str(proj / "cfg.json"), "-o", str(Path(tmp) / "r.txt")]
    rc, err = _run_from(
        proj, ["score", "diagrams", "--baseline", "maturity.json", *common]
    )
    assert rc == 0 and "baseline: recorded 3 diagram" in err, err
    base = proj / "maturity.json"
    assert list(json.loads(base.read_text(encoding="utf-8"))["diagrams"]) == _ALL
    return base, common


def _stored(base: Path) -> dict:
    return json.loads(base.read_text(encoding="utf-8"))["diagrams"]


def test_update_from_one_file_keeps_the_rest():
    with tempfile.TemporaryDirectory() as tmp:
        proj = _three_file_project(tmp)
        base, common = _record_all(tmp, proj)
        _raise_baseline_levels(base)  # every diagram "used to" score higher
        rc, err = _run_from(
            proj,
            ["score", "diagrams/b.puml", "--baseline", "maturity.json", "--update-baseline", *common],
        )
        assert rc == 0, err
        assert "baseline: updated 1 diagram level(s)" in err, err
        assert "2 kept for files not scored this run" in err and "dropped" not in err, err
        data = _stored(base)
        assert list(data) == _ALL, list(data)  # order intact
        level = _expected_level(proj / "diagrams" / "b.puml")
        assert data[_ALL[1]]["level"] == level, data  # refreshed
        assert data[_ALL[0]]["level"] == level + 1 and data[_ALL[2]]["level"] == level + 1, data
        # the rest still ratchet: a full run names the two untouched files only
        rc, err = _run_from(proj, ["score", "diagrams", "--baseline", "maturity.json", *common])
        assert rc == 1, err
        assert "diagrams/a.puml::Order" in err and "diagrams/c.puml::Bill" in err, err
        assert "b.puml" not in err, err


def test_update_drops_entries_of_deleted_files():
    with tempfile.TemporaryDirectory() as tmp:
        proj = _three_file_project(tmp)
        base, common = _record_all(tmp, proj)
        (proj / "diagrams" / "c.puml").unlink()
        rc, err = _run_from(
            proj, ["score", "diagrams", "--baseline", "maturity.json", "--update-baseline", *common]
        )
        assert rc == 0, err
        assert "1 dropped for files not found relative to maturity.json" in err, err
        assert "kept" not in err, err
        assert list(_stored(base)) == _ALL[:2]
        rc, err = _run_from(proj, ["score", "diagrams", "--baseline", "maturity.json", *common])
        assert rc == 0 and err == "", err


def test_update_from_the_staged_list_keeps_the_unstaged_file():
    # pre-commit hands the score hook the staged files only
    with tempfile.TemporaryDirectory() as tmp:
        proj = _three_file_project(tmp)
        base, common = _record_all(tmp, proj)
        rc, err = _run_from(
            proj,
            ["score", "diagrams/a.puml", "diagrams/b.puml", "--baseline", "maturity.json",
             "--update-baseline", *common],
        )
        assert rc == 0, err
        assert "baseline: updated 2 diagram level(s)" in err and "1 kept" in err, err
        assert list(_stored(base)) == _ALL


def test_update_baseline_on_a_missing_file_says_recorded():
    with tempfile.TemporaryDirectory() as tmp:
        puml, cfg = _fixture(tmp)
        out = Path(tmp) / "r.txt"
        base = Path(tmp) / "maturity.json"
        rc, err = _main_quiet(
            ["score", str(puml), "-c", str(cfg), "--baseline", str(base),
             "--update-baseline", "-o", str(out)]
        )
        assert rc == 0, err
        assert "baseline: recorded 1 diagram" in err and "updated" not in err, err
        assert base.exists()


def test_version_1_update_from_one_file_keeps_canonical_entries():
    with tempfile.TemporaryDirectory() as tmp:
        proj = _three_file_project(tmp)
        common = ["-c", str(proj / "cfg.json"), "-o", str(Path(tmp) / "r.txt")]
        base = proj / "maturity.json"
        level = _expected_level(proj / "diagrams" / "a.puml")
        base.write_text(
            json.dumps(
                {
                    "version": 1,
                    "diagrams": {
                        _ALL[0]: {"level": level, "composite": 0},
                        _ALL[1]: {"level": level, "composite": 0},
                    },
                }
            ),
            encoding="utf-8",
        )
        rc, err = _run_from(
            proj,
            ["score", "diagrams/a.puml", "--baseline", "maturity.json", "--update-baseline", *common],
        )
        assert rc == 0 and "1 kept" in err, err
        data = json.loads(base.read_text(encoding="utf-8"))
        assert data["version"] == 2 and list(data["diagrams"]) == _ALL[:2], data


def test_ratchet_keeps_a_hash_name_apart_from_a_duplicate():
    # `Dup`, `Dup`, `Dup#1` in one file used to record two entries for three
    # diagrams (the second Dup and the diagram named Dup#1 shared a key):
    # the next run showed a phantom regression, and a real one on the
    # second Dup was masked.
    good = "title T\nparticipant Alice\nparticipant Bob\nAlice -> Bob : hi\n"
    trio = (
        f"@startuml Dup\n{good}@enduml\n"
        "@startuml Dup\nCarol -> Dave\n@enduml\n"
        f"@startuml Dup#1\n{good}@enduml\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp) / "proj"
        (proj / "diagrams").mkdir(parents=True)
        puml = proj / "diagrams" / "f.puml"
        puml.write_text(trio, encoding="utf-8")
        (proj / "cfg.json").write_text("{}", encoding="utf-8")
        argv = [
            "score", "diagrams", "--baseline", "maturity.json",
            "-c", str(proj / "cfg.json"), "-o", str(Path(tmp) / "r.txt"),
        ]
        rc, err = _run_from(proj, argv)
        assert rc == 0 and "recorded 3 diagram" in err, err
        data = json.loads((proj / "maturity.json").read_text(encoding="utf-8"))
        assert list(data["diagrams"]) == [
            "diagrams/f.puml::Dup",
            "diagrams/f.puml::Dup#1",
            "diagrams/f.puml::Dup##1",
        ], data
        rc, err = _run_from(proj, argv)
        assert rc == 0 and err == "", err  # idempotent: no phantom regression
        puml.write_text(trio.replace("Carol -> Dave\n", ""), encoding="utf-8")
        rc, err = _run_from(proj, argv)
        assert rc == 1, err
        assert "regression:" in err and "::Dup#1:" in err, err  # the second Dup
        assert "Dup##1" not in err, err  # the diagram named Dup#1 did not move


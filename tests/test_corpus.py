"""Corpus generator + calibration harness tests (Phase 10a/10b).

Plain assert functions so the zero-dependency runner exercises them too. The
corpus is generated into a temp dir per run — the committed/working corpus/
directory is never touched.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import calibrate  # noqa: E402
import gen_corpus  # noqa: E402

from pumllint import parse_file  # noqa: E402


def _generate(tmp: str):
    dest = Path(tmp) / "corpus"
    manifest = gen_corpus.generate(dest)
    return dest, manifest


def test_generator_is_deterministic():
    with tempfile.TemporaryDirectory() as tmp:
        d1, m1 = _generate(tmp + "/a")
        d2, m2 = _generate(tmp + "/b")
        assert m1 == m2
        files1 = sorted(p.relative_to(d1) for p in d1.rglob("*.puml"))
        files2 = sorted(p.relative_to(d2) for p in d2.rglob("*.puml"))
        assert files1 == files2
        for rel in files1:
            assert (d1 / rel).read_bytes() == (d2 / rel).read_bytes(), rel


def test_every_corpus_unit_parses_and_differs_from_parent():
    with tempfile.TemporaryDirectory() as tmp:
        dest, manifest = _generate(tmp)
        assert len(manifest["units"]) >= 40
        for unit in manifest["units"]:
            path = calibrate._resolve(unit["file"], dest)
            diagrams = parse_file(path)
            assert diagrams, f"{unit['file']} produced no diagrams"
            if unit["tier"] == "mutation":
                parent = calibrate._resolve(unit["parent"], dest)
                assert path.read_text() != parent.read_text(), \
                    f"{unit['file']} is identical to its parent"


def test_default_config_has_no_monotonicity_violations():
    # The Phase 10 exit criterion: a degraded diagram never outscores its
    # parent under the shipped default configuration.
    with tempfile.TemporaryDirectory() as tmp:
        dest, _ = _generate(tmp)
        result = calibrate.evaluate(dest, {})
        assert result["monotonicity_violations"] == []


def test_synthetic_probes_land_on_expected_levels():
    with tempfile.TemporaryDirectory() as tmp:
        dest, _ = _generate(tmp)
        result = calibrate.evaluate(dest, {})
        assert result["expected_level_misses"] == []


def test_example_pairs_discriminate_under_defaults():
    with tempfile.TemporaryDirectory() as tmp:
        dest, _ = _generate(tmp)
        result = calibrate.evaluate(dest, {})
        for pair in result["pairs"]:
            assert pair["ordered"], pair
            assert pair["composite_gap"] >= 10, pair


def test_parser_tolerates_utf8_bom():
    # Regression: wild-harvested files may carry a BOM before @startuml
    # (found by corpus/wild — cloudinnng/PluginHub UML.puml).
    from pumllint import parse_source

    src = "\ufeff@startuml X\nparticipant A\nA -> A : x()\n@enduml\n"
    diagrams = parse_source(src, "bom.puml")
    assert len(diagrams) == 1
    assert diagrams[0].name == "X"


def test_sweep_runs_all_param_sets():
    with tempfile.TemporaryDirectory() as tmp:
        dest, _ = _generate(tmp)
        results = calibrate.run_sweep(
            dest, {"default": {}, "K75": {"k": 75}}
        )
        assert set(results) == {"default", "K75"}
        for r in results.values():
            assert r["units"] >= 40
            assert r["volatility"]  # at least one populated bucket
        report = calibrate.render_report(results)
        assert "default" in report and "K75" in report

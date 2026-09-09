"""Requirement-traceability tests (Arc G). Plain assert functions so the
zero-dependency runner exercises them too; YAML-inventory checks run only
when PyYAML happens to be installed.
"""

import contextlib
import io
import json
import re
import tempfile
from pathlib import Path

from pumllint.cli import main
from pumllint.parser import parse_source
from pumllint.reporters import get_reporter
from pumllint.schema import load_schema, validate
from pumllint.trace import (
    build_matrix,
    compile_pattern,
    diagram_references,
    load_inventory,
    pattern_from_config,
    scan_inventory,
)

_PATTERN = re.compile(r"REQ-\d+|ADR-\d+")

# Carriers: title carries REQ-1, a note carries REQ-2, the @startuml name
# carries REQ-3. The message label's REQ-9 must NOT count (GEN007 parity).
_LINKED = (
    "@startuml checkout-REQ-3\n"
    "title Checkout — REQ-1\n"
    "participant A\n"
    "participant B\n"
    "A -> B : pay(REQ-9)\n"
    "note over A : realizes REQ-2 and REQ-1\n"
    "@enduml\n"
)
_UNLINKED = "@startuml sketch\ntitle Just a sketch\nA -> B : hi\n@enduml\n"


def _diagrams(src: str, path: str = "d.puml"):
    return parse_source(src, path)


# --- reference extraction ----------------------------------------------------

def test_references_come_from_gen007_carriers_only():
    d = _diagrams(_LINKED)[0]
    refs = diagram_references(d, _PATTERN)
    assert set(refs) == {"REQ-1", "REQ-2", "REQ-3"}, refs
    assert "REQ-9" not in refs  # message labels are not carriers, same as GEN007


def test_reference_line_is_first_carrying_text():
    d = _diagrams(_LINKED)[0]
    refs = diagram_references(d, _PATTERN)
    assert refs["REQ-1"] == 2  # title line, not the later note
    assert refs["REQ-2"] == 6  # the note
    assert refs["REQ-3"] == 1  # @startuml name -> start line


# --- the matrix ---------------------------------------------------------------

def test_matrix_reports_all_three_directions():
    diagrams = _diagrams(_LINKED, "linked.puml") + _diagrams(_UNLINKED, "sketch.puml")
    result = build_matrix(diagrams, ["REQ-1", "REQ-4"], _PATTERN)
    by_id = {r.id: r for r in result.requirements}
    assert by_id["REQ-1"].covered and by_id["REQ-1"].covered_by[0].file == "linked.puml"
    assert not by_id["REQ-4"].covered
    assert [r.id for r in result.uncovered] == ["REQ-4"]
    assert {u.id for u in result.unknown_references} == {"REQ-2", "REQ-3"}
    assert [d.file for d in result.unlinked_diagrams] == ["sketch.puml"]
    assert result.diagram_count == 2


def test_matrix_preserves_inventory_order():
    result = build_matrix([], ["REQ-9", "REQ-1", "REQ-5"], _PATTERN)
    assert [r.id for r in result.requirements] == ["REQ-9", "REQ-1", "REQ-5"]


# --- inventory loading ---------------------------------------------------------

def test_text_inventory_skips_comments_blanks_and_dupes():
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "reqs.txt"
        f.write_text("# heading\nREQ-1\n\nREQ-2\nREQ-1\n", encoding="utf-8")
        assert load_inventory(f) == ["REQ-1", "REQ-2"]


def test_json_inventory_accepts_strings_objects_and_wrapper():
    with tempfile.TemporaryDirectory() as td:
        plain = Path(td) / "a.json"
        plain.write_text('["REQ-1", "REQ-2"]', encoding="utf-8")
        assert load_inventory(plain) == ["REQ-1", "REQ-2"]

        objects = Path(td) / "b.json"
        objects.write_text(
            '[{"id": "REQ-1", "title": "extra columns ride along"}, "REQ-2"]',
            encoding="utf-8",
        )
        assert load_inventory(objects) == ["REQ-1", "REQ-2"]

        wrapped = Path(td) / "c.json"
        wrapped.write_text('{"requirements": [{"id": "REQ-7"}]}', encoding="utf-8")
        assert load_inventory(wrapped) == ["REQ-7"]


def test_json_inventory_rejects_unusable_entries():
    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "bad.json"
        bad.write_text('[{"name": "no id key"}]', encoding="utf-8")
        try:
            load_inventory(bad)
        except ValueError as e:
            assert "entry 0" in str(e)
        else:
            raise AssertionError("expected ValueError for entry without an id")


def test_yaml_inventory_when_pyyaml_is_available():
    try:
        import yaml  # noqa: F401
    except ImportError:
        return  # optional dependency; the zero-dependency runner skips this
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "reqs.yaml"
        f.write_text("requirements:\n  - id: REQ-1\n  - REQ-2\n", encoding="utf-8")
        assert load_inventory(f) == ["REQ-1", "REQ-2"]


def test_scan_inventory_walks_docs_in_first_seen_order():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.md").write_text("REQ-2 then REQ-1 then REQ-2", encoding="utf-8")
        (root / "b.txt").write_text("ADR-7", encoding="utf-8")
        (root / "c.py").write_text("REQ-99  # wrong suffix, never scanned", encoding="utf-8")
        assert scan_inventory(root, _PATTERN) == ["REQ-2", "REQ-1", "ADR-7"]


def test_scan_inventory_matches_ids_carried_in_the_filename():
    # ADR/requirement schemes commonly put the ID in the filename and a plain
    # human title in the body (adr-tools, MADR). Scanning only the body finds
    # nothing at all for them, so the matrix reports every correct reference
    # as unknown.
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "ADR-0007-use-plantuml.md").write_text(
            "# Use PlantUML for design diagrams\n\n## Status\nAccepted\n",
            encoding="utf-8",
        )
        assert scan_inventory(root, re.compile(r"ADR-\d+")) == ["ADR-0007"]


def test_scan_inventory_name_precedes_body_and_dedupes_across_both():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # The file's own ID is in its name; it cites another in its body, and
        # repeats its own — first-seen order, deduped across both sources.
        (root / "REQ-1-latency.md").write_text("supersedes REQ-2, see REQ-1", encoding="utf-8")
        assert scan_inventory(root, _PATTERN) == ["REQ-1", "REQ-2"]


def test_scan_inventory_name_matching_respects_the_suffix_filter():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "REQ-9-helper.py").write_text("nothing here", encoding="utf-8")
        (root / "notes.md").write_text("REQ-1", encoding="utf-8")
        # The .py file is never walked, so its name is never scanned either.
        assert scan_inventory(root, _PATTERN) == ["REQ-1"]


def test_scan_inventory_group_patterns_use_whole_match():
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "reqs.md"
        f.write_text("REQ-12", encoding="utf-8")
        # A pattern with groups must still yield the whole match, not group 1.
        assert scan_inventory(f, re.compile(r"(REQ)-(\d+)")) == ["REQ-12"]


# --- pattern resolution ---------------------------------------------------------

def test_pattern_from_config_reads_gen007_by_id_or_name():
    assert pattern_from_config({"rules": {"GEN007": {"pattern": "REQ-\\d+"}}}) == "REQ-\\d+"
    assert (
        pattern_from_config({"rules": {"requirement-link": {"pattern": "ADR-\\d+"}}})
        == "ADR-\\d+"
    )
    assert pattern_from_config({"rules": {"requirement-link": False}}) is None
    assert pattern_from_config({}) is None


def test_compile_pattern_reports_malformed_regex_cleanly():
    try:
        compile_pattern("(", "--pattern")
    except ValueError as e:
        assert "--pattern" in str(e)
    else:
        raise AssertionError("expected ValueError for malformed regex")


# --- CLI ------------------------------------------------------------------------

def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def _workspace(td: Path):
    (td / "linked.puml").write_text(_LINKED, encoding="utf-8")
    (td / "sketch.puml").write_text(_UNLINKED, encoding="utf-8")
    reqs = td / "reqs.txt"
    reqs.write_text("REQ-1\nREQ-4\n", encoding="utf-8")
    return reqs


def test_cli_trace_text_report_and_clean_exit():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        reqs = _workspace(td)
        code, out, _ = _run(
            ["trace", str(td), "--requirements", str(reqs), "--pattern", r"REQ-\d+"]
        )
        assert code == 0  # no gates requested -> report-only
        assert "1/2 covered" in out
        assert "REQ-4  ✖ uncovered" in out
        assert "Unknown references" in out and "REQ-2" in out
        assert "Unlinked diagrams" in out and "sketch.puml" in out


def test_cli_trace_gates_trip_exit_1():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        reqs = _workspace(td)
        base = ["trace", str(td), "--requirements", str(reqs), "--pattern", r"REQ-\d+"]
        assert _run(base + ["--fail-on-uncovered"])[0] == 1
        assert _run(base + ["--fail-on-unlinked"])[0] == 1
        assert _run(base + ["--fail-on-unknown-ref"])[0] == 1
        # A covered-and-linked-only workspace passes all gates.
        (td / "sketch.puml").unlink()
        reqs.write_text("REQ-1\nREQ-2\nREQ-3\n", encoding="utf-8")
        code, _, _ = _run(
            base
            + ["--fail-on-uncovered", "--fail-on-unlinked", "--fail-on-unknown-ref"]
        )
        assert code == 0


def test_cli_trace_json_validates_against_shipped_schema():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        reqs = _workspace(td)
        code, out, _ = _run(
            [
                "trace", str(td),
                "--requirements", str(reqs),
                "--pattern", r"REQ-\d+",
                "-f", "json",
            ]
        )
        assert code == 0
        payload = json.loads(out)
        assert validate(payload, load_schema("trace")) == []
        assert payload["summary"] == {
            "requirementCount": 2,
            "coveredCount": 1,
            "uncoveredCount": 1,
            "unknownReferenceCount": 2,
            "unlinkedDiagramCount": 1,
            "diagramCount": 2,
        }


def test_cli_trace_is_deterministic():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        reqs = _workspace(td)
        argv = ["trace", str(td), "--requirements", str(reqs), "--pattern", r"REQ-\d+"]
        assert _run(argv)[1] == _run(argv)[1]


def test_cli_trace_usage_errors_exit_2():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        reqs = _workspace(td)
        # no paths
        assert _run(["trace", "--requirements", str(reqs), "--pattern", "R"])[0] == 2
        # no inventory source
        assert _run(["trace", str(td), "--pattern", "R"])[0] == 2
        # no pattern anywhere — isolate from the repo's own auto-detected
        # config, which (dogfooding GEN007) supplies one
        empty_cfg = td / "empty.json"
        empty_cfg.write_text("{}", encoding="utf-8")
        code, _, err = _run(
            ["trace", str(td), "--requirements", str(reqs), "-c", str(empty_cfg)]
        )
        assert code == 2 and "requirement-ID pattern" in err
        # malformed pattern is a clean config error, not a traceback
        code, _, err = _run(
            ["trace", str(td), "--requirements", str(reqs), "--pattern", "("]
        )
        assert code == 2 and "not a valid regex" in err
        # missing inventory file
        code, _, err = _run(
            ["trace", str(td), "--requirements", str(td / "nope.txt"), "--pattern", "R"]
        )
        assert code == 2


def test_cli_trace_pattern_falls_back_to_gen007_config():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        reqs = _workspace(td)
        cfg = td / "pumllint.json"
        cfg.write_text(
            json.dumps({"rules": {"requirement-link": {"pattern": "REQ-\\d+"}}}),
            encoding="utf-8",
        )
        code, out, _ = _run(
            ["trace", str(td), "--requirements", str(reqs), "-c", str(cfg)]
        )
        assert code == 0 and "1/2 covered" in out


def test_cli_trace_scan_and_list_union():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        reqs = _workspace(td)
        docs = td / "docs"
        docs.mkdir()
        (docs / "spec.md").write_text("REQ-2 is specified here", encoding="utf-8")
        code, out, _ = _run(
            [
                "trace", str(td / "linked.puml"),
                "--requirements", str(reqs),
                "--requirements-scan", str(docs),
                "--pattern", r"REQ-\d+",
            ]
        )
        assert code == 0
        # Union: REQ-1/REQ-4 from the list, REQ-2 discovered by the scan —
        # so REQ-2 is covered inventory now, and only REQ-3 stays unknown.
        assert "2/3 covered" in out
        assert "REQ-3" in out and "Unknown references" in out


def test_unsupported_format_is_a_clean_error():
    # badge has no render_trace(), so -f badge is rejected by argparse's
    # choices at parse time instead of failing at render time.
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        reqs = _workspace(td)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            try:
                main(
                    [
                        "trace", str(td),
                        "--requirements", str(reqs),
                        "--pattern", r"REQ-\d+",
                        "-f", "badge",
                    ]
                )
            except SystemExit as e:
                assert e.code == 2
            else:
                raise AssertionError("trace accepted -f badge")
        assert "invalid choice: 'badge'" in err.getvalue()


def test_render_trace_empty_inventory_and_no_diagrams():
    result = build_matrix([], [], _PATTERN)
    text = get_reporter("text").render_trace(result)
    assert "0/0 covered" in text
    payload = json.loads(get_reporter("json").render_trace(result))
    assert validate(payload, load_schema("trace")) == []
    assert payload["summary"]["diagramCount"] == 0


def test_text_inventory_strips_inline_comments():
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "reqs.txt"
        f.write_text("ARC-D7  # the data layer\nARC-D8\n", encoding="utf-8")
        assert load_inventory(f) == ["ARC-D7", "ARC-D8"]


def test_text_inventory_keeps_hash_embedded_in_an_id():
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "reqs.txt"
        f.write_text("REQ#5\nREQ-6 # note\n", encoding="utf-8")
        assert load_inventory(f) == ["REQ#5", "REQ-6"]


def test_text_inventory_warns_once_per_whitespace_id():
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "reqs.txt"
        f.write_text("ARC D7\nARC-D8\n", encoding="utf-8")
        warnings = []
        ids = load_inventory(f, on_warning=warnings.append)
        assert ids == ["ARC D7", "ARC-D8"]  # kept verbatim, not dropped
        assert len(warnings) == 1 and "ARC D7" in warnings[0]
        assert load_inventory(f) == ids  # silent without the callback


def test_cli_trace_warns_when_the_inventory_is_empty_without_changing_exit():
    # A scan that matches nothing is otherwise indistinguishable from a stale
    # inventory: every correct reference is reported as unknown, which reads as
    # an accusation against the diagram. Same contract as the lint path's
    # "nothing was checked" — stderr, exit code unmoved.
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        docs = td / "adr"
        docs.mkdir()
        # MADR shape: the ID is '0001', so a pattern written for the prose form
        # genuinely does not describe this inventory.
        (docs / "0001-use-plantuml.md").write_text(
            "# Use PlantUML\n", encoding="utf-8"
        )
        puml = td / "d.puml"
        puml.write_text(
            "@startuml d\ntitle Realizes ADR-0001\nA -> B : go()\n@enduml\n",
            encoding="utf-8",
        )
        code, _, err = _run(
            ["trace", str(puml), "--requirements-scan", str(docs), "--pattern", r"ADR-\d+"]
        )
        assert code == 0
        assert "warning:" in err and "inventory is empty" in err
        # It must name the source and the pattern, and say what was lost.
        assert "--requirements-scan" in err
        assert "1 diagram reference(s) were compared against nothing" in err


def test_cli_trace_no_empty_warning_when_the_inventory_has_ids():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        docs = td / "adr"
        docs.mkdir()
        (docs / "ADR-0001-use-plantuml.md").write_text("# Use PlantUML\n", encoding="utf-8")
        puml = td / "d.puml"
        puml.write_text(
            "@startuml d\ntitle Realizes ADR-0001\nA -> B : go()\n@enduml\n",
            encoding="utf-8",
        )
        code, out, err = _run(
            ["trace", str(puml), "--requirements-scan", str(docs), "--pattern", r"ADR-\d+"]
        )
        # The filename carried the ID, so the reference resolves and the gate holds.
        assert code == 0
        assert "1/1 covered" in out
        assert "inventory is empty" not in err


def test_cli_trace_filename_ids_satisfy_the_unknown_ref_gate():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        docs = td / "adr"
        docs.mkdir()
        (docs / "ADR-0001-use-plantuml.md").write_text("# Use PlantUML\n", encoding="utf-8")
        puml = td / "d.puml"
        puml.write_text(
            "@startuml d\ntitle Realizes ADR-0001\nA -> B : go()\n@enduml\n",
            encoding="utf-8",
        )
        code, _, _ = _run(
            [
                "trace", str(puml),
                "--requirements-scan", str(docs),
                "--pattern", r"ADR-\d+",
                "--fail-on-unknown-ref",
            ]
        )
        # Previously exit 1: the inventory was empty, so a correct reference
        # counted as unknown and broke the build.
        assert code == 0


def test_cli_trace_whitespace_id_warns_on_stderr_without_changing_exit():
    with tempfile.TemporaryDirectory() as td:
        reqs = Path(td) / "reqs.txt"
        reqs.write_text("REQ 1\nREQ-2\n", encoding="utf-8")
        puml = Path(td) / "d.puml"
        puml.write_text(
            "@startuml d\ntitle Covers REQ-2\nA -> B : go()\n@enduml\n",
            encoding="utf-8",
        )
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = main(
                [
                    "trace",
                    str(puml),
                    "--requirements",
                    str(reqs),
                    "--pattern",
                    r"REQ-\d+",
                ]
            )
        assert code == 0
        assert "warning:" in err.getvalue() and "REQ 1" in err.getvalue()


# --- the verification side (feature files) -----------------------------------

from pumllint.trace import (  # noqa: E402  (grouped with the tests they serve)
    FeatureFile,
    feature_name,
    feature_references,
    scan_features,
)

_ORDER_FEATURE = (
    "@REQ-1 @smoke\n"
    "Feature: Order placement\n"
    "  Scenario: happy path\n"
    "    Given REQ-1 applies again\n"
)


def test_feature_references_match_name_then_text_first_line_wins():
    refs = feature_references(_ORDER_FEATURE, "REQ-3.feature", _PATTERN)
    assert refs == {"REQ-3": 0, "REQ-1": 1}, refs  # file name is line 0; the tag, not the step


def test_feature_name_reads_the_first_heading_or_none():
    assert feature_name(_ORDER_FEATURE) == "Order placement"
    assert feature_name("Feature:   spaced   \nFeature: second\n") == "spaced"
    assert feature_name("# no heading\n") is None


def test_scan_features_walks_feature_suffix_only_and_explicit_file_regardless():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "b.feature").write_text("Feature: B\n  Scenario: REQ-2\n", encoding="utf-8")
        (td / "sub").mkdir()
        (td / "sub" / "a.feature").write_text("Feature: A\n", encoding="utf-8")
        (td / "notes.md").write_text("REQ-9 is not a feature file\n", encoding="utf-8")
        files = scan_features(td, _PATTERN)
        assert [f.file.rsplit("/", 1)[-1] for f in files] == ["b.feature", "a.feature"]  # sorted walk
        assert files[0].name == "B" and files[0].references == {"REQ-2": 2}
        assert files[1].references == {}  # unlinked
        assert "\\" not in files[0].file  # forward slashes, every platform
        explicit = scan_features(td / "notes.md", _PATTERN)
        assert explicit[0].references == {"REQ-9": 1}  # explicit file: suffix not filtered
        try:
            scan_features(td / "nope", _PATTERN)
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("missing --features path must be an error")


def test_matrix_without_features_leaves_the_verification_side_unrun():
    result = build_matrix(_diagrams(_LINKED), ["REQ-1"], _PATTERN)
    assert result.feature_count is None and not result.verification_ran
    assert result.requirements[0].verified_by == () and not result.requirements[0].verified
    assert result.unknown_feature_references == [] and result.unlinked_features == []
    assert result.verified == [] and result.unverified == []
    payload = json.loads(get_reporter("json").render_trace(result))
    # The v1 shape, key for key: nothing appears until --features is given.
    assert set(payload) == {"requirements", "unknownReferences", "unlinkedDiagrams", "summary"}
    assert set(payload["requirements"][0]) == {"id", "covered", "coveredBy"}
    assert set(payload["summary"]) == {
        "requirementCount", "coveredCount", "uncoveredCount",
        "unknownReferenceCount", "unlinkedDiagramCount", "diagramCount",
    }


def test_matrix_with_features_reports_every_verification_direction():
    diagrams = _diagrams(_LINKED, "linked.puml")  # realizes REQ-1, REQ-2, REQ-3
    features = [
        FeatureFile("t/order.feature", "Order", {"REQ-1": 1}),
        FeatureFile("t/REQ-4.feature", "By name", {"REQ-4": 0}),  # tested, not modelled
        FeatureFile("t/pay.feature", "Pay", {"REQ-99": 3}),  # unknown
        FeatureFile("t/smoke.feature", None, {}),  # unlinked
    ]
    result = build_matrix(diagrams, ["REQ-1", "REQ-2", "REQ-4"], _PATTERN, features)
    assert result.feature_count == 4 and result.verification_ran
    by_id = {r.id: r for r in result.requirements}
    assert by_id["REQ-1"].verified and by_id["REQ-1"].verified_by[0].file == "t/order.feature"
    assert not by_id["REQ-2"].verified
    assert by_id["REQ-4"].verified and not by_id["REQ-4"].covered
    # The buckets measure the model: REQ-4 (unmodelled) is in neither.
    assert [r.id for r in result.verified] == ["REQ-1"]
    assert [r.id for r in result.unverified] == ["REQ-2"]
    assert [(u.id, u.cited_by[0].line) for u in result.unknown_feature_references] == [("REQ-99", 3)]
    assert [(f.file, f.name) for f in result.unlinked_features] == [("t/smoke.feature", None)]
    # Diagram-side lists are untouched by the feature side.
    assert {u.id for u in result.unknown_references} == {"REQ-3"}


def _feature_workspace(td: Path) -> Path:
    """The CLI workspace plus a features tree: REQ-1 tagged, REQ-4 tested
    but never modelled, REQ-77 a typo, one file linking nothing."""
    reqs = _workspace(td)
    feats = td / "features"
    (feats / "sub").mkdir(parents=True)
    (feats / "order.feature").write_text(_ORDER_FEATURE, encoding="utf-8")
    (feats / "sub" / "REQ-4.feature").write_text("Feature: Refund\n  Scenario: r\n", encoding="utf-8")
    (feats / "pay.feature").write_text("Feature: Pay\n  Scenario: REQ-77\n", encoding="utf-8")
    (feats / "smoke.feature").write_text("Feature: Smoke\n  Scenario: boots\n", encoding="utf-8")
    return reqs


def test_cli_trace_features_text_report():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        reqs = _feature_workspace(td)
        reqs.write_text("REQ-1\nREQ-2\nREQ-4\n", encoding="utf-8")
        code, out, err = _run(
            ["trace", str(td), "--requirements", str(reqs), "--pattern", r"REQ-\d+",
             "--features", str(td / "features")]
        )
        assert code == 0 and "warning" not in err
        assert "1/2 modelled requirement(s) referenced by a feature file" in out
        assert "1 unverified, 1 unknown feature reference(s), 1 unlinked feature file(s)" in out
        assert "across 4 feature file(s)" in out
        assert "REQ-1  ← " in out and "✔ " in out and "order.feature [Order placement]:1" in out
        assert "REQ-2  ← " in out and "✖ unverified" in out
        assert "REQ-4  ✖ uncovered (tested, not modelled: " in out
        assert "REQ-4.feature [Refund])" in out  # file-name site: no line printed
        assert "Unknown feature references" in out and "REQ-77" in out
        assert "Unlinked feature files" in out and "smoke.feature [Smoke]" in out


def test_cli_trace_features_json_validates_and_counts_add_up():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        reqs = _feature_workspace(td)
        reqs.write_text("REQ-1\nREQ-2\nREQ-4\n", encoding="utf-8")
        code, out, _ = _run(
            ["trace", str(td), "--requirements", str(reqs), "--pattern", r"REQ-\d+",
             "--features", str(td / "features"), "-f", "json"]
        )
        assert code == 0
        payload = json.loads(out)
        schema = load_schema("trace")
        assert validate(payload, schema) == []
        s = payload["summary"]
        assert s["featureCount"] == 4
        assert s["verifiedCount"] + s["unverifiedCount"] == s["coveredCount"] == 2
        assert s["unknownFeatureReferenceCount"] == 1 and s["unlinkedFeatureCount"] == 1
        rows = {r["id"]: r for r in payload["requirements"]}
        assert rows["REQ-1"]["verified"] and rows["REQ-1"]["verifiedBy"][0]["line"] == 1
        assert rows["REQ-4"]["verified"] and not rows["REQ-4"]["covered"]
        assert rows["REQ-4"]["verifiedBy"][0]["line"] == 0  # carried by the file name
        assert payload["unlinkedFeatures"] == [
            {"file": (td / "features" / "smoke.feature").as_posix(), "name": "Smoke"}
        ]
        # Schema teeth on the new shapes.
        extra = json.loads(out)
        extra["unlinkedFeatures"][0]["scenario"] = "not a column"
        assert any("scenario" in e for e in validate(extra, schema))
        extra = json.loads(out)
        extra["summary"]["verifiedCount"] = -1
        assert any("verifiedCount" in e for e in validate(extra, schema))


def test_cli_trace_unverified_gate():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        reqs = _feature_workspace(td)
        reqs.write_text("REQ-1\nREQ-2\n", encoding="utf-8")
        base = ["trace", str(td), "--requirements", str(reqs), "--pattern", r"REQ-\d+"]
        feats = ["--features", str(td / "features")]
        assert _run(base + feats + ["--fail-on-unverified"])[0] == 1  # REQ-2 modelled, untested
        (td / "features" / "refund.feature").write_text(
            "@REQ-2\nFeature: Refund\n", encoding="utf-8"
        )
        assert _run(base + feats + ["--fail-on-unverified"])[0] == 0
        # The gate without its input is a usage error, never a silent pass.
        code, _, err = _run(base + ["--fail-on-unverified"])
        assert code == 2 and "--features" in err
        # A missing features path is a config error, like a missing inventory.
        assert _run(base + ["--features", str(td / "nope")])[0] == 2


def test_cli_trace_warns_when_no_feature_references_an_id_without_changing_exit():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        reqs = _feature_workspace(td)
        base = ["trace", str(td), "--requirements", str(reqs), "--pattern", r"REQ-\d+"]
        code, out, err = _run(base + ["--features", str(td / "features" / "smoke.feature")])
        assert code == 0
        assert "warning: no feature file references an ID" in err and "1 file(s)" in err
        assert "0/1 modelled requirement(s)" in out
        # ... and the gate still trips on the merits, warning or not.
        code, _, err = _run(
            base + ["--features", str(td / "features" / "smoke.feature"), "--fail-on-unverified"]
        )
        assert code == 1 and "warning" in err
        # A tree with references draws no warning.
        _, _, err = _run(base + ["--features", str(td / "features")])
        assert "warning" not in err


def test_cli_trace_with_features_is_deterministic():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        reqs = _feature_workspace(td)
        argv = ["trace", str(td), "--requirements", str(reqs), "--pattern", r"REQ-\d+",
                "--features", str(td / "features"), "-f", "json"]
        assert _run(argv)[1] == _run(argv)[1]

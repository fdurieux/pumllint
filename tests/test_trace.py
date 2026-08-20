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

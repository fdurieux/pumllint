"""Baseline/ratchet tests (0.6.0; anchored keys 2026-09-04). Plain assert
functions so the zero-dependency runner exercises them too.
"""

import json
import os
import tempfile
from pathlib import Path

from pumllint.baseline import (
    BASELINE_VERSION,
    BaselineEntry,
    BaselineFile,
    anchored_keys,
    carry_over,
    compute_deltas,
    diagram_keys,
    find_regressions,
    load_baseline,
    resolve_baseline,
    write_baseline,
)
from pumllint.engine import Engine
from pumllint.parser import parse_source
from pumllint.scoring import score_groups

_TWO_NAMED = (
    "@startuml One\nAlice -> Bob : hi\n@enduml\n"
    "@startuml Two\nAlice -> Bob : hi\n@enduml\n"
)
_TWO_UNNAMED = (
    "@startuml\nAlice -> Bob : hi\n@enduml\n"
    "@startuml\nAlice -> Bob : hi\n@enduml\n"
)


def _score(src: str, path: str = "m.puml"):
    diagrams = parse_source(src, path)
    return score_groups(Engine({}).lint_diagrams_grouped(diagrams))


def test_named_diagrams_key_on_file_and_name():
    diagrams = parse_source(_TWO_NAMED, "m.puml")
    assert diagram_keys(diagrams) == ["m.puml::One", "m.puml::Two"]


def test_unnamed_diagrams_key_on_ordinal():
    diagrams = parse_source(_TWO_UNNAMED, "m.puml")
    assert diagram_keys(diagrams) == ["m.puml::#0", "m.puml::#1"]


def test_duplicate_names_stay_unique():
    src = (
        "@startuml Dup\nAlice -> Bob : hi\n@enduml\n"
        "@startuml Dup\nAlice -> Bob : hi\n@enduml\n"
    )
    keys = diagram_keys(parse_source(src, "m.puml"))
    assert keys[0] == "m.puml::Dup"
    assert keys[1] != keys[0]


def test_write_then_load_round_trips():
    with tempfile.TemporaryDirectory() as tmp:
        # The file's keys are relative to its own directory: parse from a
        # path beside it, so the stored key is the bare file name.
        results = _score(_TWO_NAMED, str(Path(tmp) / "m.puml"))
        p = Path(tmp) / "b.json"
        write_baseline(p, results)
        loaded = load_baseline(p)
        assert set(loaded) == {"m.puml::One", "m.puml::Two"}
        assert loaded.version == BASELINE_VERSION == 2
        assert loaded.anchor == Path(tmp).resolve()
        view = resolve_baseline(loaded, results)
        for key, (_, r) in zip(diagram_keys(d for d, _ in results), results):
            assert view[key].level == r.level


def test_regression_detected_only_on_drop():
    results = _score(_TWO_NAMED)
    keys = diagram_keys(d for d, _ in results)
    level = results[0][1].level
    baseline = {
        keys[0]: BaselineEntry(level=level + 1, composite=0.0),  # current is worse
        keys[1]: BaselineEntry(level=max(1, level - 1), composite=0.0),  # improved
    }
    regs = find_regressions(baseline, results)
    assert [r.key for r in regs] == [keys[0]]
    assert regs[0].baseline_level == level + 1
    assert regs[0].current_level == level


def test_new_diagrams_are_not_regressions():
    assert find_regressions({}, _score(_TWO_NAMED)) == []


def test_version_mismatch_is_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "b.json"
        p.write_text(json.dumps({"version": 99, "diagrams": {}}), encoding="utf-8")
        try:
            load_baseline(p)
        except ValueError as e:
            assert "version" in str(e)
        else:
            assert False, "expected ValueError for a version mismatch"


def test_invalid_json_is_a_value_error():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "b.json"
        p.write_text("{not json", encoding="utf-8")
        try:
            load_baseline(p)
        except ValueError:
            pass
        else:
            assert False, "expected ValueError for invalid JSON"


# --- trend/delta (0.7.0) ----------------------------------------------------

def test_compute_deltas_reports_movement_per_baselined_diagram():
    from pumllint.baseline import compute_deltas

    results = _score(_TWO_NAMED)
    keys = diagram_keys(d for d, _ in results)
    lvl0, lvl1 = results[0][1].level, results[1][1].level
    baseline = {
        keys[0]: BaselineEntry(level=lvl0 - 1, composite=0.0),  # improved
        keys[1]: BaselineEntry(level=lvl1, composite=0.0),      # unchanged
    }
    deltas = compute_deltas(baseline, results)
    assert set(deltas) == {keys[0], keys[1]}
    assert deltas[keys[0]].delta == 1
    assert deltas[keys[0]].baseline_level == lvl0 - 1
    assert deltas[keys[1]].delta == 0


def test_compute_deltas_skips_diagrams_new_since_baseline():
    from pumllint.baseline import compute_deltas

    results = _score(_TWO_NAMED)
    keys = diagram_keys(d for d, _ in results)
    baseline = {keys[0]: BaselineEntry(level=results[0][1].level + 1, composite=0.0)}
    deltas = compute_deltas(baseline, results)
    assert set(deltas) == {keys[0]}  # keys[1] is new -> no delta entry
    assert deltas[keys[0]].delta == -1  # regression shows as negative


# --- anchored keys (2026-09-04) ---------------------------------------------
#
# A baseline file keys on paths relative to its own directory, so one file has
# one key from any working directory and under any argv spelling; the run
# keeps keying on the path as given, and resolve_baseline is the one
# translation between the two.


def _cd(path) -> str:
    old = os.getcwd()
    os.chdir(path)
    return old


def test_anchored_keys_agree_across_spellings_and_cwds():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        (root / "diagrams").mkdir()
        (root / "sub").mkdir()
        target = root / "diagrams" / "a.puml"
        target.write_text(_TWO_NAMED, encoding="utf-8")
        want = ["diagrams/a.puml::One", "diagrams/a.puml::Two"]
        old = _cd(root)
        try:
            for spelling in (
                "diagrams/a.puml",
                "./diagrams/a.puml",
                "sub/../diagrams/a.puml",
                str(target),
            ):
                got = anchored_keys(parse_source(_TWO_NAMED, spelling), root)
                assert got == want, (spelling, got)
            os.chdir(root / "diagrams")
            for spelling in ("a.puml", "../diagrams/a.puml"):
                got = anchored_keys(parse_source(_TWO_NAMED, spelling), root)
                assert got == want, (spelling, got)
            # From a sibling directory the key climbs: the anchor is the
            # baseline's directory, wherever the diagram lives.
            assert anchored_keys(parse_source(_TWO_NAMED, "a.puml"), root / "sub") == [
                "../diagrams/a.puml::One",
                "../diagrams/a.puml::Two",
            ]
            assert anchored_keys(parse_source(_TWO_UNNAMED, "a.puml"), root) == [
                "diagrams/a.puml::#0",
                "diagrams/a.puml::#1",
            ]
        finally:
            os.chdir(old)


def test_relpath_without_an_answer_falls_back_to_the_resolved_path():
    # os.path.relpath raises ValueError across Windows drives; the key is then
    # the resolved absolute path — not portable, but not a traceback.
    real = os.path.relpath

    def no_answer(*args, **kwargs):
        raise ValueError("path is on mount 'D:', start on mount 'C:'")

    os.path.relpath = no_answer
    try:
        keys = anchored_keys(parse_source(_TWO_NAMED, "m.puml"), Path("."))
    finally:
        os.path.relpath = real
    resolved = Path("m.puml").resolve().as_posix()
    assert keys == [f"{resolved}::One", f"{resolved}::Two"], keys


def test_cross_drive_anchor_on_windows_falls_back():
    if os.name != "nt":
        return  # only Windows has drives
    here = Path.cwd().resolve().drive.upper()
    other = "Q:" if here != "Q:" else "Z:"
    keys = anchored_keys(parse_source(_TWO_NAMED, "m.puml"), Path(other + "/anchor"))
    resolved = Path("m.puml").resolve().as_posix()
    assert keys == [f"{resolved}::One", f"{resolved}::Two"], keys
    assert "\\" not in keys[0], keys


def test_version_1_file_recorded_the_canonical_way_matches_under_any_spelling():
    # Its keys are the recording run's spellings — which, recorded from the
    # file's own directory with relative paths, already are the anchored
    # form. So it ratchets under an absolute spelling before any rewrite.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        (root / "diagrams").mkdir()
        results = _score(_TWO_NAMED, str(root / "diagrams" / "a.puml"))
        level = results[0][1].level
        p = root / "maturity.json"
        p.write_text(
            json.dumps(
                {
                    "version": 1,
                    "diagrams": {
                        "diagrams/a.puml::One": {"level": level + 1, "composite": 0},
                        "diagrams/a.puml::Two": {"level": level, "composite": 0},
                    },
                }
            ),
            encoding="utf-8",
        )
        loaded = load_baseline(p)
        assert loaded.version == 1 and loaded.anchor == root
        regs = find_regressions(loaded, results)
        assert [r.key for r in regs] == [diagram_keys(d for d, _ in results)[0]], regs


def test_version_1_file_still_matches_its_own_spelling():
    # Recorded from elsewhere (keys are not the anchored form): the run that
    # repeats the recording spelling matches, as it always did; any other
    # spelling is new, as it always was.
    with tempfile.TemporaryDirectory() as tmp:
        results = _score(_TWO_NAMED, "../elsewhere/diagrams/a.puml")
        level = results[0][1].level
        p = Path(tmp) / "maturity.json"
        p.write_text(
            json.dumps(
                {
                    "version": 1,
                    "diagrams": {
                        "../elsewhere/diagrams/a.puml::One": {"level": level + 1},
                        "../elsewhere/diagrams/a.puml::Two": {"level": level},
                    },
                }
            ),
            encoding="utf-8",
        )
        loaded = load_baseline(p)
        regs = find_regressions(loaded, results)
        assert [r.key for r in regs] == ["../elsewhere/diagrams/a.puml::One"], regs
        assert find_regressions(loaded, _score(_TWO_NAMED, "other/a.puml")) == []


def test_resolve_baseline_rekeys_onto_run_keys_and_passes_plain_dicts_through():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        results = _score(_TWO_NAMED, str(root / "m.puml"))
        p = root / "b.json"
        write_baseline(p, results)
        loaded = load_baseline(p)
        run_keys = diagram_keys(d for d, _ in results)
        view = resolve_baseline(loaded, results)
        assert set(view) == set(run_keys), view
        assert type(view) is dict  # the view carries no anchor of its own
        assert resolve_baseline(view, results) is view  # idempotent
        plain = {"x": BaselineEntry(level=1, composite=0.0)}
        assert resolve_baseline(plain, results) is plain
        # entries for diagrams not in the run are dropped
        assert set(resolve_baseline(loaded, results[:1])) == {run_keys[0]}


def test_loaded_file_can_be_handed_straight_to_the_ratchet():
    # The public pattern load_baseline -> find_regressions keeps working on a
    # version-2 file: both ratchet functions translate for themselves.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        results = _score(_TWO_NAMED, str(root / "m.puml"))
        p = root / "b.json"
        write_baseline(p, results)
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["version"] == 2, data
        assert set(data["diagrams"]) == {"m.puml::One", "m.puml::Two"}, data
        data["diagrams"]["m.puml::One"]["level"] += 1
        p.write_text(json.dumps(data), encoding="utf-8")
        loaded = load_baseline(p)
        run_keys = diagram_keys(d for d, _ in results)
        assert [r.key for r in find_regressions(loaded, results)] == [run_keys[0]]
        assert set(compute_deltas(loaded, results)) == set(run_keys)


# --- update merges by file (2026-09-04) ---------------------------------------
#
# --update-baseline replaces the entries of every file the run scored and
# keeps the entries of files it did not score while they exist; carry_over is
# the rule, write_baseline(previous=...) applies it in the file's own order.


def _e(level: int) -> BaselineEntry:
    return BaselineEntry(level=level, composite=0.0)


def _two_files(root: Path) -> None:
    for name in ("a.puml", "b.puml"):
        (root / name).write_text(_TWO_NAMED, encoding="utf-8")


def _score_files(*files):
    diagrams = [d for src, p in files for d in parse_source(src, str(p))]
    return score_groups(Engine({}).lint_diagrams_grouped(diagrams))


def test_carry_over_keeps_unscored_files_and_drops_gone_ones():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        _two_files(root)
        results = _score(_TWO_NAMED, str(root / "a.puml"))  # a scored, b not
        previous = BaselineFile(
            {
                "a.puml::One": _e(4),
                "a.puml::Two": _e(4),
                "b.puml::One": _e(3),
                "b.puml::Two": _e(2),
                "gone.puml::One": _e(1),
            },
            version=2,
            anchor=root,
        )
        kept, dropped = carry_over(previous, results, root)
        assert list(kept) == ["b.puml::One", "b.puml::Two"], kept
        assert kept["b.puml::One"] == _e(3) and kept["b.puml::Two"] == _e(2)
        assert dropped == ["gone.puml::One"], dropped


def test_carry_over_replaces_a_scored_file_wholesale():
    # A diagram that vanished from a scored file goes with the file's old
    # entries: nothing is immortal.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        _two_files(root)
        results = _score(_TWO_NAMED, str(root / "a.puml"))
        previous = BaselineFile(
            {"a.puml::One": _e(5), "a.puml::Ghost": _e(5)}, version=2, anchor=root
        )
        assert carry_over(previous, results, root) == ({}, [])
        p = root / "b.json"
        write_baseline(p, results, previous=previous)
        assert set(load_baseline(p)) == {"a.puml::One", "a.puml::Two"}


def test_carry_over_supersedes_other_spellings_of_a_scored_file():
    # An entry for a scored file under another spelling — the absolute form a
    # cross-drive Windows run stores, a version-1 `sub/../a.puml` — resolves
    # to that file and is superseded, not kept beside the run's entry.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        _two_files(root)
        (root / "sub").mkdir()
        results = _score(_TWO_NAMED, str(root / "a.puml"))
        previous = BaselineFile(
            {
                f"{(root / 'a.puml').as_posix()}::One": _e(4),
                "sub/../a.puml::One": _e(4),
                "b.puml::One": _e(3),
            },
            version=1,
            anchor=root,
        )
        kept, dropped = carry_over(previous, results, root)
        assert list(kept) == ["b.puml::One"], kept
        assert dropped == [], dropped


def test_carry_over_reads_the_path_part_before_the_first_double_colon():
    # Names may contain `::`, `#` and spaces; the path part ends at the first
    # `::`, so the existence check sees `b.puml`, not `b.puml::Foo`.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        _two_files(root)
        results = _score(_TWO_NAMED, str(root / "a.puml"))
        previous = BaselineFile(
            {"b.puml::Foo::Bar": _e(3), "b.puml::#0": _e(3), "b.puml::Dup#1": _e(3)},
            version=2,
            anchor=root,
        )
        kept, dropped = carry_over(previous, results, root)
        assert list(kept) == list(previous) and dropped == [], (kept, dropped)


def test_carry_over_on_a_version_1_file():
    # Canonical keys are the anchored form and carry over; a key recorded
    # from another directory names no file beside the baseline and drops, as
    # a rewrite always dropped it.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        _two_files(root)
        results = _score(_TWO_NAMED, str(root / "a.puml"))
        previous = BaselineFile(
            {"b.puml::One": _e(3), "../elsewhere/b.puml::One": _e(3)},
            version=1,
            anchor=root,
        )
        kept, dropped = carry_over(previous, results, root)
        assert list(kept) == ["b.puml::One"], kept
        assert dropped == ["../elsewhere/b.puml::One"], dropped


def test_write_baseline_merges_in_the_files_own_order():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        _two_files(root)
        both = _score_files((_TWO_NAMED, root / "a.puml"), (_TWO_NAMED, root / "b.puml"))
        p = root / "b.json"
        assert write_baseline(p, both) == ({}, [])  # without previous: the run, exactly
        data = json.loads(p.read_text(encoding="utf-8"))
        for entry in data["diagrams"].values():
            entry["level"] += 1
        p.write_text(json.dumps(data), encoding="utf-8")
        previous = load_baseline(p)
        level = both[0][1].level
        kept, dropped = write_baseline(
            p, _score(_TWO_NAMED, str(root / "b.puml")), previous=previous
        )
        assert set(kept) == {"a.puml::One", "a.puml::Two"} and dropped == [], (kept, dropped)
        updated = load_baseline(p)
        assert updated.version == 2
        assert list(updated) == list(previous), (list(updated), list(previous))
        assert updated["b.puml::One"].level == level  # refreshed where it stood
        assert updated["a.puml::One"].level == level + 1  # untouched


def test_write_baseline_refuses_entries_keyed_elsewhere():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        results = _score(_TWO_NAMED, str(root / "a.puml"))
        elsewhere = BaselineFile({}, version=2, anchor=root / "other")
        try:
            write_baseline(root / "b.json", results, previous=elsewhere)
        except ValueError as e:
            assert "keyed relative to" in str(e)
        else:
            assert False, "expected ValueError for a baseline keyed elsewhere"

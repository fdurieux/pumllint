"""Engine plumbing tests, focused on the per-diagram grouped accessors that
feed the maturity scorer (Phase 4). Plain assert functions so the
zero-dependency runner picks them up too.
"""

import tempfile
from pathlib import Path

from pumllint.engine import Engine
from pumllint.parser import parse_source

# Two diagrams in one source: the first is named, the second is not — so
# GEN002 (unnamed-diagram) fires on the second only, giving us a per-diagram
# discriminator. Participants are declared to keep the fixtures quiet.
_TWO_DIAGRAMS = """\
@startuml Alpha
participant Alice
participant Bob
Alice -> Bob : hi
@enduml

@startuml
participant Carol
participant Dave
Carol -> Dave : yo
@enduml
"""


def _sorted(violations):
    return sorted(violations, key=lambda v: (v.file_path, v.line, v.rule_id))


def test_grouped_returns_one_entry_per_diagram():
    diagrams = parse_source(_TWO_DIAGRAMS, "test.puml")
    groups = Engine({}).lint_diagrams_grouped(diagrams)
    assert len(groups) == len(diagrams) == 2
    assert [d for d, _ in groups] == diagrams  # same diagram objects, in order


def test_grouped_flattens_to_the_flat_result():
    diagrams = parse_source(_TWO_DIAGRAMS, "test.puml")
    engine = Engine({})
    groups = engine.lint_diagrams_grouped(diagrams)
    flat = engine.lint_diagrams(diagrams)
    combined = _sorted(v for _, vs in groups for v in vs)
    assert combined == flat


def test_grouped_isolates_violations_per_diagram():
    diagrams = parse_source(_TWO_DIAGRAMS, "test.puml")
    groups = Engine({}).lint_diagrams_grouped(diagrams)
    (named_diag, named_vs), (unnamed_diag, unnamed_vs) = groups

    # GEN002 fires on the unnamed (second) diagram only.
    assert "GEN002" not in {v.rule_id for v in named_vs}
    assert "GEN002" in {v.rule_id for v in unnamed_vs}

    # Every violation in a group belongs to that group's diagram span.
    for diag, vs in groups:
        for v in vs:
            end = diag.end_line if diag.end_line is not None else float("inf")
            assert diag.start_line <= v.line <= end


def test_lint_paths_grouped_over_a_file():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "diagrams.puml"
        p.write_text(_TWO_DIAGRAMS, encoding="utf-8")
        groups = Engine({}).lint_paths_grouped([p])
    assert len(groups) == 2
    assert all(v.file_path == str(p) for _, vs in groups for v in vs)


# --- suppressed-findings accounting (0.19.0) --------------------------------

# First diagram suppresses its self-message (SEQ006), the second keeps an
# identical one visible — the per-diagram discriminator for the counts.
_SUPPRESSED_PAIR = """\
@startuml Alpha
title Alpha
participant Alice
' pumllint: disable=SEQ006
Alice -> Alice : tick()
@enduml

@startuml Beta
title Beta
participant Carol
Carol -> Carol : spin()
@enduml
"""


def test_grouped_run_counts_suppressed_findings_per_diagram():
    diagrams = parse_source(_SUPPRESSED_PAIR, "test.puml")
    engine = Engine({})
    groups = engine.lint_diagrams_grouped(diagrams)
    assert engine.suppressed_count(diagrams[0]) == 1
    assert engine.suppressed_count(diagrams[1]) == 0
    # The suppressed finding is hidden, its visible twin is reported.
    assert "SEQ006" not in {v.rule_id for v in groups[0][1]}
    assert "SEQ006" in {v.rule_id for v in groups[1][1]}


def test_suppressed_counts_are_from_the_most_recent_run_only():
    diagrams = parse_source(_SUPPRESSED_PAIR, "test.puml")
    engine = Engine({})
    engine.lint_diagrams_grouped(diagrams)
    assert engine.suppressed_count(diagrams[0]) == 1
    engine.lint_diagrams_grouped(parse_source(_TWO_DIAGRAMS, "other.puml"))
    # Stale diagrams make no claim rather than reporting a stale count.
    assert engine.suppressed_count(diagrams[0]) == 0


def test_no_suppressions_mode_counts_nothing_as_suppressed():
    diagrams = parse_source(_SUPPRESSED_PAIR, "test.puml")
    engine = Engine({"suppressions": False})
    groups = engine.lint_diagrams_grouped(diagrams)
    assert engine.suppressed_count(diagrams[0]) == 0
    assert "SEQ006" in {v.rule_id for v in groups[0][1]}

"""Parser-fidelity regression tests for sequence-message direction.

Pins the arrow forms whose semantic direction the model must normalize
via ``effective_source``/``effective_target``. Upstream ground truth
(PlantUML 1.2026.7beta11, probed via the official renderer): ``<-``,
``<--``, ``o<-``, ``x<-``, ``<<-`` and the leading half-arrow strokes
``\\-``, ``\\\\-``, ``/-``, ``//--`` all render leftward (flow B → A);
trailing strokes ``-\\``, ``-/`` and ``<->`` render with the head at B
(flow A → B).
"""

from pumllint.parser import parse_source


def _single_message(arrow: str):
    src = f"@startuml\nA {arrow} B : x\n@enduml\n"
    diagrams = parse_source(src, "t.puml")
    assert len(diagrams) == 1
    messages = diagrams[0].messages
    assert len(messages) == 1, f"arrow {arrow!r} did not parse as a message"
    return messages[0]


RIGHTWARD = [  # effective flow A -> B
    "->",
    "-->",
    "->>",
    "->+",
    "->o",
    "->x",
    "-\\",
    "-\\\\",
    "-/",
    "-//",
    "<->",  # bidirectional keeps the written direction
    "-[#red]>",
]

LEFTWARD = [  # effective flow B -> A
    "<-",
    "<--",
    "<<-",
    "o<-",
    "x<-",
    "\\-",
    "\\\\-",
    "/-",
    "//--",
]
# Not listed: "<[#red]-" — the colored-arrow variant only matches _ARROW when
# the bracket follows the dash run, so the left-colored form never parses as
# a message today. Parse-coverage limitation, distinct from direction.


def test_rightward_arrows_keep_written_direction():
    for arrow in RIGHTWARD:
        m = _single_message(arrow)
        assert not m.is_reversed, f"{arrow!r} misread as reversed"
        assert m.effective_source == "A", arrow
        assert m.effective_target == "B", arrow


def test_leftward_arrows_are_normalized():
    for arrow in LEFTWARD:
        m = _single_message(arrow)
        assert m.is_reversed, f"{arrow!r} not recognized as reversed"
        assert m.effective_source == "B", arrow
        assert m.effective_target == "A", arrow


def test_activation_shortcut_survives_direction_check():
    m = _single_message("->+")
    assert m.activates_target and not m.is_reversed


# --- legend bodies are not live source --------------------------------------

def test_legend_body_produces_no_messages_or_participants():
    src = (
        "@startuml\n"
        "participant A\n"
        "legend right\n"
        "  Foo -> Bar : text\n"
        "  participant Ghost\n"
        "endlegend\n"
        "A -> A : real\n"
        "@enduml\n"
    )
    d = parse_source(src, "t.puml")[0]
    assert [m.label for m in d.messages] == ["real"]
    assert set(d.participants) == {"A"}


def test_legend_spaced_terminator_and_bare_form():
    src = (
        "@startuml\n"
        "legend\n"
        "  X -> Y : inside\n"
        "end legend\n"
        "A -> B : after\n"
        "@enduml\n"
    )
    d = parse_source(src, "t.puml")[0]
    assert [m.label for m in d.messages] == ["after"]


def test_unterminated_legend_swallows_but_enduml_still_closes():
    src = "@startuml\nlegend\n  X -> Y : lost\n@enduml\n"
    d = parse_source(src, "t.puml")[0]
    assert d.messages == []
    assert d.end_line == 4


def test_note_body_mentioning_legend_stays_a_note():
    src = (
        "@startuml\n"
        "note over A\n"
        "  legend says retry twice\n"
        "end note\n"
        "A -> B : real\n"
        "@enduml\n"
    )
    d = parse_source(src, "t.puml")[0]
    notes = [x for x in d.directives if x.kind == "note"]
    assert len(notes) == 1 and "legend says" in notes[0].value
    assert [m.label for m in d.messages] == ["real"]


# --- delay-annotated arrows are messages, not dropped lines -----------------

def test_delay_annotated_arrow_parses_as_plain_message():
    m = _single_message("->(10)")
    assert (m.source, m.target, m.label) == ("A", "B", "x")
    assert not m.is_reversed and not m.is_return_arrow


def test_delay_annotated_reply_keeps_return_convention():
    m = _single_message("-->(5)")
    assert m.is_return_arrow and not m.is_reversed


def test_parenthesized_target_is_still_not_a_message():
    src = "@startuml\nA -> (B) : x\n@enduml\n"
    assert parse_source(src, "t.puml")[0].messages == []


def test_legend_body_mentioning_note_does_not_open_a_note():
    src = (
        "@startuml\n"
        "legend\n"
        "  note over A\n"
        "endlegend\n"
        "A -> B : real\n"
        "@enduml\n"
    )
    d = parse_source(src, "t.puml")[0]
    assert [x for x in d.directives if x.kind == "note"] == []
    assert [m.label for m in d.messages] == ["real"]


def test_include_directives_are_recorded_not_expanded():
    src = (
        "@startuml a\n"
        "!include _shared.iuml\n"
        "!includesub parts.iuml!SUB\n"
        "!includeurl https://example.test/theme.iuml\n"
        "!define FOO bar\n"
        "!theme plain\n"
        "A -> B : go\n"
        "@enduml\n"
    )
    d = parse_source(src)[0]
    includes = [x for x in d.directives if x.kind == "include"]
    assert [x.value for x in includes] == [
        "_shared.iuml",
        "parts.iuml!SUB",
        "https://example.test/theme.iuml",
    ]
    assert [x.line for x in includes] == [2, 3, 4]
    # other preprocessor lines stay skipped, and nothing became a participant
    assert sorted(d.participants) == ["A", "B"]


def test_include_inside_a_note_body_stays_note_text():
    src = (
        "@startuml a\n"
        "note over A\n"
        "  !include not-an-include\n"
        "end note\n"
        "A -> B : go\n"
        "@enduml\n"
    )
    d = parse_source(src)[0]
    assert not [x for x in d.directives if x.kind == "include"]
    note = next(x for x in d.directives if x.kind == "note")
    assert "!include not-an-include" in note.value

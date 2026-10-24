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


# --- declaration after first use -------------------------------------------


def _one(src: str):
    (d,) = parse_source(src, "t.puml")
    return d


def test_participant_declared_after_first_use_keeps_declared_false():
    """``declared`` means declared before first use (owner decision §6.7)."""
    d = _one("@startuml\nparticipant A\nA -> B : x\nparticipant B\n@enduml\n")
    b = d.participants["B"]
    assert b.declared is False
    assert b.line == 3  # first use
    assert b.declared_line == 4
    assert d.participants["A"].declared is True
    assert d.participants["A"].declared_line == 2


def test_late_declaration_fills_kind_alias_and_stereotype():
    d = _one(
        "@startuml\nparticipant A\nA -> B : x\n"
        'actor "Big Bob" as B <<svc>>\n@enduml\n'
    )
    b = d.participants["B"]
    assert (b.declared, b.kind, b.display_name, b.stereotype) == (False, "actor", "Big Bob", "svc")


def test_second_declaration_of_a_declared_participant_is_ignored():
    d = _one("@startuml\nparticipant A\nactor A\nA -> A : x\n@enduml\n")
    a = d.participants["A"]
    assert (a.declared, a.kind, a.declared_line) == (True, "participant", 2)


def test_create_is_not_a_declaration():
    d = _one("@startuml\nparticipant A\ncreate B\nA -> B : x\n@enduml\n")
    b = d.participants["B"]
    assert b.declared is False and b.declared_line is None and b.kind == "implicit"


def test_authored_is_declared_before_or_after_first_use():
    """``authored`` is "the modeller wrote a kind", whichever side of first
    use the declaration sits; ``authored_line`` is where it was written."""
    d = _one("@startuml\nparticipant A\nA -> B : x\nactor B\nB -> C : y\n@enduml\n")
    a, b, c = (d.participants[k] for k in "ABC")
    assert (a.authored, a.authored_line) == (True, 2)  # declared first
    assert (b.authored, b.authored_line) == (True, 4)  # declared late: the declaration
    assert (c.authored, c.authored_line) == (False, 5)  # never declared: first use
    # a use-case endpoint's kind is inferred from its brackets, not written
    u = _one("@startuml\nusecase (Pay)\n:Bob: --> (Pay)\n:Bob: --> (Ship)\n@enduml\n")
    assert [(p.kind, p.declared, p.authored) for p in u.participants.values()] == [
        ("usecase", True, True), ("actor", False, False), ("usecase", False, False)
    ]


# --- keyword-named message sources -----------------------------------------
# Ground truth: PlantUML 1.2026.6 (the syntax gate's pin), the messages and
# participants in its SVG, 2026-10-22: 106 keyword files and 55 edge lines.

KEYWORD_SOURCES = (
    "activate actor bottom boundary collections control create database "
    "deactivate delay destroy end endbox endhnote endlegend endnote endrnote "
    "entity hide ignore left newpage package participant queue rectangle ref "
    "right set show top usecase"
).split() + (  # these fifteen also have a block, note, return or directive branch
    "alt opt loop par break critical group else box note hnote rnote return "
    "autonumber skinparam"
).split()

DIRECTIVE_SOURCES = "caption footer header legend mainframe title".split()


def test_a_keyword_named_participant_sends_messages():
    """``participant "Plugin packages" as package`` then ``package -> B``:
    the message used to be dropped, and SEQ002 then called B unused."""
    for kw in KEYWORD_SOURCES:
        for decl in (f'participant "Alpha" as {kw}\n', ""):
            d = _one(f"@startuml\n{decl}participant B\n{kw} -> B : x\n@enduml\n")
            got = [(m.source, m.target, m.label) for m in d.messages]
            assert got == [(kw, "B", "x")], (kw, bool(decl), got)


def test_a_directive_still_wins_over_the_arrow():
    for kw in DIRECTIVE_SOURCES:
        d = _one(f'@startuml\nparticipant "Alpha" as {kw}\nparticipant B\n{kw} -> B : x\n@enduml\n')
        assert d.messages == [], kw


def test_a_keyword_line_is_a_message_only_with_a_real_arrow():
    """A head or an ``x``/``o`` end makes the line a message; a bare dash, a
    dotted body, a ``+``/``*`` suffix or no target leaves it to the keyword."""
    sent = ["alt x->y : z", "loop x-axis", "alt <- B : x", "alt ->]", "par -/ B : x",
            "note x->y", "return --> B : r", "box x-y", "else -> B : x", "alt->B : x"]
    for line in sent:
        d = _one(f"@startuml\nparticipant A\nparticipant B\nalt ok\n{line}\nend\n@enduml\n")
        kw = line.split()[0].split("-")[0]
        assert [m.source for m in d.messages] == [kw], (line, d.messages)
    kept = ["alt -1", "alt ..> B : x", "alt ->+ B : x", "alt ->* B : x", "group -",
            "alt success", "loop over x->y", "alt (x->y)", "opt -- guard --"]
    for line in kept:
        d = _one(f"@startuml\nparticipant A\nparticipant B\n{line}\nA -> B : in\nend\n@enduml\n")
        assert [m.source for m in d.messages] == ["A"], (line, d.messages)
        assert [b.kind for b in d.blocks] == [line.split()[0]], (line, d.blocks)


def test_a_keyword_message_does_not_open_a_block_or_a_note():
    """``group -> B`` used to open a group block that nothing closed, and
    ``note -> B`` with no label opened a note that swallowed the rest."""
    d = _one("@startuml\nparticipant A\nparticipant B\ngroup -> B\nnote -> B\nA -> B : x\n@enduml\n")
    assert d.blocks == []
    assert [(m.source, m.target) for m in d.messages] == [("group", "B"), ("note", "B"), ("A", "B")]


def test_a_state_named_note_keeps_its_transitions():
    """``note --> Idle : go`` was read as an inline note, so the state lost
    its outgoing transition; PlantUML draws all three."""
    d = _one("@startuml\n[*] --> note\nnote --> Idle : go\nIdle --> [*]\n@enduml\n")
    assert [(t.source, t.target) for t in d.transitions] == [("[*]", "note"), ("note", "Idle"), ("Idle", "[*]")]

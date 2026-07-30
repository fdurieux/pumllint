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

"""DIM-SYN gate tests (Phase 7): the check_files runner and its wiring into
score_groups. Plain assert functions; the injectable runner keeps most tests
free of subprocess, and the real-subprocess cases use sys.executable so no
PlantUML/Java install is needed.
"""

import sys

from pumllint.engine import Engine
from pumllint.parser import parse_source
from pumllint.scoring import score_groups
from pumllint.syntax import check_files


def test_check_files_invokes_command_per_file_with_checkonly():
    calls = []

    def fake_runner(cmd):
        calls.append(cmd)
        return 0 if "good.puml" in cmd[-1] else 1

    results = check_files(["good.puml", "bad.puml"], command="plantuml", runner=fake_runner)
    assert results == {"good.puml": True, "bad.puml": False}
    assert calls == [
        ["plantuml", "-checkonly", "good.puml"],
        ["plantuml", "-checkonly", "bad.puml"],
    ]


def test_check_files_accepts_command_list():
    seen = []

    def fake_runner(cmd):
        seen.append(cmd)
        return 0

    check_files(["d.puml"], command=["java", "-jar", "plantuml.jar"], runner=fake_runner)
    assert seen == [["java", "-jar", "plantuml.jar", "-checkonly", "d.puml"]]


def test_string_command_is_shell_split():
    # Regression: `syntax_command: "java -jar plantuml.jar"` must become three
    # argv elements, not one executable named "java -jar plantuml.jar".
    seen = []

    def fake_runner(cmd):
        seen.append(cmd)
        return 0

    check_files(["d.puml"], command="java -jar plantuml.jar", runner=fake_runner)
    assert seen == [["java", "-jar", "plantuml.jar", "-checkonly", "d.puml"]]


def test_timeout_surfaces_as_value_error():
    # Regression: a hanging plantuml must produce a clean config error
    # (the CLI maps ValueError to exit 2), not a TimeoutExpired traceback.
    slow = [sys.executable, "-c", "import time; time.sleep(5)"]
    try:
        check_files(["x.puml"], command=slow, timeout=0.2)
    except ValueError as e:
        assert "timed out" in str(e)
    else:
        raise AssertionError("expected ValueError on syntax-gate timeout")


def test_check_files_with_real_subprocess():
    ok = [sys.executable, "-c", "import sys; sys.exit(0)"]
    fail = [sys.executable, "-c", "import sys; sys.exit(3)"]
    assert check_files(["x.puml"], command=ok) == {"x.puml": True}
    assert check_files(["x.puml"], command=fail) == {"x.puml": False}


def test_syntax_results_gate_diagrams_per_file():
    src = "@startuml X\nparticipant A\nparticipant B\nA -> B : go()\n@enduml\n"
    groups = Engine({}).lint_diagrams_grouped(parse_source(src, "d.puml"))

    gated = score_groups(groups, syntax_results={"d.puml": False})
    assert gated[0][1].level == 1  # C2: forced Sketchy
    assert not gated[0][1].syntax_ok

    passed = score_groups(groups, syntax_results={"d.puml": True})
    assert passed[0][1].level > 1

    absent = score_groups(groups, syntax_results={"other.puml": False})
    assert absent[0][1].level > 1  # unlisted files fall back to syntax_ok=True

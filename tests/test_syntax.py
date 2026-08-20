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


def test_windows_string_command_keeps_backslash_paths():
    # POSIX splitting would eat the separators: `C:\tools\plantuml.jar` ->
    # `C:toolsplantuml.jar`, so the gate failed naming a path nobody typed.
    # `java -jar <path>` is the normal Windows PlantUML install.
    from pumllint.syntax import _split_command

    got = _split_command(r"java -jar C:\tools\plantuml.jar", windows=True)
    assert got == ["java", "-jar", r"C:\tools\plantuml.jar"], got


def test_windows_string_command_unquotes_a_quoted_path():
    from pumllint.syntax import _split_command

    got = _split_command(r'"C:\Program Files\pl\plantuml.bat" --verbose', windows=True)
    assert got == [r"C:\Program Files\pl\plantuml.bat", "--verbose"], got


def test_posix_string_command_splitting_is_unchanged():
    from pumllint.syntax import _split_command

    assert _split_command("java -jar plantuml.jar", windows=False) == [
        "java", "-jar", "plantuml.jar",
    ]
    assert _split_command("'/opt/my tools/plantuml' -x", windows=False) == [
        "/opt/my tools/plantuml", "-x",
    ]


def test_command_is_resolved_through_which():
    # subprocess resolves a bare name through CreateProcess on Windows, which
    # appends .exe and never consults PATHEXT — so a plantuml.bat on PATH is
    # invisible. shutil.which does apply PATHEXT; run what it hands back.
    import pumllint.syntax as syntax

    seen = []

    class _Completed:
        returncode = 0

    real_which, real_run = syntax.shutil.which, syntax.subprocess.run
    syntax.shutil.which = lambda program: f"C:\\tools\\{program}.bat"
    syntax.subprocess.run = lambda argv, **kw: (seen.append(argv), _Completed())[1]
    try:
        check_files(["d.puml"], command="plantuml")
    finally:
        syntax.shutil.which, syntax.subprocess.run = real_which, real_run

    assert seen == [["C:\\tools\\plantuml.bat", "-checkonly", "d.puml"]], seen


def test_missing_command_says_it_is_not_on_path():
    import pumllint.syntax as syntax

    real_which = syntax.shutil.which
    syntax.shutil.which = lambda program: None
    try:
        check_files(["d.puml"], command="nosuchplantuml")
    except FileNotFoundError as e:
        assert "nosuchplantuml" in str(e), e
        assert "not found on PATH" in str(e), e
    else:
        raise AssertionError("a missing syntax-gate command must raise")
    finally:
        syntax.shutil.which = real_which


def test_empty_command_is_a_config_error():
    try:
        check_files(["d.puml"], command="   ")
    except ValueError as e:
        assert "empty" in str(e), e
    else:
        raise AssertionError("an empty syntax_command must raise")

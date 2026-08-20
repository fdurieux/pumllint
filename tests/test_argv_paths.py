"""Argument resolution: globs, directories, and errors that say what is wrong.

PowerShell and cmd.exe do not expand wildcards for native programs, so
`pumllint *.puml` arrives as the literal pattern and pumllint has to expand it
itself. These tests work at the argv level, which is platform-neutral: passing
the unexpanded string on Linux reproduces exactly what a Windows shell hands
over. Plain assert functions for the zero-dependency runner.
"""

import os
import tempfile
from pathlib import Path

from pumllint.engine import PUML_EXTENSIONS, collect_files

_SRC = "@startuml\nAlice -> Bob : hi\n@enduml\n"


def _tree(tmp: str, *names: str) -> Path:
    root = Path(tmp)
    for name in names:
        f = root / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(_SRC, encoding="utf-8")
    return root


def _in(tmp: str, args):
    """collect_files(args) with the process cwd at *tmp*, names relative."""
    old = os.getcwd()
    os.chdir(tmp)
    try:
        return [Path(f).name for f in collect_files(args)]
    finally:
        os.chdir(old)


def test_glob_pattern_is_expanded_when_the_literal_path_is_absent():
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "a.puml", "b.puml", "notes.md")
        assert _in(tmp, ["*.puml"]) == ["a.puml", "b.puml"]


def test_glob_matches_are_filtered_by_extension():
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "a.puml", "notes.md")
        assert _in(tmp, ["*"]) == ["a.puml"]


def test_recursive_glob_crosses_directories():
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "a.puml", "sub/b.puml", "sub/deep/c.puml")
        assert _in(tmp, ["**/*.puml"]) == ["a.puml", "b.puml", "c.puml"]


def test_glob_matching_nothing_raises_rather_than_reporting_success():
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "a.puml")
        try:
            _in(tmp, ["*.xyz"])
        except FileNotFoundError as e:
            assert "no files match pattern" in str(e), e
        else:
            raise AssertionError("a pattern matching nothing must not pass silently")


def test_glob_matching_only_other_extensions_says_so():
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "notes.md")
        try:
            _in(tmp, ["*.md"])
        except FileNotFoundError as e:
            assert "none had a diagram extension" in str(e), e
            for ext in PUML_EXTENSIONS:
                assert ext in str(e), e
        else:
            raise AssertionError("matched-but-filtered must be an error, not silence")


def test_a_real_file_whose_name_looks_like_a_pattern_wins():
    # Literal-first ordering: bracket characters are legal in filenames.
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "weird[1].puml", "a.puml")
        assert _in(tmp, ["weird[1].puml"]) == ["weird[1].puml"]


def test_shell_expanded_arguments_are_passed_through_unchanged():
    # The POSIX no-regression pin: bash already expanded, so the pattern
    # branch must never run.
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "a.puml", "b.puml")
        assert _in(tmp, ["b.puml", "a.puml"]) == ["b.puml", "a.puml"]


def test_an_explicitly_named_file_keeps_any_extension():
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "diagram.txt")
        assert _in(tmp, ["diagram.txt"]) == ["diagram.txt"]


def test_directory_extension_match_is_case_insensitive():
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "Order.PUML", "b.puml")
        assert _in(tmp, ["."]) == ["Order.PUML", "b.puml"]


def test_duplicate_arguments_are_collected_once():
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "a.puml")
        assert _in(tmp, [".", "a.puml", "*.puml"]) == ["a.puml"]


def test_missing_path_message_states_what_is_wrong():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            collect_files([str(Path(tmp) / "nope.puml")])
        except FileNotFoundError as e:
            assert "no such file or directory" in str(e), e
        else:
            raise AssertionError("a missing path must raise")


def test_tilde_argument_gets_a_hint():
    try:
        collect_files(["~/diagrams/x.puml"])
    except FileNotFoundError as e:
        assert "'~' is expanded by the shell" in str(e), e
    else:
        raise AssertionError("an unexpanded ~ must raise")


def test_powershell_trailing_quote_gets_a_hint():
    # PowerShell turns "C:\dir\" into C:\dir" when passing to a native program.
    try:
        collect_files(['C:\\My Diagrams"'])
    except FileNotFoundError as e:
        assert "trailing quote" in str(e), e
    else:
        raise AssertionError("a stray trailing quote must raise")


def test_every_bad_argument_is_reported_not_just_the_first():
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "a.puml")
        try:
            _in(tmp, ["nope.puml", "a.puml", "also-missing.puml"])
        except FileNotFoundError as e:
            assert "nope.puml" in str(e) and "also-missing.puml" in str(e), e
        else:
            raise AssertionError("bad arguments must fail the run")

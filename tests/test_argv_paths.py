"""Argument resolution: globs, directories, and errors that say what is wrong.

PowerShell and cmd.exe do not expand wildcards for native programs, so
`pumllint *.puml` arrives as the literal pattern and pumllint has to expand it
itself. These tests work at the argv level, which is platform-neutral: passing
the unexpanded string on Linux reproduces exactly what a Windows shell hands
over. Plain assert functions for the zero-dependency runner.
"""

import contextlib
import io
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
    # Compare whole relative paths, not basenames: a collector that flattened
    # the tree would otherwise look correct.
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "a.puml", "sub/b.puml", "sub/deep/c.puml")
        old = os.getcwd()
        os.chdir(tmp)
        try:
            got = sorted(Path(f).as_posix() for f in collect_files(["**/*.puml"]))
        finally:
            os.chdir(old)
        assert got == ["a.puml", "sub/b.puml", "sub/deep/c.puml"], got


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
    # Sorted-order comparison would be flavour-dependent: PurePath comparison
    # is case-folded on Windows and not on POSIX, so compare as a set.
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "Order.PUML", "b.puml")
        assert set(_in(tmp, ["."])) == {"Order.PUML", "b.puml"}


def test_duplicate_arguments_are_collected_once():
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "a.puml")
        assert _in(tmp, [".", "a.puml", "*.puml"]) == ["a.puml"]


def _spelled(tmp: str, args):
    """collect_files(args) with the process cwd at *tmp*, spellings kept."""
    old = os.getcwd()
    os.chdir(tmp)
    try:
        return [Path(f).as_posix() for f in collect_files(args)]
    finally:
        os.chdir(old)


# The three spellings above already collapse to one Path object, so that test
# never stressed the de-dup. Path equality collapses only what PurePath
# normalises at construction (`./x`, doubled separators); identity is the
# filesystem's. The spelling kept is the first given — it is what parse_file
# reports, so the report follows argv, never a resolved path. The baseline
# key is the deliberate exception: it is anchored to the baseline file's
# directory (baseline.py) precisely so it does *not* follow argv.


def test_absolute_and_relative_spellings_of_one_file_are_collected_once():
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "x.puml")
        absolute = str(Path(tmp) / "x.puml")
        assert _spelled(tmp, ["x.puml", absolute]) == ["x.puml"]
        assert _spelled(tmp, [absolute, "x.puml"]) == [Path(absolute).as_posix()]


def test_a_parent_hop_spelling_is_the_same_file():
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "d/x.puml")
        (Path(tmp) / "sub").mkdir()
        assert _spelled(tmp, ["d/x.puml", "sub/../d/x.puml"]) == ["d/x.puml"]


def test_a_symlink_and_its_target_are_collected_once():
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "d/x.puml")
        try:
            os.symlink(Path(tmp) / "d" / "x.puml", Path(tmp) / "link.puml")
        except (OSError, NotImplementedError):
            return  # symlinks need a privilege this platform withholds
        assert _spelled(tmp, ["d/x.puml", "link.puml"]) == ["d/x.puml"]
        assert _spelled(tmp, ["link.puml", "d/x.puml"]) == ["link.puml"]


def test_a_sweep_and_an_absolute_spelling_inside_it_are_collected_once():
    # The Action's `paths` input is word-split verbatim into argv, so
    # "${{ github.workspace }}/diagrams diagrams/x.puml" is a live route.
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "d/x.puml", "d/y.puml")
        absolute = str(Path(tmp) / "d" / "x.puml")
        assert _spelled(tmp, [".", absolute]) == ["d/x.puml", "d/y.puml"]
        assert _spelled(tmp, [absolute, "d"]) == [Path(absolute).as_posix(), "d/y.puml"]


def test_score_reports_one_diagram_under_two_spellings():
    # Before the identity key the report listed the diagram twice under two
    # paths, the model set counted it twice, and the second copy was "new
    # since baseline" — exempt from the ratchet by definition.
    import json

    from pumllint.cli import main

    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "x.puml")
        (Path(tmp) / "cfg.json").write_text("{}", encoding="utf-8")
        absolute = str(Path(tmp) / "x.puml")
        old = os.getcwd()
        os.chdir(tmp)
        try:
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                main(["score", "x.puml", absolute, "-f", "json", "-c", "cfg.json"])
        finally:
            os.chdir(old)
        report = json.loads(out.getvalue())
        assert [d["file"] for d in report["diagrams"]] == ["x.puml"], report["diagrams"]
        assert report["modelSet"]["diagramCount"] == 1, report["modelSet"]


def test_a_one_file_run_stays_a_one_diagram_batch_under_two_spellings():
    # The cross-diagram pack is dormant on a single diagram; a duplicate used
    # to make it two, so a file whose own participants collide by case was
    # compared with itself and XD003 fired on a one-file run.
    from pumllint.engine import Engine

    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "c.puml"
        f.write_text(
            "@startuml checkout\nparticipant Api\nparticipant api\nApi -> api : call\n@enduml\n",
            encoding="utf-8",
        )
        old = os.getcwd()
        os.chdir(tmp)
        try:
            ids = {v.rule_id for v in Engine({}).lint_paths(["c.puml", str(f)])}
        finally:
            os.chdir(old)
        assert ids, "the fixture should trip something"
        assert "XD003" not in ids, ids


def test_fix_applies_once_under_two_spellings():
    # fix_paths computed a result per spelling: the same diff twice, doubled
    # counts, and through a symlink two contradictory GEN002 names — the fix
    # takes the diagram name from the spelling's stem — with the last
    # spelling winning on disk.
    from pumllint.fixer import fix_paths

    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "x.puml")
        absolute = str(Path(tmp) / "x.puml")
        old = os.getcwd()
        os.chdir(tmp)
        try:
            results = fix_paths([absolute, "x.puml"])
            assert [r.path for r in results] == [Path(absolute)], results
            assert results[0].fixes, "the nameless fixture should draw a GEN002 fix"
            try:
                os.symlink(Path(tmp) / "x.puml", Path(tmp) / "link.puml")
            except (OSError, NotImplementedError):
                return  # symlinks need a privilege this platform withholds
            results = fix_paths(["link.puml", "x.puml"])
        finally:
            os.chdir(old)
        assert [r.path for r in results] == [Path("link.puml")], results
        names = [f.description for f in results[0].fixes if f.rule_id == "GEN002"]
        assert names and all("'link'" in n for n in names), names


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


def test_an_absolute_pattern_is_expanded_from_its_anchor():
    # Path.glob rejects a rooted pattern, so collect_files splits the anchor
    # off — the branch that carries drive-qualified Windows patterns.
    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "a.puml", "b.puml")
        pattern = str(Path(tmp) / "*.puml")
        got = [Path(f).name for f in collect_files([pattern])]
        assert got == ["a.puml", "b.puml"], got


def test_a_pattern_hint_survives_the_wildcard_branch():
    # A malformed argument is as likely to carry a wildcard as not; the hint
    # is what makes the message useful either way.
    try:
        collect_files(["~/diagrams/*.puml"])
    except FileNotFoundError as e:
        assert "'~' is expanded by the shell" in str(e), e
    else:
        raise AssertionError("an unexpanded ~ pattern must raise")


def test_cli_exits_two_on_an_unresolvable_argument():
    # The four CLI entry points collect separately from Engine.lint_paths;
    # pin that a bad argument still reaches exit 2 through the CLI.
    from pumllint.cli import main

    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "cfg.json").write_text("{}", encoding="utf-8")
        cfg = ["-c", str(Path(tmp) / "cfg.json")]
        for argv in (
            [str(Path(tmp) / "nope.puml"), *cfg],
            [str(Path(tmp) / "*.nothing"), *cfg],
            ["score", str(Path(tmp) / "nope.puml"), *cfg],
            ["fix", str(Path(tmp) / "nope.puml"), *cfg],
        ):
            err = io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                rc = main(argv)
            assert rc == 2, (argv, rc)
            assert "error:" in err.getvalue(), (argv, err.getvalue())


def test_expansion_globs_only_from_the_first_wildcard_component():
    # The literal prefix of a pattern must be used as a directory, never
    # matched component by component: on Windows a path may name a directory
    # by its 8.3 short form (RUNNER~1) that no directory listing contains, so
    # globbing the literal part finds nothing. Absolute patterns failed
    # exactly this way on the windows-latest runner.
    calls = []
    real_glob = Path.glob

    def spy(self, pattern, *a, **kw):
        calls.append((str(self), pattern))
        return real_glob(self, pattern, *a, **kw)

    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "a.puml", "sub/b.puml")
        Path.glob = spy
        try:
            got = [Path(f).name for f in collect_files([str(Path(tmp) / "*.puml")])]
        finally:
            Path.glob = real_glob

    assert got == ["a.puml"], got
    assert calls == [(tmp, "*.puml")], calls


def test_reported_paths_use_forward_slashes():
    # Reports and the syntax gate key off this string, and the baseline key
    # is derived from it; a Windows-produced report must match a
    # POSIX-produced one byte for byte.
    from pumllint.parser import parse_file

    with tempfile.TemporaryDirectory() as tmp:
        _tree(tmp, "sub/a.puml")
        target = Path(tmp) / "sub" / "a.puml"
        (diagram,) = parse_file(target)
        assert diagram.file_path == target.as_posix(), diagram.file_path
        assert "\\" not in diagram.file_path, diagram.file_path

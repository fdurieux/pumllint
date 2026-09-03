"""Packaging sync guards (0.8.0). The GitHub Action (action.yml) and the
pre-commit hooks (.pre-commit-hooks.yaml) are string-templated wrappers around
the CLI — these tests keep them from silently drifting when CLI flags or the
file collector change. Plain asserts; YAML parsing only when PyYAML happens to
be installed (the zero-dependency promise holds without it).
"""

import inspect
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_ACTION = (_ROOT / "action.yml").read_text(encoding="utf-8")
_HOOKS = (_ROOT / ".pre-commit-hooks.yaml").read_text(encoding="utf-8")


def test_docs_pin_the_current_version():
    """Every `fdurieux/pumllint@vX` and `rev: vX` pin in the user-facing docs
    must match the package. docs/setup-and-ci.md sat on v0.18.0 for three
    releases while only the README was guarded — hence the file list."""
    import pumllint

    for rel in ("README.md", "docs/setup-and-ci.md"):
        text = (_ROOT / rel).read_text(encoding="utf-8")
        pins = re.findall(r"fdurieux/pumllint@v([0-9.]+)", text)
        pins += re.findall(r"rev: v([0-9.]+)", text)
        assert pins, f"{rel} lost its version-pinned examples?"
        assert set(pins) == {pumllint.__version__}, (
            f"{rel} pins {sorted(set(pins))} but the package is "
            f"{pumllint.__version__} — bump the @vX / rev: examples when releasing"
        )


def test_pyproject_version_matches_the_package():
    import tomllib

    import pumllint

    data = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == pumllint.__version__


def test_version_flag_reports_the_package_version():
    """`pumllint --version` is the first thing a pip-install user runs."""
    import contextlib
    import io

    import pumllint
    from pumllint.cli import build_parser

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            build_parser().parse_args(["--version"])
        except SystemExit as e:
            assert e.code == 0
        else:
            raise AssertionError("--version did not exit")
    assert out.getvalue().strip() == f"pumllint {pumllint.__version__}"


def _cli_options() -> set:
    from pumllint import cli

    known = set()
    for factory in (
        cli.build_parser,
        cli.build_score_parser,
        cli.build_fix_parser,
        cli.build_trace_parser,
        cli.build_schema_parser,
    ):
        for action in factory()._actions:
            known.update(action.option_strings)
    return known


def test_top_level_help_lists_all_commands():
    """`pumllint --help` is the only discovery surface for the subcommands —
    main() dispatches on argv[0] before argparse runs, so the epilog must
    name every command and the exit-code contract.

    Derived from `_SUBCOMMANDS`, never a list frozen here: this test asserted
    "every command" against a hand-written four while `lsp` shipped, so the
    guard could not see the very omission it exists to catch. Deriving it
    covers each future command the moment it is dispatchable.
    """
    from pumllint.cli import _SUBCOMMANDS, build_parser

    text = build_parser().format_help()
    for cmd in sorted(_SUBCOMMANDS):
        assert f"pumllint {cmd}" in text, f"--help no longer mentions '{cmd}'"
    assert "Exit codes:" in text, "--help lost the exit-code contract"


def test_action_forwards_only_real_cli_flags():
    known = _cli_options()
    forwarded = {
        "-c", "--profile", "-f", "-o",
        "--fail-on", "--min-level", "--baseline", "--update-baseline",
    }
    assert forwarded <= known
    for flag in forwarded:
        assert flag in _ACTION, f"action.yml no longer forwards {flag}"


def test_action_dispatches_every_cli_command():
    """The action mirrors the CLI: every subcommand must appear in the
    bash dispatch (schema was missing until 0.27.x).

    Derived from `_SUBCOMMANDS` minus `_ACTION_EXCLUDED`, so a new command is
    covered automatically and the one genuine exclusion has to be declared in
    cli.py rather than looking like an oversight.
    """
    from pumllint.cli import _ACTION_EXCLUDED, _SUBCOMMANDS

    for cmd in sorted(set(_SUBCOMMANDS) - _ACTION_EXCLUDED):
        assert f'"{cmd}"' in _ACTION, f"action.yml does not dispatch '{cmd}'"


def test_action_rejects_the_commands_it_excludes():
    """The exclusion must be real, not just declared.

    `_ACTION_EXCLUDED` is only honest if action.yml genuinely does not accept
    those commands — otherwise the guard above could be relaxed by adding a
    name to a set in cli.py.
    """
    from pumllint.cli import _ACTION_EXCLUDED

    for cmd in sorted(_ACTION_EXCLUDED):
        assert f'"{cmd}"' not in _ACTION, (
            f"action.yml dispatches '{cmd}', so it is not excluded — "
            "remove it from _ACTION_EXCLUDED"
        )


def test_action_is_composite_and_installs_itself():
    assert 'using: "composite"' in _ACTION
    # Installing from the action's own checkout keeps the action pinned to the
    # exact ref the workflow requested — no PyPI drift.
    assert "GITHUB_ACTION_PATH" in _ACTION


def test_hook_entries_and_language():
    assert "entry: pumllint\n" in _HOOKS
    assert "entry: pumllint score" in _HOOKS
    assert _HOOKS.count("language: python") == 2


def test_hook_file_pattern_matches_the_collector_extensions():
    from pumllint.engine import collect_files

    exts = inspect.signature(collect_files).parameters["exts"].default
    assert exts, "collect_files lost its extension defaults?"
    for ext in exts:
        assert ext.lstrip(".") in _HOOKS, (
            f"collector accepts {ext} but .pre-commit-hooks.yaml files: "
            f"pattern does not mention it"
        )


def test_yaml_files_parse_when_yaml_is_available():
    try:
        import yaml
    except ImportError:
        return  # optional: the zero-dependency runner skips the parse check
    action = yaml.safe_load(_ACTION)
    assert action["runs"]["using"] == "composite"
    assert set(action["inputs"]) >= {
        "command", "paths", "config", "profile", "format", "output",
        "fail-on", "min-level", "baseline", "update-baseline", "report",
        "extra-args",
    }
    hooks = yaml.safe_load(_HOOKS)
    assert [h["id"] for h in hooks] == ["pumllint", "pumllint-score"]
    for h in hooks:
        assert h["files"] == r"\.(puml|plantuml|iuml|wsd)$"

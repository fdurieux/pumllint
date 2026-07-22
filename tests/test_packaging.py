"""Packaging sync guards (0.8.0). The GitHub Action (action.yml) and the
pre-commit hooks (.pre-commit-hooks.yaml) are string-templated wrappers around
the CLI — these tests keep them from silently drifting when CLI flags or the
file collector change. Plain asserts; YAML parsing only when PyYAML happens to
be installed (the zero-dependency promise holds without it).
"""

import inspect
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_ACTION = (_ROOT / "action.yml").read_text(encoding="utf-8")
_HOOKS = (_ROOT / ".pre-commit-hooks.yaml").read_text(encoding="utf-8")


def _cli_options() -> set:
    from pumllint.cli import build_parser, build_score_parser

    known = set()
    for parser in (build_parser(), build_score_parser()):
        for action in parser._actions:
            known.update(action.option_strings)
    return known


def test_action_forwards_only_real_cli_flags():
    known = _cli_options()
    forwarded = {
        "-c", "--profile", "-f", "-o",
        "--fail-on", "--min-level", "--baseline", "--update-baseline",
    }
    assert forwarded <= known
    for flag in forwarded:
        assert flag in _ACTION, f"action.yml no longer forwards {flag}"


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
        "fail-on", "min-level", "baseline", "update-baseline", "extra-args",
    }
    hooks = yaml.safe_load(_HOOKS)
    assert [h["id"] for h in hooks] == ["pumllint", "pumllint-score"]
    for h in hooks:
        assert h["files"] == r"\.(puml|plantuml|iuml|wsd)$"

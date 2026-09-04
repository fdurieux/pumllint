"""Config-loading tests. Plain assert functions for the zero-dep runner."""

import sys
import tempfile
from pathlib import Path

from pumllint.config import load_config


def test_yaml_config_without_pyyaml_is_a_clean_error():
    # Regression (0.8.0): an isolated environment (e.g. a pre-commit hook env)
    # meeting a pumllint.yaml must get an actionable error, not a traceback.
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / "pumllint.yaml"
        cfg.write_text("profile: codegen\n", encoding="utf-8")
        had_yaml = "yaml" in sys.modules
        saved = sys.modules.get("yaml")
        sys.modules["yaml"] = None  # forces `import yaml` to raise ImportError
        try:
            load_config(cfg)
        except ValueError as e:
            assert "PyYAML" in str(e)
            assert "additional_dependencies" in str(e)
        else:
            assert False, "expected ValueError without PyYAML"
        finally:
            if had_yaml:
                sys.modules["yaml"] = saved
            else:
                del sys.modules["yaml"]


def test_json_config_needs_no_optional_dependency():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / "pumllint.json"
        cfg.write_text('{"profile": "codegen"}', encoding="utf-8")
        assert load_config(cfg) == {"profile": "codegen"}


# --- issue #37: a config that says nothing must not fail silently ----------

def test_table_form_enabled_false_actually_disables():
    """`[rules.X]` + `enabled = false` used to leave the rule armed.

    The table fell through `_rule_config` as *options*, so a config that
    plainly reads as "off" ran the rule anyway. #37 records the cost: a
    "rules disabled" experimental control that was running every rule.
    """
    from pumllint.engine import Engine
    from pumllint.parser import parse_source

    src = "@startuml a\nSvc -> Peer : go()\n@enduml\n"
    for key in ("GEN001", "missing-title"):
        engine = Engine({"rules": {key: {"enabled": False}}})
        ids = {v.rule_id for v in engine.lint_diagrams(parse_source(src, "t.puml"))}
        assert "GEN001" not in ids, f"keyed by {key}"


def test_enabled_true_still_passes_the_other_options_through():
    """`enabled` is consumed by the dispatch, never handed to the rule."""
    from pumllint.engine import Engine
    from pumllint.parser import parse_source

    src = "@startuml a\ntitle T\nparticipant A\nparticipant B\n" + \
        "".join(f"A -> B : m{i}()\n" for i in range(3)) + "@enduml\n"
    engine = Engine({"rules": {"SEQ011": {"enabled": True, "max": 1}}})
    ids = [v.rule_id for v in engine.lint_diagrams(parse_source(src, "t.puml"))]
    assert "SEQ011" in ids, "max=1 must still reach the rule"


def test_scalar_disable_spellings_are_unchanged():
    from pumllint.engine import Engine
    from pumllint.parser import parse_source

    src = "@startuml a\nSvc -> Peer : go()\n@enduml\n"
    for spelling in (False, "off", "disabled"):
        engine = Engine({"rules": {"GEN001": spelling}})
        ids = {v.rule_id for v in engine.lint_diagrams(parse_source(src, "t.puml"))}
        assert "GEN001" not in ids, f"spelling {spelling!r} stopped disabling"


def test_unknown_top_level_and_rule_keys_are_disclosed():
    from pumllint.config import config_warnings
    from pumllint.rules import discover

    warnings = config_warnings(
        {"rulez": {}, "rules": {"GEN999": False, "codegen-vaugue-guard": False}}, discover()
    )
    joined = "\n".join(warnings)
    assert "rulez" in joined
    assert "GEN999" in joined and "codegen-vaugue-guard" in joined


def test_a_valid_config_warns_about_nothing():
    """The repo's own config must stay silent, or the warning is noise."""
    from pumllint.config import config_warnings
    from pumllint.rules import discover

    root = Path(__file__).resolve().parent.parent
    assert config_warnings(load_config(root / "pumllint.toml"), discover()) == []
    assert config_warnings(load_config(root / "docs" / "pilot-starter-config.toml"), discover()) == []


def test_unknown_option_keys_are_disclosed():
    """Issue #37's second defect: `[rules.GEN009] maximum = 5` was accepted at
    exit 0 and read as "the cap never binds". The declaration in catalog.toml
    is what makes the typo sayable, and the message names the legal keys."""
    from pumllint.config import config_warnings
    from pumllint.rules import discover

    warnings = config_warnings(
        {"rules": {"GEN009": {"maximum": 3}, "missing-title": {"foo": 1}}}, discover()
    )
    assert len(warnings) == 2, warnings
    gen009 = next(w for w in warnings if "GEN009" in w)
    assert "'maximum'" in gen009 and "(max-elements)" in gen009 and "takes: max" in gen009
    gen001 = next(w for w in warnings if "GEN001" in w)
    assert "'foo'" in gen001 and "takes no options" in gen001


def test_generic_keys_aliases_and_lexicon_extras_are_legal():
    """`severity` and `enabled` on any rule, SEQ008's `max` alias, GEN005's
    dict-valued `per_type`, and the codegen `extra_<lexicon>` twins are all
    read somewhere — a disclosure on any of them would be a false positive,
    which is worse than none."""
    from pumllint.config import config_warnings
    from pumllint.rules import discover

    cfg = {
        "rules": {
            "GEN009": {"max": 5, "severity": "major", "enabled": True},
            "SEQ008": {"max": 2},
            "GEN005": {"per_type": {"usecase": 20}},
            "SEQ107": {"extra_failure_keywords": ["boom"], "failure_keywords": ["fail"]},
            "XD003": {"distinct": ["Order"], "authoritative": {"Order": "Order"}},
            "GEN001": {"enabled": False},
        }
    }
    assert config_warnings(cfg, discover()) == []


def test_rule_keys_match_case_insensitively_in_engine_and_warning():
    """`[rules.gen009]` passed the unknown-rule disclosure (lowercased) and was
    then ignored by the engine (exact match) — the option-key disclosure would
    have vouched for a table nothing read. Both lookups now agree; an exact
    spelling still wins over a case variant."""
    from pumllint.config import config_warnings
    from pumllint.engine import Engine
    from pumllint.rules import discover

    assert config_warnings({"rules": {"gen009": {"max": 1}}}, discover()) == []
    rule = next(r for r in Engine({"rules": {"gen009": {"max": 1}}}).rules if r.id == "GEN009")
    assert rule.options == {"max": 1}
    rule = next(r for r in Engine({"rules": {"Max-Elements": {"max": 1}}}).rules if r.id == "GEN009")
    assert rule.options == {"max": 1}
    both = {"rules": {"GEN009": {"max": 2}, "gen009": {"max": 1}}}
    rule = next(r for r in Engine(both).rules if r.id == "GEN009")
    assert rule.options == {"max": 2}


def _list_rules_lines(argv):
    import contextlib
    import io

    from pumllint.cli import main

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = main(argv)
    return rc, out.getvalue().splitlines(), err.getvalue()


def test_list_rules_tags_dormant_rules_until_the_config_wakes_them():
    """Issue #37's third defect, second half: five rules cannot fire without
    configuration and the listing gave no hint. The tag names the key."""
    with tempfile.TemporaryDirectory() as tmp:
        empty = Path(tmp) / "empty.toml"
        empty.write_text("", encoding="utf-8")
        rc, lines, _ = _list_rules_lines(["--list-rules", "-c", str(empty)])
        assert rc == 0
        tagged = {ln.split()[0]: ln for ln in lines if "dormant:" in ln}
        assert sorted(tagged) == ["ACT006", "GEN006", "GEN007", "SEQ010", "UC002"], sorted(tagged)
        assert "[dormant: needs pattern]" in tagged["GEN006"]
        assert "[dormant: needs verbs]" in tagged["ACT006"]
        assert "[dormant: needs require_explicit_order]" in tagged["SEQ010"]

        # The repo config arms GEN006/GEN007 with a pattern: the tag must go.
        repo = Path(__file__).resolve().parent.parent / "pumllint.toml"
        rc, lines, _ = _list_rules_lines(["--list-rules", "-c", str(repo)])
        assert rc == 0
        by_id = {ln.split()[0]: ln for ln in lines}
        # (the description says "dormant until…" — the *tag* is what must go)
        assert "[dormant:" not in by_id["GEN006"] and "[dormant:" not in by_id["GEN007"]
        assert "[dormant: needs verbs]" in by_id["ACT006"]

        # An empty pattern is "not configured" (test_hardening pins the rule
        # side); the listing must agree. A disabled rule is disabled, not dormant.
        cfg = Path(tmp) / "c.toml"
        cfg.write_text('[rules]\nGEN006 = { pattern = "" }\nGEN007 = false\n', encoding="utf-8")
        rc, lines, _ = _list_rules_lines(["--list-rules", "-c", str(cfg)])
        by_id = {ln.split()[0]: ln for ln in lines}
        assert "[dormant: needs pattern]" in by_id["GEN006"]
        assert "[disabled]" in by_id["GEN007"] and "[dormant:" not in by_id["GEN007"]


def test_list_rules_with_a_null_option_is_exit_2():
    """The listing now builds the Engine, so a null option reaches the same
    config-error path as a lint run — exit 2, never a traceback."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / "c.json"
        cfg.write_text('{"rules": {"GEN009": {"max": null}}}', encoding="utf-8")
        rc, lines, err = _list_rules_lines(["--list-rules", "-c", str(cfg)])
    assert rc == 2 and not lines
    assert "GEN009" in err and "null" in err


def test_a_config_that_is_not_a_mapping_is_exit_2_material():
    """A list-rooted config used to die on `.get` and escape as exit 1."""
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / "pumllint.json"
        cfg.write_text('["a", "b"]', encoding="utf-8")
        try:
            load_config(cfg)
        except ValueError as e:
            assert "mapping" in str(e)
            return
    raise AssertionError("expected ValueError for a non-mapping config root")


def test_list_rules_reflects_the_loaded_config():
    """`--list-rules` used to print before the config was even read.

    Output was byte-identical with and without `-c`, so the one command whose
    job is "tell me what will run" could not answer the question.
    """
    import contextlib
    import io

    from pumllint.cli import main

    def run(argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = main(argv)
        return rc, out.getvalue()

    with tempfile.TemporaryDirectory() as tmp:
        empty = Path(tmp) / "empty.toml"
        empty.write_text("", encoding="utf-8")
        cfg = Path(tmp) / "c.toml"
        cfg.write_text("[rules]\nGEN001 = false\n", encoding="utf-8")
        rc_plain, plain = run(["--list-rules", "-c", str(empty)])
        rc_cfg, with_cfg = run(["--list-rules", "-c", str(cfg)])

    # Both must be real listings, or the comparison below proves nothing.
    assert rc_plain == 0 and rc_cfg == 0
    assert len(plain.splitlines()) == len(with_cfg.splitlines()) > 40
    assert plain != with_cfg, "config made no difference to --list-rules"
    gen001 = [ln for ln in with_cfg.splitlines() if ln.startswith("GEN001")]
    assert gen001 and "disabled" in gen001[0], gen001


def test_list_rules_does_not_tag_a_no_op_escalation():
    """Escalating a rule to the severity it already has is not a change."""
    import contextlib
    import io

    from pumllint.cli import main

    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        main(["--list-rules", "-c", str(Path(__file__).resolve().parent.parent / "pumllint.toml")])
    assert "critical -> critical" not in out.getvalue()


def test_list_rules_agrees_with_the_engine_that_will_run():
    """The listing re-derives state; this pins it to the real Engine.

    `--list-rules` computes "disabled" and "needs profile" itself, because
    Engine drops a rule with a bare `continue` and records no reason. Two
    independent derivations of the same fact drift, so the agreement is the
    thing worth asserting: every rule the listing does not tag must be one the
    Engine actually arms, and vice versa.
    """
    import contextlib
    import io

    from pumllint.cli import main
    from pumllint.engine import Engine

    repo_toml = Path(__file__).resolve().parent.parent / "pumllint.toml"
    for cfg, argv in (
        (load_config(repo_toml), ["--list-rules", "-c", str(repo_toml)]),
        ({"profile": "codegen"}, ["--list-rules", "--profile", "codegen"]),
    ):
        engine = Engine(cfg)
        armed = {r.id for r in engine.rules} | {r.id for r in engine.cross_rules}

        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            main(argv)
        lines = out.getvalue().splitlines()
        assert lines, argv
        listed_on = {
            ln.split()[0]
            for ln in lines
            if "[disabled" not in ln and "off (needs profile" not in ln
        }
        assert listed_on == armed, (
            sorted(armed - listed_on), sorted(listed_on - armed), argv
        )

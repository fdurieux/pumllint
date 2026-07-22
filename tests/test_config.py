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

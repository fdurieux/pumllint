"""Guard the generated .feature files against drift from RULES.md.

RULES.md is canonical; ``tools/extract_features.py`` regenerates the committed
feature files from it. If they diverge (someone edited a .feature by hand, or
changed the Gherkin in RULES.md without re-running the extractor), this fails.

Stdlib-only on purpose, so it runs under both the zero-dep run_tests.py and
pytest — no pytest-bdd import here.
"""

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_EXTRACTOR = _ROOT / "tools" / "extract_features.py"
_FEATURES_DIR = _ROOT / "tests" / "bdd" / "features"


def _load_extractor():
    spec = importlib.util.spec_from_file_location("extract_features", _EXTRACTOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_committed_features_match_rules_md():
    extractor = _load_extractor()
    expected = extractor.extract((_ROOT / "RULES.md").read_text(encoding="utf-8"))
    expected.update(extractor.extract_scoring((_ROOT / "SCORING.md").read_text(encoding="utf-8")))

    on_disk = {p.stem: p.read_text(encoding="utf-8") for p in _FEATURES_DIR.glob("*.feature")}

    assert set(on_disk) == set(expected), {
        "missing_files": sorted(set(expected) - set(on_disk)),
        "stale_files": sorted(set(on_disk) - set(expected)),
        "hint": "run: python tools/extract_features.py",
    }
    for rule_id, content in expected.items():
        assert on_disk[rule_id] == content, \
            f"{rule_id}.feature is stale — run: python tools/extract_features.py"

"""Extract executable ``.feature`` files from the Gherkin blocks in RULES.md.

RULES.md is the single source of truth: each rule section carries a fenced
```gherkin block that IS the acceptance spec. This script lifts those blocks
into ``tests/bdd/features/<ID>.feature`` so pytest-bdd can run them, keeping the
human spec and the executable spec one and the same.

Implemented rules (✅) are written against the canonical step vocabulary (see
tests/bdd/test_features.py) and run for real. Rules whose Status line is 🚫
(blocked) or ⏳ (planned) keep their descriptive prose and are emitted with a
``@skip`` tag, so they stay visible in the suite without needing step
definitions or failing CI. The sync test (``tests/test_features_sync.py``) fails
if generated output drifts from what is committed.

Run:  python tools/extract_features.py
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RULES_MD = REPO_ROOT / "RULES.md"
SCORING_MD = REPO_ROOT / "SCORING.md"
FEATURES_DIR = REPO_ROOT / "tests" / "bdd" / "features"

_SECTION_RE = re.compile(r"^### (?P<id>[A-Z]{2,3}\d{3}) ", re.MULTILINE)
_STATUS_RE = re.compile(r"^\*\*Severity:\*\*.*?\*\*Status:\*\*\s*(?P<emoji>\S+)", re.MULTILINE)
_GHERKIN_RE = re.compile(r"```gherkin\n(?P<body>.*?)\n```", re.DOTALL)

_BLOCKED_EMOJI = {"🚫", "⏳"}


def _sections(text: str) -> list[tuple[str, str]]:
    """Split RULES.md into (rule_id, section_text) pairs."""
    matches = list(_SECTION_RE.finditer(text))
    out = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append((m.group("id"), text[m.start():end]))
    return out


def extract(text: str) -> dict[str, str]:
    """Map ``rule_id -> .feature file content`` for every migrated rule."""
    features: dict[str, str] = {}
    for rule_id, section in _sections(text):
        gherkin = _GHERKIN_RE.search(section)
        if not gherkin:
            continue
        status = _STATUS_RE.search(section)
        blocked = bool(status and status.group("emoji") in _BLOCKED_EMOJI)
        body = gherkin.group("body").rstrip() + "\n"
        features[rule_id] = ("@skip\n" + body) if blocked else body
    return features


def extract_scoring(text: str) -> dict[str, str]:
    """Map ``scoring -> .feature`` content from SCORING.md's §7 Gherkin block.

    SCORING.md is canonical for the maturity scorer the same way RULES.md is
    for rules; its single fenced Gherkin block becomes ``scoring.feature``
    (step vocabulary: tests/bdd/test_scoring_feature.py).
    """
    gherkin = _GHERKIN_RE.search(text)
    if not gherkin:
        return {}
    return {"scoring": gherkin.group("body").rstrip() + "\n"}


def main() -> int:
    text = RULES_MD.read_text(encoding="utf-8")
    features = extract(text)
    features.update(extract_scoring(SCORING_MD.read_text(encoding="utf-8")))
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    # Drop stale feature files for rules no longer migrated.
    for existing in FEATURES_DIR.glob("*.feature"):
        if existing.stem not in features:
            existing.unlink()
    for rule_id, content in sorted(features.items()):
        (FEATURES_DIR / f"{rule_id}.feature").write_text(content, encoding="utf-8")
    print(f"Wrote {len(features)} feature(s) to {FEATURES_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

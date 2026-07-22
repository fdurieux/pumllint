"""Shared scoring plumbing for the calibration/experiment tools.

The parse -> lint -> score pipeline is the product's job; the tools should
call it, not re-implement it. Engines and lint results are cached at module
level: rule configuration is independent of scoring configuration, so reuse
across parameter sweeps is safe and saves repeated parsing/linting.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pumllint import Engine, parse_file, score  # noqa: E402

_ENGINES: dict[Optional[str], Engine] = {}
_LINTED: dict[tuple[str, Optional[str]], Optional[tuple]] = {}


def engine_for(profile: Optional[str]) -> Engine:
    """One Engine per profile, shared process-wide."""
    if profile not in _ENGINES:
        _ENGINES[profile] = Engine({"profile": profile} if profile else {})
    return _ENGINES[profile]


def lint_first_diagram(path, profile: Optional[str] = None):
    """(diagram, violations) for the first diagram in *path*, or None when the
    file yields no diagrams. Cached per (path, profile) — parsing and linting
    do not depend on scoring configuration."""
    key = (str(path), profile)
    if key not in _LINTED:
        diagrams = parse_file(path)
        if not diagrams:
            _LINTED[key] = None
        else:
            d = diagrams[0]
            _LINTED[key] = (d, engine_for(profile).lint_diagram(d))
    return _LINTED[key]


def score_first_diagram(path, profile: Optional[str] = None, scoring_cfg=None):
    """MaturityResult for the first diagram in *path* under *scoring_cfg*."""
    entry = lint_first_diagram(path, profile)
    if entry is None:
        raise ValueError(f"no diagrams in {path}")
    diagram, violations = entry
    return score(violations, diagram, config=scoring_cfg, active_profile=profile)


def collect_puml(*dirs) -> list[Path]:
    """All .puml files across *dirs*, each directory's files sorted."""
    out: list[Path] = []
    for d in dirs:
        out.extend(sorted(Path(d).glob("*.puml")))
    return out

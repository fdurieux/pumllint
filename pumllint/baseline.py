"""Baseline/ratchet support for the ``score`` command.

A baseline records each diagram's maturity level at a point in time. On later
runs the gate fails only on *regression* — a diagram dropping below its
recorded level — so the score gate is adoptable on a brownfield model set
without a big-bang cleanup: existing debt is tolerated, new debt is not.

Diagrams are keyed by ``<file path>::<diagram name>``; unnamed diagrams fall
back to their per-file ordinal (``::#0``) so the key survives edits elsewhere
in the file. Diagrams new since the baseline pass by definition (they can be
gated with ``--min-level``); diagrams removed from the set are ignored.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .model import Diagram
from .scoring import MaturityResult

BASELINE_VERSION = 1


@dataclass
class BaselineEntry:
    level: int
    composite: float  # informational; the ratchet compares levels only


@dataclass
class Regression:
    key: str
    baseline_level: int
    current_level: int


@dataclass
class Delta:
    """Level movement of one diagram since the baseline was recorded."""

    baseline_level: int
    current_level: int

    @property
    def delta(self) -> int:
        return self.current_level - self.baseline_level


def diagram_keys(diagrams: Iterable[Diagram]) -> list[str]:
    """Stable identity per diagram: file path + name, ordinal when unnamed.

    Ordinals count unnamed diagrams per file in document order, so renaming or
    editing one diagram never shifts another's key; duplicate names in one
    file (already a GEN002 finding) get an ordinal suffix to stay unique.
    """
    counters: dict[str, int] = {}
    keys = []
    for d in diagrams:
        base = f"{d.file_path}::{d.name or ''}"
        n = counters.get(base, 0)
        counters[base] = n + 1
        keys.append(base if d.name and n == 0 else f"{base}#{n}")
    return keys


def load_baseline(path: str | Path) -> dict[str, BaselineEntry]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"baseline file {path} is not valid JSON: {e}") from e
    if not isinstance(raw, dict) or "diagrams" not in raw:
        raise ValueError(f"baseline file {path} has no 'diagrams' key")
    version = raw.get("version")
    if version != BASELINE_VERSION:
        raise ValueError(
            f"baseline file {path} has version {version!r}; this pumllint "
            f"reads version {BASELINE_VERSION} — regenerate with --update-baseline"
        )
    out: dict[str, BaselineEntry] = {}
    for key, entry in raw["diagrams"].items():
        out[key] = BaselineEntry(
            level=int(entry["level"]), composite=float(entry.get("composite", 0.0))
        )
    return out


def write_baseline(
    path: str | Path, results: list[tuple[Diagram, MaturityResult]]
) -> None:
    payload = {
        "version": BASELINE_VERSION,
        "diagrams": {
            key: {"level": r.level, "composite": round(r.composite, 2)}
            for key, (_, r) in zip(diagram_keys(d for d, _ in results), results)
        },
    }
    Path(path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def find_regressions(
    baseline: dict[str, BaselineEntry],
    results: list[tuple[Diagram, MaturityResult]],
) -> list[Regression]:
    """Diagrams scoring below their baselined level, in result order."""
    out = []
    for key, (_, r) in zip(diagram_keys(d for d, _ in results), results):
        entry = baseline.get(key)
        if entry is not None and r.level < entry.level:
            out.append(Regression(key, entry.level, r.level))
    return out


def compute_deltas(
    baseline: dict[str, BaselineEntry],
    results: list[tuple[Diagram, MaturityResult]],
) -> dict[str, Delta]:
    """Level movement per baselined diagram (trend reporting).

    Diagrams absent from the baseline have no delta — they are new, which the
    reporters call out separately.
    """
    out: dict[str, Delta] = {}
    for key, (_, r) in zip(diagram_keys(d for d, _ in results), results):
        entry = baseline.get(key)
        if entry is not None:
            out[key] = Delta(baseline_level=entry.level, current_level=r.level)
    return out

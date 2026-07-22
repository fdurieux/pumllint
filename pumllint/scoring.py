"""Maturity scoring model (see SCORING.md).

A **reporter-layer aggregation** over rule findings: no new analysis, every
score is derived from existing violations plus the diagram's element count.
:func:`score` is a pure function of its inputs — no I/O, no registry access, no
clock/randomness — so it is trivially unit-testable. Violations already carry
their :class:`~pumllint.model.Dimension` (stamped by the emitting rule), so the
scorer never consults the rule registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Optional

from .model import SEVERITY_ORDER, Diagram, Dimension, Severity, Violation

# ---------------------------------------------------------------------------
# Defaults (all overridable via the ``scoring:`` config key)
# ---------------------------------------------------------------------------

DEFAULT_K = 50.0

# SonarQube-aligned severity weights. SCORING.md §3 omits CRITICAL (the spec
# predates the 5-severity enum); it is slotted at 8 — "almost a blocker" —
# continuing the decelerating multiplier ladder (×4, ×2.5, ×2, →×1.6/×1.25).
DEFAULT_SEVERITY_WEIGHTS: dict[Severity, float] = {
    Severity.BLOCKER: 10.0,
    Severity.CRITICAL: 8.0,
    Severity.MAJOR: 5.0,
    Severity.MINOR: 2.0,
    Severity.INFO: 0.5,
}

# Weighted dimensions (§2). DIM-SYN is the external gate, not weighted here.
# Weights sum to 1.0. Calibrated in Phase 10 (SCORING.md §9): the 2-rule
# dimensions TRC/RDB carry 0.05 each — coarse signals get proportionate
# composite weight — with the difference redistributed to CMP/AMB, the
# dimensions that carry the generation-readiness thesis.
DEFAULT_DIMENSION_WEIGHTS: dict[Dimension, float] = {
    Dimension.SEMANTIC: 0.20,
    Dimension.COMPLETENESS: 0.30,
    Dimension.CONSISTENCY: 0.15,
    Dimension.TRACEABILITY: 0.05,
    Dimension.READABILITY: 0.05,
    Dimension.AMBIGUITY: 0.25,
}

LEVEL_NAMES: dict[int, str] = {
    1: "Sketchy",
    2: "Structured",
    3: "Disciplined",
    4: "Precise",
    5: "Generation-ready",
}

# Dimensions gated at Level 4 (must each clear ``l4_dim_min``).
L4_GATED_DIMENSIONS = (Dimension.COMPLETENESS, Dimension.AMBIGUITY)

# Severities that block Level 5 ("zero major" read as "no finding >= major", so
# CRITICAL — e.g. an unterminated block — also blocks generation-ready).
# Derived from the canonical ladder in model.py, never re-encoded.
_MAJOR_OR_WORSE = SEVERITY_ORDER[SEVERITY_ORDER.index(Severity.MAJOR):]


@dataclass
class ScoringConfig:
    """Resolved scoring parameters; :meth:`from_dict` applies overrides."""

    k: float = DEFAULT_K
    severity_weights: dict[Severity, float] = field(
        default_factory=lambda: dict(DEFAULT_SEVERITY_WEIGHTS)
    )
    dimension_weights: dict[Dimension, float] = field(
        default_factory=lambda: dict(DEFAULT_DIMENSION_WEIGHTS)
    )
    # Composite floors and dimension gates per maturity level (§4).
    l2_composite: float = 40.0
    l3_composite: float = 60.0
    l4_composite: float = 75.0
    l4_dim_min: float = 70.0
    l5_composite: float = 90.0
    l5_dim_min: float = 80.0
    c3_dim_floor: float = 40.0  # any dimension below this caps the level at 3
    # Integrity caps (C4-C7): scoring rewards absence-of-findings, so vacuous
    # input must be capped structurally, and the Level-5 claim is bound to the
    # profile whose rules give it substance.
    l4_min_elements: int = 3  # C6: fewer elements caps the level at 3
    l5_requires_profile: Optional[str] = "codegen"  # C7: None disables

    @classmethod
    def from_dict(cls, cfg: Optional[Mapping] = None) -> "ScoringConfig":
        """Build a config from the ``scoring:`` sub-mapping (or defaults)."""
        out = cls()
        if not cfg:
            return out
        if "k" in cfg:
            out.k = float(cfg["k"])
        for sev_name, w in (cfg.get("severity_weights") or {}).items():
            out.severity_weights[Severity(str(sev_name).lower())] = float(w)
        for dim_id, w in (cfg.get("dimension_weights") or {}).items():
            out.dimension_weights[Dimension(str(dim_id).upper())] = float(w)
        for key in (
            "l2_composite", "l3_composite", "l4_composite", "l4_dim_min",
            "l5_composite", "l5_dim_min", "c3_dim_floor",
        ):
            if key in (cfg.get("thresholds") or {}):
                setattr(out, key, float(cfg["thresholds"][key]))
        if "l4_min_elements" in (cfg.get("thresholds") or {}):
            out.l4_min_elements = int(cfg["thresholds"]["l4_min_elements"])
        if "l5_requires_profile" in cfg:
            raw = cfg["l5_requires_profile"]
            out.l5_requires_profile = str(raw) if raw else None
        # A weight typo must be a loud error, not a silently distorted verdict:
        # the composite is a weighted mean, so weights must sum to 1.0.
        total = sum(out.dimension_weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"scoring dimension weights must sum to 1.0, got {total:.4f} "
                f"(rebalance the other dimensions when overriding one)"
            )
        return out


@dataclass
class DimensionScore:
    dimension: Dimension
    score: float
    penalty: float
    weight: float
    violations: list[Violation]  # findings in this dimension (for the gap report)


@dataclass
class GapItem:
    """One obstacle blocking promotion to the next level, plus the findings to
    fix. ``kind`` is one of: ``syntax`` | ``content`` | ``diagram-type`` |
    ``blocker`` | ``severity`` | ``profile`` | ``dimension`` | ``composite``."""

    kind: str
    message: str
    dimension: Optional[Dimension] = None
    current: Optional[float] = None
    required: Optional[float] = None
    findings: list[Violation] = field(default_factory=list)


@dataclass
class MaturityResult:
    level: int
    level_name: str
    composite: float
    syntax_ok: bool
    element_count: int
    dimensions: dict[Dimension, DimensionScore]
    gap_report: list[GapItem] = field(default_factory=list)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def compute_dimension_scores(
    violations: Iterable[Violation], element_count: int, cfg: ScoringConfig
) -> dict[Dimension, DimensionScore]:
    """Per-dimension score = clamp(100 − K·penalty/max(1,elements), 0, 100)."""
    buckets: dict[Dimension, list[Violation]] = {d: [] for d in cfg.dimension_weights}
    for v in violations:
        if v.dimension in buckets:  # DIM-SYN / unknown dims are not scored here
            buckets[v.dimension].append(v)
    denom = max(1, element_count)
    scores: dict[Dimension, DimensionScore] = {}
    for dim, weight in cfg.dimension_weights.items():
        vs = buckets[dim]
        penalty = sum(cfg.severity_weights.get(v.severity, 0.0) for v in vs)
        density = penalty / denom
        scores[dim] = DimensionScore(
            dimension=dim,
            score=_clamp(100.0 - cfg.k * density, 0.0, 100.0),
            penalty=penalty,
            weight=weight,
            violations=vs,
        )
    return scores


def composite_score(
    dim_scores: Mapping[Dimension, DimensionScore], cfg: ScoringConfig
) -> float:
    """Weighted mean of dimension scores (dimension weights sum to 1.0)."""
    return sum(ds.score * ds.weight for ds in dim_scores.values())


def assign_level(
    composite: float,
    scores: Mapping[Dimension, float],
    *,
    has_blocker: bool,
    has_major_or_worse: bool,
    syntax_ok: bool,
    cfg: ScoringConfig,
    element_count: Optional[int] = None,
    diagram_type: Optional[str] = None,
    active_profile: Optional[str] = None,
) -> tuple[int, str]:
    """Map a composite + per-dimension scores onto a maturity level (§4).

    ``scores`` maps each weighted dimension to its 0–100 score. The level
    predicates are monotone (L5 ⟹ L4 ⟹ L3 ⟹ L2), so the highest satisfied wins;
    caps C1–C7 then lower it. ``element_count``/``diagram_type`` default to
    ``None`` (skip the vacuity caps) so pure boundary tests stay independent of
    diagram construction; :func:`score` always passes real values.
    """
    if not syntax_ok:  # C2: syntax gate failure forces Level 1
        return 1, LEVEL_NAMES[1]

    min_dim = min(scores.values()) if scores else 100.0
    cmp_ok = all(scores.get(d, 100.0) >= cfg.l4_dim_min for d in L4_GATED_DIMENSIONS)
    all_dims_high = all(s >= cfg.l5_dim_min for s in scores.values())

    # The zero-blocker requirement for L3+ is enforced once, by cap C1 below —
    # the predicates deliberately don't re-encode it. Likewise L5's zero-major
    # check subsumes blockers (BLOCKER is in _MAJOR_OR_WORSE).
    level = 1
    if composite >= cfg.l2_composite:
        level = 2
    if composite >= cfg.l3_composite:
        level = 3
    if composite >= cfg.l4_composite and cmp_ok:
        level = 4
    if composite >= cfg.l5_composite and all_dims_high and not has_major_or_worse:
        level = 5

    if has_blocker:  # C1: any blocker caps at Level 2
        level = min(level, 2)
    if min_dim < cfg.c3_dim_floor:  # C3: a sacrificed dimension caps at Level 3
        level = min(level, 3)
    if element_count is not None:
        if element_count == 0:  # C4: nothing modelled -> nothing to assess
            level = 1
        elif element_count < cfg.l4_min_elements:  # C6: too thin for Precise
            level = min(level, 3)
    if diagram_type == "unknown":  # C5: unrecognized model type
        level = min(level, 2)
    if cfg.l5_requires_profile and active_profile != cfg.l5_requires_profile:
        level = min(level, 4)  # C7: the L5 claim is bound to its rule pack
    return level, LEVEL_NAMES[level]


@dataclass
class _Requirements:
    """What a target level demands (mirrors the §4 predicates)."""

    composite_floor: float
    dim_gates: dict[Dimension, float]  # per-dimension minimum score
    zero_blocker: bool
    zero_major: bool  # "no finding >= major" (blocks Level 5)


def _target_requirements(target: int, cfg: ScoringConfig) -> _Requirements:
    if target == 2:
        return _Requirements(cfg.l2_composite, {}, False, False)
    if target == 3:
        return _Requirements(cfg.l3_composite, {}, True, False)
    if target == 4:
        gates = {d: cfg.c3_dim_floor for d in cfg.dimension_weights}  # C3 floor
        for d in L4_GATED_DIMENSIONS:
            gates[d] = max(gates[d], cfg.l4_dim_min)
        return _Requirements(cfg.l4_composite, gates, True, False)
    # target == 5
    gates = {d: cfg.l5_dim_min for d in cfg.dimension_weights}
    return _Requirements(cfg.l5_composite, gates, True, True)


def _by_weight(violations: list[Violation], cfg: ScoringConfig) -> list[Violation]:
    """Findings ordered heaviest-severity first (stable on line, rule id)."""
    return sorted(
        violations,
        key=lambda v: (-cfg.severity_weights.get(v.severity, 0.0), v.line, v.rule_id),
    )


def _findings_to_meet(
    dim: DimensionScore, required: float, denom: int, cfg: ScoringConfig
) -> list[Violation]:
    """Heaviest findings whose removal lifts this dimension to ``required``."""
    target_penalty = (100.0 - required) * denom / cfg.k
    need = dim.penalty - target_penalty
    if need <= 0:
        return []
    chosen: list[Violation] = []
    removed = 0.0
    for v in _by_weight(dim.violations, cfg):
        if removed >= need:
            break
        chosen.append(v)
        removed += cfg.severity_weights.get(v.severity, 0.0)
    return chosen


def _composite_findings(
    dim_scores: Mapping[Dimension, DimensionScore],
    element_count: int,
    floor: float,
    cfg: ScoringConfig,
) -> list[Violation]:
    """Heaviest findings overall whose removal lifts composite to ``floor``.

    Walks the weight-sorted findings once, updating per-dimension penalties
    incrementally — O(n · dims) instead of re-simulating the full scorer per
    candidate.
    """
    denom = max(1, element_count)
    penalties = {d: ds.penalty for d, ds in dim_scores.items()}

    def composite() -> float:
        return sum(
            weight * _clamp(100.0 - cfg.k * penalties[d] / denom, 0.0, 100.0)
            for d, weight in cfg.dimension_weights.items()
        )

    all_viols = [v for ds in dim_scores.values() for v in ds.violations]
    chosen: list[Violation] = []
    for v in _by_weight(all_viols, cfg):
        if composite() >= floor:
            break
        penalties[v.dimension] -= cfg.severity_weights.get(v.severity, 0.0)
        chosen.append(v)
    return chosen


def build_gap_report(
    level: int,
    composite: float,
    dim_scores: Mapping[Dimension, DimensionScore],
    element_count: int,
    syntax_ok: bool,
    cfg: ScoringConfig,
    diagram_type: Optional[str] = None,
    active_profile: Optional[str] = None,
) -> list[GapItem]:
    """The minimal blocking set to reach ``level + 1`` (§5): caps, then
    dimension thresholds, then composite shortfall. Empty at Level 5."""
    target = level + 1
    if target > 5:
        return []
    req = _target_requirements(target, cfg)
    denom = max(1, element_count)
    all_viols = [v for ds in dim_scores.values() for v in ds.violations]
    scores = {d: ds.score for d, ds in dim_scores.items()}
    items: list[GapItem] = []

    # 1. Caps ---------------------------------------------------------------
    if not syntax_ok:  # C2 — nothing else is meaningful until syntax passes
        return [
            GapItem("syntax", "syntax gate (plantuml -checkonly) must pass first")
        ]
    if element_count == 0:  # C4 — ditto: model something before scoring means anything
        return [
            GapItem("content", "diagram has no modelled content — add elements before scoring means anything")
        ]
    if diagram_type == "unknown" and target >= 3:  # C5 binds at Level 2
        items.append(
            GapItem("diagram-type", "diagram type is not recognized — use a supported diagram form (sequence/activity/usecase)")
        )
    if target >= 4 and element_count < cfg.l4_min_elements:  # C6
        items.append(
            GapItem(
                "content",
                f"diagram has only {element_count} element(s); Level 4 requires >= {cfg.l4_min_elements}",
                current=float(element_count),
                required=float(cfg.l4_min_elements),
            )
        )
    if (
        target == 5
        and cfg.l5_requires_profile
        and active_profile != cfg.l5_requires_profile
    ):  # C7
        items.append(
            GapItem(
                "profile",
                f"Level 5 requires the '{cfg.l5_requires_profile}' profile active "
                f"(run with --profile {cfg.l5_requires_profile})",
            )
        )
    blockers = [v for v in all_viols if v.severity is Severity.BLOCKER]
    if req.zero_blocker and blockers:
        items.append(
            GapItem(
                "blocker",
                f"{len(blockers)} blocker finding(s) cap the level at 2 — resolve them",
                findings=_by_weight(blockers, cfg),
            )
        )
    if req.zero_major:
        severe = [v for v in all_viols if v.severity in _MAJOR_OR_WORSE]
        if severe:
            items.append(
                GapItem(
                    "severity",
                    f"{len(severe)} finding(s) at major severity or worse block Level 5 — resolve them",
                    findings=_by_weight(severe, cfg),
                )
            )

    # 2. Dimension thresholds (heaviest-weighted dimension first) -----------
    for dim in sorted(req.dim_gates, key=lambda d: cfg.dimension_weights[d], reverse=True):
        required = req.dim_gates[dim]
        current = scores.get(dim, 100.0)
        if current < required:
            items.append(
                GapItem(
                    "dimension",
                    f"{dim.value} is {current:.0f}, needs >= {required:.0f}",
                    dimension=dim,
                    current=current,
                    required=required,
                    findings=_findings_to_meet(dim_scores[dim], required, denom, cfg),
                )
            )

    # 3. Composite shortfall ------------------------------------------------
    if composite < req.composite_floor:
        items.append(
            GapItem(
                "composite",
                f"composite is {composite:.0f}, needs >= {req.composite_floor:.0f}",
                current=composite,
                required=req.composite_floor,
                findings=_composite_findings(dim_scores, element_count, req.composite_floor, cfg),
            )
        )
    return items


def score(
    violations: Iterable[Violation],
    diagram: Diagram,
    *,
    syntax_ok: bool = True,
    config: Optional[Mapping] = None,
    active_profile: Optional[str] = None,
) -> MaturityResult:
    """Aggregate one diagram's violations into a :class:`MaturityResult`.

    ``syntax_ok`` is the DIM-SYN gate result (see :mod:`pumllint.syntax`); it
    defaults to True so scoring is testable without the external tool.
    ``active_profile`` is the engine's active rule profile, used by the C7
    profile-binding cap.
    """
    cfg = ScoringConfig.from_dict(config)
    violations = list(violations)
    element_count = diagram.element_count
    dim_scores = compute_dimension_scores(violations, element_count, cfg)
    composite = composite_score(dim_scores, cfg)

    severities = {v.severity for v in violations}
    has_blocker = Severity.BLOCKER in severities
    has_major_or_worse = any(s in severities for s in _MAJOR_OR_WORSE)

    level, name = assign_level(
        composite,
        {d: ds.score for d, ds in dim_scores.items()},
        has_blocker=has_blocker,
        has_major_or_worse=has_major_or_worse,
        syntax_ok=syntax_ok,
        cfg=cfg,
        element_count=element_count,
        diagram_type=diagram.diagram_type,
        active_profile=active_profile,
    )
    gap_report = build_gap_report(
        level, composite, dim_scores, element_count, syntax_ok, cfg,
        diagram_type=diagram.diagram_type, active_profile=active_profile,
    )
    return MaturityResult(
        level=level,
        level_name=name,
        composite=composite,
        syntax_ok=syntax_ok,
        element_count=element_count,
        dimensions=dim_scores,
        gap_report=gap_report,
    )


def score_groups(
    groups: Iterable[tuple[Diagram, list[Violation]]],
    *,
    config: Optional[Mapping] = None,
    syntax_ok: bool = True,
    syntax_results: Optional[Mapping[str, bool]] = None,
    active_profile: Optional[str] = None,
    engine=None,
) -> list[tuple[Diagram, MaturityResult]]:
    """Score each ``(diagram, violations)`` group from the engine.

    ``syntax_results`` maps file paths to their ``plantuml -checkonly`` gate
    outcome (see :mod:`pumllint.syntax`); files absent from the map — or all
    files, when no map is given — fall back to the blanket ``syntax_ok``.

    Pass the ``engine`` that produced the groups whenever you have it: its
    active profile is then used for the C7 cap, so a diagram can only be
    certified Level 5 when the profile's rules actually ran. A bare
    ``active_profile`` string is trusted as-is — it must match the engine
    configuration that produced ``groups``, or the certification lies.
    """
    if engine is not None:
        active_profile = getattr(engine, "profile", None)
    def _ok(d: Diagram) -> bool:
        if syntax_results is None:
            return syntax_ok
        return syntax_results.get(d.file_path, syntax_ok)

    return [
        (
            diagram,
            score(
                violations, diagram,
                syntax_ok=_ok(diagram), config=config, active_profile=active_profile,
            ),
        )
        for diagram, violations in groups
    ]

"""pumllint — semantic linter and maturity scorer for PlantUML diagrams.

Public API: lint with :class:`Engine` over parsed diagrams, score with
:func:`score_groups` (aggregate with :func:`aggregate_scores`), render with
:func:`get_reporter`; ratchet CI with :mod:`pumllint.baseline`. The JSON
report shapes are pinned by :mod:`pumllint.schema` (:func:`load_schema`).
"""

__version__ = "0.18.0"

from .baseline import (
    BaselineEntry,
    Delta,
    Regression,
    compute_deltas,
    find_regressions,
    load_baseline,
    write_baseline,
)
from .config import load_config
from .engine import Engine, collect_files
from .model import Diagram, Dimension, Severity, Violation
from .parser import parse_file, parse_source
from .reporters import Reporter, get_reporter
from .schema import load_schema
from .scoring import (
    DimensionScore,
    GapItem,
    MaturityResult,
    ModelSetResult,
    ScoringConfig,
    aggregate_scores,
    score,
    score_groups,
)
from .syntax import check_files

__all__ = [
    "__version__",
    "Engine",
    "collect_files",
    "load_config",
    "parse_file",
    "parse_source",
    "Diagram",
    "Dimension",
    "Severity",
    "Violation",
    "Reporter",
    "get_reporter",
    "load_schema",
    "DimensionScore",
    "GapItem",
    "MaturityResult",
    "ModelSetResult",
    "ScoringConfig",
    "aggregate_scores",
    "score",
    "score_groups",
    "check_files",
    "BaselineEntry",
    "Delta",
    "Regression",
    "compute_deltas",
    "find_regressions",
    "load_baseline",
    "write_baseline",
]

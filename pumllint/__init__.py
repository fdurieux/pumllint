"""pumllint — semantic linter and maturity scorer for PlantUML diagrams.

Public API: lint with :class:`Engine` over parsed diagrams, score with
:func:`score_groups`, render with :func:`get_reporter`.
"""

__version__ = "0.3.0"

from .config import load_config
from .engine import Engine, collect_files
from .model import Diagram, Dimension, Severity, Violation
from .parser import parse_file, parse_source
from .reporters import Reporter, get_reporter
from .scoring import (
    DimensionScore,
    GapItem,
    MaturityResult,
    ScoringConfig,
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
    "DimensionScore",
    "GapItem",
    "MaturityResult",
    "ScoringConfig",
    "score",
    "score_groups",
    "check_files",
]

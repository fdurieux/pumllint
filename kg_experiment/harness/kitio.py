"""Read the CargoQuote kit and the authored inputs into memory, then apply
a scenario's plant (plant.py). Nothing here touches the committed kit.

Keys are kit-relative paths; the three authored files and links.toml are
under ``kit/`` and come from kg_experiment/kit/.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
REPO = EXP.parent
CARGO = REPO / "stack_experiment" / "cargo_quote"

# Fixed order: the baseline arm concatenates in this order (§7 of the
# pre-registration).
KIT_FILES = [
    ("kit/requirements.md", EXP / "kit" / "requirements.md"),
    ("contract/decision_table.md", CARGO / "contract" / "decision_table.md"),
    ("contract/spec.md", CARGO / "contract" / "spec.md"),
    ("contract/openapi.yaml", CARGO / "contract" / "openapi.yaml"),
    ("behavior/quote_flow.puml", CARGO / "behavior" / "quote_flow.puml"),
    ("structure/containers.puml", CARGO / "structure" / "containers.puml"),
    ("kit/quote_process.bpmn", EXP / "kit" / "quote_process.bpmn"),
    ("kit/screening_decision.dmn", EXP / "kit" / "screening_decision.dmn"),
    ("tests_input/acceptance.feature", CARGO / "tests_input" / "acceptance.feature"),
    ("kit/links.toml", EXP / "kit" / "links.toml"),
]

FAMILY = {
    "kit/requirements.md": ("requirements", "markdown"),
    "contract/decision_table.md": ("decision_tables", "markdown"),
    "contract/spec.md": ("specification", "markdown"),
    "contract/openapi.yaml": ("api", "openapi-3.0"),
    "behavior/quote_flow.puml": ("behaviour", "plantuml-sequence"),
    "structure/containers.puml": ("structure", "c4-plantuml"),
    "kit/quote_process.bpmn": ("process", "bpmn-2.0"),
    "kit/screening_decision.dmn": ("decision", "dmn-1.3"),
    "tests_input/acceptance.feature": ("tests", "gherkin"),
    "kit/links.toml": ("links", "toml"),
    "notes/analysis_notes.md": ("notes", "markdown"),
}


def pristine() -> dict[str, str]:
    return {key: path.read_text(encoding="utf-8") for key, path in KIT_FILES}


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def kit_for(scenario: str, stage: int = 1) -> dict[str, str]:
    """The in-memory kit for a scenario. S6 has two stages: the first is
    S1's kit, the second applies the tariff change."""
    from plant import apply_plant  # local import: plant imports nothing

    kit = pristine()
    return apply_plant(kit, scenario, stage)

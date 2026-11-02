"""Write the checks behind the scoring wheel as JSON, for the slides to read.

    python export_checks.py OUT.json

Everything comes from pumllint itself, so the wheel and the appendix lists
cannot drift from the tool: the rules and their dimension, severity, diagram
types, profile and dormancy from pumllint/rules/catalog.toml; the dimension
weights and severity weights from pumllint.scoring; the dimension names from
the headings of docs/rule-map.md. build.sh runs it before assembling the deck.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pumllint import __version__  # noqa: E402
from pumllint.scoring import DEFAULT_DIMENSION_WEIGHTS, DEFAULT_SEVERITY_WEIGHTS  # noqa: E402

# Wheel order, clockwise from 12 o'clock: the order docs/rule-map.md uses.
ORDER = ["DIM-SEM", "DIM-CMP", "DIM-AMB", "DIM-CON", "DIM-TRC", "DIM-RDB"]


def export() -> dict:
    catalog = tomllib.loads((ROOT / "pumllint" / "rules" / "catalog.toml").read_text(encoding="utf-8"))
    rules = {k: v for k, v in catalog.items() if isinstance(v, dict) and "dimension" in v}
    rule_map = (ROOT / "docs" / "rule-map.md").read_text(encoding="utf-8")
    labels = dict((d, name) for name, d in re.findall(r"^## (.+?) \((DIM-[A-Z]{3})\)\s*$", rule_map, re.M))
    weights = {d.value: w for d, w in DEFAULT_DIMENSION_WEIGHTS.items()}
    dims = []
    for d in ORDER:
        dims.append({
            "id": d,
            "label": labels[d],
            "weight": weights[d],
            "rules": [
                {
                    "id": rid,
                    "name": r["name"],
                    "description": r["description"],
                    "severity": r["severity"],
                    "applies_to": r.get("applies_to", ["*"]),
                    "profiles": r.get("profiles", []),
                    "dormant": bool(r.get("dormant_unless")),
                }
                for rid, r in rules.items()
                if r["dimension"] == d
            ],
        })
    return {
        "version": __version__,
        "total": len(rules),
        "severity_weights": {s.value: w for s, w in DEFAULT_SEVERITY_WEIGHTS.items()},
        "dimensions": dims,
    }


if __name__ == "__main__":
    Path(sys.argv[1]).write_text(json.dumps(export(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

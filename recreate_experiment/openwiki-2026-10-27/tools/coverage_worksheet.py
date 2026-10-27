"""Coverage worksheet: one row per kit requirement, to be mapped onto the wiki.

    python coverage_worksheet.py <kit/requirements.json> <out.md>

Writes a Markdown table with the 163 requirements (id, kind, statement) and
two empty columns for the grader: `stated` (FULL, PARTIAL, NONE) and `page`
(the wiki page and section that states it, or the claim id). The grader
reads the wiki, never the code, for this worksheet: the question is what the
wiki tells a reader, not what is true. ``coverage_tally.py`` summarises it by
kind. Stdlib only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

STATED = ("FULL", "PARTIAL", "NONE")


def main() -> int:
    reqs = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    lines = [
        "# Coverage worksheet",
        "",
        "One row per kit requirement. Fill `stated` with FULL (the wiki states the "
        "behaviour with its condition and outcome), PARTIAL (the behaviour is "
        "mentioned without its condition, outcome or boundary) or NONE, and `page` "
        "with the page and section or claim id that states it. Read the wiki only.",
        "",
        "| id | kind | statement | stated | page |",
        "|---|---|---|---|---|",
    ]
    for r in reqs:
        statement = r["statement"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {r['id']} | {r['kind']} | {statement} |  |  |")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(reqs)} requirements written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

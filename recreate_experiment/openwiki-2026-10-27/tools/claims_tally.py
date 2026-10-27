"""Tally the grader's verdicts in a claims worksheet written by claims_worksheet.py.

    python claims_tally.py <claims.worksheet.md>

Prints the count per verdict and the precision figures the pre-registration
defines: strict precision = TRUE / graded, lenient = (TRUE + PARTIAL) / graded,
where graded excludes UNVERIFIABLE. Exits 2 when any sampled row is ungraded
or carries a verdict outside the four allowed, so a partial grading cannot be
tallied by accident. Stdlib only.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

VERDICTS = ("TRUE", "FALSE", "PARTIAL", "UNVERIFIABLE")
ROW = re.compile(r"^\| (\d+) \| `[^`]*` \| `[^`]*` \| .* \| (?P<verdict>[^|]*) \| (?P<note>[^|]*) \|$")


def main() -> int:
    path = Path(sys.argv[1])
    counts: Counter[str] = Counter()
    bad: list[str] = []
    rows = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        m = ROW.match(line)
        if not m:
            continue
        rows += 1
        verdict = m.group("verdict").strip()
        if verdict not in VERDICTS:
            bad.append(f"row {m.group(1)}: verdict {verdict!r}")
            continue
        counts[verdict] += 1
    if rows == 0:
        print("no worksheet rows found")
        return 2
    if bad:
        print("\n".join(bad))
        print(f"{len(bad)} of {rows} rows ungraded or mis-graded; tally refused")
        return 2
    graded = rows - counts["UNVERIFIABLE"]
    print(f"rows {rows}: " + ", ".join(f"{v} {counts[v]}" for v in VERDICTS))
    if graded:
        print(f"strict precision {counts['TRUE']}/{graded} = {counts['TRUE'] / graded:.3f}")
        print(f"lenient precision {(counts['TRUE'] + counts['PARTIAL'])}/{graded} = "
              f"{(counts['TRUE'] + counts['PARTIAL']) / graded:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Tally a coverage worksheet written by coverage_worksheet.py, by requirement kind.

    python coverage_tally.py <coverage.worksheet.md>

Exits 2 when any row is ungraded or carries a value outside FULL, PARTIAL,
NONE. Prints per-kind counts and the two coverage figures the
pre-registration defines: strict = FULL / all, lenient = (FULL + PARTIAL) / all.
Stdlib only.
"""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

STATED = ("FULL", "PARTIAL", "NONE")
ROW = re.compile(r"^\| (?P<id>JDL-\d{3}) \| (?P<kind>[a-z]+) \| .* \| (?P<stated>[^|]*) \| (?P<page>[^|]*) \|$")


def main() -> int:
    by_kind: dict[str, Counter[str]] = defaultdict(Counter)
    bad: list[str] = []
    rows = 0
    for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
        m = ROW.match(line)
        if not m:
            continue
        rows += 1
        stated = m.group("stated").strip()
        if stated not in STATED:
            bad.append(f"{m.group('id')}: stated {stated!r}")
            continue
        by_kind[m.group("kind")][stated] += 1
    if rows == 0:
        print("no worksheet rows found")
        return 2
    if bad:
        print("\n".join(bad))
        print(f"{len(bad)} of {rows} rows ungraded or mis-graded; tally refused")
        return 2
    total: Counter[str] = Counter()
    print("| kind | FULL | PARTIAL | NONE | n |")
    print("|---|---|---|---|---|")
    for kind in sorted(by_kind):
        c = by_kind[kind]
        total.update(c)
        print(f"| {kind} | {c['FULL']} | {c['PARTIAL']} | {c['NONE']} | {sum(c.values())} |")
    print(f"| all | {total['FULL']} | {total['PARTIAL']} | {total['NONE']} | {rows} |")
    print(f"strict coverage {total['FULL']}/{rows} = {total['FULL'] / rows:.3f}; "
          f"lenient {(total['FULL'] + total['PARTIAL'])}/{rows} = "
          f"{(total['FULL'] + total['PARTIAL']) / rows:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

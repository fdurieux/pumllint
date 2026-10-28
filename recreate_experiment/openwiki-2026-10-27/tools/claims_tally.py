"""Tally the grader's verdicts in a claims worksheet written by claims_worksheet.py.

    python claims_tally.py <claims.worksheet.md>

Prints the count per verdict and the precision figures the pre-registration
defines: strict precision = TRUE / graded, lenient = (TRUE + PARTIAL) / graded,
where graded excludes UNVERIFIABLE. Then the secondary, part-level figure
(owner decision 2026-10-28): holding parts / all parts over the graded rows.
Then M3: among TRUE rows, how many `in_kit` NO, the facts the wiki states that
no kit requirement or contract does. Exits 2 when any row is ungraded or
inconsistent (a verdict outside the four; parts missing or below 1; failed
above parts; TRUE with failed parts or FALSE/PARTIAL with none; in_kit not
YES or NO on a TRUE row, or set on another), so a partial grading cannot be
tallied by accident. Stdlib only.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

VERDICTS = ("TRUE", "FALSE", "PARTIAL", "UNVERIFIABLE")
ROW = re.compile(
    r"^\| (\d+) \| `[^`]*` \| `[^`]*` \| .* \| (?P<verdict>[^|]*) \| (?P<parts>[^|]*) \| "
    r"(?P<failed>[^|]*) \| (?P<in_kit>[^|]*) \| (?P<note>[^|]*) \|$")


def check(m: re.Match) -> tuple[str, int, int, str] | str:
    verdict = m.group("verdict").strip()
    if verdict not in VERDICTS:
        return f"verdict {verdict!r}"
    try:
        parts, failed = int(m.group("parts")), int(m.group("failed"))
    except ValueError:
        return "parts/failed not integers"
    if parts < 1 or not 0 <= failed <= parts:
        return f"parts {parts}, failed {failed}"
    if verdict == "TRUE" and failed:
        return "TRUE with failed parts"
    if verdict in ("FALSE", "PARTIAL") and not failed:
        return f"{verdict} with no failed part"
    in_kit = m.group("in_kit").strip()
    if verdict == "TRUE" and in_kit not in ("YES", "NO"):
        return f"TRUE row needs in_kit YES or NO, has {in_kit!r}"
    if verdict != "TRUE" and in_kit not in ("", "-"):
        return f"in_kit {in_kit!r} on a {verdict} row"
    return verdict, parts, failed, in_kit


def main() -> int:
    path = Path(sys.argv[1])
    counts: Counter[str] = Counter()
    bad: list[str] = []
    rows = parts_all = failed_all = 0
    in_kit: Counter[str] = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        m = ROW.match(line)
        if not m:
            continue
        rows += 1
        got = check(m)
        if isinstance(got, str):
            bad.append(f"row {m.group(1)}: {got}")
            continue
        verdict, parts, failed, kit = got
        counts[verdict] += 1
        if verdict != "UNVERIFIABLE":
            parts_all += parts
            failed_all += failed
        if verdict == "TRUE":
            in_kit[kit] += 1
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
        print(f"part-level precision {parts_all - failed_all}/{parts_all} = "
              f"{(parts_all - failed_all) / parts_all:.3f} (parts per graded claim "
              f"{parts_all / graded:.2f})")
    if counts["TRUE"]:
        print(f"M3: TRUE claims not in the kit {in_kit['NO']}/{counts['TRUE']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

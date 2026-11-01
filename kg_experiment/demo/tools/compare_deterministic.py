"""Compare a deterministic run against the published record, field by field.

    python compare_deterministic.py <run_dir> [<record_dir>] [--scenarios S1 S6]

For every scenario present in <run_dir>, loads ``<S>/deterministic.json``
from both trees and reports every leaf that differs, ignoring what cannot
be equal across two executions: wall-clock timestamps (``at``,
``ingested_at``, ``invalidated_at``), the SHACL report's text sample
(blank-node labels are fresh per run; its counts are compared), and the
running number R-CONFLICT appends to a conflict gap's id, which follows
the store's return order (the set of gaps, text included, is compared).
Everything else — counts, rule hits, census, verdicts, the invalidation
set, the gate's keys — must match. Exit 0 iff nothing differs; the diff
is printed either way, one line per leaf.

S6 is compared against ``results/d3check/S6`` by default: that is the
record's deterministic-mode run (``run.py --deterministic``, after the
loader fix the pre-registration's run notes describe). ``results/S6``
was written by the scored run, whose stage 2 also registers S1's first
governed output as a ``Derived`` node — a node, 88 ``USED_ASSERTION``
edges and a suspect flag that ``--deterministic`` did not create.
Pass ``--s6-record results/S6`` to see exactly that difference. Since
2026-11-01 (pumllint #257 and #259) the demo's runner copies S1's
generated code into the run folder and the harness reads it in both
modes, so a demo run's S6 carries that Derived node too: compare such a
run with ``--s6-record results/S6``; the ``d3check`` default is the
record's older deterministic-only run, which predates the change.

Standard library only, so the CI job and a laptop can run it with no
install. The record is ``kg_experiment/results`` by default.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECORD = HERE.parent.parent / "results"
SCENARIOS = ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]
VOLATILE_KEYS = {"at", "ingested_at", "invalidated_at", "sample"}


def _leaves(obj, prefix: str = "") -> dict[str, object]:
    out: dict[str, object] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in VOLATILE_KEYS:
                continue
            out.update(_leaves(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        # lists of dicts are compared as sets of their canonical forms when
        # order is not meaningful (rule hits come back in store order)
        if obj and all(isinstance(x, dict) for x in obj):
            canon = sorted(json.dumps(_strip(x), sort_keys=True) for x in obj)
            for i, c in enumerate(canon):
                out[f"{prefix}[{i}]"] = c
        else:
            for i, x in enumerate(obj):
                out.update(_leaves(x, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


CONFLICT_ID = re.compile(r"^(gap:conflict:.+):\d+$")


def _strip(obj):
    if isinstance(obj, dict):
        out = {k: _strip(v) for k, v in obj.items() if k not in VOLATILE_KEYS}
        if isinstance(out.get("id"), str):
            out["id"] = CONFLICT_ID.sub(r"\1:n", out["id"])
        return out
    if isinstance(obj, list):
        if obj and all(isinstance(x, dict) for x in obj):
            return sorted((_strip(x) for x in obj), key=lambda d: json.dumps(d, sort_keys=True))
        return [_strip(x) for x in obj]
    return obj


def compare(run_dir: Path, record_dir: Path, scenarios: list[str], s6_record: Path | None = None) -> tuple[int, list[str]]:
    lines: list[str] = []
    n_diff = 0
    for sc in scenarios:
        rec = s6_record if (sc == "S6" and s6_record) else record_dir / sc
        a, b = run_dir / sc / "deterministic.json", rec / "deterministic.json"
        if not a.exists():
            continue
        if not b.exists():
            lines.append(f"{sc}: no record at {b}")
            n_diff += 1
            continue
        la = _leaves(json.loads(a.read_text(encoding="utf-8")))
        lb = _leaves(json.loads(b.read_text(encoding="utf-8")))
        diffs = []
        for k in sorted(set(la) | set(lb)):
            if la.get(k, "<missing>") != lb.get(k, "<missing>"):
                diffs.append(f"  {k}: run={la.get(k, '<missing>')!r} record={lb.get(k, '<missing>')!r}")
        n_diff += len(diffs)
        lines.append(f"{sc} against {b.parent.relative_to(record_dir.parent) if record_dir.parent in b.parents else b.parent}: "
                     f"{len(la)} leaves compared, {len(diffs)} differ" + ("" if diffs else " — identical"))
        lines.extend(diffs)
    return n_diff, lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("record_dir", type=Path, nargs="?", default=RECORD)
    ap.add_argument("--scenarios", nargs="*", default=SCENARIOS)
    ap.add_argument("--s6-record", type=Path, default=None,
                    help="directory holding S6's deterministic.json (default: <record_dir>/d3check/S6)")
    args = ap.parse_args()
    s6 = args.s6_record or (args.record_dir / "d3check" / "S6")
    n, lines = compare(args.run_dir, args.record_dir, args.scenarios, s6_record=s6)
    print("\n".join(lines))
    compared = [ln for ln in lines if "leaves compared" in ln]
    if not compared:
        print(f"\nNOTHING COMPARED: no <scenario>/deterministic.json under {args.run_dir} for {' '.join(args.scenarios)}")
        return 1
    print(f"\n{'OK' if n == 0 else 'DIFF'}: {n} differing leaf/leaves over {len(compared)} scenario(s) against {args.record_dir}")
    return 0 if n == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

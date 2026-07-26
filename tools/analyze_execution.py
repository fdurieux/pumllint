"""Analyze execution-oracle results against the pre-registered expectations.

Reads execution_results/<wave>/execution.json (from tools/run_acceptance.py)
and evaluates X1-X4 from EVIDENCE.md §Execution oracle:

  X1 gradient: pass-rate rises with maturity; r(composite, pass-rate) > 0
  X2 cliff:    below composite ~40, mean pass-rate >= 10 pp lower
  X3 judge:    per-run r(judged fidelity, executed pass-rate) >= 0.4
  X4 honesty:  X1 sign holds on semantic-only pass-rate too

Metrics mirror tools/analyze_evidence.py: same Pearson/partial formulas,
same hard-demand control (judge-counted guards + failure paths).

  python tools/analyze_execution.py execution_results/original \
      execution_results/main2 execution_results/gen_haiku
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

ADAPTER_STAGES = {"import_error", "no_entry", "construct_error", "harness_error"}


def _pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def _partial(xs, ys, zs):
    rxy, rxz, ryz = _pearson(xs, ys), _pearson(xs, zs), _pearson(ys, zs)
    denom = math.sqrt((1 - rxz**2) * (1 - ryz**2))
    return (rxy - rxz * ryz) / denom if denom else 0.0


def per_run_rates(rows):
    """(label, run) -> {composite, level, fidelity, hard_demand, full, semantic}."""
    runs: dict = {}
    for r in rows:
        key = (r["label"], r["run"])
        a = runs.setdefault(key, {
            "label": r["label"], "level": r["level"],
            "composite": r["composite"],
            "fidelity": r.get("judge_fidelity"),
            "hard_demand": r.get("hard_demand", 0),
            "n": 0, "passed": 0, "sem_n": 0, "sem_passed": 0,
        })
        a["n"] += 1
        a["passed"] += bool(r["passed"])
        if r["stage"] not in ADAPTER_STAGES:
            a["sem_n"] += 1
            a["sem_passed"] += bool(r["passed"])
    for a in runs.values():
        a["full"] = a["passed"] / a["n"]
        a["semantic"] = a["sem_passed"] / a["sem_n"] if a["sem_n"] else None
    return runs


def per_diagram(runs):
    diags: dict = {}
    for a in runs.values():
        d = diags.setdefault(a["label"], {
            "label": a["label"], "level": a["level"],
            "composite": a["composite"], "rates": [], "sem": [], "hd": [],
        })
        d["rates"].append(a["full"])
        if a["semantic"] is not None:
            d["sem"].append(a["semantic"])
        d["hd"].append(a["hard_demand"])
    out = []
    for d in diags.values():
        out.append({
            "label": d["label"], "level": d["level"], "composite": d["composite"],
            "runs": len(d["rates"]),
            "pass_rate": sum(d["rates"]) / len(d["rates"]),
            "semantic_rate": sum(d["sem"]) / len(d["sem"]) if d["sem"] else None,
            "hard_demand": sum(d["hd"]) / len(d["hd"]),
        })
    return sorted(out, key=lambda d: -d["composite"])


def analyze(name, rows):
    runs = per_run_rates(rows)
    diags = per_diagram(runs)
    rvals = list(runs.values())

    by_level: dict = {}
    for a in rvals:
        b = by_level.setdefault(a["level"], {"runs": 0, "n": 0, "p": 0,
                                             "sn": 0, "sp": 0, "diagrams": set()})
        b["runs"] += 1
        b["n"] += a["n"]
        b["p"] += a["passed"]
        b["sn"] += a["sem_n"]
        b["sp"] += a["sem_passed"]
        b["diagrams"].add(a["label"])
    level_table = [
        {"level": lv, "diagrams": len(b["diagrams"]), "artifact_runs": b["runs"],
         "pass_rate": round(b["p"] / b["n"], 3),
         "semantic_rate": round(b["sp"] / b["sn"], 3) if b["sn"] else None}
        for lv, b in sorted(by_level.items(), reverse=True)
    ]

    lo = [a for a in rvals if a["composite"] < 40]
    hi = [a for a in rvals if a["composite"] >= 40]
    cliff = {
        "below_40_rate": round(sum(a["passed"] for a in lo) / sum(a["n"] for a in lo), 3) if lo else None,
        "above_40_rate": round(sum(a["passed"] for a in hi) / sum(a["n"] for a in hi), 3) if hi else None,
        "runs_below": len(lo), "runs_above": len(hi),
    }
    if cliff["below_40_rate"] is not None and cliff["above_40_rate"] is not None:
        cliff["gap_pp"] = round(100 * (cliff["above_40_rate"] - cliff["below_40_rate"]), 1)

    x = [a["composite"] for a in rvals]
    y = [a["full"] for a in rvals]
    dj = [d for d in diags]
    dx = [d["composite"] for d in dj]
    dy = [d["pass_rate"] for d in dj]
    dz = [d["hard_demand"] for d in dj]
    sem_d = [d for d in dj if d["semantic_rate"] is not None]

    fid_pairs = [(a["fidelity"], a["full"]) for a in rvals if a["fidelity"] is not None]

    correlations = {
        "per_run_r": round(_pearson(x, y), 3) if len(x) > 2 else None,
        "per_diagram_r": round(_pearson(dx, dy), 3) if len(dx) > 2 else None,
        "per_diagram_partial_hard_demand": round(_partial(dx, dy, dz), 3) if len(dx) > 2 else None,
        "per_diagram_semantic_r": round(
            _pearson([d["composite"] for d in sem_d],
                     [d["semantic_rate"] for d in sem_d]), 3) if len(sem_d) > 2 else None,
        "fidelity_vs_execution_per_run_r": round(
            _pearson([p[0] for p in fid_pairs], [p[1] for p in fid_pairs]), 3)
        if len(fid_pairs) > 2 else None,
    }

    stages: dict = {}
    for r in rows:
        stages[r["stage"]] = stages.get(r["stage"], 0) + 1

    return {
        "wave": name, "scenario_runs": len(rows),
        "artifact_runs": len(rvals), "diagrams": len(diags),
        "per_level": level_table, "cliff_at_40": cliff,
        "correlations": correlations, "stages": stages,
        "per_diagram": [
            {k: (round(v, 3) if isinstance(v, float) else v)
             for k, v in d.items()} for d in diags
        ],
    }


def main(argv=None) -> int:
    paths = [Path(p) for p in (argv or sys.argv[1:])]
    if not paths:
        print(__doc__)
        return 2
    waves = []
    pooled_rows = []
    for p in paths:
        data = json.loads((p / "execution.json").read_text(encoding="utf-8"))
        waves.append(analyze(data["wave"], data["rows"]))
        if data["wave"] in ("original", "main2"):  # identical gen/judge config
            pooled_rows.extend(data["rows"])
    result = {"waves": waves}
    if pooled_rows:
        result["pooled_identical_config"] = analyze("original+main2", pooled_rows)

    out = REPO_ROOT / "execution_results" / "analysis.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    for w in waves + ([result["pooled_identical_config"]] if pooled_rows else []):
        print(f"\n=== {w['wave']} — {w['scenario_runs']} scenario runs, "
              f"{w['diagrams']} diagrams ===")
        print(f"{'level':>5} {'diagrams':>9} {'runs':>5} {'pass':>6} {'semantic':>9}")
        for row in w["per_level"]:
            sem = row["semantic_rate"]
            print(f"{row['level']:>5} {row['diagrams']:>9} {row['artifact_runs']:>5} "
                  f"{row['pass_rate']:>6.3f} {sem if sem is None else format(sem, '.3f'):>9}")
        c = w["cliff_at_40"]
        print(f"cliff@40: below={c['below_40_rate']} above={c['above_40_rate']} "
              f"gap={c.get('gap_pp')}pp (runs {c['runs_below']}/{c['runs_above']})")
        print("correlations:", json.dumps(w["correlations"]))
        print("stages:", json.dumps(w["stages"]))
    print(f"\n-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

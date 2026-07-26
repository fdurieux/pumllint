"""Analyze the agent-repair wave against X-R1..X-R4 (EVIDENCE.md).

Frozen with the pre-registration, before any scored run. Inputs:
  execution_results/original/execution.json   (stored degraded + pristine)
  execution_results/main2/execution.json      (stored degraded + pristine)
  execution_results/repair/execution.json     (repaired arm + 2 fresh baselines)
  experiment_results/wave_repair/repair_log.json  (X-R1: repaired levels)

Pooling per the pre-registration: rates are pooled over scenario runs per
*original*-level tier; pristine reference and degraded baselines come from
the two stored identical-config waves (plus this wave's two fresh degraded
baselines). Per-diagram paired deltas are supporting detail.

  python tools/analyze_repair.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXEC = REPO_ROOT / "execution_results"
REPAIR_LOG = REPO_ROOT / "experiment_results/wave_repair/repair_log.json"

ADAPTER_STAGES = {"import_error", "no_entry", "construct_error", "harness_error"}


def rows_of(wave: str) -> list[dict]:
    return json.loads((EXEC / wave / "execution.json").read_text())["rows"]


def pool(rows) -> dict:
    n = len(rows)
    p = sum(bool(r["passed"]) for r in rows)
    sem = [r for r in rows if r["stage"] not in ADAPTER_STAGES]
    return {
        "scenario_runs": n,
        "pass_rate": round(p / n, 3) if n else None,
        "semantic_runs": len(sem),
        "semantic_rate": round(sum(bool(r["passed"]) for r in sem) / len(sem), 3)
        if sem else None,
    }


def per_diagram(rows, key="label") -> dict[str, float]:
    acc: dict[str, list] = {}
    for r in rows:
        acc.setdefault(r[key], []).append(bool(r["passed"]))
    return {k: round(sum(v) / len(v), 3) for k, v in sorted(acc.items())}


def main() -> int:
    stored = rows_of("original") + rows_of("main2")
    wave = rows_of("repair")
    repair_log = json.loads(REPAIR_LOG.read_text())
    repairs = [r for r in repair_log["repairs"] if "error" not in r]

    repaired_rows = [r for r in wave if r["label"].startswith("R_")]
    fresh_rows = [r for r in wave if not r["label"].startswith("R_")]

    # Tiers by ORIGINAL level: R_L1_... / R_L2_... parse from label.
    def orig_level(label: str) -> int:
        return int(label.removeprefix("R_")[1])

    pristine = pool([r for r in stored if r["level"] == 5])
    stored_l1 = [r for r in stored if r["level"] == 1]
    stored_l2 = [r for r in stored if r["level"] == 2] + fresh_rows
    base_l1, base_l2 = pool(stored_l1), pool(stored_l2)
    rep_l1 = pool([r for r in repaired_rows if orig_level(r["label"]) == 1])
    rep_l2 = pool([r for r in repaired_rows if orig_level(r["label"]) == 2])

    print("pooled executed pass-rates (full / semantic):")
    for name, d in (("pristine L5 (stored)", pristine),
                    ("degraded L2 (stored + fresh)", base_l2),
                    ("repaired  L2", rep_l2),
                    ("degraded L1 (stored)", base_l1),
                    ("repaired  L1", rep_l1)):
        print(f"  {name:30s} {d['pass_rate']}\t{d['semantic_rate']}"
              f"\t(n={d['scenario_runs']})")

    # X-R1: repairability (deterministic, from the repair log)
    finals = [r["final"]["level"] for r in repairs]
    xr1 = all(lv >= 4 for lv in finals) and sum(lv >= 5 for lv in finals) >= 12
    print(f"\nX-R1 repairability: final levels {sorted(finals, reverse=True)} "
          f"-> {'CONFIRMED' if xr1 else 'FAILED'} "
          f"(all >=4: {all(lv >= 4 for lv in finals)}, "
          f"L5 count: {sum(lv >= 5 for lv in finals)}/{len(finals)})")

    # X-R2: repaired-L2 within 5 pp of pristine
    gap2 = pristine["pass_rate"] - rep_l2["pass_rate"]
    xr2 = gap2 <= 0.05
    print(f"X-R2 recoverable tier: pristine {pristine['pass_rate']} - "
          f"repaired-L2 {rep_l2['pass_rate']} = {gap2:+.3f} "
          f"-> {'CONFIRMED' if xr2 else 'FAILED'} (bar <= 0.05)")

    # X-R3a: repaired-L1 beats degraded-L1 by >= 5 pp
    lift = rep_l1["pass_rate"] - base_l1["pass_rate"]
    xr3a = lift >= 0.05
    print(f"X-R3a repair helps: repaired-L1 {rep_l1['pass_rate']} - "
          f"degraded-L1 {base_l1['pass_rate']} = {lift:+.3f} "
          f"-> {'CONFIRMED' if xr3a else 'FAILED'} (bar >= 0.05)")

    # X-R3b: repaired-L1 recovers at most half the deficit
    half_bar = pristine["pass_rate"] - (pristine["pass_rate"] - base_l1["pass_rate"]) / 2
    xr3b = rep_l1["pass_rate"] <= half_bar
    print(f"X-R3b bounded by authorship: repaired-L1 {rep_l1['pass_rate']} "
          f"vs half-recovery bar {half_bar:.3f} "
          f"-> {'CONFIRMED' if xr3b else 'FAILED (recovered more than half)'}")

    # X-R4: gate passes while execution stays below pristine
    l1_gate = [r for r in repairs if r["orig_level"] == 1]
    gate_ok = all(r["final"]["level"] >= 2 for r in l1_gate)
    below = rep_l1["pass_rate"] < pristine["pass_rate"]
    xr4 = gate_ok and below
    print(f"X-R4 gate honesty: all repaired-L1 pass the Level-2 gate: {gate_ok}; "
          f"repaired-L1 executes below pristine: {below} "
          f"-> {'CONFIRMED' if xr4 else 'FAILED'}")

    # Supporting detail: per-diagram paired deltas
    stored_by_label = per_diagram(stored)
    fresh_by_label = per_diagram(fresh_rows)
    print("\nper-diagram (repaired vs its own degraded baseline):")
    pairs = []
    for r in sorted(repairs, key=lambda x: x["orig_label"]):
        rep = per_diagram(
            [x for x in repaired_rows
             if x["label"] == f"R_{r['orig_label']}"[:60]]).values()
        rep_rate = next(iter(rep), None)
        base_rate = stored_by_label.get(r["orig_label"],
                                       fresh_by_label.get(r["orig_label"]))
        delta = (None if rep_rate is None or base_rate is None
                 else round(rep_rate - base_rate, 3))
        pairs.append({"label": r["orig_label"], "orig_level": r["orig_level"],
                      "repaired_level": r["final"]["level"],
                      "base": base_rate, "repaired": rep_rate, "delta": delta,
                      "invented": len(r.get("invented_decisions", []))})
        print(f"  L{r['orig_level']} {r['orig_label']:50s} "
              f"{base_rate} -> {rep_rate}  d={delta}  "
              f"(L{r['final']['level']}, {len(r.get('invented_decisions', []))} inv)")

    out = {
        "pooled": {"pristine": pristine, "degraded_l2": base_l2,
                   "repaired_l2": rep_l2, "degraded_l1": base_l1,
                   "repaired_l1": rep_l1},
        "expectations": {"X-R1": xr1, "X-R2": xr2, "X-R3a": xr3a,
                         "X-R3b": xr3b, "X-R4": xr4},
        "half_recovery_bar": round(half_bar, 3),
        "per_diagram_pairs": pairs,
    }
    out_path = EXEC / "repair" / "analysis_repair.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"\n-> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

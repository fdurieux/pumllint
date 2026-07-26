"""Analyze the with-author repair arm against X-A1..X-A5 (EVIDENCE.md).

Frozen with the pre-registration, before any scored run. Inputs:
  execution_results/{original,main2}/execution.json   stored baselines
  execution_results/repair/execution.json             no-author arm +
                                                      3 fresh degraded baselines
  execution_results/repair_author/execution.json      with-author arm
  experiment_results/wave_repair/repair_log.json      no-author invention total
  experiment_results/wave_repair_author/repair_log.json  levels, Q&A, leakage

  python tools/analyze_repair_author.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXEC = REPO_ROOT / "execution_results"

import sys  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_repair import pool, rows_of, per_diagram  # noqa: E402


def main() -> int:
    stored = rows_of("original") + rows_of("main2")
    noauthor = rows_of("repair")
    wave = rows_of("repair_author")
    log = json.loads(
        (REPO_ROOT / "experiment_results/wave_repair_author/repair_log.json")
        .read_text())
    noauthor_log = json.loads(
        (REPO_ROOT / "experiment_results/wave_repair/repair_log.json")
        .read_text())
    repairs = [r for r in log["repairs"] if "error" not in r]

    authored_rows = [r for r in wave if r["label"].startswith("A_")]
    fresh_rows = [r for r in noauthor if not r["label"].startswith("R_")]
    noauthor_rows = [r for r in noauthor if r["label"].startswith("R_")]

    def orig_level(label: str, prefix: str) -> int:
        return int(label.removeprefix(prefix)[1])

    pristine = pool([r for r in stored if r["level"] == 5])
    base_l1 = pool([r for r in stored if r["level"] == 1])
    base_l2 = pool([r for r in stored if r["level"] == 2] + fresh_rows)
    a_l1 = pool([r for r in authored_rows if orig_level(r["label"], "A_") == 1])
    a_l2 = pool([r for r in authored_rows if orig_level(r["label"], "A_") == 2])
    r_l1 = pool([r for r in noauthor_rows if orig_level(r["label"], "R_") == 1])
    r_l2 = pool([r for r in noauthor_rows if orig_level(r["label"], "R_") == 2])

    print("pooled executed pass-rates (full / semantic):")
    for name, d in (("pristine L5 (stored)", pristine),
                    ("degraded L2", base_l2), ("no-author repaired L2", r_l2),
                    ("WITH-AUTHOR repaired L2", a_l2),
                    ("degraded L1", base_l1), ("no-author repaired L1", r_l1),
                    ("WITH-AUTHOR repaired L1", a_l1)):
        print(f"  {name:28s} {d['pass_rate']}\t{d['semantic_rate']}"
              f"\t(n={d['scenario_runs']})")

    finals = [r["final"]["level"] for r in repairs]
    xa1 = all(lv >= 4 for lv in finals) and len(finals) == 16
    print(f"\nX-A1 repairability: final levels {sorted(finals, reverse=True)} "
          f"-> {'CONFIRMED' if xa1 else 'FAILED'}")

    xa2 = a_l1["pass_rate"] >= base_l1["pass_rate"] + 0.10
    print(f"X-A2 authored content recovers: with-author L1 {a_l1['pass_rate']} "
          f"vs degraded {base_l1['pass_rate']} + 0.10 "
          f"-> {'CONFIRMED' if xa2 else 'FAILED'}")

    xa3 = a_l1["pass_rate"] <= pristine["pass_rate"] - 0.05
    print(f"X-A3 gap-report ceiling: with-author L1 {a_l1['pass_rate']} vs "
          f"pristine - 0.05 = {pristine['pass_rate'] - 0.05:.3f} "
          f"-> {'CONFIRMED (ceiling holds)' if xa3 else 'FAILED UPWARD'}")

    inv_total = sum(len(r.get("invented_decisions", [])) for r in repairs)
    noauthor_inv = sum(len(r.get("invented_decisions", []))
                       for r in noauthor_log["repairs"] if "error" not in r)
    xa4 = inv_total <= 0.2 * noauthor_inv
    print(f"X-A4 invention eliminated: {inv_total} invented vs bar "
          f"{0.2 * noauthor_inv:.0f} (20% of no-author {noauthor_inv}) "
          f"-> {'CONFIRMED' if xa4 else 'FAILED'}")

    xa5 = a_l2["pass_rate"] >= pristine["pass_rate"] - 0.05
    print(f"X-A5 recoverable tier closes: with-author L2 {a_l2['pass_rate']} "
          f"vs pristine - 0.05 = {pristine['pass_rate'] - 0.05:.3f} "
          f"-> {'CONFIRMED' if xa5 else 'FAILED'}")

    # Q&A + leakage audit
    n_q = sum(len(q["questions"]) for r in repairs for q in r["qa"])
    n_find = sum(q["n_finding"] for r in repairs for q in r["qa"])
    n_expl = sum(q["n_exploratory"] for r in repairs for q in r["qa"])
    leaks = sum(q["leak_flags"] for r in repairs for q in r["qa"])
    ans = [a["answer"] for r in repairs for q in r["qa"] for a in q["answers"]]
    lens = sorted(len(a.split()) for a in ans) or [0]
    print(f"\nQ&A audit: {n_q} questions ({n_find} finding / {n_expl} "
          f"exploratory), {len(ans)} answers, leakage flags: {leaks}, "
          f"answer words mean {sum(lens)/len(lens):.1f} max {lens[-1]}")

    stored_by = per_diagram(stored)
    fresh_by = per_diagram(fresh_rows)
    noauthor_by = per_diagram(noauthor_rows)
    print("\nper-diagram (degraded -> no-author -> with-author):")
    pairs = []
    for r in sorted(repairs, key=lambda x: (x["orig_level"], x["orig_label"])):
        a_rate = next(iter(per_diagram(
            [x for x in authored_rows
             if x["label"] == f"A_{r['orig_label']}"[:60]]).values()), None)
        base = stored_by.get(r["orig_label"], fresh_by.get(r["orig_label"]))
        na = noauthor_by.get(f"R_{r['orig_label']}"[:60])
        pairs.append({"label": r["orig_label"], "orig_level": r["orig_level"],
                      "final_level": r["final"]["level"], "base": base,
                      "no_author": na, "with_author": a_rate,
                      "questions": sum(len(q["questions"]) for q in r["qa"]),
                      "invented": len(r.get("invented_decisions", []))})
        print(f"  L{r['orig_level']} {r['orig_label']:50s} "
              f"{base} -> {na} -> {a_rate}  "
              f"(L{r['final']['level']}, {pairs[-1]['questions']}q, "
              f"{pairs[-1]['invented']} inv)")

    out = {
        "pooled": {"pristine": pristine, "degraded_l2": base_l2,
                   "noauthor_l2": r_l2, "author_l2": a_l2,
                   "degraded_l1": base_l1, "noauthor_l1": r_l1,
                   "author_l1": a_l1},
        "expectations": {"X-A1": xa1, "X-A2": xa2, "X-A3": xa3,
                         "X-A4": xa4, "X-A5": xa5},
        "qa_audit": {"questions": n_q, "finding": n_find,
                     "exploratory": n_expl, "answers": len(ans),
                     "leak_flags": leaks,
                     "answer_words_mean": round(sum(lens) / len(lens), 1),
                     "answer_words_max": lens[-1],
                     "invented_total": inv_total,
                     "noauthor_invented_total": noauthor_inv},
        "per_diagram": pairs,
    }
    out_path = EXEC / "repair_author" / "analysis_repair_author.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"\n-> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

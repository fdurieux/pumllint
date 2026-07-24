"""Arc D analysis: complexity-normalized fidelity and cross-wave robustness.

Pure stdlib analysis over the experiment reports (no API calls). Attacks the
synthetic-triviality confound named in EVIDENCE.md: fidelity is judged
relative to the diagram, so a structurally trivial diagram scores
near-perfect regardless of maturity. Complexity per run is measured by the
judge's own ground-truth counts — participants + messages + guards +
failure paths *expected* — i.e. the number of obligations the code had the
opportunity to miss.

Outputs (printed + JSON):
- raw and complexity-partial correlation r(composite, fidelity | complexity)
- correlations within complexity terciles (low/mid/high demand)
- when extra wave reports are given: per-wave correlations/cliff table and
  judge-agreement stats for re-judge waves.

Run:  python tools/analyze_evidence.py [report.json ...]
      (default: experiment_results/report.json plus any
       experiment_results/*/report.json wave directories)
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "experiment_results"


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def _partial(xs: list[float], ys: list[float], zs: list[float]) -> float:
    """Partial correlation r(x, y | z) from pairwise Pearson correlations."""
    rxy, rxz, ryz = _pearson(xs, ys), _pearson(xs, zs), _pearson(ys, zs)
    denom = math.sqrt((1 - rxz**2) * (1 - ryz**2))
    return (rxy - rxz * ryz) / denom if denom else 0.0


def _demand(judge: dict) -> int:
    """Obligations the code could miss — the complexity denominator."""
    return (
        judge["participants_expected"]
        + judge["messages_expected"]
        + judge["guards_expected"]
        + judge["failure_paths_expected"]
    )


def _hard_demand(judge: dict) -> int:
    """Semantically hard obligations: the ones a generator can get *wrong*
    in meaning (guards and failure paths), as opposed to plain call
    plumbing. A long linear call chain has high demand but zero hard
    demand — which is exactly the synthetic-triviality confound."""
    return judge["guards_expected"] + judge["failure_paths_expected"]


def _runs(report: dict) -> list[dict]:
    composites = {u["label"]: u["composite"] for u in report["selected"]}
    out = []
    for r in report["runs"]:
        if "error" in r:
            continue
        out.append({
            "label": r["label"],
            "composite": composites[r["label"]],
            "fidelity": r["judge"]["fidelity_score"],
            "demand": _demand(r["judge"]),
            "hard_demand": _hard_demand(r["judge"]),
            "invented": len(r["judge"]["invented_business_logic"]),
        })
    return out


def analyze_wave(report: dict) -> dict:
    runs = _runs(report)
    comps = [r["composite"] for r in runs]
    fids = [float(r["fidelity"]) for r in runs]
    demands = [float(r["demand"]) for r in runs]

    by_demand = sorted(runs, key=lambda r: (r["demand"], r["label"]))
    n = len(by_demand)
    terciles = {}
    for name, chunk in (
        ("low", by_demand[: n // 3]),
        ("mid", by_demand[n // 3 : 2 * n // 3]),
        ("high", by_demand[2 * n // 3 :]),
    ):
        if len(chunk) > 2:
            terciles[name] = {
                "n": len(chunk),
                "demand_range": [chunk[0]["demand"], chunk[-1]["demand"]],
                "r": round(
                    _pearson(
                        [c["composite"] for c in chunk],
                        [float(c["fidelity"]) for c in chunk],
                    ),
                    3,
                ),
                "mean_fidelity": round(
                    sum(c["fidelity"] for c in chunk) / len(chunk), 1
                ),
            }

    below = [r for r in runs if r["composite"] < 40]
    above = [r for r in runs if r["composite"] >= 40]
    cliff = {
        "below_40": {
            "runs": len(below),
            "mean_fidelity": round(sum(r["fidelity"] for r in below) / len(below), 1)
            if below else None,
            "invented_per_run": round(sum(r["invented"] for r in below) / len(below), 2)
            if below else None,
        },
        "at_or_above_40": {
            "runs": len(above),
            "mean_fidelity": round(sum(r["fidelity"] for r in above) / len(above), 1)
            if above else None,
            "invented_per_run": round(sum(r["invented"] for r in above) / len(above), 2)
            if above else None,
        },
    }

    # Per-diagram aggregation: the 3 runs of one diagram are not independent
    # observations, so the run-level r overstates n. The diagram-level r is
    # the honest headline unit.
    by_label: dict[str, list[dict]] = {}
    for r in runs:
        by_label.setdefault(r["label"], []).append(r)
    d_comps, d_fids, d_demands, d_hard = [], [], [], []
    for rs in by_label.values():
        d_comps.append(rs[0]["composite"])
        d_fids.append(sum(r["fidelity"] for r in rs) / len(rs))
        d_demands.append(sum(r["demand"] for r in rs) / len(rs))
        d_hard.append(sum(r["hard_demand"] for r in rs) / len(rs))

    hard = [float(r["hard_demand"]) for r in runs]
    return {
        "gen_model": report["gen_model"],
        "judge_model": report["judge_model"],
        "runs": len(runs),
        "diagrams": len(by_label),
        "r_raw": round(_pearson(comps, fids), 3),
        "r_fidelity_demand": round(_pearson(fids, demands), 3),
        "r_partial_given_demand": round(_partial(comps, fids, demands), 3),
        "r_partial_given_hard_demand": round(_partial(comps, fids, hard), 3),
        "per_diagram": {
            "r_raw": round(_pearson(d_comps, d_fids), 3),
            "r_partial_given_demand": round(_partial(d_comps, d_fids, d_demands), 3),
            "r_partial_given_hard_demand": round(_partial(d_comps, d_fids, d_hard), 3),
        },
        "terciles": terciles,
        "cliff": cliff,
    }


def pooled_same_config(reports: list[dict]) -> dict | None:
    """Pool runs across waves with the same gen+judge pair (larger n).

    Diagrams are matched by label; composites must agree exactly, so a
    label can never silently pool two different diagrams.
    """
    by_config: dict[tuple[str, str], list[dict]] = {}
    for rep in reports:
        if rep.get("rejudge_of"):
            continue  # a re-judge reuses artifacts; pooling it double-counts
        by_config.setdefault((rep["gen_model"], rep["judge_model"]), []).append(rep)
    pools = {k: v for k, v in by_config.items() if len(v) > 1}
    if not pools:
        return None
    (gen, judge), reps = next(iter(pools.items()))

    runs: dict[str, list[dict]] = {}
    composites: dict[str, float] = {}
    for rep in reps:
        for r in _runs(rep):
            if r["label"] in composites and composites[r["label"]] != r["composite"]:
                continue  # same label, different diagram — never pool
            composites[r["label"]] = r["composite"]
            runs.setdefault(r["label"], []).append(r)

    d_comps, d_fids, d_hard, ns = [], [], [], []
    for label, rs in runs.items():
        d_comps.append(composites[label])
        d_fids.append(sum(r["fidelity"] for r in rs) / len(rs))
        d_hard.append(sum(r["hard_demand"] for r in rs) / len(rs))
        ns.append(len(rs))
    flat = [r for rs in runs.values() for r in rs]
    return {
        "gen_model": gen,
        "judge_model": judge,
        "waves": len(reps),
        "diagrams": len(runs),
        "runs": len(flat),
        "n_per_diagram": {
            "min": min(ns), "max": max(ns),
            "n>=6": sum(1 for n in ns if n >= 6),
        },
        "r_runs": round(
            _pearson(
                [composites[r["label"]] for r in flat],
                [float(r["fidelity"]) for r in flat],
            ), 3,
        ),
        "per_diagram": {
            "r_raw": round(_pearson(d_comps, d_fids), 3),
            "r_partial_given_hard_demand": round(_partial(d_comps, d_fids, d_hard), 3),
        },
    }


def judge_agreement(base: dict, rejudge: dict) -> dict | None:
    """Fidelity agreement between two judges over the same artifacts."""
    a = {(r["label"], r["run"]): r for r in base["runs"] if "error" not in r}
    b = {(r["label"], r["run"]): r for r in rejudge["runs"] if "error" not in r}
    shared = sorted(set(a) & set(b))
    if len(shared) < 3:
        return None
    fa = [float(a[k]["judge"]["fidelity_score"]) for k in shared]
    fb = [float(b[k]["judge"]["fidelity_score"]) for k in shared]
    return {
        "judges": [base["judge_model"], rejudge["judge_model"]],
        "shared_runs": len(shared),
        "r_fidelity": round(_pearson(fa, fb), 3),
        "mean_fidelity": [round(sum(fa) / len(fa), 1), round(sum(fb) / len(fb), 1)],
        "mean_abs_diff": round(sum(abs(x - y) for x, y in zip(fa, fb)) / len(fa), 1),
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    paths = [Path(p).resolve() for p in argv] or sorted(
        {RESULTS_DIR / "report.json", *RESULTS_DIR.glob("*/report.json")}
    )
    reports = {p: json.loads(p.read_text(encoding="utf-8")) for p in paths if p.exists()}
    if not reports:
        print("no reports found", file=sys.stderr)
        return 2

    out: dict = {"waves": {}, "judge_agreement": []}
    for p, rep in reports.items():
        key = str(p.relative_to(REPO_ROOT))
        out["waves"][key] = analyze_wave(rep)
    out["pooled_same_config"] = pooled_same_config(list(reports.values()))

    # Judge agreement: pair each re-judge wave with exactly the report it
    # re-judged (its rejudge_of) — label+run keys only identify artifacts
    # within that pair, not across independent waves.
    by_path = {str(p): rep for p, rep in reports.items()}
    for rep in reports.values():
        base = by_path.get(str(Path(rep["rejudge_of"]).resolve())) if rep.get("rejudge_of") else None
        if base is not None:
            agr = judge_agreement(base, rep)
            if agr:
                out["judge_agreement"].append(agr)

    dest = RESULTS_DIR / "analysis.json"
    dest.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    for key, w in out["waves"].items():
        print(f"\n== {key}  (gen={w['gen_model']}, judge={w['judge_model']}, "
              f"n={w['runs']} runs / {w['diagrams']} diagrams)")
        print(f"  r(composite, fidelity)                 = {w['r_raw']}")
        print(f"  r(fidelity, demand)                    = {w['r_fidelity_demand']}")
        print(f"  r(composite, fidelity | demand)        = {w['r_partial_given_demand']}")
        print(f"  r(composite, fidelity | hard demand)   = {w['r_partial_given_hard_demand']}")
        pd = w["per_diagram"]
        print(f"  per-diagram: r={pd['r_raw']}  |demand={pd['r_partial_given_demand']}"
              f"  |hard={pd['r_partial_given_hard_demand']}")
        for name, t in w["terciles"].items():
            print(f"  {name:>4} demand {t['demand_range']}: r={t['r']}  "
                  f"mean fidelity {t['mean_fidelity']}  (n={t['n']})")
        c = w["cliff"]
        print(f"  cliff: <40 fidelity {c['below_40']['mean_fidelity']} "
              f"(invented {c['below_40']['invented_per_run']}/run, n={c['below_40']['runs']})"
              f"  vs >=40 fidelity {c['at_or_above_40']['mean_fidelity']} "
              f"(invented {c['at_or_above_40']['invented_per_run']}/run)")
    pooled = out["pooled_same_config"]
    if pooled:
        print(f"\n== pooled ({pooled['gen_model']}/{pooled['judge_model']}, "
              f"{pooled['waves']} waves): {pooled['runs']} runs / "
              f"{pooled['diagrams']} diagrams, n {pooled['n_per_diagram']['min']}"
              f"-{pooled['n_per_diagram']['max']} "
              f"({pooled['n_per_diagram']['n>=6']} diagrams at n>=6)")
        print(f"  r(runs)={pooled['r_runs']}  per-diagram r={pooled['per_diagram']['r_raw']}"
              f"  |hard demand={pooled['per_diagram']['r_partial_given_hard_demand']}")
    for agr in out["judge_agreement"]:
        print(f"\n== judge agreement {agr['judges'][0]} vs {agr['judges'][1]} "
              f"({agr['shared_runs']} shared runs)")
        print(f"  r={agr['r_fidelity']}  means={agr['mean_fidelity']}  "
              f"mean |diff|={agr['mean_abs_diff']}")
    print(f"\nwrote {dest.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

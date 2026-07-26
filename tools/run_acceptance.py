"""Execution oracle parent: run the acceptance suites over a wave's artifacts.

For every stored generated module of a family diagram (order_payment,
credit_intake, insurance_claim — synthetic/wild have no suite and are
skipped), run every family scenario in a sandboxed child process
(`python -I tools/acceptance/runner_child.py`, sockets disabled, stdin
closed, hard timeout) and record pass/fail with its failure stage.

Zero API cost: this executes code already on disk.

Usage:
  python tools/run_acceptance.py --wave main2=experiment_results/wave_main2/report.json
  python tools/run_acceptance.py --wave original=experiment_results/report.json \
      --wave gen_haiku=experiment_results/wave_gen_haiku/report.json
  # calibration (pre-registered protocol: pristine-L5 artifacts only):
  python tools/run_acceptance.py --wave main2=... --only-label L5_order_payment_codegen_good

Output: execution_results/<wave>/execution.json with per-(run, scenario)
rows joined with the wave report's metadata (level, composite, judge
fidelity, hard demand) so the analyzer needs no further joins.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from acceptance import suites  # noqa: E402

CHILD = Path(__file__).resolve().parent / "acceptance" / "runner_child.py"
OUT_ROOT = REPO_ROOT / "execution_results"
TIMEOUT_S = 15


def run_child(artifact: Path, spec: dict) -> dict:
    payload = base64.b64encode(json.dumps(spec).encode()).decode()
    try:
        proc = subprocess.run(
            [sys.executable, "-I", str(CHILD), str(artifact), payload],
            capture_output=True, text=True, timeout=TIMEOUT_S,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return {"stage": "timeout", "passed": False, "outcome_class": None,
                "entry": None, "calls": [], "configs_applied": {},
                "detail": f"killed after {TIMEOUT_S}s"}
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    if not lines:
        return {"stage": "harness_error", "passed": False, "outcome_class": None,
                "entry": None, "calls": [], "configs_applied": {},
                "detail": (proc.stderr or "no output")[:300]}
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return {"stage": "harness_error", "passed": False, "outcome_class": None,
                "entry": None, "calls": [], "configs_applied": {},
                "detail": ("unparseable: " + lines[-1])[:300]}


def hard_demand(judge: dict) -> int:
    return int(judge.get("guards_expected", 0)) + int(
        judge.get("failure_paths_expected", 0))


def process_wave(name: str, report_path: Path, only_labels, only_sub) -> Path:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    art_dir = report_path.parent
    meta = {u["label"]: u for u in report["selected"]}

    jobs = []  # (label, run_idx, scenario, artifact_path, spec, run_row)
    skipped_no_family = set()
    for r in report["runs"]:
        if "error" in r:
            continue
        label = r["label"]
        u = meta.get(label)
        fam = suites.family_of(u["path"]) if u else None
        if fam is None:
            skipped_no_family.add(label)
            continue
        if only_labels and label not in only_labels:
            continue
        if only_sub and not any(s in label for s in only_sub):
            continue
        artifact = art_dir / r["code_file"]
        if not artifact.exists():
            continue
        for scen in suites.FAMILIES[fam]["scenarios"]:
            jobs.append((label, r["run"], scen, artifact,
                         suites.build_spec(fam, scen), r))

    print(f"[{name}] {len(jobs)} scenario runs over "
          f"{len({(j[0], j[1]) for j in jobs})} artifacts "
          f"({len(skipped_no_family)} non-family diagrams skipped)")

    rows = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {
            pool.submit(run_child, artifact, spec): (label, run_idx, scen, spec, rr)
            for label, run_idx, scen, artifact, spec, rr in jobs
        }
        for fut, (label, run_idx, scen, spec, rr) in futs.items():
            res = fut.result()
            u = meta[label]
            rows.append({
                "label": label, "run": run_idx, "scenario": scen,
                "family": spec["family"], "path": u["path"],
                "level": u["level"], "composite": u["composite"],
                "judge_fidelity": rr.get("judge", {}).get("fidelity_score"),
                "hard_demand": hard_demand(rr.get("judge", {})),
                **{k: res.get(k) for k in
                   ("stage", "passed", "outcome_class", "entry", "detail")},
                "configs_applied": res.get("configs_applied", {}),
            })

    # per-artifact and per-diagram aggregates
    per_artifact: dict = {}
    for row in rows:
        key = (row["label"], row["run"])
        a = per_artifact.setdefault(key, {"n": 0, "passed": 0})
        a["n"] += 1
        a["passed"] += bool(row["passed"])
    per_diagram: dict = {}
    for (label, _run), a in per_artifact.items():
        d = per_diagram.setdefault(label, {"scenarios": 0, "passed": 0, "artifacts": 0})
        d["scenarios"] += a["n"]
        d["passed"] += a["passed"]
        d["artifacts"] += 1
    diagrams = [
        {
            "label": label, "level": meta[label]["level"],
            "composite": meta[label]["composite"],
            "family": suites.family_of(meta[label]["path"]),
            "artifacts": d["artifacts"], "scenario_runs": d["scenarios"],
            "pass_rate": round(d["passed"] / d["scenarios"], 3) if d["scenarios"] else None,
        }
        for label, d in sorted(per_diagram.items())
    ]

    out_dir = OUT_ROOT / name
    out_dir.mkdir(parents=True, exist_ok=True)
    out = {
        "wave": name, "report": str(report_path.relative_to(REPO_ROOT))
        if report_path.is_relative_to(REPO_ROOT) else str(report_path),
        "gen_model": report.get("gen_model"),
        "judge_model": report.get("judge_model"),
        "suite_version": "phase-a-frozen",
        "rows": sorted(rows, key=lambda r: (r["label"], r["run"], r["scenario"])),
        "per_diagram": diagrams,
    }
    out_path = out_dir / "execution.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    total = len(rows)
    passed = sum(bool(r["passed"]) for r in rows)
    stages: dict = {}
    for r in rows:
        stages[r["stage"]] = stages.get(r["stage"], 0) + 1
    print(f"[{name}] {passed}/{total} scenario runs passed; stages: "
          + ", ".join(f"{k}={v}" for k, v in sorted(stages.items())))
    print(f"[{name}] -> {out_path}")
    return out_path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run acceptance suites over wave artifacts")
    ap.add_argument("--wave", action="append", required=True,
                    metavar="NAME=REPORT_JSON")
    ap.add_argument("--only-label", action="append", default=[],
                    help="exact artifact label filter (calibration protocol)")
    ap.add_argument("--only", action="append", default=[],
                    help="substring label filter")
    args = ap.parse_args(argv)
    for w in args.wave:
        name, _, path = w.partition("=")
        if not path:
            ap.error(f"--wave needs NAME=REPORT_JSON, got {w!r}")
        process_wave(name, (REPO_ROOT / path).resolve(),
                     set(args.only_label), args.only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

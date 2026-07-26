"""Agent-repair wave driver (EVIDENCE.md §Agent-repair wave).

Measures the interventional claim behind docs/agents.md: repair a degraded
diagram from the pumllint gap report alone (no author available), then
generate and execute — does executed correctness recover, and how far?

Phases:
  R  repair   — deterministic `pumllint fix`, then <= 2 sonnet-5 repair
                passes per target, gap-report-driven; repaired diagrams and
                a structured repair log land in experiment_results/wave_repair/.
  G  generate — the stored wave-main2 configuration exactly (opus-4-8,
                legacy prompt, 3 runs, sonnet-5 judge) over the 16 repaired
                diagrams plus the 2 targets with no stored degraded baseline.
Execution of the frozen acceptance suites is tools/run_acceptance.py's job;
analysis against X-R1..X-R4 is tools/analyze_repair.py's.

Run:  python tools/agent_repair.py [--dry-run] [--skip-repair]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import codegen_experiment as ce  # noqa: E402

REPAIR_MODEL = "claude-sonnet-5"
GEN_MODEL = "claude-opus-4-8"
JUDGE_MODEL = "claude-sonnet-5"
PROMPT_VARIANT = "legacy"          # matches wave_main2 / original exactly
RUNS = 3
WAVE_DIR = REPO_ROOT / "experiment_results" / "wave_repair"
REPAIRED_DIR = WAVE_DIR / "repaired"
REPAIR_CEILING_USD = 6.0           # abort before Phase G if repairs cost more
FRESH_BASELINE_LABELS = {          # targets absent from original AND main2
    "L2_credit_intake_good__S-drop_title",
    "L2_order_payment_codegen_good__L6",
}

REPAIR_PROMPT = """\
You are a coding agent following the pumllint repair protocol \
(docs/agents.md). You were about to implement the PlantUML sequence \
diagram below, but the pumllint maturity gate failed. Repair the diagram \
so that it passes.

The repair covenant (lab mode):
- Work the gap report top-down and fix every finding: declare implicit \
participants with typed keywords or stereotypes, turn prose message \
labels into operation signatures, replace vague or empty guards with \
concrete conditions, add missing return arrows naming the returned \
value, add failure paths for external/database/queue calls, replace \
elision markers (`...`, `TBD`) by specifying the elided behavior, \
balance activations, label blocks, add the missing title/name.
- Normally, decisions the diagram does not contain must come from its \
author. No author is available in this session. Where a decision is \
missing, choose the most domain-plausible resolution — and record every \
such invented decision in the repair log.
- Preserve everything the diagram already specifies: participants, \
message order, guard meanings, data names. Repair is additive and \
clarifying, never a redesign.
- Do not add pumllint suppression comments.

Gap report (pumllint score --profile codegen -f json):
{gap_json}

Diagram:
{diagram}

Output exactly: the full repaired PlantUML source from @startuml to \
@enduml (no markdown fences), then on a new line `REPAIR_LOG:` followed \
by a single JSON object of the form \
{{"invented_decisions": ["<one entry per decision the diagram did not \
contain>"], "notes": "<anything else worth recording>"}}.
"""


def _cli(args: list[str]) -> subprocess.CompletedProcess:
    """Run the pumllint CLI from a config-free cwd (the wave dir) so the
    repository's own pumllint.toml cannot leak into scoring."""
    import os
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT))
    return subprocess.run(
        [sys.executable, "-m", "pumllint", *args],
        capture_output=True, text=True, cwd=WAVE_DIR, env=env, timeout=120,
    )


def score_json(path: Path) -> dict:
    """First diagram's maturity object via the public JSON contract."""
    proc = _cli(["score", str(path), "--profile", "codegen", "-f", "json"])
    report = json.loads(proc.stdout)
    return report["diagrams"][0]["maturity"]


def parse_repair_output(text: str) -> tuple[str | None, dict]:
    m = re.search(r"(@startuml.*?@enduml)", text, flags=re.DOTALL)
    diagram = m.group(1) + "\n" if m else None
    log: dict = {"invented_decisions": [], "notes": ""}
    lm = re.search(r"REPAIR_LOG:\s*(\{.*\})", text, flags=re.DOTALL)
    if lm:
        try:
            log = json.loads(lm.group(1))
        except json.JSONDecodeError:
            log = {"invented_decisions": [], "notes": "unparseable repair log"}
    return diagram, log


def _repair_call(client, prompt: str, usage: dict):
    """One repair call; retries transient API errors with backoff."""
    import time
    delay = 20.0
    for attempt in range(3):
        try:
            return ce._call(
                client, REPAIR_MODEL, usage, max_tokens=12000,
                **ce._thinking(REPAIR_MODEL),
                messages=[{"role": "user", "content": prompt}])
        except Exception:
            if attempt == 2:
                raise
            time.sleep(delay)
            delay *= 2


def repair_one(client, unit: dict, usage: dict) -> dict:
    """Fix + <=2 LLM repair passes for one target. Returns the repair record."""
    stem = Path(unit["path"]).stem
    out_path = REPAIRED_DIR / f"{stem}.puml"
    out_path.write_text(
        (REPO_ROOT / unit["path"]).read_text(encoding="utf-8"), encoding="utf-8")

    rec: dict = {
        "orig_label": unit["label"], "orig_level": unit["level"],
        "orig_composite": unit["composite"], "orig_path": unit["path"],
        "repaired_path": str(out_path.relative_to(REPO_ROOT)),
        "passes": [], "invented_decisions": [], "mechanical_retries": 0,
    }

    _cli(["fix", str(out_path)])                      # recipe step: pumllint fix
    m = score_json(out_path)
    rec["after_fix"] = {"level": m["level"], "composite": m["score"]}

    for pass_no in (1, 2):
        if m["level"] >= 5 or (pass_no == 2 and m["level"] >= 4):
            break
        prompt = REPAIR_PROMPT.format(
            gap_json=json.dumps(
                {"level": m["level"], "levelName": m["levelName"],
                 "score": m["score"], "gapReport": m["gapReport"]}, indent=1),
            diagram=out_path.read_text(encoding="utf-8"),
        )
        diagram, log = None, {}
        for attempt in (1, 2, 3):     # tolerate empty/truncated model output
            resp = _repair_call(client, prompt, usage)
            # A max_tokens-exhausted adaptive-thinking response can contain
            # no text block at all — join() instead of next() so that case
            # lands in the mechanical retry, not a StopIteration.
            text = "".join(b.text for b in resp.content if b.type == "text")
            diagram, log = parse_repair_output(text)
            if diagram:
                break
            rec["mechanical_retries"] += 1
        if not diagram:
            rec["passes"].append({"pass": pass_no, "error": "no diagram in output"})
            break
        out_path.write_text(diagram, encoding="utf-8")
        m = score_json(out_path)
        rec["passes"].append({
            "pass": pass_no, "level": m["level"], "composite": m["score"],
            "invented": len(log.get("invented_decisions", [])),
        })
        rec["invented_decisions"].extend(log.get("invented_decisions", []))

    rec["final"] = {"level": m["level"], "composite": m["score"]}
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Agent-repair evidence wave")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-repair", action="store_true",
                    help="reuse existing repaired/ + repair_log.json")
    args = ap.parse_args(argv)

    targets = [u for u in ce.select_diagrams(8, families_only=True)
               if u["level"] <= 2]
    if len(targets) != 16:
        print(f"error: expected 16 targets, selection returned {len(targets)}",
              file=sys.stderr)
        return 2
    fresh = [u for u in targets if u["label"] in FRESH_BASELINE_LABELS]
    if len(fresh) != len(FRESH_BASELINE_LABELS):
        print("error: fresh-baseline labels not found in selection", file=sys.stderr)
        return 2

    n_repair_calls = len(targets) * 2                 # worst case
    n_gen_calls = (len(targets) + len(fresh)) * RUNS * 2
    print(f"Agent-repair wave plan: {len(targets)} repairs "
          f"(<= {n_repair_calls} calls, {REPAIR_MODEL}) + "
          f"{len(targets) + len(fresh)} diagrams x {RUNS} runs "
          f"({n_gen_calls} calls; gen={GEN_MODEL}, judge={JUDGE_MODEL}, "
          f"prompt={PROMPT_VARIANT})")
    for u in targets:
        tag = " [+fresh degraded baseline]" if u["label"] in FRESH_BASELINE_LABELS else ""
        print(f"  L{u['level']} {u['composite']:5.1f} {u['path']}{tag}")
    if n_gen_calls + n_repair_calls > ce.MAX_CALLS:
        print("error: plan exceeds the cost guard", file=sys.stderr)
        return 2
    if args.dry_run:
        print("(dry run — no API calls made)")
        return 0

    ce.GEN_MODEL, ce.JUDGE_MODEL = GEN_MODEL, JUDGE_MODEL
    ce.ACTIVE_PROMPT = ce.PROMPTS[PROMPT_VARIANT]
    ce.RESULTS_DIR = WAVE_DIR
    err = ce._require_credentials()
    if err:
        print(f"error: {err}.", file=sys.stderr)
        return 2
    import anthropic

    client = anthropic.Anthropic()
    WAVE_DIR.mkdir(parents=True, exist_ok=True)
    REPAIRED_DIR.mkdir(parents=True, exist_ok=True)
    usage: dict = {}

    # ---- Phase R: repair --------------------------------------------------
    log_path = WAVE_DIR / "repair_log.json"
    if args.skip_repair and log_path.exists():
        repair_log = json.loads(log_path.read_text(encoding="utf-8"))
        print(f"(reusing {len(repair_log['repairs'])} repairs from {log_path})")
    else:
        repairs: list[dict] = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            futs = {pool.submit(repair_one, client, u, usage): u["label"]
                    for u in targets}
            for fut, label in futs.items():
                try:
                    rec = fut.result()
                    repairs.append(rec)
                    print(f"  repaired {label}: L{rec['orig_level']} -> "
                          f"L{rec['final']['level']} "
                          f"({len(rec['invented_decisions'])} invented)")
                except Exception as e:  # noqa: BLE001 — record and continue
                    repairs.append({"orig_label": label,
                                    "error": f"{type(e).__name__}: {e}"})
                    print(f"  FAIL repair {label}: {e}", file=sys.stderr)
        repair_cost = sum(
            u["in"] / 1e6 * ce.PRICES[m][0] + u["out"] / 1e6 * ce.PRICES[m][1]
            for m, u in usage.items())
        repair_log = {
            "repair_model": REPAIR_MODEL, "max_passes": 2,
            "repairs": sorted(repairs, key=lambda r: r["orig_label"]),
            "repair_cost_usd": round(repair_cost, 2),
        }
        log_path.write_text(json.dumps(repair_log, indent=2) + "\n",
                            encoding="utf-8")
        print(f"Phase R done: ${repair_cost:.2f} -> {log_path}")
        if repair_cost > REPAIR_CEILING_USD:
            print("error: repair phase exceeded its ceiling — investigate "
                  "before generating", file=sys.stderr)
            return 2

    # ---- Phase G: generate + judge (wave_main2 config) --------------------
    ok_repairs = [r for r in repair_log["repairs"] if "error" not in r]
    units: list[dict] = []
    for r in ok_repairs:
        m = score_json(REPO_ROOT / r["repaired_path"])
        units.append({
            "path": r["repaired_path"],
            "label": f"R_{r['orig_label']}"[:60],
            "level": m["level"], "composite": round(m["score"], 1),
            "elements": r.get("elements", 0),
            "orig_label": r["orig_label"], "orig_level": r["orig_level"],
            "orig_composite": r["orig_composite"],
        })
    units.extend({**u, "orig_label": u["label"], "orig_level": u["level"],
                  "orig_composite": u["composite"], "fresh_baseline": True}
                 for u in fresh)

    tasks = [(u, i) for u in units for i in range(1, RUNS + 1)]
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=ce._workers()) as pool:
        futs = {pool.submit(ce._run_one, client, u, i, usage): (u["label"], i)
                for u, i in tasks}
        for fut, (label, i) in futs.items():
            try:
                results.append(fut.result())
                print(f"  done {label} run{i}")
            except Exception as e:  # noqa: BLE001
                results.append({"label": label, "run": i,
                                "error": f"{type(e).__name__}: {e}"})
                print(f"  FAIL {label} run{i}: {e}", file=sys.stderr)

    per_diagram, per_level = ce._aggregate(units, results)
    cost = sum(
        u["in"] / 1e6 * ce.PRICES[m][0] + u["out"] / 1e6 * ce.PRICES[m][1]
        for m, u in usage.items())
    report = {
        "wave": "agent_repair",
        "gen_model": GEN_MODEL, "judge_model": JUDGE_MODEL,
        "repair_model": REPAIR_MODEL, "runs_per_diagram": RUNS,
        "prompt_variant": PROMPT_VARIANT,
        "selected": units, "per_level": per_level, "per_diagram": per_diagram,
        "runs": results, "usage": usage, "cost_usd": round(cost, 2),
        "failures": [r for r in results if "error" in r],
    }
    (WAVE_DIR / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\ncost so far (repair + generation): ${cost:.2f}")
    print(f"report: {WAVE_DIR / 'report.json'}")
    print("next: python tools/run_acceptance.py --wave "
          "repair=experiment_results/wave_repair/report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

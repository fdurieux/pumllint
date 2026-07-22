"""Phase 10e full experiment: does maturity level predict codegen outcome?

Definitive harness for the maturity->codegen experiments. Its 12-run pilot
predecessor is retired (raw pilot data: pilot_results/report.json); this
version carries the refinements the pilot identified:

- **Independent judge**: generation on claude-opus-4-8, judging on
  claude-sonnet-5 (no same-model self-judging bias).
- **stop_reason recorded** for every call; generations that fail to compile
  or are truncated (max_tokens) are retried once, with both attempts logged.
- **Split hallucination rubric**: `invented_business_logic` (harmful — rules,
  endpoints, semantics the diagram never specified) vs
  `defensive_embellishments` (benign — validation/guard-rails around
  specified behavior).
- **Corpus-wide selection**: every sequence diagram in examples/ + corpus/
  (mutations, synthetic, wild) with >= 3 elements, scored under the codegen
  profile, bucketed by level, up to 8 evenly spaced picks per level.

Pre-registered expectations (written before the run):
  E1. Mean judge fidelity increases with maturity level.
  E2. Invented-business-logic count decreases as level increases.
  E3. Composite score correlates positively with per-run fidelity (Pearson).
The generation prompt is unchanged from the pilot for comparability.

Cost guard: aborts if the plan exceeds 300 API calls (~$25).

Run:  python tools/codegen_experiment.py [--dry-run] [--runs N] [--per-level N]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling tool modules

import _scorelib  # noqa: E402

GEN_MODEL = "claude-opus-4-8"
JUDGE_MODEL = "claude-sonnet-5"
PRICES = {  # $/M tokens (input, output)
    GEN_MODEL: (5.00, 25.00),
    JUDGE_MODEL: (3.00, 15.00),
}
RESULTS_DIR = REPO_ROOT / "experiment_results"
MAX_CALLS = 300

GEN_PROMPT = """\
Implement the following PlantUML sequence diagram as a single self-contained \
Python module.

Rules:
- One class per participant; each message becomes a method call from the \
source participant's class to the target's.
- alt/opt guards become conditionals; loop becomes a loop.
- Failure/error paths become raised exceptions or error returns.
- Where the diagram is ambiguous or incomplete, make your best guess and \
implement something concrete.
- Output ONLY Python code. No markdown fences, no prose.

Diagram:

{diagram}
"""

JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "participants_expected": {"type": "integer"},
        "participants_implemented": {"type": "integer"},
        "messages_expected": {"type": "integer"},
        "messages_implemented": {"type": "integer"},
        "guards_expected": {"type": "integer"},
        "guards_faithful": {"type": "integer"},
        "failure_paths_expected": {"type": "integer"},
        "failure_paths_implemented": {"type": "integer"},
        "invented_business_logic": {"type": "array", "items": {"type": "string"}},
        "defensive_embellishments": {"type": "array", "items": {"type": "string"}},
        "fidelity_score": {"type": "integer"},
        "notes": {"type": "string"},
    },
    "required": [
        "participants_expected", "participants_implemented",
        "messages_expected", "messages_implemented",
        "guards_expected", "guards_faithful",
        "failure_paths_expected", "failure_paths_implemented",
        "invented_business_logic", "defensive_embellishments",
        "fidelity_score", "notes",
    ],
}

JUDGE_PROMPT = """\
You are auditing whether generated code faithfully implements a PlantUML \
sequence diagram. The DIAGRAM is ground truth; the CODE is under audit.

Count in the diagram: participants, messages (arrows), guards (alt/opt/loop \
conditions), and failure/error paths. Then count how many of each the code \
actually realizes (a message is realized if the corresponding interaction \
happens between the corresponding components; a guard is faithful if the \
condition's meaning is preserved).

Separate the code's inventions into two lists:
- invented_business_logic: behavior with domain meaning that the diagram \
never specified — invented business rules, thresholds, endpoints, state \
transitions, or a concrete meaning assigned to a vague label. These are \
harmful: they look intentional but are the generator's guess.
- defensive_embellishments: benign engineering the diagram didn't ask for \
but that adds no domain semantics — input validation around specified \
behavior, logging, type checks, constructors.

fidelity_score: 0-100 overall — 100 means the code is a faithful, complete \
realization; deduct for missing interactions, altered guard semantics, and \
invented business logic (embellishments cost little).

DIAGRAM:
{diagram}

CODE:
{code}
"""


def _strip_fences(text: str) -> str:
    m = re.search(r"```(?:python)?\n(.*?)```", text, flags=re.DOTALL)
    return m.group(1) if m else text


def _compiles(code: str) -> tuple[bool, str | None]:
    try:
        compile(code, "<generated>", "exec")
        return True, None
    except SyntaxError as e:
        return False, str(e)


def select_diagrams(per_level: int) -> list[dict]:
    pool: list[dict] = []
    paths = _scorelib.collect_puml(
        REPO_ROOT / "examples",
        REPO_ROOT / "corpus/mutations",
        REPO_ROOT / "corpus/synthetic",
        REPO_ROOT / "corpus/wild",
    )
    for p in paths:
        entry = _scorelib.lint_first_diagram(p, "codegen")
        if entry is None:
            continue
        d, _violations = entry
        if d.diagram_type != "sequence" or d.element_count < 3:
            continue
        r = _scorelib.score_first_diagram(p, "codegen")
        rel = str(Path(p).relative_to(REPO_ROOT))
        pool.append({
            "path": rel,
            "label": f"L{r.level}_{Path(p).stem}"[:60],
            "level": r.level,
            "composite": round(r.composite, 1),
            "elements": r.element_count,
        })

    selected: list[dict] = []
    for level in (5, 4, 3, 2, 1):
        bucket = sorted(
            (u for u in pool if u["level"] == level),
            key=lambda u: (u["composite"], u["path"]),
        )
        if len(bucket) <= per_level:
            selected.extend(bucket)
        else:  # evenly spaced across the composite range, deterministic
            idx = sorted({
                round(i * (len(bucket) - 1) / max(1, per_level - 1))
                for i in range(per_level)
            })
            selected.extend(bucket[i] for i in idx)

    # Labels are the sole downstream join key (aggregation, correlation,
    # output filenames) — force uniqueness after stem-truncation.
    seen: dict[str, int] = {}
    for u in selected:
        n = seen.get(u["label"], 0)
        seen[u["label"]] = n + 1
        if n:
            u["label"] = f"{u['label']}~{n}"
    return selected


_USAGE_LOCK = threading.Lock()  # usage is shared across the worker pool


def _call(client, model: str, usage: dict, **kwargs):
    resp = client.messages.create(model=model, **kwargs)
    with _USAGE_LOCK:  # += is a non-atomic read-modify-write across threads
        u = usage.setdefault(model, {"in": 0, "out": 0})
        u["in"] += resp.usage.input_tokens
        u["out"] += resp.usage.output_tokens
    return resp


def _generate(client, diagram_text: str, usage: dict) -> dict:
    resp = _call(
        client, GEN_MODEL, usage,
        max_tokens=12000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": GEN_PROMPT.format(diagram=diagram_text)}],
    )
    code = _strip_fences(
        next(b.text for b in resp.content if b.type == "text")
    ).strip()
    ok, err = _compiles(code)
    return {"code": code, "stop_reason": resp.stop_reason, "compiles": ok, "syntax_error": err}


def _run_one(client, unit: dict, run_idx: int, usage: dict) -> dict:
    diagram_text = (REPO_ROOT / unit["path"]).read_text(encoding="utf-8")
    out: dict = {"label": unit["label"], "run": run_idx}

    attempt = _generate(client, diagram_text, usage)
    out["compile_first_try"] = attempt["compiles"]
    retried = False
    if not attempt["compiles"] or attempt["stop_reason"] == "max_tokens":
        retried = True
        second = _generate(client, diagram_text, usage)
        # Keep the better artifact: compiling beats non-compiling, then
        # non-truncated beats truncated; ties keep the first attempt.
        rank = lambda a: (a["compiles"], a["stop_reason"] != "max_tokens")  # noqa: E731
        attempt = max((attempt, second), key=rank)
    out["retried"] = retried
    out["gen_stop_reason"] = attempt["stop_reason"]  # describes the KEPT artifact
    out["compiles"] = attempt["compiles"]
    if attempt["syntax_error"]:
        out["syntax_error"] = attempt["syntax_error"]

    code_file = RESULTS_DIR / f"{unit['label']}_run{run_idx}.py"
    code_file.write_text(attempt["code"] + "\n", encoding="utf-8")
    out["code_file"] = code_file.name

    judge = _call(
        client, JUDGE_MODEL, usage,
        max_tokens=6000,
        thinking={"type": "adaptive"},
        output_config={"format": {"type": "json_schema", "schema": JUDGE_SCHEMA}},
        messages=[{
            "role": "user",
            "content": JUDGE_PROMPT.format(diagram=diagram_text, code=attempt["code"]),
        }],
    )
    out["judge_stop_reason"] = judge.stop_reason
    out["judge"] = json.loads(next(b.text for b in judge.content if b.type == "text"))
    return out


def _aggregate(selected: list[dict], results: list[dict]) -> tuple[list[dict], list[dict]]:
    per_diagram = []
    for u in selected:
        rs = [r for r in results if r["label"] == u["label"] and "error" not in r]
        if not rs:
            per_diagram.append({**u, "runs_ok": 0})
            continue
        n = len(rs)
        per_diagram.append({
            **u,
            "runs_ok": n,
            "compile_first_try": round(sum(r["compile_first_try"] for r in rs) / n, 2),
            "compile_final": round(sum(r["compiles"] for r in rs) / n, 2),
            "mean_fidelity": round(sum(r["judge"]["fidelity_score"] for r in rs) / n, 1),
            "mean_guard_faith": round(
                sum(
                    r["judge"]["guards_faithful"] / max(1, r["judge"]["guards_expected"])
                    for r in rs
                ) / n, 2,
            ),
            "invented_per_run": round(
                sum(len(r["judge"]["invented_business_logic"]) for r in rs) / n, 2
            ),
            "embellish_per_run": round(
                sum(len(r["judge"]["defensive_embellishments"]) for r in rs) / n, 2
            ),
        })

    per_level = []
    for level in (5, 4, 3, 2, 1):
        ds = [d for d in per_diagram if d["level"] == level and d["runs_ok"]]
        if not ds:
            continue
        per_level.append({
            "level": level,
            "diagrams": len(ds),
            "runs": sum(d["runs_ok"] for d in ds),
            "compile_first_try": round(
                sum(d["compile_first_try"] * d["runs_ok"] for d in ds)
                / sum(d["runs_ok"] for d in ds), 2,
            ),
            "mean_fidelity": round(
                sum(d["mean_fidelity"] * d["runs_ok"] for d in ds)
                / sum(d["runs_ok"] for d in ds), 1,
            ),
            "mean_guard_faith": round(
                sum(d["mean_guard_faith"] * d["runs_ok"] for d in ds)
                / sum(d["runs_ok"] for d in ds), 2,
            ),
            "invented_per_run": round(
                sum(d["invented_per_run"] * d["runs_ok"] for d in ds)
                / sum(d["runs_ok"] for d in ds), 2,
            ),
            "embellish_per_run": round(
                sum(d["embellish_per_run"] * d["runs_ok"] for d in ds)
                / sum(d["runs_ok"] for d in ds), 2,
            ),
        })
    return per_diagram, per_level


def _ensure_corpus() -> None:
    corpus = REPO_ROOT / "corpus"
    if not (corpus / "manifest.json").exists():
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import gen_corpus

        gen_corpus.generate(corpus)
        print(f"(generated corpus at {corpus})")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Maturity -> codegen-outcome experiment")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--per-level", type=int, default=8)
    args_ns = ap.parse_args(argv)
    dry_run, runs, per_level = args_ns.dry_run, args_ns.runs, args_ns.per_level

    _ensure_corpus()  # corpus/ is gitignored; a fresh clone must still work
    selected = select_diagrams(per_level)
    composites = {}
    for u in selected:
        composites[u["label"]] = u["composite"]
    n_calls = len(selected) * runs * 2
    by_level: dict[int, int] = {}
    for u in selected:
        by_level[u["level"]] = by_level.get(u["level"], 0) + 1

    print(f"Experiment plan: {len(selected)} diagrams x {runs} runs "
          f"({n_calls} calls; gen={GEN_MODEL}, judge={JUDGE_MODEL})")
    print(f"  per level: { {f'L{k}': v for k, v in sorted(by_level.items(), reverse=True)} }")
    for u in selected:
        print(f"  L{u['level']} {u['composite']:5.1f} e={u['elements']:<3} {u['path']}")
    if n_calls > MAX_CALLS:
        print(f"error: plan exceeds the {MAX_CALLS}-call cost guard", file=sys.stderr)
        return 2
    if dry_run:
        print("(dry run — no API calls made)")
        return 0
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("error: no API credentials in the environment.", file=sys.stderr)
        return 2

    import anthropic

    client = anthropic.Anthropic()
    RESULTS_DIR.mkdir(exist_ok=True)
    usage: dict = {}

    tasks = [(u, i) for u in selected for i in range(1, runs + 1)]
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_run_one, client, u, i, usage): (u["label"], i) for u, i in tasks}
        for future, (label, i) in futures.items():
            try:
                results.append(future.result())
                print(f"  done {label} run{i}")
            except Exception as e:  # noqa: BLE001 — record and continue
                results.append({"label": label, "run": i, "error": f"{type(e).__name__}: {e}"})
                print(f"  FAIL {label} run{i}: {e}", file=sys.stderr)

    per_diagram, per_level_summary = _aggregate(selected, results)

    # E3: composite <-> fidelity correlation across individual runs.
    xs, ys = [], []
    for r in results:
        if "error" not in r:
            xs.append(composites[r["label"]])
            ys.append(r["judge"]["fidelity_score"])
    correlation = round(statistics.correlation(xs, ys), 3) if len(xs) > 2 else None

    cost = sum(
        u["in"] / 1e6 * PRICES[m][0] + u["out"] / 1e6 * PRICES[m][1]
        for m, u in usage.items()
    )
    report = {
        "gen_model": GEN_MODEL, "judge_model": JUDGE_MODEL, "runs_per_diagram": runs,
        "selected": selected,
        "per_level": per_level_summary,
        "per_diagram": per_diagram,
        "correlation_composite_fidelity": correlation,
        "runs": results,
        "usage": usage,
        "cost_usd": round(cost, 2),
        "failures": [r for r in results if "error" in r],
    }
    (RESULTS_DIR / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    print(f"\n{'level':>5} {'diag':>5} {'runs':>5} {'compile1':>9} "
          f"{'fidelity':>9} {'guards':>7} {'invented':>9} {'embellish':>10}")
    for s in per_level_summary:
        print(f"{s['level']:>5} {s['diagrams']:>5} {s['runs']:>5} "
              f"{s['compile_first_try']:>9} {s['mean_fidelity']:>9} "
              f"{s['mean_guard_faith']:>7} {s['invented_per_run']:>9} "
              f"{s['embellish_per_run']:>10}")
    print(f"\ncorrelation(composite, fidelity) = {correlation}")
    print(f"cost: ${cost:.2f}   report: {RESULTS_DIR / 'report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

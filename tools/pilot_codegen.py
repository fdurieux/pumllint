"""Phase 10e pilot: does maturity level predict codegen outcome?

Protocol (pre-registered before running):

- 4 diagrams spanning maturity levels under the codegen profile
  (L5 pristine, L4 minor structural flaw, L2 ambiguity injected, L1 degraded),
  x 3 generations each = 12 generation runs on claude-opus-4-8.
- Fixed generation prompt; ambiguity resolution is left to the model on
  purpose — that divergence is what the maturity score claims to predict.
- Per run: (a) local compile check (syntax), (b) LLM-judge fidelity scoring
  against a structured rubric (participants/messages/guards/failure paths
  covered, hallucinated behaviors, fidelity 0-100) with a JSON-schema-
  constrained response.
- Pilot success criterion: the protocol runs clean end-to-end and mean
  fidelity orders L5 > L1. (n is far too small for more than direction.)

Cost: ~24 calls, ~$1-3 at Opus 4.8 pricing. Requires ANTHROPIC_API_KEY (or
ANTHROPIC_AUTH_TOKEN) in the environment.

Run:  python tools/pilot_codegen.py [--dry-run] [--runs N]
"""

from __future__ import annotations

import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pumllint import Engine, parse_file, score  # noqa: E402

MODEL = "claude-opus-4-8"
PRICE_IN, PRICE_OUT = 5.00, 25.00  # $/M tokens, Opus 4.8
RESULTS_DIR = REPO_ROOT / "pilot_results"

# (label, path) — spanning maturity levels under the codegen profile.
DIAGRAMS = [
    ("L5-pristine", "examples/order_payment_codegen_good.puml"),
    ("L4-unbalanced", "corpus/mutations/order_payment_codegen_good__S-unbalance_activation.puml"),
    ("L2-ambiguous", "corpus/mutations/order_payment_codegen_good__L4.puml"),
    ("L1-degraded", "examples/order_payment_codegen_bad.puml"),
]

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
        "hallucinations": {"type": "array", "items": {"type": "string"}},
        "fidelity_score": {"type": "integer"},
        "notes": {"type": "string"},
    },
    "required": [
        "participants_expected", "participants_implemented",
        "messages_expected", "messages_implemented",
        "guards_expected", "guards_faithful",
        "failure_paths_expected", "failure_paths_implemented",
        "hallucinations", "fidelity_score", "notes",
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

hallucinations: behaviors the code implements that the diagram does not \
specify — invented business rules, invented endpoints, invented data \
validation. Ordinary glue code (constructors, logging, type hints) does NOT \
count.

fidelity_score: 0-100 overall — 100 means the code is a faithful, complete \
realization; deduct for missing interactions, altered guard semantics, and \
hallucinated behavior.

DIAGRAM:
{diagram}

CODE:
{code}
"""


def _strip_fences(text: str) -> str:
    m = re.search(r"```(?:python)?\n(.*?)```", text, flags=re.DOTALL)
    return m.group(1) if m else text


def _score_diagram(path: str) -> tuple[int, float]:
    d = parse_file(REPO_ROOT / path)[0]
    vs = Engine({"profile": "codegen"}).lint_diagram(d)
    r = score(vs, d, active_profile="codegen")
    return r.level, round(r.composite, 1)


def _run_one(client, label: str, path: str, run_idx: int) -> dict:
    diagram_text = (REPO_ROOT / path).read_text(encoding="utf-8")
    out: dict = {"label": label, "run": run_idx}
    usage = {"in": 0, "out": 0}

    gen = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": GEN_PROMPT.format(diagram=diagram_text)}],
    )
    usage["in"] += gen.usage.input_tokens
    usage["out"] += gen.usage.output_tokens
    code = _strip_fences(
        next(b.text for b in gen.content if b.type == "text")
    ).strip()
    code_file = RESULTS_DIR / f"{label}_run{run_idx}.py"
    code_file.write_text(code + "\n", encoding="utf-8")
    out["code_file"] = code_file.name

    try:
        compile(code, str(code_file), "exec")
        out["compiles"] = True
    except SyntaxError as e:
        out["compiles"] = False
        out["syntax_error"] = str(e)

    judge = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        thinking={"type": "adaptive"},
        output_config={"format": {"type": "json_schema", "schema": JUDGE_SCHEMA}},
        messages=[{
            "role": "user",
            "content": JUDGE_PROMPT.format(diagram=diagram_text, code=code),
        }],
    )
    usage["in"] += judge.usage.input_tokens
    usage["out"] += judge.usage.output_tokens
    verdict = json.loads(next(b.text for b in judge.content if b.type == "text"))
    out["judge"] = verdict
    out["usage"] = usage
    return out


def main(argv: list[str]) -> int:
    dry_run = "--dry-run" in argv
    runs = int(argv[argv.index("--runs") + 1]) if "--runs" in argv else 3

    plan = []
    for label, path in DIAGRAMS:
        level, composite = _score_diagram(path)
        plan.append({"label": label, "path": path, "level": level, "composite": composite})

    print(f"Pilot plan: {len(plan)} diagrams x {runs} runs on {MODEL}")
    for p in plan:
        print(f"  {p['label']:<14} L{p['level']} {p['composite']:5.1f}  {p['path']}")
    if dry_run:
        print("(dry run — no API calls made)")
        return 0

    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print(
            "error: no API credentials. Export ANTHROPIC_API_KEY (or "
            "ANTHROPIC_AUTH_TOKEN) and re-run.",
            file=sys.stderr,
        )
        return 2

    import anthropic

    client = anthropic.Anthropic()
    RESULTS_DIR.mkdir(exist_ok=True)

    tasks = [
        (p["label"], p["path"], i) for p in plan for i in range(1, runs + 1)
    ]
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(_run_one, client, label, path, i): (label, i)
            for label, path, i in tasks
        }
        for future, (label, i) in futures.items():
            try:
                results.append(future.result())
                print(f"  done {label} run{i}")
            except Exception as e:  # noqa: BLE001 — record and continue
                results.append({"label": label, "run": i, "error": f"{type(e).__name__}: {e}"})
                print(f"  FAIL {label} run{i}: {e}", file=sys.stderr)

    # Aggregate per diagram.
    summary = []
    tot_in = tot_out = 0
    for p in plan:
        rs = [r for r in results if r["label"] == p["label"] and "error" not in r]
        errs = [r for r in results if r["label"] == p["label"] and "error" in r]
        for r in rs:
            tot_in += r["usage"]["in"]
            tot_out += r["usage"]["out"]
        n = len(rs)
        agg = {
            **p,
            "runs_ok": n,
            "runs_failed": len(errs),
            "compile_rate": round(sum(r["compiles"] for r in rs) / n, 2) if n else None,
            "mean_fidelity": round(
                sum(r["judge"]["fidelity_score"] for r in rs) / n, 1
            ) if n else None,
            "mean_msg_coverage": round(
                sum(
                    r["judge"]["messages_implemented"]
                    / max(1, r["judge"]["messages_expected"])
                    for r in rs
                ) / n, 2,
            ) if n else None,
            "total_hallucinations": sum(len(r["judge"]["hallucinations"]) for r in rs),
        }
        summary.append(agg)

    cost = tot_in / 1e6 * PRICE_IN + tot_out / 1e6 * PRICE_OUT
    report = {
        "model": MODEL, "runs_per_diagram": runs,
        "summary": summary, "runs": results,
        "usage": {"input_tokens": tot_in, "output_tokens": tot_out,
                  "cost_usd": round(cost, 2)},
    }
    (RESULTS_DIR / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    print(f"\n{'diagram':<14} {'level':>5} {'comp':>6} {'compile':>8} "
          f"{'fidelity':>9} {'msg-cov':>8} {'halluc':>7}")
    for s in summary:
        print(f"{s['label']:<14} {s['level']:>5} {s['composite']:>6} "
              f"{s['compile_rate']!s:>8} {s['mean_fidelity']!s:>9} "
              f"{s['mean_msg_coverage']!s:>8} {s['total_hallucinations']:>7}")
    print(f"\ntokens: {tot_in} in / {tot_out} out -> ${cost:.2f}")
    print(f"report: {RESULTS_DIR / 'report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

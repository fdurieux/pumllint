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
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    # Cross-vendor (output price includes Gemini thinking tokens, which we
    # count as output). gemini-2.5-pro is retired for new API keys; the
    # 3.1-pro-preview rates are the ≤200k-context published figures.
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-3.1-pro-preview": (2.00, 12.00),
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

# Execution-oracle entry-point contract (EVIDENCE.md §Execution oracle,
# expectation XB). Deliberately generic: it names the request-key PATTERN
# and outcome vocabulary but never which systems or branches exist — the
# diagram (or its degraded absence) must remain the only source of that.
REQUEST_CONTRACT = """\
Additionally expose a module-level function:

    def handle(request: dict) -> dict

that runs one end-to-end flow. `request` carries the scenario input: \
entity ids and amounts, existence flags (keys like "<entity>_exists" / \
"<entity>_found"), and — where your implementation depends on an external \
system's outcome — keys of the form "<system>_result" / "<system>_status" \
whose values are short words such as "approved", "declined", "active", \
"lapsed", "stored", "assessed", "error", or a number for scores. Return a \
dict whose "status" key names the outcome (e.g. "confirmed", "rejected", \
"error: <reason>").
"""

PINNED_MINIMAL_PROMPT = """\
Implement the behavior specified by the following PlantUML sequence \
diagram as a single self-contained Python module. Where the diagram is \
ambiguous or incomplete, make your best guess and implement something \
concrete. Output ONLY Python code. No markdown fences, no prose.

""" + REQUEST_CONTRACT + """
Diagram:

{diagram}
"""

PROMPTS = {
    "legacy": GEN_PROMPT,
    "pinned_structured": GEN_PROMPT.replace(
        "\nDiagram:\n\n{diagram}",
        "\n" + REQUEST_CONTRACT + "\nDiagram:\n\n{diagram}"),
    "pinned_minimal": PINNED_MINIMAL_PROMPT,
}

FAMILY_KEYS = ("order_payment", "credit_intake", "insurance_claim")

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


def select_diagrams(per_level: int, families_only: bool = False) -> list[dict]:
    pool: list[dict] = []
    paths = _scorelib.collect_puml(
        REPO_ROOT / "examples",
        REPO_ROOT / "corpus/mutations",
        REPO_ROOT / "corpus/synthetic",
        REPO_ROOT / "corpus/wild",
    )
    if families_only:  # execution-oracle waves: only suite-covered families
        paths = [p for p in paths if any(k in str(p) for k in FAMILY_KEYS)]
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


def _thinking(model: str) -> dict:
    """Adaptive thinking where supported; omitted where not (haiku)."""
    if model.startswith("claude-haiku"):
        return {}
    return {"thinking": {"type": "adaptive"}}


def _call(client, model: str, usage: dict, **kwargs):
    resp = client.messages.create(model=model, **kwargs)
    with _USAGE_LOCK:  # += is a non-atomic read-modify-write across threads
        u = usage.setdefault(model, {"in": 0, "out": 0})
        u["in"] += resp.usage.input_tokens
        u["out"] += resp.usage.output_tokens
    return resp


# ---------------------------------------------------------------- Gemini shim
# Cross-vendor evidence wave (EVIDENCE.md §Cross-vendor). Stdlib REST only —
# no new dependency; the anthropic SDK keeps serving the Claude calls.

def _is_gemini(model: str) -> bool:
    return model.startswith("gemini")


def _gemini_schema(schema: dict):
    """JSON schema -> Gemini responseSchema subset (uppercase types, no
    additionalProperties)."""
    if not isinstance(schema, dict):
        return schema
    out = {}
    for k, v in schema.items():
        if k == "additionalProperties":
            continue
        if k == "type" and isinstance(v, str):
            out[k] = v.upper()
        elif k in ("properties",):
            out[k] = {pk: _gemini_schema(pv) for pk, pv in v.items()}
        elif k == "items":
            out[k] = _gemini_schema(v)
        else:
            out[k] = v
    return out


def _gemini_call(model: str, prompt: str, max_tokens: int, usage: dict,
                 schema: dict | None = None) -> tuple[str, str]:
    """One generateContent call. Returns (text, stop_reason). Retries
    transient throttling/5xx with backoff; thinking tokens count as output."""
    import time
    import urllib.error
    import urllib.request

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    body: dict = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    if schema is not None:
        body["generationConfig"]["responseMimeType"] = "application/json"
        body["generationConfig"]["responseSchema"] = _gemini_schema(schema)
    req = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    # framework Pythons on macOS miss the system trust store; certifi rides
    # along with the anthropic SDK this harness already requires
    import ssl
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()

    delay = 15.0
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=300, context=ctx) as r:
                resp = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and attempt < 4:
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            raise
    um = resp.get("usageMetadata", {})
    with _USAGE_LOCK:
        u = usage.setdefault(model, {"in": 0, "out": 0})
        u["in"] += um.get("promptTokenCount", 0)
        u["out"] += (um.get("candidatesTokenCount", 0)
                     + um.get("thoughtsTokenCount", 0))
    cand = resp["candidates"][0]
    text = "".join(p.get("text", "")
                   for p in cand.get("content", {}).get("parts", []))
    stop = "max_tokens" if cand.get("finishReason") == "MAX_TOKENS" else "end_turn"
    return text, stop


def _workers() -> int:
    """Gemini throttles harder than the Anthropic tier we run at."""
    return 4 if (_is_gemini(GEN_MODEL) or _is_gemini(JUDGE_MODEL)) else 8


def _require_credentials() -> str | None:
    """Return an error string if the configured models' keys are missing."""
    needs_claude = not (_is_gemini(GEN_MODEL) and _is_gemini(JUDGE_MODEL))
    if needs_claude and not (os.environ.get("ANTHROPIC_API_KEY")
                             or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        return "no Anthropic API credentials in the environment"
    if (_is_gemini(GEN_MODEL) or _is_gemini(JUDGE_MODEL)) and not (
            os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        return "no Gemini API credentials in the environment"
    return None


def _judge_call(client, diagram_text: str, code: str, usage: dict) -> tuple[dict, str]:
    """Judge one artifact with JUDGE_MODEL (Claude or Gemini); returns
    (judge dict, stop_reason)."""
    prompt = JUDGE_PROMPT.format(diagram=diagram_text, code=code)
    if _is_gemini(JUDGE_MODEL):
        text, stop = _gemini_call(JUDGE_MODEL, prompt, 6000, usage,
                                  schema=JUDGE_SCHEMA)
        return json.loads(text), stop
    resp = _call(
        client, JUDGE_MODEL, usage,
        max_tokens=6000,
        **_thinking(JUDGE_MODEL),
        output_config={"format": {"type": "json_schema", "schema": JUDGE_SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    return (json.loads(next(b.text for b in resp.content if b.type == "text")),
            resp.stop_reason)


ACTIVE_PROMPT = GEN_PROMPT  # overridden by --prompt-variant


def _generate(client, diagram_text: str, usage: dict) -> dict:
    prompt = ACTIVE_PROMPT.format(diagram=diagram_text)
    if _is_gemini(GEN_MODEL):
        text, stop_reason = _gemini_call(GEN_MODEL, prompt, 12000, usage)
    else:
        resp = _call(
            client, GEN_MODEL, usage,
            max_tokens=12000,
            **_thinking(GEN_MODEL),
            messages=[{"role": "user", "content": prompt}],
        )
        text = next(b.text for b in resp.content if b.type == "text")
        stop_reason = resp.stop_reason
    code = _strip_fences(text).strip()
    ok, err = _compiles(code)
    return {"code": code, "stop_reason": stop_reason, "compiles": ok, "syntax_error": err}


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

    judge, judge_stop = _judge_call(client, diagram_text, attempt["code"], usage)
    out["judge_stop_reason"] = judge_stop
    out["judge"] = judge
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


def _rejudge(client, base_dir: Path, base_report: dict, usage: dict) -> list[dict]:
    """Judge an earlier wave's stored artifacts with the current JUDGE_MODEL.

    Judge-only calls: generator robustness costs generation, but judge
    robustness is nearly free because every artifact is on disk.
    """
    results: list[dict] = []
    ok_runs = [r for r in base_report["runs"] if "error" not in r]
    with ThreadPoolExecutor(max_workers=_workers()) as pool:
        def one(r: dict) -> dict:
            diagram_text = (REPO_ROOT / next(
                u["path"] for u in base_report["selected"] if u["label"] == r["label"]
            )).read_text(encoding="utf-8")
            code = (base_dir / r["code_file"]).read_text(encoding="utf-8")
            judge, judge_stop = _judge_call(client, diagram_text, code, usage)
            return {
                "label": r["label"], "run": r["run"],
                "compile_first_try": r["compile_first_try"],
                "compiles": r["compiles"], "retried": r.get("retried", False),
                "gen_stop_reason": r.get("gen_stop_reason"),
                "code_file": r["code_file"],
                "judge_stop_reason": judge_stop,
                "judge": judge,
            }

        futures = {pool.submit(one, r): (r["label"], r["run"]) for r in ok_runs}
        for future, (label, i) in futures.items():
            try:
                results.append(future.result())
                print(f"  rejudged {label} run{i}")
            except Exception as e:  # noqa: BLE001 — record and continue
                results.append({"label": label, "run": i, "error": f"{type(e).__name__}: {e}"})
                print(f"  FAIL {label} run{i}: {e}", file=sys.stderr)
    return results


def main(argv: list[str] | None = None) -> int:
    global GEN_MODEL, JUDGE_MODEL, RESULTS_DIR
    ap = argparse.ArgumentParser(description="Maturity -> codegen-outcome experiment")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--per-level", type=int, default=8)
    ap.add_argument("--gen-model", default=GEN_MODEL)
    ap.add_argument("--judge-model", default=JUDGE_MODEL)
    ap.add_argument(
        "--results-dir", default=str(RESULTS_DIR),
        help="Where artifacts + report.json land (waves must not clobber the "
        "original evidence record)",
    )
    ap.add_argument(
        "--rejudge", metavar="REPORT",
        help="Judge an existing wave's stored artifacts with --judge-model "
        "instead of generating (judge robustness, judge-only cost)",
    )
    ap.add_argument(
        "--prompt-variant", choices=sorted(PROMPTS), default="legacy",
        help="generation prompt (execution-oracle waves use the pinned_* "
        "variants; see EVIDENCE.md §Execution oracle, expectation XB)",
    )
    ap.add_argument(
        "--families-only", action="store_true",
        help="restrict selection to the acceptance-suite families",
    )
    args_ns = ap.parse_args(argv)
    dry_run, runs, per_level = args_ns.dry_run, args_ns.runs, args_ns.per_level
    GEN_MODEL, JUDGE_MODEL = args_ns.gen_model, args_ns.judge_model
    RESULTS_DIR = Path(args_ns.results_dir)
    global ACTIVE_PROMPT
    ACTIVE_PROMPT = PROMPTS[args_ns.prompt_variant]
    for m in (GEN_MODEL, JUDGE_MODEL):
        if m not in PRICES:
            print(f"error: no pricing for model '{m}' — add it to PRICES", file=sys.stderr)
            return 2

    if args_ns.rejudge:
        base_path = Path(args_ns.rejudge)
        base_report = json.loads(base_path.read_text(encoding="utf-8"))
        ok_runs = [r for r in base_report["runs"] if "error" not in r]
        print(f"Re-judge plan: {len(ok_runs)} stored artifacts from {base_path} "
              f"(gen={base_report['gen_model']}) judged by {JUDGE_MODEL}")
        if len(ok_runs) > MAX_CALLS:
            print(f"error: plan exceeds the {MAX_CALLS}-call cost guard", file=sys.stderr)
            return 2
        if dry_run:
            print("(dry run — no API calls made)")
            return 0
        err = _require_credentials()
        if err:
            print(f"error: {err}.", file=sys.stderr)
            return 2
        import anthropic

        client = anthropic.Anthropic()
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        usage: dict = {}
        results = _rejudge(client, base_path.parent, base_report, usage)
        selected = base_report["selected"]
        per_diagram, per_level_summary = _aggregate(selected, results)
        composites = {u["label"]: u["composite"] for u in selected}
        xs = [composites[r["label"]] for r in results if "error" not in r]
        ys = [r["judge"]["fidelity_score"] for r in results if "error" not in r]
        correlation = round(statistics.correlation(xs, ys), 3) if len(xs) > 2 else None
        cost = sum(
            u["in"] / 1e6 * PRICES[m][0] + u["out"] / 1e6 * PRICES[m][1]
            for m, u in usage.items()
        )
        report = {
            "gen_model": base_report["gen_model"], "judge_model": JUDGE_MODEL,
            "rejudge_of": str(base_path),
            "runs_per_diagram": base_report["runs_per_diagram"],
            "selected": selected, "per_level": per_level_summary,
            "per_diagram": per_diagram,
            "correlation_composite_fidelity": correlation,
            "runs": results, "usage": usage, "cost_usd": round(cost, 2),
            "failures": [r for r in results if "error" in r],
        }
        (RESULTS_DIR / "report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        print(f"\ncorrelation(composite, fidelity) = {correlation}")
        print(f"cost: ${cost:.2f}   report: {RESULTS_DIR / 'report.json'}")
        return 0

    _ensure_corpus()  # corpus/ is gitignored; a fresh clone must still work
    selected = select_diagrams(per_level, families_only=args_ns.families_only)
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
    err = _require_credentials()
    if err:
        print(f"error: {err}.", file=sys.stderr)
        return 2

    import anthropic

    client = anthropic.Anthropic()
    RESULTS_DIR.mkdir(exist_ok=True)
    usage: dict = {}

    tasks = [(u, i) for u in selected for i in range(1, runs + 1)]
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=_workers()) as pool:
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
        "prompt_variant": args_ns.prompt_variant,
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

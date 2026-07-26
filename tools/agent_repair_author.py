"""Agent-repair with-author wave driver (EVIDENCE.md §Agent-repair, with-author arm).

The recipe's intended use, measured: for every decision the diagram does
not contain, the repair agent ASKS; a firewalled author oracle — an LLM
holding only the pristine diagram and the questions — answers; the agent
repairs from the answers. Everything else (targets, fix-first, <=2
passes, generation config, frozen suites) matches the no-author arm.

Phases:
  R  ask -> author -> repair per target; Q&A logged with leakage flags.
  G  generation under the stored wave-main2 config over the 16 repaired
     diagrams (all degraded baselines already exist).

Run:  python tools/agent_repair_author.py [--dry-run] [--skip-repair]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import codegen_experiment as ce  # noqa: E402
import agent_repair as ar  # noqa: E402

WAVE_DIR = REPO_ROOT / "experiment_results" / "wave_repair_author"
REPAIRED_DIR = WAVE_DIR / "repaired"
# score_json/_cli must run from THIS wave's config-free cwd
ar.WAVE_DIR = WAVE_DIR
ar.REPAIRED_DIR = REPAIRED_DIR

REPAIR_MODEL = "claude-sonnet-5"
AUTHOR_MODEL = "claude-sonnet-5"
GEN_MODEL = "claude-opus-4-8"
JUDGE_MODEL = "claude-sonnet-5"
PROMPT_VARIANT = "legacy"
RUNS = 3
REPAIR_CEILING_USD = 8.0

LEAK_RE = re.compile(r"-{1,2}>{1,2}|@startuml|@enduml")

ASK_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"questions": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "properties": {
            "id": {"type": "integer"},
            "kind": {"type": "string", "enum": ["finding", "exploratory"]},
            "about": {"type": "string"},
            "question": {"type": "string"},
        },
        "required": ["id", "kind", "about", "question"],
    }}},
    "required": ["questions"],
}

ANSWER_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"answers": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "properties": {"id": {"type": "integer"}, "answer": {"type": "string"}},
        "required": ["id", "answer"],
    }}},
    "required": ["answers"],
}

ASK_PROMPT = """\
You are a coding agent following the pumllint repair protocol \
(docs/agents.md). You were about to implement the PlantUML sequence \
diagram below, but the pumllint maturity gate failed. You will repair \
the diagram — and this time the design's AUTHOR is available to answer \
questions.

First step: for every decision the diagram does not contain, ask. \
Output your questions as JSON. Tag each question:
- kind "finding" — driven by a gap-report entry (a vague guard to make \
concrete, a prose label to turn into a signature, a missing failure \
path, an elision marker to resolve, a missing return value);
- kind "exploratory" — behavior you suspect is missing though no \
finding flags it (e.g. what happens when a call fails, whether unhappy \
branches exist, what a loop's exit condition is).

Ask about everything you would otherwise have to guess. Do not ask the \
author to draw or dump the diagram — ask for decisions.

Gap report (pumllint score --profile codegen -f json):
{gap_json}

Diagram:
{diagram}
"""

AUTHOR_PROMPT = """\
You are the author of the system design below; the sequence diagram is \
your intended design and the ground truth. A colleague repairing an \
under-specified copy asks you the questions listed after it.

Answer each question from your design, concisely and specifically — \
the decision itself (the guard condition, the returned value, the \
failure behavior, the operation signature), in at most 40 words per \
answer. Answer ONLY what is asked; do not volunteer other parts of the \
design; never output diagram source or arrow syntax. If a question \
concerns something not in your design, answer "not part of my design".

Your design:
{pristine}

Questions:
{questions}
"""

REPAIR_TURN = """\
Author's answers:
{answers}

Now repair the diagram.
- Work the gap report top-down; use the author's answers for every \
content-bearing decision. Decisions must come from the answers or from \
the diagram itself — record any decision you still had to guess.
- Preserve everything the diagram already specifies. Repair is additive \
and clarifying, never a redesign. Do not add pumllint suppression \
comments.

Output exactly: the full repaired PlantUML source from @startuml to \
@enduml (no markdown fences), then on a new line `REPAIR_LOG:` followed \
by a single JSON object of the form \
{{"authored_decisions": ["<one entry per decision taken from an \
answer>"], "invented_decisions": ["<one entry per decision you still \
guessed>"], "notes": "<anything else worth recording>"}}.
"""


def _call_retry(client, model: str, usage: dict, messages: list,
                schema: dict | None = None, max_tokens: int = 12000):
    """Model call with schema option and transient-error backoff; returns
    joined text (empty string possible — caller decides how to retry)."""
    kwargs: dict = {"max_tokens": max_tokens, **ce._thinking(model),
                    "messages": messages}
    if schema is not None:
        kwargs["output_config"] = {"format": {"type": "json_schema",
                                              "schema": schema}}
    delay = 20.0
    for attempt in range(3):
        try:
            resp = ce._call(client, model, usage, **kwargs)
            return "".join(b.text for b in resp.content if b.type == "text")
        except Exception:
            if attempt == 2:
                raise
            time.sleep(delay)
            delay *= 2
    return ""


def pristine_of(path: str) -> Path:
    stem = Path(path).stem.split("__")[0].replace("_bad", "_good")
    if not stem.endswith("_good"):
        stem += "_good"
    p = REPO_ROOT / "examples" / f"{stem}.puml"
    if not p.exists():
        raise FileNotFoundError(f"no pristine example for {path}")
    return p


def qa_round(client, out_path: Path, maturity: dict, pristine_text: str,
             usage: dict) -> tuple[str | None, dict, dict]:
    """One ask -> author -> repair conversation. Returns (repaired_text,
    repair_log, qa_record)."""
    ask_prompt = ASK_PROMPT.format(
        gap_json=json.dumps(
            {"level": maturity["level"], "levelName": maturity["levelName"],
             "score": maturity["score"], "gapReport": maturity["gapReport"]},
            indent=1),
        diagram=out_path.read_text(encoding="utf-8"),
    )
    questions: list = []
    q_raw = ""
    for _ in range(3):
        q_raw = _call_retry(client, REPAIR_MODEL, usage,
                            [{"role": "user", "content": ask_prompt}],
                            schema=ASK_SCHEMA, max_tokens=8000)
        try:
            questions = json.loads(q_raw)["questions"]
            break
        except (json.JSONDecodeError, KeyError):
            continue

    answers: list = []
    leak_flags = 0
    if questions:
        author_prompt = AUTHOR_PROMPT.format(
            pristine=pristine_text,
            questions=json.dumps(questions, indent=1))
        for _ in range(3):
            a_raw = _call_retry(client, AUTHOR_MODEL, usage,
                                [{"role": "user", "content": author_prompt}],
                                schema=ANSWER_SCHEMA, max_tokens=8000)
            try:
                answers = json.loads(a_raw)["answers"]
                break
            except (json.JSONDecodeError, KeyError):
                continue
        leak_flags = sum(bool(LEAK_RE.search(a["answer"])) for a in answers)

    turn = REPAIR_TURN.format(
        answers=json.dumps(answers, indent=1) if answers
        else "(you asked no questions — nothing to answer)")
    diagram, log = None, {}
    for _ in range(3):
        text = _call_retry(
            client, REPAIR_MODEL, usage,
            [{"role": "user", "content": ask_prompt},
             {"role": "assistant", "content": q_raw or "{\"questions\": []}"},
             {"role": "user", "content": turn}])
        diagram, log = ar.parse_repair_output(text)
        if diagram:
            break
    qa = {"questions": questions, "answers": answers,
          "leak_flags": leak_flags,
          "n_finding": sum(q["kind"] == "finding" for q in questions),
          "n_exploratory": sum(q["kind"] == "exploratory" for q in questions)}
    return diagram, log, qa


def repair_one(client, unit: dict, usage: dict) -> dict:
    stem = Path(unit["path"]).stem
    out_path = REPAIRED_DIR / f"{stem}.puml"
    out_path.write_text(
        (REPO_ROOT / unit["path"]).read_text(encoding="utf-8"), encoding="utf-8")
    pristine_text = pristine_of(unit["path"]).read_text(encoding="utf-8")

    rec: dict = {
        "orig_label": unit["label"], "orig_level": unit["level"],
        "orig_composite": unit["composite"], "orig_path": unit["path"],
        "pristine_path": str(pristine_of(unit["path"]).relative_to(REPO_ROOT)),
        "repaired_path": str(out_path.relative_to(REPO_ROOT)),
        "passes": [], "qa": [],
        "authored_decisions": [], "invented_decisions": [],
    }

    ar._cli(["fix", str(out_path)])
    m = ar.score_json(out_path)
    rec["after_fix"] = {"level": m["level"], "composite": m["score"]}

    for pass_no in (1, 2):
        if m["level"] >= 5 or (pass_no == 2 and m["level"] >= 4):
            break
        diagram, log, qa = qa_round(client, out_path, m, pristine_text, usage)
        rec["qa"].append({"pass": pass_no, **qa})
        if not diagram:
            rec["passes"].append({"pass": pass_no, "error": "no diagram in output"})
            break
        out_path.write_text(diagram, encoding="utf-8")
        m = ar.score_json(out_path)
        rec["passes"].append({
            "pass": pass_no, "level": m["level"], "composite": m["score"],
            "authored": len(log.get("authored_decisions", [])),
            "invented": len(log.get("invented_decisions", [])),
        })
        rec["authored_decisions"].extend(log.get("authored_decisions", []))
        rec["invented_decisions"].extend(log.get("invented_decisions", []))

    rec["final"] = {"level": m["level"], "composite": m["score"]}
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Agent-repair with-author wave")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-repair", action="store_true")
    args = ap.parse_args(argv)

    targets = [u for u in ce.select_diagrams(8, families_only=True)
               if u["level"] <= 2]
    if len(targets) != 16:
        print(f"error: expected 16 targets, got {len(targets)}", file=sys.stderr)
        return 2
    for u in targets:
        pristine_of(u["path"])                        # assert mapping up front

    n_repair = len(targets) * 6                       # worst case: 2 passes x 3
    n_gen = len(targets) * RUNS * 2
    print(f"With-author wave plan: {len(targets)} targets, <= {n_repair} "
          f"repair-phase calls ({REPAIR_MODEL} agent + author) + {n_gen} "
          f"generation calls (gen={GEN_MODEL}, judge={JUDGE_MODEL}, "
          f"prompt={PROMPT_VARIANT})")
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
                    nq = sum(len(q["questions"]) for q in rec["qa"])
                    print(f"  repaired {label}: L{rec['orig_level']} -> "
                          f"L{rec['final']['level']} ({nq} questions, "
                          f"{len(rec['authored_decisions'])} authored, "
                          f"{len(rec['invented_decisions'])} invented)")
                except Exception as e:  # noqa: BLE001
                    repairs.append({"orig_label": label,
                                    "error": f"{type(e).__name__}: {e}"})
                    print(f"  FAIL repair {label}: {e}", file=sys.stderr)
        repair_cost = sum(
            u["in"] / 1e6 * ce.PRICES[m][0] + u["out"] / 1e6 * ce.PRICES[m][1]
            for m, u in usage.items())
        repair_log = {
            "repair_model": REPAIR_MODEL, "author_model": AUTHOR_MODEL,
            "max_passes": 2,
            "repairs": sorted(repairs, key=lambda r: r["orig_label"]),
            "repair_cost_usd": round(repair_cost, 2),
        }
        log_path.write_text(json.dumps(repair_log, indent=2) + "\n",
                            encoding="utf-8")
        print(f"Phase R done: ${repair_cost:.2f} -> {log_path}")
        if repair_cost > REPAIR_CEILING_USD:
            print("error: repair phase exceeded its ceiling", file=sys.stderr)
            return 2

    ok = [r for r in repair_log["repairs"] if "error" not in r]
    units: list[dict] = []
    for r in ok:
        m = ar.score_json(REPO_ROOT / r["repaired_path"])
        units.append({
            "path": r["repaired_path"], "label": f"A_{r['orig_label']}"[:60],
            "level": m["level"], "composite": round(m["score"], 1),
            "elements": 0,
            "orig_label": r["orig_label"], "orig_level": r["orig_level"],
            "orig_composite": r["orig_composite"],
        })

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
        "wave": "agent_repair_author",
        "gen_model": GEN_MODEL, "judge_model": JUDGE_MODEL,
        "repair_model": REPAIR_MODEL, "author_model": AUTHOR_MODEL,
        "runs_per_diagram": RUNS, "prompt_variant": PROMPT_VARIANT,
        "selected": units, "per_level": per_level, "per_diagram": per_diagram,
        "runs": results, "usage": usage, "cost_usd": round(cost, 2),
        "failures": [r for r in results if "error" in r],
    }
    (WAVE_DIR / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\ncost so far (repair + generation): ${cost:.2f}")
    print(f"report: {WAVE_DIR / 'report.json'}")
    print("next: python tools/run_acceptance.py --wave "
          "repair_author=experiment_results/wave_repair_author/report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

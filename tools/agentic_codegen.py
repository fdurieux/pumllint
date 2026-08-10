"""W5 agentic-condition driver: do the standing claims survive the
workflow people actually run?

Protocol: stack_experiment/W5_PREREGISTRATION.md (frozen before any
scored run; --wave requires --confirm-frozen).

The agentic loop, per run: generate with the substrate's STORED
prompt (unchanged, for comparability) -> compile-check -> execute the
pre-registered VISIBLE scenario subset -> if anything failed and
iterations remain, feed a structured failure report back in the same
conversation and ask for a full revision (max 2 revisions = max 3
model calls) -> grade the FINAL artifact on the FULL frozen suite,
reported as visible-subset / hidden-subset / full rates. Single-shot
baseline mode (--single arms) runs the identical path with zero
revisions.

Substrates and arms:
- cargo (stack_experiment/cargo_quote, frozen cargo_quote_suite):
  A2 (brief+structure+behavior L5), A2-BC (behavior swapped for the
  L1 below-cliff variant, label per the W1 precedent), A3
  (A2+contract). Prompt: stack-bundle-v2 (imported).
- c4 (c4_experiment rungs, frozen c4_loan_suite): R0, R3. Prompt:
  the stored C4 GEN_PROMPT (imported). Opus-only (the stored C4 wave
  was opus-only; declared narrowing).

Guards: MAX_CALLS live counter over every API call; wave ceiling
includes prior recorded phases under results/W5/.

Run:
  python tools/agentic_codegen.py --dry-run
  python tools/agentic_codegen.py --wave --confirm-frozen
  python tools/agentic_codegen.py --rejudge
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from acceptance import cargo_quote_suite as cargo_suite  # noqa: E402
from acceptance import c4_loan_suite  # noqa: E402
import c4_codegen_experiment as c4x  # noqa: E402
import stack_ablation as sa  # noqa: E402
from stack_ablation import (  # noqa: E402
    GEN_MODELS, JUDGE_MODEL, PRICES, GEN_MAX_TOKENS, JUDGE_MAX_TOKENS,
    WaveAbort, _thinking, _text_of, _strip_fences, _compiles,
)

SE = REPO_ROOT / "stack_experiment"
RESULTS = SE / "results" / "W5"
MAX_CALLS = 250
CEILING_USD = 40.00
MAX_MODEL_CALLS_PER_RUN = 3  # 1 generation + up to 2 revisions
RUNS_PER_ARM = 3  # per generator

# ---------------------------------------------------------------- arms

_K = "cargo_quote"
_A2 = [("brief.md", f"{_K}/brief.md"),
       ("structure/containers.puml", f"{_K}/structure/containers.puml"),
       ("behavior/quote_flow.puml", f"{_K}/behavior/quote_flow.puml")]
_A3 = _A2 + [("contract/spec.md", f"{_K}/contract/spec.md"),
             ("contract/decision_table.md",
              f"{_K}/contract/decision_table.md"),
             ("contract/openapi.yaml", f"{_K}/contract/openapi.yaml"),
             ("contract/quote_states.puml",
              f"{_K}/contract/quote_states.puml")]
_A2BC = [(lbl, p) if lbl != "behavior/quote_flow.puml" else
         ("behavior/quote_flow_bad.puml",
          f"{_K}/behavior/quote_flow_bad.puml")
         for lbl, p in _A2]

# arm -> (substrate, generators, agentic?, bundle-or-rung)
ARMS = {
    "A2": ("cargo", ["opus", "haiku"], True, _A2),
    "A2-BC": ("cargo", ["opus", "haiku"], True, _A2BC),
    "A3": ("cargo", ["opus", "haiku"], True, _A3),
    "A2-BC-single": ("cargo", ["opus", "haiku"], False, _A2BC),
    "R0": ("c4", ["opus"], True, "R0"),
    "R3": ("c4", ["opus"], True, "R3"),
}

# Pre-registered visible smoke subsets; everything else is hidden.
VISIBLE = {
    "cargo": ["quoted_low_risk", "invalid_weight_low", "refuse_high_risk"],
    "c4": ["approved_high", "invalid_zero", "declined_low"],
}

FEEDBACK_PROMPT = """\
Your implementation was tested against {n} acceptance scenarios; \
{failed} failed:

{failures}

Revise the module to fix these failures while staying faithful to the \
specification. Output ONLY the complete revised Python module. No \
markdown fences, no prose.
"""

COMPILE_FEEDBACK = """\
Your module did not compile: {error}

Revise it. Output ONLY the complete revised Python module. No markdown \
fences, no prose.
"""


# ------------------------------------------------------------ plumbing

_LOCK = threading.Lock()
_CALLS = {"n": 0}


def _spend(usage: dict) -> float:
    total = 0.0
    for model, u in usage.items():
        pin, pout = PRICES[model]
        total += u["in"] / 1e6 * pin + u["out"] / 1e6 * pout
    return round(total, 4)


def prior_spend() -> float:
    total = 0.0
    for rep in RESULTS.glob("*/report.json"):
        try:
            total += float(json.loads(rep.read_text())["spend_usd"])
        except Exception:  # noqa: BLE001
            pass
    return round(total, 4)


def _call(client, model: str, usage: dict, prior: float, **kwargs):
    with _LOCK:
        if _CALLS["n"] >= MAX_CALLS:
            raise WaveAbort(f"MAX_CALLS={MAX_CALLS} reached")
        if prior + _spend(usage) >= CEILING_USD:
            raise WaveAbort(f"ceiling ${CEILING_USD} reached")
        _CALLS["n"] += 1
    resp = client.messages.create(model=model, **kwargs)
    with _LOCK:
        u = usage.setdefault(model, {"in": 0, "out": 0})
        u["in"] += resp.usage.input_tokens
        u["out"] += resp.usage.output_tokens
    return resp


def gen_prompt(arm: str) -> str:
    substrate, _, _, src = ARMS[arm]
    if substrate == "cargo":
        spec = "\n\n".join(
            f"--- FILE: {lbl} ---\n{(SE / p).read_text(encoding='utf-8')}"
            for lbl, p in src)
        return sa.GEN_PROMPT.format(spec=spec)
    return c4x.GEN_PROMPT.format(spec=c4x.rung_spec_text(src))


def judge_prompt(arm: str, code: str) -> str:
    substrate, _, _, src = ARMS[arm]
    if substrate == "cargo":
        spec = "\n\n".join(
            f"--- FILE: {lbl} ---\n{(SE / p).read_text(encoding='utf-8')}"
            for lbl, p in src)
        return sa.JUDGE_PROMPT.format(spec=spec, code=code)
    return c4x.JUDGE_PROMPT.format(spec=c4x.rung_spec_text(src), code=code)


def run_scenarios(substrate: str, artifact: Path,
                  names: list[str]) -> list[dict]:
    rows = []
    for scen in names:
        if substrate == "cargo":
            res = sa.apply_overlay(scen, sa.run_child(
                artifact, sa.build_spec(scen)))
        else:
            res = c4x.run_child(artifact, c4x.build_spec(scen))
            if scen == "borderline_review" and res.get("passed"):
                import re as _re
                d = (res.get("detail") or "").lower()
                if not (_re.search(c4_loan_suite.REVIEW_RE, d)
                        and not _re.search(c4_loan_suite.DECIDED_RE, d)):
                    res.update(passed=False, stage="wrong_outcome")
        rows.append({"scenario": scen,
                     **{k: res.get(k) for k in
                        ("stage", "passed", "outcome_class", "detail")}})
    return rows


def all_scenarios(substrate: str) -> list[str]:
    return (list(cargo_suite.SUITE["scenarios"]) if substrate == "cargo"
            else list(c4_loan_suite.SUITE["scenarios"]))


def agentic_one(client, arm: str, short: str, run_idx: int, usage: dict,
                prior: float, out_dir: Path) -> dict:
    substrate, _, agentic, _ = ARMS[arm]
    model = GEN_MODELS[short]
    visible = VISIBLE[substrate]
    messages = [{"role": "user", "content": gen_prompt(arm)}]
    iterations = []
    code = ""
    art = out_dir / f"gen_{arm}_{short}_run{run_idx}.py"
    max_calls = MAX_MODEL_CALLS_PER_RUN if agentic else 1
    in_tok_first = 0
    for it in range(max_calls):
        resp = _call(client, model, usage, prior,
                     max_tokens=GEN_MAX_TOKENS, **_thinking(model),
                     messages=messages)
        code = _strip_fences(_text_of(resp)).strip()
        if it == 0:
            in_tok_first = resp.usage.input_tokens
        ok, err = _compiles(code)
        rec = {"call": it + 1, "stop_reason": resp.stop_reason,
               "compiles": ok}
        if not ok:
            rec["visible"] = None
            iterations.append(rec)
            if it + 1 >= max_calls:
                break
            messages += [{"role": "assistant", "content": code},
                         {"role": "user",
                          "content": COMPILE_FEEDBACK.format(
                              error=(err or "")[:300])}]
            continue
        art.write_text(code, encoding="utf-8")
        vis_rows = run_scenarios(substrate, art, visible)
        fails = [r for r in vis_rows if not r["passed"]]
        rec["visible"] = f"{len(vis_rows) - len(fails)}/{len(vis_rows)}"
        iterations.append(rec)
        if not fails or it + 1 >= max_calls:
            break
        report = "\n".join(
            f"- {r['scenario']}: [{r['stage']}] "
            f"{(r['detail'] or '')[:200]}" for r in fails)
        messages += [{"role": "assistant", "content": code},
                     {"role": "user",
                      "content": FEEDBACK_PROMPT.format(
                          n=len(vis_rows), failed=len(fails),
                          failures=report)}]
    ok, _err = _compiles(code)
    # the on-disk artifact is ALWAYS the graded (final) code, even when
    # a last revision regressed to non-compiling (adversarial finding 6a)
    art.write_text(code, encoding="utf-8")
    if ok:
        execution = run_scenarios(substrate, art, all_scenarios(substrate))
    else:
        execution = [{"scenario": s, "stage": "import_error",
                      "passed": False, "outcome_class": None,
                      "detail": "final artifact does not compile"}
                     for s in all_scenarios(substrate)]
    # a revision counts as visible-feedback-driven iff some non-final
    # call had a computed, non-clean visible result (finding 1: compile-
    # only iterations do NOT count toward G1)
    def _failed(v):
        return v is not None and v.split("/")[0] != v.split("/")[1]
    vis_fb = any(_failed(rec.get("visible")) for rec in iterations[:-1])
    return {"arm": arm, "generator": short, "model": model,
            "run": run_idx, "agentic": agentic, "code": code,
            "code_file": art.name, "compiles": ok,
            "iterations": iterations,
            "model_calls": len(iterations),
            "visible_feedback_revision": vis_fb,
            "input_tokens_first": in_tok_first,
            "execution": execution}


def judge_one(client, arm: str, code: str, usage: dict,
              prior: float) -> dict:
    prompt = judge_prompt(arm, code)
    last = None
    for _ in range(2):
        resp = _call(
            client, JUDGE_MODEL, usage, prior,
            max_tokens=JUDGE_MAX_TOKENS, **_thinking(JUDGE_MODEL),
            output_config={"format": {"type": "json_schema",
                                      "schema": c4x.JUDGE_SCHEMA}},
            messages=[{"role": "user", "content": prompt}])
        try:
            return json.loads(_text_of(resp))
        except json.JSONDecodeError as e:
            last = e
    raise last


# ------------------------------------------------------------ analysis

def _subset_rate(runs, arm, names, short=None, semantic=False):
    rows = [row for r in runs
            if r["arm"] == arm and (short is None or r["generator"] == short)
            for row in r["execution"] if row["scenario"] in names]
    if semantic:
        rows = [x for x in rows if x["stage"] not in sa.ADAPTER_STAGES]
    return round(sum(bool(x["passed"]) for x in rows) / len(rows), 4) \
        if rows else None


def analyze(runs: list[dict]) -> dict:
    out = {}
    for arm, (substrate, gens, agentic, _src) in ARMS.items():
        vis = set(VISIBLE[substrate])
        hid = [s for s in all_scenarios(substrate) if s not in vis]
        entry = {
            "substrate": substrate, "agentic": agentic,
            "full": _subset_rate(runs, arm, all_scenarios(substrate)),
            "full_semantic": _subset_rate(runs, arm,
                                          all_scenarios(substrate),
                                          semantic=True),
            "visible": _subset_rate(runs, arm, list(vis)),
            "hidden": _subset_rate(runs, arm, hid),
            "hidden_semantic": _subset_rate(runs, arm, hid, semantic=True),
            "visible_feedback_revisions": sum(
                1 for r in runs if r["arm"] == arm
                and r.get("visible_feedback_revision")),
            "per_generator": {
                s: {"full": _subset_rate(runs, arm,
                                         all_scenarios(substrate), s),
                    "visible": _subset_rate(runs, arm, list(vis), s),
                    "hidden": _subset_rate(runs, arm, hid, s)}
                for s in gens},
            "model_calls_used": [r["model_calls"] for r in runs
                                 if r["arm"] == arm],
            "judged_median": {
                s: (median(c) if (c := [
                    len(r["judge"]["invented_business_logic"])
                    for r in runs if r["arm"] == arm
                    and r["generator"] == s and r.get("judge")]) else None)
                for s in gens},
        }
        out[arm] = entry
    return out


# ---------------------------------------------------------------- modes

def run_wave(prior: float) -> int:
    import anthropic
    client = anthropic.Anthropic()
    usage: dict = {}
    out_dir = RESULTS / "wave_main"
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = [(arm, short, i + 1)
            for arm, (_sub, gens, _a, _s) in ARMS.items()
            for short in gens for i in range(RUNS_PER_ARM)]
    runs: list[dict] = []
    aborted = None
    try:
        with ThreadPoolExecutor(max_workers=6) as pool:
            futs = {pool.submit(agentic_one, client, arm, short, idx,
                                usage, prior, out_dir): 0
                    for arm, short, idx in jobs}
            for fut in futs:
                runs.append(fut.result())
    except WaveAbort as e:
        aborted = str(e)
    runs.sort(key=lambda r: (list(ARMS).index(r["arm"]),
                             r["generator"], r["run"]))
    if not aborted:
        try:
            with ThreadPoolExecutor(max_workers=6) as pool:
                futs = {pool.submit(judge_one, client, r["arm"], r["code"],
                                    usage, prior): r
                        for r in runs if r["compiles"]}
                for fut, r in futs.items():
                    try:
                        r["judge"] = fut.result()
                    except WaveAbort:
                        raise
                    except Exception as e:  # noqa: BLE001
                        r["judge"] = None
                        r["judge_error"] = str(e)[:300]
        except WaveAbort as e:
            aborted = str(e)

    hashes = {p: hashlib.sha256((SE / p).read_bytes()).hexdigest()
              for _a, (_s, _g, _ag, src) in ARMS.items()
              if isinstance(src, list) for _lbl, p in src}
    for rung in ("R0", "R3"):  # anchor the c4 inputs too (finding 8a)
        for p in sorted((REPO_ROOT / "c4_experiment" / rung).iterdir()):
            if p.suffix in (".puml", ".md"):
                hashes[f"c4_experiment/{rung}/{p.name}"] = \
                    hashlib.sha256(p.read_bytes()).hexdigest()
    report = {
        "phase": "W5/wave_main",
        "pre_registration": "stack_experiment/W5_PREREGISTRATION.md",
        "generators": GEN_MODELS, "judge_model": JUDGE_MODEL,
        "visible": VISIBLE, "runs_per_arm": RUNS_PER_ARM,
        "max_model_calls_per_run": MAX_MODEL_CALLS_PER_RUN,
        "feedback_prompt": FEEDBACK_PROMPT,
        "compile_feedback": COMPILE_FEEDBACK,
        "kit_hashes": hashes,
        "usage": usage, "spend_usd": _spend(usage),
        "prior_spend_usd": prior, "calls_used": _CALLS["n"],
        "aborted": aborted,
        "runs": [{k: v for k, v in r.items() if k != "code"}
                 for r in runs],
    }
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = analyze(runs)
    (out_dir / "analysis.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({a: {k: v[k] for k in ("full", "visible", "hidden")}
                      for a, v in summary.items()}, indent=2))
    if aborted:
        print(f"ABORTED: {aborted}")
    print(f"W5 spend: ${_spend(usage)} "
          f"(cumulative ${round(prior + _spend(usage), 2)} of "
          f"${CEILING_USD}) -> {out_dir}/report.json")
    return 2 if aborted else 0


def rejudge(prior: float) -> int:
    import anthropic
    client = anthropic.Anthropic()
    out_dir = RESULTS / "wave_main"
    report = json.loads((out_dir / "report.json").read_text())
    usage: dict = report.get("usage", {})
    todo = [r for r in report["runs"]
            if r.get("compiles") and r.get("judge") is None
            and (out_dir / r["code_file"]).exists()]
    print(f"re-judging {len(todo)}")
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(
            judge_one, client, r["arm"],
            (out_dir / r["code_file"]).read_text(encoding="utf-8"),
            usage, prior): r for r in todo}
        for fut, r in futs.items():
            try:
                r["judge"] = fut.result()
                r.pop("judge_error", None)
            except Exception as e:  # noqa: BLE001
                r["judge_error"] = str(e)[:300]
    report["usage"] = usage
    report["spend_usd"] = _spend(usage)
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for r in report["runs"]:
        r["code"] = (out_dir / r["code_file"]).read_text(encoding="utf-8")
    summary = analyze(report["runs"])
    (out_dir / "analysis.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--wave", action="store_true")
    ap.add_argument("--confirm-frozen", action="store_true")
    ap.add_argument("--rejudge", action="store_true")
    args = ap.parse_args(argv)

    n_runs = sum(len(gens) * RUNS_PER_ARM
                 for _a, (_s, gens, _ag, _src) in ARMS.items())
    n_agentic = sum(len(gens) * RUNS_PER_ARM
                    for _a, (_s, gens, ag, _src) in ARMS.items() if ag)
    plan = (f"W5 plan: {n_runs} runs ({n_agentic} agentic, "
            f"{n_runs - n_agentic} single-shot) x <= "
            f"{MAX_MODEL_CALLS_PER_RUN} model calls + {n_runs} "
            f"judgements; ceiling ${CEILING_USD}; MAX_CALLS={MAX_CALLS}")
    print(plan)
    if args.dry_run:
        for arm, (sub, gens, ag, src) in ARMS.items():
            if isinstance(src, list):
                missing = [p for _l, p in src if not (SE / p).exists()]
                detail = f"files={len(src)}" + (
                    f" MISSING={missing}" if missing else "")
            else:
                detail = f"rung={src} exists=" + str(
                    (REPO_ROOT / 'c4_experiment' / src).is_dir())
            print(f"  {arm:14s} {sub:5s} gens={gens} agentic={ag} "
                  f"{detail}")
        for sub, names in VISIBLE.items():
            pool = all_scenarios(sub)
            bad = [n for n in names if n not in pool]
            print(f"  visible[{sub}] = {names}"
                  + (f"  UNKNOWN={bad}" if bad else
                     f"  (hidden {len(pool) - len(names)})"))
        return 0
    if not (os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("no Anthropic API credentials in the environment")
        return 2
    prior = prior_spend()
    if args.rejudge:
        return rejudge(prior)
    if args.wave:
        if not args.confirm_frozen:
            print("refusing: --wave requires --confirm-frozen")
            return 2
        return run_wave(prior)
    print("pass --dry-run or --wave")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""W2/W3/W4 variant waves over the CargoQuote kit — one driver.

Protocols: stack_experiment/W2_PREREGISTRATION.md /
W3_PREREGISTRATION.md / W4_PREREGISTRATION.md (each frozen before its
scored run; --wave requires --confirm-frozen).

Shared frozen base, inherited from W1 by import from
tools/stack_ablation.py (NOT copied): generator/judge model IDs and
prices, the stack-bundle-v2 prompt (REQUEST_CONTRACT byte-identity by
import), the judge prompt + C4-wave JSON schema, the execution path
(frozen suite + runner + OVERLAYS driver-side), retry-once, adaptive
thinking rules. W1's calibration (opus 11/11/11, haiku 10/9/11 on
pristine A4 under this exact configuration) carries: these waves add
input variants, not oracle or config changes.

Arms per wave (bundle roots at stack_experiment/):
- W2 (redundancy/conflict): pristine A4 with ONE file swapped for a
  single-change conflict variant (w2_variants/, diff-verified):
  C1-numeric (stale accept threshold in spec prose vs DT-S),
  C2-behavioral (stale "refusals are not notified" vs diagram+DT+AC),
  C3-stale-test (stale Gherkin worked price vs DT-P). Control =
  W1 A4 (declared reuse; identical bundle, prompt, models, suite).
- W3 (carrier equivalence): pristine A2 with the behavior carrier
  swapped (w3_carriers/): mermaid / yaml / controlled-english /
  code-stub. PlantUML arm = W1 A2 (declared reuse).
- W4 (dose-response far side): pristine A4 plus over-specification
  (w4_farside/): O1-redundant (accurate prose restatement of all DT
  numbers), O2-irrelevant (plausible unrelated context), O3-
  enumeration (accurate exhaustive worked examples). Below-knee side
  = W1 A0..A4 (declared reuse).

W2 extra measure: deterministic conflict-surfacing scan over each
generated module (pre-registered regex CONFLICT_MARKER_RE) — did the
code or its comments surface the contradiction, or resolve silently?

Run:
  python tools/stack_variants.py --dry-run --wave W2|W3|W4
  python tools/stack_variants.py --wave W2 --confirm-frozen
  python tools/stack_variants.py --rejudge W2
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from acceptance import cargo_quote_suite as suite_mod  # noqa: E402
from c4_codegen_experiment import JUDGE_SCHEMA  # noqa: E402
from stack_ablation import (  # noqa: E402 — the frozen W1 base
    GEN_MODELS, JUDGE_MODEL, PRICES, GEN_PROMPT, JUDGE_PROMPT,
    GEN_MAX_TOKENS, JUDGE_MAX_TOKENS, WaveAbort,
    _thinking, _text_of, _strip_fences, _compiles,
    execute_artifact, _rates, _scen_rate,
)

SE = REPO_ROOT / "stack_experiment"
RESULTS = {w: SE / "results" / w for w in ("W2", "W3", "W4")}
W1_ANALYSIS = SE / "results" / "W1" / "wave_main" / "analysis.json"

MAX_CALLS = 120  # live counter per wave process, retries included
CEILINGS = {"W2": 10.00, "W3": 12.00, "W4": 12.00}
RUNS_PER_ARM = 3  # per generator, every arm, all three waves

# Bundle entries are (label, path): the label is what the prompt's
# --- FILE: ... --- header shows and is ALWAYS the W1 kit-relative
# name (adversarial findings, all three passes: variant paths like
# w2_variants/C1_spec.md must never leak into the model input, and
# swapped files keep their pristine labels so the only prompt delta
# vs the reused W1 baseline is the injected content itself; --dry-run
# proves that identity mechanically).
_K = "cargo_quote"
_A4 = [("brief.md", f"{_K}/brief.md"),
       ("structure/containers.puml", f"{_K}/structure/containers.puml"),
       ("behavior/quote_flow.puml", f"{_K}/behavior/quote_flow.puml"),
       ("contract/spec.md", f"{_K}/contract/spec.md"),
       ("contract/decision_table.md", f"{_K}/contract/decision_table.md"),
       ("contract/openapi.yaml", f"{_K}/contract/openapi.yaml"),
       ("contract/quote_states.puml", f"{_K}/contract/quote_states.puml"),
       ("tests_input/acceptance.feature",
        f"{_K}/tests_input/acceptance.feature")]
_A2 = _A4[:3]


def _swap(base, label, new_path, new_label=None):
    return [(new_label or lbl, new_path) if lbl == label else (lbl, p)
            for lbl, p in base]


ARMS: dict[str, dict[str, list[tuple[str, str]]]] = {
    "W2": {
        "C1-numeric": _swap(_A4, "contract/spec.md",
                            "w2_variants/C1_spec.md"),
        "C2-behavioral": _swap(_A4, "contract/spec.md",
                               "w2_variants/C2_spec.md"),
        "C3-stale-test": _swap(_A4, "tests_input/acceptance.feature",
                               "w2_variants/C3_acceptance.feature"),
    },
    "W3": {
        "mermaid": _swap(_A2, "behavior/quote_flow.puml",
                         "w3_carriers/quote_flow.mmd",
                         "behavior/quote_flow.mmd"),
        "yaml": _swap(_A2, "behavior/quote_flow.puml",
                      "w3_carriers/quote_flow.yaml",
                      "behavior/quote_flow.yaml"),
        "controlled-english": _swap(_A2, "behavior/quote_flow.puml",
                                    "w3_carriers/quote_flow.md",
                                    "behavior/quote_flow.md"),
        "code-stub": _swap(_A2, "behavior/quote_flow.puml",
                           "w3_carriers/quote_flow_stub.py",
                           "behavior/quote_flow_stub.py"),
    },
    "W4": {
        "O1-redundant": _swap(_A4, "contract/spec.md",
                              "w4_farside/O1_spec.md"),
        "O2-irrelevant": _A4 + [("operations-appendix.md",
                                 "w4_farside/O2_appendix.md")],
        "O3-enumeration": _A4 + [("worked-examples.md",
                                  "w4_farside/O3_worked_examples.md")],
    },
}

# W2 pre-registered conflict-surfacing scan (deterministic, code text).
CONFLICT_MARKER_RE = re.compile(
    r"(?i)conflict|contradict|inconsist|discrepan|mismatch", re.A)

# W2 discriminator scenarios per arm (pre-registered).
W2_DISCRIMINATORS = {
    "C1-numeric": ["review_boundary_42"],
    "C2-behavioral": ["refuse_boundary_67"],
    "C3-stale-test": ["price_exact_heavy", "price_exact_both"],
}


# ------------------------------------------------------------ API plumbing

_LOCK = threading.Lock()
_CALLS = {"n": 0}


def _spend(usage: dict) -> float:
    total = 0.0
    for model, u in usage.items():
        pin, pout = PRICES[model]
        total += u["in"] / 1e6 * pin + u["out"] / 1e6 * pout
    return round(total, 4)


def prior_spend(wave: str) -> float:
    total = 0.0
    for rep in RESULTS[wave].glob("*/report.json"):
        try:
            total += float(json.loads(rep.read_text())["spend_usd"])
        except Exception:  # noqa: BLE001
            pass
    return round(total, 4)


def _call(client, model: str, usage: dict, ceiling: float, prior: float,
          **kwargs):
    with _LOCK:
        if _CALLS["n"] >= MAX_CALLS:
            raise WaveAbort(f"MAX_CALLS={MAX_CALLS} reached — aborting")
        if prior + _spend(usage) >= ceiling:
            raise WaveAbort(f"ceiling ${ceiling} reached — aborting")
        _CALLS["n"] += 1
    resp = client.messages.create(model=model, **kwargs)
    with _LOCK:
        u = usage.setdefault(model, {"in": 0, "out": 0})
        u["in"] += resp.usage.input_tokens
        u["out"] += resp.usage.output_tokens
    return resp


def bundle_files(wave: str, arm: str) -> list[tuple[str, str]]:
    return [(label, (SE / rel).read_text(encoding="utf-8"))
            for label, rel in ARMS[wave][arm]]


def bundle_text(wave: str, arm: str) -> str:
    return "\n\n".join(f"--- FILE: {name} ---\n{text}"
                       for name, text in bundle_files(wave, arm))


def kit_hashes(wave: str) -> dict:
    files = sorted({rel for arm in ARMS[wave].values() for _, rel in arm})
    if wave == "W3":  # the audit's reference diagram is pinned too
        files.append(f"{_K}/behavior/quote_flow.puml")
    return {rel: hashlib.sha256((SE / rel).read_bytes()).hexdigest()
            for rel in sorted(set(files))}


def verify_prompt_identity(wave: str) -> list[str]:
    """Prove each arm's bundle equals the reused W1 baseline bundle
    with ONLY the declared substitution/addition (pristine labels
    everywhere). Returns a list of failures; empty = identical."""
    import stack_ablation as sa
    base_arm = "A2" if wave == "W3" else "A4"
    base = sa.bundle_text(base_arm)
    failures = []
    for arm, entries in ARMS[wave].items():
        expected = base
        for label, rel in entries:
            pristine = dict((lbl, p) for lbl, p in
                            (_A2 if wave == "W3" else _A4))
            if label in pristine and pristine[label] == rel:
                continue  # unchanged pristine file
            text = (SE / rel).read_text(encoding="utf-8")
            if wave == "W3":
                old = (SE / f"{_K}/behavior/quote_flow.puml").read_text(
                    encoding="utf-8")
                expected = expected.replace(
                    f"--- FILE: behavior/quote_flow.puml ---\n{old}",
                    f"--- FILE: {label} ---\n{text}")
            elif label in ("contract/spec.md",
                           "tests_input/acceptance.feature"):
                old = (SE / _K / label).read_text(encoding="utf-8")
                expected = expected.replace(old, text)
            else:  # W4 additions, appended in bundle order
                expected = expected + f"\n\n--- FILE: {label} ---\n{text}"
        if bundle_text(wave, arm) != expected:
            failures.append(arm)
    return failures


def generate_one(client, wave: str, short: str, arm: str, run_idx: int,
                 usage: dict, ceiling: float, prior: float) -> dict:
    model = GEN_MODELS[short]
    prompt = GEN_PROMPT.format(spec=bundle_text(wave, arm))
    attempts = []
    code, ok = "", False
    in_tok = out_tok = 0
    for _ in range(2):
        resp = _call(client, model, usage, ceiling, prior,
                     max_tokens=GEN_MAX_TOKENS, **_thinking(model),
                     messages=[{"role": "user", "content": prompt}])
        code = _strip_fences(_text_of(resp)).strip()
        ok, err = _compiles(code)
        in_tok = resp.usage.input_tokens
        out_tok = resp.usage.output_tokens
        attempts.append({"stop_reason": resp.stop_reason,
                         "compiles": ok, "error": err})
        if ok and resp.stop_reason != "max_tokens":
            break
    return {"arm": arm, "generator": short, "model": model, "run": run_idx,
            "code": code, "attempts": attempts, "compiles": ok,
            "input_tokens": in_tok, "output_tokens": out_tok}


def judge_one(client, wave: str, arm: str, code: str, usage: dict,
              ceiling: float, prior: float) -> dict:
    prompt = JUDGE_PROMPT.format(spec=bundle_text(wave, arm), code=code)
    last = None
    for _ in range(2):
        resp = _call(
            client, JUDGE_MODEL, usage, ceiling, prior,
            max_tokens=JUDGE_MAX_TOKENS, **_thinking(JUDGE_MODEL),
            output_config={"format": {"type": "json_schema",
                                      "schema": JUDGE_SCHEMA}},
            messages=[{"role": "user", "content": prompt}])
        try:
            return json.loads(_text_of(resp))
        except json.JSONDecodeError as e:
            last = e
    raise last


# ---------------------------------------------------------------- analysis

def _w1_pooled():
    a = json.loads(W1_ANALYSIS.read_text())
    return a["pooled"], a["per_generator"], a["tokens"]


def analyze(wave: str, runs: list[dict]) -> dict:
    arms = list(ARMS[wave])
    pooled = {a: _rates(runs, a) for a in arms}
    per_gen = {s: {a: _rates(runs, a, s) for a in arms} for s in GEN_MODELS}
    judged = {}
    for s in GEN_MODELS:
        judged[s] = {}
        for a in arms:
            counts = [len(r["judge"]["invented_business_logic"])
                      for r in runs if r["arm"] == a and r["generator"] == s
                      and r.get("judge")]
            judged[s][a] = {"n": len(counts),
                            "median": median(counts) if counts else None}
    tokens = {}
    for s in GEN_MODELS:
        tokens[s] = {a: round(sum(r["input_tokens"] for r in runs
                                  if r["arm"] == a and r["generator"] == s)
                              / max(1, sum(1 for r in runs
                                           if r["arm"] == a
                                           and r["generator"] == s)), 1)
                     for a in arms}

    w1_pooled, w1_gen, w1_tokens = _w1_pooled()
    out = {"pooled": pooled, "per_generator": per_gen,
           "judged_inventions": judged, "mean_input_tokens": tokens}

    if wave == "W2":
        base = w1_pooled["A4"]
        markers = {}
        for a in arms:
            hits = [bool(CONFLICT_MARKER_RE.search(r["code"]))
                    for r in runs if r["arm"] == a]
            markers[a] = {"surfaced": sum(hits), "n": len(hits)}
        disc = {}
        for a, scens in W2_DISCRIMINATORS.items():
            disc[a] = {
                s: {"rate": _scen_rate(pooled[a], s),
                    "w1_A4_baseline": _scen_rate(base, s)}
                for s in scens}
        collateral = {}
        for a, scens in W2_DISCRIMINATORS.items():
            others = [s for s in suite_mod.SUITE["scenarios"]
                      if s not in scens]
            collateral[a] = {
                "rate": round(sum(_scen_rate(pooled[a], s)
                                  for s in others) / len(others), 4),
                "w1_A4_baseline": round(sum(_scen_rate(base, s)
                                            for s in others) / len(others),
                                        4)}
        out["expectation_inputs"] = {
            "markers": markers, "discriminators": disc,
            "collateral_nondiscriminator_mean": collateral,
            "w1_A4_pooled": base["executed"]}
    elif wave == "W3":
        base_pooled = w1_pooled["A2"]["executed"]
        out["expectation_inputs"] = {
            "w1_A2_plantuml_pooled": base_pooled,
            "delta_vs_plantuml_pooled": {a: round(
                pooled[a]["executed"] - base_pooled, 4) for a in arms},
            "delta_vs_plantuml_by_gen": {s: {a: round(
                per_gen[s][a]["executed"]
                - w1_gen[s]["A2"]["executed"], 4) for a in arms}
                for s in GEN_MODELS},
            "w1_A2_scenarios": w1_pooled["A2"]["scenario_pass"]}
    elif wave == "W4":
        base_pooled = w1_pooled["A4"]["executed"]
        out["expectation_inputs"] = {
            "w1_A4_pooled": base_pooled,
            "delta_vs_A4_pooled": {a: round(
                pooled[a]["executed"] - base_pooled, 4) for a in arms},
            "delta_vs_A4_by_gen": {s: {a: round(
                per_gen[s][a]["executed"]
                - w1_gen[s]["A4"]["executed"], 4) for a in arms}
                for s in GEN_MODELS},
            "w1_ladder_pooled": {a: w1_pooled[a]["executed"]
                                 for a in ("A0", "A1", "A2", "A3", "A4")},
            "w1_mean_input_tokens": {s: w1_tokens[s]["mean_input_tokens"]
                                     for s in GEN_MODELS},
            "w1_A4_judged_medians": {
                s: json.loads(W1_ANALYSIS.read_text())
                ["judged_inventions"][s]["A4"]["median"]
                for s in GEN_MODELS}}
    return out


# ------------------------------------------------------------------ modes

def run_wave(wave: str, prior: float) -> int:
    import anthropic
    client = anthropic.Anthropic()
    ceiling = CEILINGS[wave]
    usage: dict = {}
    out_dir = RESULTS[wave] / "wave_main"
    out_dir.mkdir(parents=True, exist_ok=True)

    jobs = [(arm, short, i + 1) for arm in ARMS[wave]
            for short in GEN_MODELS for i in range(RUNS_PER_ARM)]
    runs: list[dict] = []
    aborted = None
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = {pool.submit(generate_one, client, wave, short, arm,
                                idx, usage, ceiling, prior): 0
                    for arm, short, idx in jobs}
            for fut in futs:
                runs.append(fut.result())
    except WaveAbort as e:
        aborted = str(e)
    runs.sort(key=lambda r: (list(ARMS[wave]).index(r["arm"]),
                             r["generator"], r["run"]))

    for r in runs:
        art = out_dir / f"gen_{r['arm']}_{r['generator']}_run{r['run']}.py"
        art.write_text(r["code"], encoding="utf-8")
        r["code_file"] = art.name
        if r["compiles"]:
            r["execution"] = execute_artifact(art)
        else:
            r["execution"] = [{"scenario": s, "stage": "import_error",
                               "passed": False, "outcome_class": None,
                               "entry": None, "detail": "does not compile"}
                              for s in suite_mod.SUITE["scenarios"]]

    if not aborted:
        try:
            with ThreadPoolExecutor(max_workers=8) as pool:
                futs = {pool.submit(judge_one, client, wave, r["arm"],
                                    r["code"], usage, ceiling, prior): r
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

    report = {
        "phase": f"{wave}/wave_main",
        "pre_registration": f"stack_experiment/{wave}_PREREGISTRATION.md",
        "generators": GEN_MODELS, "judge_model": JUDGE_MODEL,
        "runs_per_arm": RUNS_PER_ARM, "kit_hashes": kit_hashes(wave),
        "usage": usage, "spend_usd": _spend(usage),
        "prior_spend_usd": prior, "calls_used": _CALLS["n"],
        "aborted": aborted,
        "runs": [{k: v for k, v in r.items() if k != "code"}
                 for r in runs],
    }
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = analyze(wave, runs)
    (out_dir / "analysis.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary["expectation_inputs"], indent=2))
    if aborted:
        print(f"ABORTED: {aborted}")
    print(f"{wave} spend: ${_spend(usage)} "
          f"(cumulative ${round(prior + _spend(usage), 2)} of "
          f"${ceiling}) -> {out_dir}/report.json")
    return 2 if aborted else 0


def rejudge(wave: str, prior: float) -> int:
    import anthropic
    client = anthropic.Anthropic()
    ceiling = CEILINGS[wave]
    out_dir = RESULTS[wave] / "wave_main"
    report = json.loads((out_dir / "report.json").read_text())
    usage: dict = report.get("usage", {})
    todo = [r for r in report["runs"]
            if r.get("compiles") and r.get("judge") is None]
    print(f"re-judging {len(todo)}")
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {pool.submit(
            judge_one, client, wave, r["arm"],
            (out_dir / r["code_file"]).read_text(encoding="utf-8"),
            usage, ceiling, prior): r for r in todo}
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
    summary = analyze(wave, report["runs"])
    (out_dir / "analysis.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--wave", choices=["W2", "W3", "W4"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--confirm-frozen", action="store_true")
    ap.add_argument("--rejudge", choices=["W2", "W3", "W4"])
    args = ap.parse_args(argv)

    if args.rejudge:
        return rejudge(args.rejudge, prior_spend(args.rejudge))
    if not args.wave:
        print("pass --wave W2|W3|W4")
        return 2

    n_gen = len(ARMS[args.wave]) * 2 * RUNS_PER_ARM
    print(f"{args.wave} plan: {n_gen} generations (+<=1 retry each) + "
          f"{n_gen} judgements; ceiling ${CEILINGS[args.wave]}; "
          f"MAX_CALLS={MAX_CALLS} (live)")
    if args.dry_run:
        for arm, entries in ARMS[args.wave].items():
            missing = [p for _, p in entries if not (SE / p).exists()]
            chars = sum(len((SE / p).read_bytes()) for _, p in entries
                        if (SE / p).exists())
            print(f"  {arm:20s} files={len(entries)} chars={chars}"
                  + (f"  MISSING={missing}" if missing else ""))
        bad = verify_prompt_identity(args.wave)
        print("prompt-identity vs reused W1 baseline: "
              + ("OK — only the declared substitution differs"
                 if not bad else f"FAILED for {bad}"))
        return 0 if not bad else 1
    if not (os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("no Anthropic API credentials in the environment")
        return 2
    if not args.confirm_frozen:
        print(f"refusing: --wave requires --confirm-frozen (freeze "
              f"stack_experiment/{args.wave}_PREREGISTRATION.md first)")
        return 2
    return run_wave(args.wave, prior_spend(args.wave))


if __name__ == "__main__":
    raise SystemExit(main())

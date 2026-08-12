"""W1b contract-bundle decomposition: which of the four A3 contract
artifacts carry the bundle's executed value?

Protocol, pre-registered expectations and interpretation matrix:
stack_experiment/W1B_PREREGISTRATION.md (verified revision; --wave
refuses to start until that file is frozen and owner go recorded —
--confirm-frozen asserts both).

Driver placement (disclosed in the pre-registration's Driver bullet):
this module IMPORTS the frozen W1 driver (tools/stack_ablation.py —
file untouched on disk, W1's pinned sha still describes what W1 ran)
and registers the ten W1b arms into its ARMS table at import time, so
the assembly, generation, runner/overlay and judge paths are the
frozen code paths themselves, not copies. New here: the W1b job plan
(ten arms only — never the W1 arms), the W1b results root
(stack_experiment/results/W1B/ — the $30 ceiling accounts this wave
alone), the W1b analysis block (in-wave A2/A3 baselines, named-set
nets, E5 residual, judged add-one drops, every E1-E7/G1-G2 input),
and the three pre-freeze equivalence/cross-check obligations as an
executable mode (--prefreeze-checks, $0, no API).

Arm keys use ASCII '+'/'-' ("C+dt", "C-dt") so artifact filenames
stay portable; the pre-registration's prose uses typographic minus.

Run:
  python tools/stack_w1b.py --dry-run           # plan + arm inventories, $0
  python tools/stack_w1b.py --smoke             # reference impl through the
                                                # frozen scoring path, $0
  python tools/stack_w1b.py --prefreeze-checks  # obligations (1)(2)(3), $0
  python tools/stack_w1b.py --wave --confirm-frozen   # scored wave (60 runs)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stack_ablation as sa  # noqa: E402 — the frozen W1 driver, by import

REPO_ROOT = sa.REPO_ROOT
RESULTS_W1B = REPO_ROOT / "stack_experiment" / "results" / "W1B"
PREREG = "stack_experiment/W1B_PREREGISTRATION.md"

_SPEC = "contract/spec.md"
_DT = "contract/decision_table.md"
_API = "contract/openapi.yaml"
_STATES = "contract/quote_states.puml"

# The ten W1b arms. Anchors A2/A3 are W1's own entries (asserted below);
# component arms keep W1's additive order (pre-registration, Design).
W1B_ARMS: dict[str, list[str]] = {
    "A2": [sa._BRIEF, sa._STRUCT, sa._BEHAV],
    "A3": [sa._BRIEF, sa._STRUCT, sa._BEHAV, _SPEC, _DT, _API, _STATES],
    "C+spec": [sa._BRIEF, sa._STRUCT, sa._BEHAV, _SPEC],
    "C+dt": [sa._BRIEF, sa._STRUCT, sa._BEHAV, _DT],
    "C+api": [sa._BRIEF, sa._STRUCT, sa._BEHAV, _API],
    "C+states": [sa._BRIEF, sa._STRUCT, sa._BEHAV, _STATES],
    "C-spec": [sa._BRIEF, sa._STRUCT, sa._BEHAV, _DT, _API, _STATES],
    "C-dt": [sa._BRIEF, sa._STRUCT, sa._BEHAV, _SPEC, _API, _STATES],
    "C-api": [sa._BRIEF, sa._STRUCT, sa._BEHAV, _SPEC, _DT, _STATES],
    "C-states": [sa._BRIEF, sa._STRUCT, sa._BEHAV, _SPEC, _DT, _API],
}
W1B_ORDER = list(W1B_ARMS)
RUNS_PER_ARM = 3
ADD_ONE = {"spec": "C+spec", "dt": "C+dt", "api": "C+api",
           "states": "C+states"}
LOO = {"spec": "C-spec", "dt": "C-dt", "api": "C-api",
       "states": "C-states"}

# Named scenario sets (pre-registration, Design — defined by enumeration).
DTNUM5 = {"accept_boundary_41", "review_boundary_42", "refuse_boundary_67",
          "price_exact_heavy", "price_exact_both"}
VALBOUND2 = {"invalid_weight_low", "invalid_value_over"}
REST4 = {"quoted_low_risk", "refuse_high_risk", "store_down_error",
         "screening_down_hold"}

# Register the W1b component arms into the frozen driver's table so its
# bundle/generation/judge paths resolve them. Anchors must equal W1's
# own entries byte-for-byte — asserted, never overwritten.
assert sa.ARMS["A2"] == W1B_ARMS["A2"], "A2 anchor drifted from W1"
assert sa.ARMS["A3"] == W1B_ARMS["A3"], "A3 anchor drifted from W1"
for _k, _v in W1B_ARMS.items():
    if _k in ("A2", "A3"):
        continue
    assert _k not in sa.ARMS, f"arm name collision with W1: {_k}"
    sa.ARMS[_k] = _v


def kit_hashes() -> dict:
    files = sorted({rel for arm in W1B_ARMS.values() for rel in arm})
    h = {rel: hashlib.sha256((sa.KIT / rel).read_bytes()).hexdigest()
         for rel in files}
    h["tools/acceptance/cargo_quote_suite.py"] = hashlib.sha256(
        sa.SUITE_FILE.read_bytes()).hexdigest()
    h["tools/acceptance/runner_child.py"] = hashlib.sha256(
        sa.CHILD.read_bytes()).hexdigest()
    return h


def prior_spend() -> float:
    """This wave's spend only (results/W1B/*) — pre-registration, Budget."""
    total = 0.0
    for rep in RESULTS_W1B.glob("*/report.json"):
        try:
            total += float(json.loads(rep.read_text())["spend_usd"])
        except Exception:  # noqa: BLE001 — unreadable report: ignore
            pass
    return round(total, 4)


# ---------------------------------------------------------------- analysis

def _delta(scope: dict, lo: str, hi: str):
    a, b = scope.get(lo), scope.get(hi)
    if not a or not b or a["executed"] is None or b["executed"] is None:
        return None
    return round(b["executed"] - a["executed"], 4)


def analyze_w1b(runs: list[dict]) -> dict:
    arms = [a for a in W1B_ORDER if any(r["arm"] == a for r in runs)]
    pooled = {a: sa._rates(runs, a) for a in arms}
    per_gen = {s: {a: sa._rates(runs, a, s) for a in arms}
               for s in sa.GEN_MODELS}

    # artifact tokens: mean input tokens minus the in-wave A2 arm's
    tokens: dict = {}
    for s in sa.GEN_MODELS:
        by_arm = {}
        for a in arms:
            ins = [r["input_tokens"] for r in runs
                   if r["arm"] == a and r["generator"] == s]
            by_arm[a] = round(sum(ins) / len(ins), 1) if ins else None
        base = by_arm.get("A2")
        tokens[s] = {"mean_input_tokens": by_arm,
                     "artifact_tokens": {a: (round(by_arm[a] - base, 1)
                                             if base and by_arm.get(a)
                                             else None) for a in arms}}

    # judged inventions per arm (n reported — judged-n conventions)
    judged: dict = {}
    for s in sa.GEN_MODELS:
        by_arm = {}
        for a in arms:
            counts = [len(r["judge"]["invented_business_logic"])
                      for r in runs
                      if r["arm"] == a and r["generator"] == s
                      and r.get("judge")]
            by_arm[a] = {"n": len(counts),
                         "median": median(counts) if counts else None}
        judged[s] = by_arm

    def _scoped(fn):
        return {"pooled": fn(pooled),
                **{s: fn(per_gen[s]) for s in sa.GEN_MODELS}}

    add_one = {c: _scoped(lambda sc, a=arm: _delta(sc, "A2", a))
               for c, arm in ADD_ONE.items()}          # signed: C+x − A2
    loo = {c: _scoped(lambda sc, a=arm: _delta(sc, a, "A3"))
           for c, arm in LOO.items()}                  # signed: A3 − C−x
    jump = _scoped(lambda sc: _delta(sc, "A2", "A3"))  # A3 − A2, in-wave

    per_kilo: dict = {}
    for s in sa.GEN_MODELS:
        at = tokens[s]["artifact_tokens"]
        add = {}
        for c, arm in ADD_ONE.items():
            d = add_one[c][s]
            if d is not None and at.get(arm):
                add[c] = round(d * 100 / (at[arm] / 1000), 2)
        drop = {}
        for c, arm in LOO.items():
            d = loo[c][s]
            if d is not None and at.get("A3") is not None \
                    and at.get(arm) is not None and at["A3"] != at[arm]:
                drop[c] = round(d * 100 / ((at["A3"] - at[arm]) / 1000), 2)
        per_kilo[s] = {"add_one_pp_per_ktok": add, "loo_pp_per_ktok": drop}

    def _nets(lo_arm: str, hi_arm: str) -> dict:
        if lo_arm not in pooled or hi_arm not in pooled:
            return {}
        lo, hi = pooled[lo_arm], pooled[hi_arm]
        return {"DTNUM5": sa._net_gain(lo, hi, DTNUM5),
                "VALBOUND2": sa._net_gain(lo, hi, VALBOUND2),
                "REST4": sa._net_gain(lo, hi, REST4),
                "total": sa._net_gain(lo, hi,
                                      sa.suite_mod.SUITE["scenarios"])}

    net_gains = {c: _nets("A2", arm) for c, arm in ADD_ONE.items()}
    net_losses = {c: _nets(arm, "A3") for c, arm in LOO.items()}

    judged_drops = {}
    for s in sa.GEN_MODELS:
        a2 = judged[s].get("A2", {})
        judged_drops[s] = {
            c: {"drop": (a2["median"] - judged[s][arm]["median"]
                         if a2.get("median") is not None
                         and judged[s].get(arm, {}).get("median") is not None
                         else None),
                "n_A2": a2.get("n"), "n_arm": judged[s].get(arm, {}).get("n")}
            for c, arm in ADD_ONE.items() if arm in judged[s]}

    def _largest(d: dict[str, float | None]):
        vals = {k: v for k, v in d.items() if v is not None}
        return max(vals, key=vals.get) if vals else None

    e5 = {}
    for scope in ["pooled", *sa.GEN_MODELS]:
        incs = [add_one[c][scope] for c in ADD_ONE]
        if jump[scope] is not None and all(v is not None for v in incs):
            e5[scope] = {"sum_add_one": round(sum(incs), 4),
                         "jump": jump[scope],
                         "residual": round(sum(incs) - jump[scope], 4)}

    opus_ceiling = sum(
        1 for arm in ADD_ONE.values()
        if per_gen["opus"].get(arm, {}).get("executed") == 1.0)

    expectation_inputs = {
        "E1a_add_one_pooled": {c: add_one[c]["pooled"] for c in ADD_ONE},
        "E1a_largest_pooled": _largest(
            {c: add_one[c]["pooled"] for c in ADD_ONE}),
        "E1b_loo_pooled": {c: loo[c]["pooled"] for c in LOO},
        "E1b_largest_pooled": _largest({c: loo[c]["pooled"] for c in LOO}),
        "E2_net_gains_Cdt": net_gains.get("dt", {}),
        "E3_net_losses_Cdt": net_losses.get("dt", {}),
        "E4_deltas_pooled": {c: loo[c]["pooled"]
                             for c in ("spec", "api", "states")},
        "E4_deltas_by_gen": {s: {c: loo[c][s]
                                 for c in ("spec", "api", "states")}
                             for s in sa.GEN_MODELS},
        "E5": e5,
        "E6_judged_drops": judged_drops,
        "E7_largest_add_one_by_gen": {
            s: _largest({c: add_one[c][s] for c in ADD_ONE})
            for s in sa.GEN_MODELS},
        "E7_opus_ceiling_arms": opus_ceiling,
        "G1_jump_pooled": jump["pooled"],
        "G2_A3_by_gen": {s: per_gen[s].get("A3", {}).get("executed")
                         for s in sa.GEN_MODELS},
    }

    return {"pooled": pooled, "per_generator": per_gen, "tokens": tokens,
            "judged_inventions": judged, "add_one_increments": add_one,
            "loo_drops": loo, "in_wave_jump": jump,
            "net_gains_vs_A2": net_gains, "net_losses_vs_A3": net_losses,
            "pp_per_kilotoken": per_kilo,
            "expectation_inputs": expectation_inputs}


# ------------------------------------------------------------------- wave

def run_wave(prior: float) -> int:
    import anthropic
    client = anthropic.Anthropic()
    usage: dict = {}
    out_dir = RESULTS_W1B / "wave_main"
    out_dir.mkdir(parents=True, exist_ok=True)

    jobs = [(arm, short, i + 1) for arm in W1B_ORDER
            for short in sa.GEN_MODELS for i in range(RUNS_PER_ARM)]
    runs: list[dict] = []
    aborted = None
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = {pool.submit(sa.generate_one, client, short, arm, idx,
                                usage, prior): (arm, short, idx)
                    for arm, short, idx in jobs}
            for fut in futs:
                runs.append(fut.result())
    except sa.WaveAbort as e:
        aborted = str(e)
    runs.sort(key=lambda r: (W1B_ORDER.index(r["arm"]), r["generator"],
                             r["run"]))

    for r in runs:
        art = out_dir / f"gen_{r['arm']}_{r['generator']}_run{r['run']}.py"
        art.write_text(r["code"], encoding="utf-8")
        r["code_file"] = art.name
        if r["compiles"]:
            r["execution"] = sa.execute_artifact(art)
        else:
            r["execution"] = [
                {"scenario": s, "stage": "import_error", "passed": False,
                 "outcome_class": None, "entry": None,
                 "detail": "does not compile"}
                for s in sa.suite_mod.SUITE["scenarios"]]

    if not aborted:
        try:
            with ThreadPoolExecutor(max_workers=8) as pool:
                futs = {pool.submit(sa.judge_one, client, r["arm"],
                                    r["code"], usage, prior): r
                        for r in runs if r["compiles"]}
                for fut, r in futs.items():
                    try:
                        r["judge"] = fut.result()
                    except sa.WaveAbort:
                        raise
                    except Exception as e:  # noqa: BLE001 — logged, excluded
                        r["judge"] = None
                        r["judge_error"] = str(e)[:300]
        except sa.WaveAbort as e:
            aborted = str(e)

    report = {
        "phase": "wave_main", "pre_registration": PREREG,
        "generators": sa.GEN_MODELS, "judge_model": sa.JUDGE_MODEL,
        "runs_per_arm": {a: RUNS_PER_ARM for a in W1B_ARMS},
        "gen_prompt": sa.GEN_PROMPT, "judge_prompt": sa.JUDGE_PROMPT,
        "kit_hashes": kit_hashes(),
        "usage": usage, "spend_usd": sa._spend(usage),
        "prior_spend_usd": prior, "calls_used": sa._CALLS["n"],
        "aborted": aborted,
        "runs": [{k: v for k, v in r.items() if k != "code"}
                 for r in runs],
    }
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = analyze_w1b(runs)
    (out_dir / "analysis.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary["expectation_inputs"], indent=2))
    if aborted:
        print(f"ABORTED: {aborted}")
    print(f"spend this phase: ${sa._spend(usage)} "
          f"(W1B cumulative ${round(prior + sa._spend(usage), 2)} "
          f"of ${sa.CEILING_USD}) -> {out_dir}/report.json")
    return 2 if aborted else 0


# --------------------------------------------------------- pre-freeze checks

def prefreeze_checks() -> int:
    """Obligations (1)(2)(3) from the pre-registration's Driver bullet,
    plus the smoke and inventory checks from Calibration. $0, no API."""
    checks: list[dict] = []

    def rec(name: str, ok: bool, detail: str = ""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})
        print(f"  {'PASS' if ok else 'FAIL'}  {name}"
              + (f" — {detail}" if detail else ""))

    wave_dir = sa.RESULTS_ROOT / "wave_main"
    stored = json.loads((wave_dir / "report.json").read_text())
    stored_analysis = json.loads((wave_dir / "analysis.json").read_text())

    # -- Obligation 1: A2/A3 bundle byte-identity against W1's stored record.
    for rel, h in kit_hashes().items():
        if rel in stored["kit_hashes"]:
            rec(f"kit hash unchanged: {rel}", stored["kit_hashes"][rel] == h)
    rec("GEN_PROMPT template byte-identical to stored wave",
        sa.GEN_PROMPT == stored["gen_prompt"])
    for arm in ("A2", "A3"):
        text = sa.bundle_text(arm)
        rec(f"bundle_text({arm}) assembled and sha-recorded",
            len(text) > 0, hashlib.sha256(text.encode()).hexdigest()[:16])

    # -- Obligation 2: stored W1 A2/A3 artifacts replay bit-for-bit.
    replayed = mismatches = 0
    for r in stored["runs"]:
        if r["arm"] not in ("A2", "A3") or not r["compiles"]:
            continue
        rows = sa.execute_artifact(wave_dir / r["code_file"])
        replayed += 1
        if rows != r["execution"]:
            mismatches += 1
            for new, old in zip(rows, r["execution"]):
                if new != old:
                    rec(f"replay mismatch {r['code_file']} "
                        f"{new['scenario']}", False,
                        f"stored={old['passed']} replay={new['passed']}")
    rec(f"replay: {replayed} stored A2/A3 artifacts re-scored",
        replayed == 12 and mismatches == 0,
        f"{mismatches} mismatching artifacts")

    # -- Obligation 3a: revised analysis reproduces W1's stored marginals.
    w1_runs = [dict(r) for r in stored["runs"] if r["arm"] in ("A2", "A3")]
    out = analyze_w1b(w1_runs)
    jump = out["in_wave_jump"]
    sa2a3 = stored_analysis["additive_increments"]["A2->A3"]
    rec("A2->A3 pooled reproduced", jump["pooled"] == sa2a3["pooled"],
        f"{jump['pooled']} vs stored {sa2a3['pooled']}")
    for s in sa.GEN_MODELS:
        rec(f"A2->A3 {s} reproduced", jump[s] == sa2a3[s],
            f"{jump[s]} vs stored {sa2a3[s]}")
    for s in sa.GEN_MODELS:
        for a in ("A2", "A3"):
            mine = out["judged_inventions"][s][a]["median"]
            theirs = stored_analysis["judged_inventions"][s][a]["median"]
            rec(f"judged median {s}/{a} reproduced", mine == theirs,
                f"{mine} vs stored {theirs}")

    # -- Obligation 3b: expectation-inputs dry-run over a synthetic
    #    complete dataset (stored A2 runs cloned into every component arm;
    #    scoring meaning: none — code-path exercise only, the X-R1 lesson).
    synth = [dict(r) for r in stored["runs"] if r["arm"] in ("A2", "A3")]
    for arm in list(ADD_ONE.values()) + list(LOO.values()):
        for r in stored["runs"]:
            if r["arm"] == "A2":
                c = dict(r)
                c["arm"] = arm
                synth.append(c)
    ei = analyze_w1b(synth)["expectation_inputs"]
    required = ["E1a_add_one_pooled", "E1a_largest_pooled",
                "E1b_loo_pooled", "E1b_largest_pooled", "E2_net_gains_Cdt",
                "E3_net_losses_Cdt", "E4_deltas_pooled", "E4_deltas_by_gen",
                "E5", "E6_judged_drops", "E7_largest_add_one_by_gen",
                "E7_opus_ceiling_arms", "G1_jump_pooled", "G2_A3_by_gen"]
    missing = [k for k in required if k not in ei or ei[k] in (None, {}, [])]
    rec("expectation-inputs dry-run emits every E1-E7/G1-G2 input",
        not missing, f"missing: {missing}" if missing else
        f"{len(required)} inputs emitted (synthetic data, no meaning)")

    # -- Calibration checks: smoke + arm inventories.
    ref_rows = sa.execute_artifact(sa.KIT / "reference_impl.py")
    rec("reference impl 11/11 through the frozen scoring path",
        sum(bool(r["passed"]) for r in ref_rows) == 11)
    for arm, files in W1B_ARMS.items():
        missing_f = [f for f in files if not (sa.KIT / f).exists()]
        rec(f"arm inventory {arm}: {len(files)} files", not missing_f,
            " ".join(Path(f).name for f in files))

    ok = all(c["ok"] for c in checks)
    out_dir = RESULTS_W1B / "prefreeze_checks"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps({
        "phase": "prefreeze_checks", "pre_registration": PREREG,
        "spend_usd": 0.0,
        "driver_sha256_at_check": hashlib.sha256(
            Path(__file__).read_bytes()).hexdigest(),
        "stack_ablation_sha256": hashlib.sha256(
            (Path(__file__).parent / "stack_ablation.py")
            .read_bytes()).hexdigest(),
        "checks": checks, "all_ok": ok,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"PRE-FREEZE CHECKS {'PASSED' if ok else 'FAILED'} "
          f"-> {out_dir}/report.json")
    return 0 if ok else 1


# ------------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--prefreeze-checks", action="store_true")
    ap.add_argument("--wave", action="store_true")
    ap.add_argument("--confirm-frozen", action="store_true",
                    help="required with --wave: asserts the W1b "
                         "pre-registration is FROZEN in a commit and "
                         "owner go is recorded in its preamble")
    args = ap.parse_args(argv)

    plan = (f"W1b plan: {len(W1B_ORDER) * 2 * RUNS_PER_ARM} scored "
            f"generations (+ up to 1 retry each) + as many judgements "
            f"across {len(W1B_ORDER)} arms x 2 generators x "
            f"{RUNS_PER_ARM} runs; MAX_CALLS={sa.MAX_CALLS} (live), "
            f"ceiling ${sa.CEILING_USD} scoped to results/W1B")
    if args.dry_run:
        print(plan)
        for arm in W1B_ORDER:
            files = W1B_ARMS[arm]
            chars = sum(len((sa.KIT / f).read_bytes()) for f in files)
            print(f"  {arm:10s} runs/gen={RUNS_PER_ARM} "
                  f"files={len(files)} chars={chars}  "
                  + " ".join(Path(f).name for f in files))
        print(f"sets: DTNUM5={sorted(DTNUM5)}\n      VALBOUND2="
              f"{sorted(VALBOUND2)}\n      REST4={sorted(REST4)}")
        return 0
    if args.smoke:
        return sa.smoke()
    if args.prefreeze_checks:
        return prefreeze_checks()
    if args.wave:
        if not args.confirm_frozen:
            print("refusing: --wave requires --confirm-frozen (the W1b "
                  "pre-registration must be frozen in a commit and owner "
                  "go recorded — W1B_PREREGISTRATION.md preamble)")
            return 2
        if "VERIFIED REVISION" in (REPO_ROOT / PREREG).read_text()[:400]:
            print("refusing: W1B_PREREGISTRATION.md still reads "
                  "'VERIFIED REVISION' — freeze it first")
            return 2
        if not (os.environ.get("ANTHROPIC_API_KEY")
                or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            print("no Anthropic API credentials in the environment")
            return 2
        print(plan)
        return run_wave(prior_spend())
    print(plan + "\nnothing to do: pass one of --dry-run/--smoke/"
          "--prefreeze-checks/--wave")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

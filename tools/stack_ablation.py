"""W1 artifact-portfolio ablation: which artifacts of a specification
stack carry executed-correctness value for the model->code hop?

Protocol, pre-registered expectations and interpretation matrix:
stack_experiment/W1_PREREGISTRATION.md (frozen before any scored run;
--wave refuses to start without an explicit --confirm-frozen
acknowledgement of that freeze).

One system (CargoQuote, stack_experiment/cargo_quote/) at 9 artifact
conditions — additive ladder A0..A4, leave-one-out L-structure /
L-behavior / L-contract (L-tests == A3, deduplicated), and the
below-cliff arm BC-behavior — x 2 generators x 3 runs (5 on A4,
L-behavior, BC-behavior): 66 scored runs. Scored against:

- **Execution** (primary): the frozen acceptance suite
  (tools/acceptance/cargo_quote_suite.py) via the frozen sandbox
  runner (tools/acceptance/runner_child.py, unchanged), suite OVERLAYS
  applied driver-side after a runner pass (the c4 precedent).
- **Judged inventions** (secondary, judgments only): the C4-wave
  rubric and JSON schema (imported from tools/c4_codegen_experiment.py
  unchanged); the judge-prompt header is adapted to name the stack's
  artifact kinds, the counting/invention/fidelity language is the
  C4 wave's.

Prompt: stack-bundle-v2 — the c4 conforming-prompt scaffold
generalized to a bundle of named artifact sections; the entry contract
is imported from tools/codegen_experiment.py (REQUEST_CONTRACT), so
byte-identity with the stored waves holds by construction. v2 adds one
seam rule after the first calibration attempt (disclosed in the
pre-registration): collaborator methods return single values, never
tuples — the runner's ProteanNum stubs legacy-iterate via __getitem__,
so a tuple-unpacking caller dies with "too many values to unpack" at
the first stubbed call (haiku's attempt-1 failure signature).

Guards: MAX_CALLS is a LIVE counter over every API call this driver
makes (generation, judge, retries, probe, calibration); the $ ceiling
counts spend recorded by earlier phases under stack_experiment/
results/W1/ plus the current process. Crossing either aborts.

Kit .puml maturity scores are NOT re-computed here: the repo's own
pumllint.toml would leak convention rules into kit scoring (W0 README
warning); the pinned scores live in stack_experiment/README.md.

Run:
  python tools/stack_ablation.py --dry-run     # plan + kit check, $0
  python tools/stack_ablation.py --smoke       # reference impl through
                                               # this driver's scoring
                                               # path: expect 11/11, $0
  python tools/stack_ablation.py --probe       # live model probe, cents
  python tools/stack_ablation.py --calibrate   # pristine A4 x 3 runs x
                                               # both generators, no judge
  python tools/stack_ablation.py --wave --confirm-frozen  # scored wave
  python tools/stack_ablation.py --rejudge     # re-judge failed judge
                                               # calls on stored artifacts
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
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
from codegen_experiment import REQUEST_CONTRACT  # noqa: E402

GEN_MODELS = {  # short name -> exact id (live-probed before freeze)
    "opus": "claude-opus-4-8",
    "haiku": "claude-haiku-4-5-20251001",
}
JUDGE_MODEL = "claude-sonnet-5"
PRICES = {  # $/M tokens (input, output)
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
}

KIT = REPO_ROOT / "stack_experiment" / "cargo_quote"
RESULTS_ROOT = REPO_ROOT / "stack_experiment" / "results" / "W1"
CHILD = Path(__file__).resolve().parent / "acceptance" / "runner_child.py"
SUITE_FILE = Path(__file__).resolve().parent / "acceptance" / "cargo_quote_suite.py"

MAX_CALLS = 250          # live counter, every API call incl. retries
CEILING_USD = 30.00      # hard, includes spend recorded by prior phases
GEN_MAX_TOKENS = 12000
JUDGE_MAX_TOKENS = 16000
TIMEOUT_S = 15
CALIB_RUNS = 3

# ------------------------------------------------------------------- arms

_BRIEF = "brief.md"
_STRUCT = "structure/containers.puml"
_BEHAV = "behavior/quote_flow.puml"
_BEHAV_BAD = "behavior/quote_flow_bad.puml"
_CONTRACT = ["contract/spec.md", "contract/decision_table.md",
             "contract/openapi.yaml", "contract/quote_states.puml"]
_TESTS = "tests_input/acceptance.feature"

# Additive order is fixed for every arm (pre-registration: no per-arm
# reordering). L-tests == A3 by ladder nesting — deduplicated; the
# analysis reports A3 in both views.
ARMS: dict[str, list[str]] = {
    "A0": [_BRIEF],
    "A1": [_BRIEF, _STRUCT],
    "A2": [_BRIEF, _STRUCT, _BEHAV],
    "A3": [_BRIEF, _STRUCT, _BEHAV, *_CONTRACT],
    "A4": [_BRIEF, _STRUCT, _BEHAV, *_CONTRACT, _TESTS],
    "L-structure": [_BRIEF, _BEHAV, *_CONTRACT, _TESTS],
    "L-behavior": [_BRIEF, _STRUCT, *_CONTRACT, _TESTS],
    "L-contract": [_BRIEF, _STRUCT, _BEHAV, _TESTS],
    "BC-behavior": [_BRIEF, _STRUCT, _BEHAV_BAD, *_CONTRACT, _TESTS],
}
ARM_ORDER = list(ARMS)
RUNS_PER_ARM = {arm: 5 if arm in ("A4", "L-behavior", "BC-behavior") else 3
                for arm in ARMS}
ADDITIVE_PAIRS = [("A0", "A1"), ("A1", "A2"), ("A2", "A3"), ("A3", "A4")]
LOO_DROPS = {"structure": "L-structure", "behavior": "L-behavior",
             "contract": "L-contract", "tests": "A3"}

# Named scenario sets (pre-registration, Shared definitions).
CONTRACT7 = {"accept_boundary_41", "review_boundary_42",
             "refuse_boundary_67", "price_exact_heavy", "price_exact_both",
             "invalid_weight_low", "invalid_value_over"}
FLOWPI6 = {"quoted_low_risk", "refuse_boundary_67", "refuse_high_risk",
           "invalid_weight_low", "screening_down_hold", "store_down_error"}
LEAK2 = {"invalid_weight_low", "screening_down_hold"}
VALUE9 = set(suite_mod.SUITE["scenarios"]) - LEAK2

# ---------------------------------------------------------------- prompts

GEN_PROMPT = """\
Implement the system specified below as a single self-contained Python \
module. The specification is a bundle of named artifacts — a project \
brief plus, depending on the bundle: a PlantUML C4 container diagram, a \
PlantUML UML sequence diagram, a companion markdown specification, \
decision tables, an OpenAPI description, a UML state machine, and \
Gherkin acceptance scenarios. All artifacts describe ONE system.

Rules:
- If a container diagram is provided: one class per Container, \
ContainerDb and System_Ext element, named after the element's alias in \
CamelCase (alias tariff_engine -> class TariffEngine). Relationships \
(Rel) become method calls from the source element's class to the target \
element's class. Do not add calls between elements that have no declared \
relationship.
- If no container diagram is provided, choose a sensible class \
decomposition; keep the external screening provider, the tariff/pricing \
computation, the quote store and the notification provider as separate \
classes so they can be substituted.
- Where the specification describes flows, steps, guards, rules, tables \
or acceptance scenarios, implement them; failure paths become raised \
exceptions or error returns.
- External systems are outside the system boundary: implement each as a \
simple class whose methods return plausible values.
- Every collaborator and external-system method returns a SINGLE value \
(the screening call returns the shipper risk index; the pricing call \
returns the price; the store call returns a confirmation) — never a \
tuple, and callers never tuple-unpack a collaborator's return.
- Where the specification is ambiguous or incomplete, make your best \
guess and implement something concrete.
- Output ONLY Python code. No markdown fences, no prose.

""" + REQUEST_CONTRACT + """
SPECIFICATION:

{spec}
"""

JUDGE_PROMPT = """\
You are auditing whether generated code faithfully implements a \
specification stack: a project brief plus, depending on the bundle, \
PlantUML diagrams (C4 container, UML sequence, UML state machine), a \
companion markdown specification, decision tables, an OpenAPI \
description, and Gherkin acceptance scenarios. The SPECIFICATION is \
ground truth; the CODE is under audit.

Count in the specification: elements (containers, diagram participants, \
external systems), relationships (declared interactions between \
elements; count each distinct pair once, a return edge belongs to its \
call edge), guards / flow conditions (branch conditions in diagrams, \
validation and threshold rules in tables or spec text), failure/error \
paths, and technology annotations (the technology argument on elements \
and relationships). Then count how many of each the code actually \
realizes (a relationship is realized if the corresponding interaction \
happens between the corresponding classes; a guard is faithful if the \
condition's meaning is preserved; a technology annotation is honored if \
the code plausibly reflects it in naming, interface shape or comments).

Separate the code's inventions into two lists:
- invented_business_logic: behavior with domain meaning that the \
specification never specified — invented business rules, thresholds, \
validation limits, state transitions, endpoints, or a concrete meaning \
assigned to a vague label. These are harmful: they look intentional but \
are the generator's guess.
- defensive_embellishments: benign engineering the specification didn't \
ask for but that adds no domain semantics — logging, type checks, \
constructors, defensive null handling around specified behavior.

fidelity_score: 0-100 overall — 100 means the code is a faithful, \
complete realization of everything the specification states; deduct for \
missing elements or interactions, altered guard semantics, and invented \
business logic (embellishments cost little).

SPECIFICATION:
{spec}

CODE:
{code}
"""


# ------------------------------------------------------------ API plumbing

class WaveAbort(RuntimeError):
    pass


_LOCK = threading.Lock()
_CALLS = {"n": 0}


def _thinking(model: str) -> dict:
    if model.startswith("claude-haiku"):
        return {}
    return {"thinking": {"type": "adaptive"}}


def _spend(usage: dict) -> float:
    total = 0.0
    for model, u in usage.items():
        pin, pout = PRICES[model]
        total += u["in"] / 1e6 * pin + u["out"] / 1e6 * pout
    return round(total, 4)


def prior_spend() -> float:
    """Spend recorded by earlier phases (probe/calib/wave reports)."""
    total = 0.0
    for rep in RESULTS_ROOT.glob("*/report.json"):
        try:
            total += float(json.loads(rep.read_text())["spend_usd"])
        except Exception:  # noqa: BLE001 — unreadable report: ignore
            pass
    return round(total, 4)


def _call(client, model: str, usage: dict, prior: float, **kwargs):
    with _LOCK:
        if _CALLS["n"] >= MAX_CALLS:
            raise WaveAbort(f"MAX_CALLS={MAX_CALLS} reached — aborting")
        if prior + _spend(usage) >= CEILING_USD:
            raise WaveAbort(f"ceiling ${CEILING_USD} reached — aborting")
        _CALLS["n"] += 1
    resp = client.messages.create(model=model, **kwargs)
    with _LOCK:
        u = usage.setdefault(model, {"in": 0, "out": 0})
        u["in"] += resp.usage.input_tokens
        u["out"] += resp.usage.output_tokens
    return resp


def _text_of(resp) -> str:
    # adaptive-thinking responses can carry zero text blocks
    return "".join(b.text for b in resp.content if b.type == "text")


def _strip_fences(text: str) -> str:
    m = re.search(r"```(?:python)?\n(.*?)```", text, flags=re.DOTALL)
    return m.group(1) if m else text


def _compiles(code: str):
    try:
        compile(code, "<generated>", "exec")
        return True, None
    except SyntaxError as e:
        return False, str(e)


# ----------------------------------------------------------------- bundles

def bundle_files(arm: str) -> list[tuple[str, str]]:
    return [(rel, (KIT / rel).read_text(encoding="utf-8"))
            for rel in ARMS[arm]]


def bundle_text(arm: str) -> str:
    return "\n\n".join(f"--- FILE: {name} ---\n{text}"
                       for name, text in bundle_files(arm))


def kit_hashes() -> dict:
    files = sorted({rel for arm in ARMS.values() for rel in arm})
    h = {rel: hashlib.sha256((KIT / rel).read_bytes()).hexdigest()
         for rel in files}
    h["tools/acceptance/cargo_quote_suite.py"] = hashlib.sha256(
        SUITE_FILE.read_bytes()).hexdigest()
    h["tools/acceptance/runner_child.py"] = hashlib.sha256(
        CHILD.read_bytes()).hexdigest()
    return h


# --------------------------------------------------------------- execution

def build_spec(scenario: str) -> dict:
    fam = suite_mod.SUITE
    sc = fam["scenarios"][scenario]
    return {
        "family": "cargo_quote", "scenario": scenario,
        "lexicons": fam["lexicons"],
        "entry_cls_like": fam["entry_cls_like"],
        "entry_cls_fallback": fam["entry_cls_fallback"],
        "entry_method_like": fam["entry_method_like"],
        "entry_func_like": fam["entry_func_like"],
        "args": fam["args"],
        "stubs": sc.get("stubs", []),
        "expect": sc["expect"],
        "failure_like": sc.get("failure_like", []),
        "must_call": sc.get("must_call", []),
        "must_not_call": sc.get("must_not_call", []),
        "request": sc.get("request", {}),
        "check_calls": True,
    }


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
                "entry": None, "detail": f"killed after {TIMEOUT_S}s"}
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    if not lines:
        return {"stage": "harness_error", "passed": False,
                "outcome_class": None, "entry": None,
                "detail": (proc.stderr or "no output")[:300]}
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return {"stage": "harness_error", "passed": False,
                "outcome_class": None, "entry": None,
                "detail": ("unparseable: " + lines[-1])[:300]}


def apply_overlay(scenario: str, res: dict) -> dict:
    ov = suite_mod.OVERLAYS.get(scenario)
    if not ov or not res.get("passed"):
        return res
    detail = (res.get("detail") or "").lower()
    require, forbid = ov.get("require_re"), ov.get("forbid_re")
    if require and not re.search(require, detail):
        res.update(passed=False, stage="wrong_outcome",
                   detail=f"overlay-require({require}): " + detail)
    elif forbid and re.search(forbid, detail):
        res.update(passed=False, stage="wrong_outcome",
                   detail=f"overlay-forbid({forbid}): " + detail)
    return res


ADAPTER_STAGES = {"import_error", "no_entry", "construct_error",
                  "harness_error"}


def execute_artifact(artifact: Path) -> list[dict]:
    rows = []
    for scen in suite_mod.SUITE["scenarios"]:
        res = apply_overlay(scen, run_child(artifact, build_spec(scen)))
        rows.append({"scenario": scen,
                     **{k: res.get(k) for k in
                        ("stage", "passed", "outcome_class", "entry",
                         "detail")}})
    return rows


# ------------------------------------------------------------------- waves

def generate_one(client, short: str, arm: str, run_idx: int,
                 usage: dict, prior: float) -> dict:
    model = GEN_MODELS[short]
    prompt = GEN_PROMPT.format(spec=bundle_text(arm))
    attempts = []
    code, ok = "", False
    in_tok = out_tok = 0
    for _ in range(2):  # retry once on truncation / non-compiling output
        resp = _call(client, model, usage, prior, max_tokens=GEN_MAX_TOKENS,
                     **_thinking(model),
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


def judge_one(client, arm: str, code: str, usage: dict,
              prior: float) -> dict:
    prompt = JUDGE_PROMPT.format(spec=bundle_text(arm), code=code)
    last = None
    for _ in range(2):
        resp = _call(
            client, JUDGE_MODEL, usage, prior, max_tokens=JUDGE_MAX_TOKENS,
            **_thinking(JUDGE_MODEL),
            output_config={"format": {"type": "json_schema",
                                      "schema": JUDGE_SCHEMA}},
            messages=[{"role": "user", "content": prompt}])
        try:
            return json.loads(_text_of(resp))
        except json.JSONDecodeError as e:
            last = e
    raise last


# ---------------------------------------------------------------- analysis

def _rates(runs: list[dict], arm: str, short: str | None = None) -> dict:
    """Pooled executed/semantic rates + per-scenario pass counts."""
    rows = [(r, row) for r in runs
            if r["arm"] == arm and (short is None or r["generator"] == short)
            for row in r.get("execution", [])]
    n = len(rows)
    n_pass = sum(bool(row["passed"]) for _, row in rows)
    sem = [(r, row) for r, row in rows if row["stage"] not in ADAPTER_STAGES]
    per_scen: dict[str, list[int]] = {}
    for _, row in rows:
        sp = per_scen.setdefault(row["scenario"], [0, 0])
        sp[1] += 1
        sp[0] += bool(row["passed"])
    return {
        "slots": n,
        "executed": round(n_pass / n, 4) if n else None,
        "semantic": (round(sum(bool(row["passed"]) for _, row in sem)
                           / len(sem), 4) if sem else None),
        "scenario_pass": {k: v for k, v in sorted(per_scen.items())},
    }


def _scen_rate(block: dict, scen: str) -> float:
    p, n = block["scenario_pass"].get(scen, (0, 0))
    return p / n if n else 0.0


def _net_gain(lo: dict, hi: dict, scen_set) -> float:
    """Sum of per-scenario pass-RATE deltas (scale-free across mixed n)."""
    return round(sum(_scen_rate(hi, s) - _scen_rate(lo, s)
                     for s in scen_set), 4)


def analyze(runs: list[dict]) -> dict:
    arms_present = [a for a in ARM_ORDER
                    if any(r["arm"] == a for r in runs)]
    pooled = {a: _rates(runs, a) for a in arms_present}
    per_gen = {short: {a: _rates(runs, a, short) for a in arms_present}
               for short in GEN_MODELS}

    # artifact tokens per arm per generator = mean input tokens - A0's
    tokens: dict = {}
    for short in GEN_MODELS:
        by_arm = {}
        for a in arms_present:
            ins = [r["input_tokens"] for r in runs
                   if r["arm"] == a and r["generator"] == short]
            by_arm[a] = round(sum(ins) / len(ins), 1) if ins else None
        base = by_arm.get("A0")
        tokens[short] = {
            "mean_input_tokens": by_arm,
            "artifact_tokens": {a: (round(by_arm[a] - base, 1)
                                    if base and by_arm.get(a) else None)
                                for a in arms_present},
        }

    # judged inventions (secondary; quoted as judgments, never merged)
    judged: dict = {}
    for short in GEN_MODELS:
        by_arm = {}
        for a in arms_present:
            counts = [len(r["judge"]["invented_business_logic"])
                      for r in runs
                      if r["arm"] == a and r["generator"] == short
                      and r.get("judge")]
            by_arm[a] = {
                "n": len(counts),
                "median": median(counts) if counts else None,
                "mean": (round(sum(counts) / len(counts), 2)
                         if counts else None),
            }
        judged[short] = by_arm

    def _pair_delta(scope: dict, lo: str, hi: str):
        a, b = scope.get(lo), scope.get(hi)
        if not a or not b or a["executed"] is None or b["executed"] is None:
            return None
        return round(b["executed"] - a["executed"], 4)

    additive = {f"{lo}->{hi}": {
        "pooled": _pair_delta(pooled, lo, hi),
        **{s: _pair_delta(per_gen[s], lo, hi) for s in GEN_MODELS}}
        for lo, hi in ADDITIVE_PAIRS}
    loo = {cls: {
        "pooled": (round(pooled["A4"]["executed"] - pooled[arm]["executed"], 4)
                   if pooled.get("A4") and pooled.get(arm) else None),
        **{s: (round(per_gen[s]["A4"]["executed"]
                     - per_gen[s][arm]["executed"], 4)
               if per_gen[s].get("A4") and per_gen[s].get(arm) else None)
           for s in GEN_MODELS}}
        for cls, arm in LOO_DROPS.items()}

    # marginal pp per thousand artifact tokens (per generator; additive
    # direction uses the token delta between adjacent arms, LOO the
    # A4-minus-arm token delta)
    per_kilo: dict = {}
    for short in GEN_MODELS:
        at = tokens[short]["artifact_tokens"]
        add = {}
        for lo, hi in ADDITIVE_PAIRS:
            d = additive[f"{lo}->{hi}"][short]
            if d is not None and at.get(hi) is not None \
                    and at.get(lo) is not None and at[hi] != at[lo]:
                add[f"{lo}->{hi}"] = round(
                    d * 100 / ((at[hi] - at[lo]) / 1000), 2)
        drop = {}
        for cls, arm in LOO_DROPS.items():
            d = loo[cls][short]
            if d is not None and at.get("A4") is not None \
                    and at.get(arm) is not None and at["A4"] != at[arm]:
                drop[cls] = round(d * 100 / ((at["A4"] - at[arm]) / 1000), 2)
        per_kilo[short] = {"additive_pp_per_ktok": add,
                          "loo_pp_per_ktok": drop}

    expectation_inputs = {}
    if all(a in pooled for a in
           ("A0", "A1", "A2", "A3", "A4", "L-structure", "L-behavior",
            "L-contract", "BC-behavior")):
        e6_hi = [r for r in runs if r["arm"] in ("A2", "A3", "A4")]
        e6_lo = [r for r in runs if r["arm"] in ("A0", "A1")]

        def _pool_scen(rs, scen):
            rows = [row for r in rs for row in r.get("execution", [])
                    if row["scenario"] == scen]
            return (round(sum(bool(x["passed"]) for x in rows)
                          / len(rows), 4) if rows else None)

        expectation_inputs = {
            "E1_A1_A2": additive["A1->A2"],
            "E1_largest_additive_pooled": max(
                additive, key=lambda k: (additive[k]["pooled"]
                                         if additive[k]["pooled"] is not None
                                         else -9)),
            "E2_A2_A3": additive["A2->A3"],
            "E2_net_gain_CONTRACT7": _net_gain(pooled["A2"], pooled["A3"],
                                               CONTRACT7),
            "E2_net_gain_total": _net_gain(pooled["A2"], pooled["A3"],
                                           suite_mod.SUITE["scenarios"]),
            "E3_A3_A4": additive["A3->A4"],
            "E3_net_gain_VALUE9": _net_gain(pooled["A3"], pooled["A4"],
                                            VALUE9),
            "E3_net_gain_LEAK2": _net_gain(pooled["A3"], pooled["A4"],
                                           LEAK2),
            "E4_loo_drops_pooled": {c: loo[c]["pooled"] for c in loo},
            "E5_BC_minus_Lbehavior_pooled": round(
                pooled["BC-behavior"]["executed"]
                - pooled["L-behavior"]["executed"], 4),
            "E5_net_loss_FLOWPI6": _net_gain(pooled["BC-behavior"],
                                             pooled["L-behavior"], FLOWPI6),
            "E5_net_loss_total": _net_gain(pooled["BC-behavior"],
                                           pooled["L-behavior"],
                                           suite_mod.SUITE["scenarios"]),
            "E6_hold_carrying": _pool_scen(e6_hi, "screening_down_hold"),
            "E6_hold_noncarrying": _pool_scen(e6_lo, "screening_down_hold"),
            "E6_refuse67_carrying": _pool_scen(e6_hi, "refuse_boundary_67"),
            "E6_refuse67_noncarrying": _pool_scen(e6_lo,
                                                  "refuse_boundary_67"),
            "E8_A1_A2_by_gen": {s: additive["A1->A2"][s]
                                for s in GEN_MODELS},
            "E8_A4_minus_BC_by_gen": {
                s: (round(per_gen[s]["A4"]["executed"]
                          - per_gen[s]["BC-behavior"]["executed"], 4)
                    if per_gen[s]["A4"]["executed"] is not None else None)
                for s in GEN_MODELS},
            "G1_A0_pooled": pooled["A0"]["executed"],
            "G2_A4_by_gen": {s: per_gen[s]["A4"]["executed"]
                             for s in GEN_MODELS},
        }

    return {
        "pooled": pooled, "per_generator": per_gen, "tokens": tokens,
        "judged_inventions": judged, "additive_increments": additive,
        "loo_drops": loo, "pp_per_kilotoken": per_kilo,
        "expectation_inputs": expectation_inputs,
    }


# ------------------------------------------------------------------ modes

def smoke() -> int:
    ref = KIT / "reference_impl.py"
    rows = execute_artifact(ref)
    n_pass = sum(bool(r["passed"]) for r in rows)
    for r in rows:
        mark = "PASS" if r["passed"] else "FAIL"
        print(f"  {mark}  {r['scenario']:24s} [{r['stage']}]")
    print(f"reference through driver scoring path: {n_pass}/{len(rows)}")
    return 0 if n_pass == len(rows) else 1


def probe(prior: float) -> int:
    import anthropic
    client = anthropic.Anthropic()
    usage: dict = {}
    models = list(GEN_MODELS.values()) + [JUDGE_MODEL]
    out = {}
    for m in models:
        try:
            resp = _call(client, m, usage, prior, max_tokens=64,
                         **_thinking(m),
                         messages=[{"role": "user",
                                    "content": "Reply with exactly: ok"}])
            out[m] = {"ok": True, "stop_reason": resp.stop_reason,
                      "thinking_param": bool(_thinking(m)),
                      "text": _text_of(resp).strip()[:40]}
        except Exception as e:  # noqa: BLE001 — probe reports, never raises
            out[m] = {"ok": False, "error": str(e)[:300]}
    report = {"phase": "probe", "models": out, "usage": usage,
              "spend_usd": _spend(usage), "calls_used": _CALLS["n"]}
    out_dir = RESULTS_ROOT / "probe"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if all(v["ok"] for v in out.values()) else 1


def run_wave(arms_runs: list[tuple[str, str, int]], out_name: str,
             with_judge: bool, prior: float) -> int:
    import anthropic
    client = anthropic.Anthropic()
    usage: dict = {}
    out_dir = RESULTS_ROOT / out_name
    out_dir.mkdir(parents=True, exist_ok=True)

    runs: list[dict] = []
    aborted = None
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = {pool.submit(generate_one, client, short, arm, idx,
                                usage, prior): (arm, short, idx)
                    for arm, short, idx in arms_runs}
            for fut in futs:
                runs.append(fut.result())
    except WaveAbort as e:
        aborted = str(e)
    runs.sort(key=lambda r: (ARM_ORDER.index(r["arm"]), r["generator"],
                             r["run"]))

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

    if with_judge and not aborted:
        try:
            with ThreadPoolExecutor(max_workers=8) as pool:
                futs = {pool.submit(judge_one, client, r["arm"], r["code"],
                                    usage, prior): r
                        for r in runs if r["compiles"]}
                for fut, r in futs.items():
                    try:
                        r["judge"] = fut.result()
                    except WaveAbort:
                        raise
                    except Exception as e:  # noqa: BLE001 — logged, excluded
                        r["judge"] = None
                        r["judge_error"] = str(e)[:300]
        except WaveAbort as e:
            aborted = str(e)

    report = {
        "phase": out_name,
        "pre_registration": "stack_experiment/W1_PREREGISTRATION.md",
        "generators": GEN_MODELS, "judge_model": JUDGE_MODEL,
        "runs_per_arm": {a: RUNS_PER_ARM[a] for a in ARMS},
        "gen_prompt": GEN_PROMPT, "judge_prompt": JUDGE_PROMPT,
        "kit_hashes": kit_hashes(),
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
    print(json.dumps(summary.get("pooled") or {}, indent=2))
    if aborted:
        print(f"ABORTED: {aborted}")
    print(f"spend this phase: ${_spend(usage)} "
          f"(cumulative ${round(prior + _spend(usage), 2)} "
          f"of ${CEILING_USD}) -> {out_dir}/report.json")
    return 2 if aborted else 0


def calibrate(prior: float) -> int:
    jobs = [("A4", short, i + 1)
            for short in GEN_MODELS for i in range(CALIB_RUNS)]
    rc = run_wave(jobs, "calib", with_judge=False, prior=prior)
    if rc:
        return rc
    report = json.loads(
        (RESULTS_ROOT / "calib" / "report.json").read_text())
    ok = True
    covered: set[str] = set()
    for short in GEN_MODELS:
        scores = []
        for r in report["runs"]:
            if r["generator"] != short:
                continue
            passed = sum(bool(row["passed"]) for row in r["execution"])
            scores.append(passed)
            covered |= {row["scenario"] for row in r["execution"]
                        if row["passed"]}
        med = median(scores) if scores else 0
        bar = "PASS" if med >= 9 else "FAIL"
        ok &= med >= 9
        print(f"calibration {short}: runs {scores}, median {med} "
              f"(bar >= 9/11): {bar}")
    missing = set(suite_mod.SUITE["scenarios"]) - covered
    if missing:
        ok = False
        print(f"scenarios never passed by any calibration run: "
              f"{sorted(missing)}")
    else:
        print("every scenario passed by >= 1 calibration run")
    print("CALIBRATION", "PASSED — freeze may proceed" if ok
          else "FAILED — fix, disclose, re-calibrate (freeze blocked)")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke", action="store_true",
                    help="reference impl through this driver's scoring "
                         "path ($0)")
    ap.add_argument("--probe", action="store_true",
                    help="one tiny live call per model ($0.01-ish)")
    ap.add_argument("--calibrate", action="store_true",
                    help="pristine A4 x 3 runs x both generators, "
                         "no judge")
    ap.add_argument("--wave", action="store_true",
                    help="the scored wave (66 runs + judges)")
    ap.add_argument("--confirm-frozen", action="store_true",
                    help="required with --wave: asserts the "
                         "pre-registration freeze commit exists and "
                         "owner go is recorded")
    ap.add_argument("--rejudge", action="store_true",
                    help="re-judge stored wave artifacts whose judge "
                         "call failed; no regeneration")
    args = ap.parse_args(argv)

    if args.smoke:
        return smoke()

    jobs = [(arm, short, i + 1) for arm in ARM_ORDER
            for short in GEN_MODELS for i in range(RUNS_PER_ARM[arm])]
    n_gen = len(jobs)
    plan = (f"plan: {n_gen} scored generations (+ up to 1 retry each) "
            f"+ {n_gen} judgements across {len(ARMS)} arms x 2 generators; "
            f"calibration {CALIB_RUNS} x 2 on A4; MAX_CALLS={MAX_CALLS} "
            f"(live), ceiling ${CEILING_USD} (cumulative)")
    if args.dry_run:
        print(plan)
        for arm in ARM_ORDER:
            files = ARMS[arm]
            missing = [f for f in files if not (KIT / f).exists()]
            chars = sum(len((KIT / f).read_bytes()) for f in files
                        if (KIT / f).exists())
            print(f"  {arm:12s} runs/gen={RUNS_PER_ARM[arm]} "
                  f"files={len(files)} chars={chars}"
                  + (f"  MISSING={missing}" if missing else ""))
        print(f"suite scenarios: {len(suite_mod.SUITE['scenarios'])}; "
              f"sets: CONTRACT7={len(CONTRACT7)} FLOWPI6={len(FLOWPI6)} "
              f"VALUE9={len(VALUE9)} LEAK2={len(LEAK2)}")
        return 0

    if not (os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("no Anthropic API credentials in the environment")
        return 2

    prior = prior_spend()
    if args.probe:
        return probe(prior)
    if args.calibrate:
        return calibrate(prior)
    if args.rejudge:
        return rejudge(prior)
    if args.wave:
        if not args.confirm_frozen:
            print("refusing: --wave requires --confirm-frozen (the "
                  "pre-registration must be frozen in a commit and owner "
                  "go recorded — W1_PREREGISTRATION.md preamble)")
            return 2
        print(plan)
        return run_wave(jobs, "wave_main", with_judge=True, prior=prior)
    print(plan + "\nnothing to do: pass one of --dry-run/--smoke/--probe/"
          "--calibrate/--wave/--rejudge")
    return 0


def rejudge(prior: float) -> int:
    import anthropic
    client = anthropic.Anthropic()
    out_dir = RESULTS_ROOT / "wave_main"
    report = json.loads((out_dir / "report.json").read_text())
    usage: dict = report.get("usage", {})
    todo = [r for r in report["runs"]
            if r.get("compiles") and r.get("judge") is None]
    print(f"re-judging {len(todo)} stored artifacts")
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {}
        for r in todo:
            code = (out_dir / r["code_file"]).read_text(encoding="utf-8")
            futs[pool.submit(judge_one, client, r["arm"], code,
                             usage, prior)] = r
        for fut, r in futs.items():
            try:
                r["judge"] = fut.result()
                r.pop("judge_error", None)
                r["judge_note"] = "re-judged"
            except Exception as e:  # noqa: BLE001
                r["judge_error"] = str(e)[:300]
    report["usage"] = usage
    report["spend_usd"] = _spend(usage)
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = analyze(report["runs"])
    (out_dir / "analysis.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"total spend recorded: ${report['spend_usd']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

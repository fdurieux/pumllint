"""C4 detail-ladder codegen experiment: what spec detail does C4-based
AI-codegen need?

Protocol, pre-registered expectations and interpretation matrix:
docs/c4-codegen-detail-experiment.md (frozen before any scored run).

One invented system (LoanCheck — credit check for a personal loan) is
specified at five additive detail rungs (c4_experiment/R0..R4): bare
containers -> checklist-complete containers -> + component diagrams ->
+ dynamic diagrams (qualitative guards) -> + companion spec (thresholds,
error policy, API contract). Code is generated from each rung and scored
against three oracles:

- **Mechanical structural conformance** (no LLM): AST-derived class set
  and cross-group reference edges vs the declared C4 relationship graph.
- **Execution** against the frozen acceptance suite derived from the
  intended system (tools/acceptance/c4_loan_suite.py), run by the frozen
  sandbox runner (tools/acceptance/runner_child.py, unchanged).
- **Judged fidelity/inventions** (claude-sonnet-5, judgments only): the
  house invention taxonomy vs the generating rung's own spec text.

Generation: claude-opus-4-8, 3 runs per rung, scaffold-pinned prompt
(class-per-element, alias-derived names, handle(request) entry — the
Phase-B lesson: pinning makes the mechanical oracle meaningful; the
conformance claim is therefore "under an explicitly conforming prompt").

Cost guard: aborts if the plan exceeds MAX_CALLS API calls. Execution and
conformance are $0.

Run:
  python tools/c4_codegen_experiment.py --dry-run
  python tools/c4_codegen_experiment.py --calibrate 2   # R4 only, no judge
  python tools/c4_codegen_experiment.py                 # the scored wave

Adversarial-threshold replication (pre-registered in the protocol doc's
§Adversarial-threshold replication; arms R3 and R4A, suite
tools/acceptance/c4_loan_adv_suite.py, results c4_experiment_results/
adv_wave/):
  python tools/c4_codegen_experiment.py --adversarial            # API wave
  python tools/c4_codegen_experiment.py --adversarial \
      --score-dir c4_experiment_results/adv_wave \
      --instrument-label "<generator label>"
The --score-dir mode runs the $0 oracles (mechanical conformance +
execution) over pre-generated gen_<rung>_run<n>.py artifacts — the path
used when generation happens outside this harness (e.g. the disclosed
subagent instrument of the 2026-08-01 replication, where the environment
held no raw API credentials).
"""

from __future__ import annotations

import argparse
import ast
import base64
import json
import os
import re
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _scorelib  # noqa: E402
from acceptance import c4_loan_suite  # noqa: E402

GEN_MODEL = "claude-opus-4-8"
JUDGE_MODEL = "claude-sonnet-5"
PRICES = {  # $/M tokens (input, output)
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
}
RUNGS = ["R0", "R1", "R2", "R3", "R4"]
# Adversarial-threshold replication arms: R3 (inputs identical to the main
# ladder's R3 — qualitative guards, no numbers) vs R4A (R3 + companion spec
# whose business-rule numbers are all moved off their canonical values).
ADV_RUNGS = ["R3", "R4A"]
RUNG_ROOT = REPO_ROOT / "c4_experiment"
RESULTS_DIR = REPO_ROOT / "c4_experiment_results"
CHILD = Path(__file__).resolve().parent / "acceptance" / "runner_child.py"
RUNS_PER_RUNG = 3
MAX_CALLS = 60
TIMEOUT_S = 15

# ------------------------------------------------------- declared structure
# Hand-derived from the rung diagrams at freeze time. The scaffold prompt
# pins class names to element aliases, so conformance matching is exact
# CamelCase first, alias-token fallback.

EXPECTED_BASE = ["OriginationApi", "DecisionEngine", "ApplicationStore",
                 "CreditBureau", "NotificationService"]
EXPECTED_COMPONENTS = ["ApplicationService", "ApplicationValidator",
                       "ScoringPolicy", "BureauGateway"]

GROUPS = {
    "origination_api": {"originationapi", "applicationservice",
                        "applicationvalidator"},
    "decision_engine": {"decisionengine", "scoringpolicy", "bureaugateway"},
    "application_store": {"applicationstore"},
    "credit_bureau": {"creditbureau"},
    "notification_service": {"notificationservice"},
}
# Call-direction container-level graph (return Rels in the dynamics map
# onto their call edge; the Person entry edge is realized as handle()).
GROUP_EDGES = {
    ("origination_api", "application_store"),
    ("origination_api", "decision_engine"),
    ("decision_engine", "credit_bureau"),
    ("origination_api", "notification_service"),
}
# Internal refinement edges declared by the R2+ component diagrams.
COMPONENT_EDGES = {
    ("applicationservice", "applicationvalidator"),
    ("scoringpolicy", "bureaugateway"),
}

ALIAS_OF = {  # normalized class name -> snake alias as written in diagrams
    "originationapi": "origination_api",
    "decisionengine": "decision_engine",
    "applicationstore": "application_store",
    "creditbureau": "credit_bureau",
    "notificationservice": "notification_service",
    "applicationservice": "application_service",
    "applicationvalidator": "application_validator",
    "scoringpolicy": "scoring_policy",
    "bureaugateway": "bureau_gateway",
}


def expected_classes(rung: str) -> list[str]:
    return EXPECTED_BASE + (EXPECTED_COMPONENTS if rung >= "R2" else [])


# ------------------------------------------------------------------ prompts

# Entry-point contract: identical wording to the Phase-B pinned prompts
# (tools/codegen_experiment.py REQUEST_CONTRACT) for cross-program
# comparability.
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

GEN_PROMPT = """\
Implement the system specified below as a single self-contained Python \
module. The specification is a C4 model: one or more PlantUML diagrams \
using C4 macros (Person / Container / Component / System_Ext / Rel), \
possibly followed by a companion markdown specification.

Rules:
- One class per Container, ContainerDb and System_Ext element. If \
component diagrams are provided, additionally one class per Component; \
a component class implements part of its container's responsibility.
- Name each class after the element's alias in CamelCase (alias \
credit_bureau -> class CreditBureau).
- Relationships (Rel) become method calls from the source element's \
class to the target element's class. Do not add calls between elements \
that have no declared relationship.
- Where the specification describes flows, steps, guards or rules, \
implement them; failure paths become raised exceptions or error returns.
- External systems (System_Ext) are outside the system boundary: \
implement each as a simple class whose methods return plausible values.
- Where the specification is ambiguous or incomplete, make your best \
guess and implement something concrete.
- Output ONLY Python code. No markdown fences, no prose.

""" + REQUEST_CONTRACT + """
SPECIFICATION:

{spec}
"""

JUDGE_PROMPT = """\
You are auditing whether generated code faithfully implements a C4 model \
specification (PlantUML C4 diagrams, possibly with a companion markdown \
spec). The SPECIFICATION is ground truth; the CODE is under audit.

Count in the specification: elements (Person/Container/Component/external \
systems), relationships (Rel lines; count each distinct pair once, a \
numbered dynamic-flow return edge belongs to its call edge), guards / \
flow conditions (bracketed conditions in dynamic diagrams, validation and \
threshold rules in a companion spec), failure/error paths, and technology \
annotations (the technology argument on elements and relationships). Then \
count how many of each the code actually realizes (a relationship is \
realized if the corresponding interaction happens between the \
corresponding classes; a guard is faithful if the condition's meaning is \
preserved; a technology annotation is honored if the code plausibly \
reflects it in naming, interface shape or comments).

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

JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "elements_expected": {"type": "integer"},
        "elements_implemented": {"type": "integer"},
        "relationships_expected": {"type": "integer"},
        "relationships_implemented": {"type": "integer"},
        "guards_expected": {"type": "integer"},
        "guards_faithful": {"type": "integer"},
        "failure_paths_expected": {"type": "integer"},
        "failure_paths_implemented": {"type": "integer"},
        "technologies_expected": {"type": "integer"},
        "technologies_honored": {"type": "integer"},
        "invented_business_logic": {"type": "array",
                                    "items": {"type": "string"}},
        "defensive_embellishments": {"type": "array",
                                     "items": {"type": "string"}},
        "fidelity_score": {"type": "integer"},
        "notes": {"type": "string"},
    },
    "required": [
        "elements_expected", "elements_implemented",
        "relationships_expected", "relationships_implemented",
        "guards_expected", "guards_faithful",
        "failure_paths_expected", "failure_paths_implemented",
        "technologies_expected", "technologies_honored",
        "invented_business_logic", "defensive_embellishments",
        "fidelity_score", "notes",
    ],
}


# ------------------------------------------------------------- API plumbing

_USAGE_LOCK = threading.Lock()


def _thinking(model: str) -> dict:
    if model.startswith("claude-haiku"):
        return {}
    return {"thinking": {"type": "adaptive"}}


def _call(client, model: str, usage: dict, **kwargs):
    resp = client.messages.create(model=model, **kwargs)
    with _USAGE_LOCK:
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


def _spend(usage: dict) -> float:
    total = 0.0
    for model, u in usage.items():
        pin, pout = PRICES[model]
        total += u["in"] / 1e6 * pin + u["out"] / 1e6 * pout
    return round(total, 2)


# ------------------------------------------------------------------- inputs

def rung_files(rung: str) -> list[tuple[str, str]]:
    return [(p.name, p.read_text(encoding="utf-8"))
            for p in sorted((RUNG_ROOT / rung).iterdir())
            if p.suffix in (".puml", ".md")]


def rung_spec_text(rung: str) -> str:
    return "\n\n".join(f"--- FILE: {name} ---\n{text}"
                       for name, text in rung_files(rung))


def pumllint_view(rung: str) -> list[dict]:
    """What today's pumllint (codegen profile) says about each rung file."""
    out = []
    for p in sorted((RUNG_ROOT / rung).glob("*.puml")):
        r = _scorelib.score_first_diagram(p, "codegen")
        _, violations = _scorelib.lint_first_diagram(p, "codegen")
        out.append({
            "file": p.name, "level": r.level, "composite": r.composite,
            "element_count": r.element_count,
            "findings": sorted({v.rule_id for v in violations}),
        })
    return out


# ------------------------------------------------- mechanical conformance

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _group_of(nn: str):
    for g, members in GROUPS.items():
        if nn in members:
            return g
    return None


_ACTOR_NAMES = {"applicant", "person", "loanapplicant", "customer",
                "applicantperson"}  # Person-actor modeling, not architecture


def conformance(code: str, rung: str) -> dict:
    """AST + token scan: declared-graph realization, extras. Deterministic;
    calibrated on R4 pristine artifacts before the freeze (see protocol).
    Edges are detected two ways, OR-ed: (a) textual mention of another
    element's class name or alias inside a class body; (b) name-flow
    through constructor injection — instantiation-site argument types
    mapped onto __init__ params, params onto self attributes, and
    self.<attr>.<method>() uses inside the class body."""
    tree = ast.parse(code)
    expected = expected_classes(rung)
    known = {_norm(n): n for n in expected}
    camel_to_norm = {v: k for k, v in known.items()}
    segments: dict[str, str] = {}   # normalized known name -> class source
    nodes: dict[str, ast.ClassDef] = {}
    extra_classes: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        nn = _norm(node.name)
        seg = ast.get_source_segment(code, node) or ""
        if nn in known:
            segments[nn] = seg
            nodes[nn] = node
        else:
            bases = [getattr(b, "id", getattr(b, "attr", "")) for b in node.bases]
            if (node.name.endswith(("Error", "Exception"))
                    or any(str(b).endswith(("Error", "Exception")) for b in bases)):
                continue  # exception types are modeling vocabulary, not elements
            if nn in _ACTOR_NAMES:
                continue
            extra_classes.append(node.name)

    # ---- name-flow: which known class does each constructor param carry?
    def _call_class(call) -> str | None:
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name):
            return camel_to_norm.get(call.func.id)
        return None

    var_types: dict[str, str] = {}  # any `x = KnownClass(...)` in the module
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 \
                and isinstance(n.targets[0], ast.Name):
            t = _call_class(n.value)
            if t:
                var_types[n.targets[0].id] = t

    init_params: dict[str, list] = {}      # class -> [(param, annotation)]
    param_attr: dict[str, dict] = {}       # class -> {param: attr}
    attr_types: dict[str, dict] = {}       # class -> {attr: known class}
    for nn, cnode in nodes.items():
        for item in cnode.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                params = item.args.args[1:]
                init_params[nn] = [
                    (a.arg, camel_to_norm.get(getattr(a.annotation, "id", "")))
                    for a in params]
                pa, at = {}, {}
                for st in ast.walk(item):
                    if isinstance(st, ast.Assign) and len(st.targets) == 1 \
                            and isinstance(st.targets[0], ast.Attribute) \
                            and isinstance(st.targets[0].value, ast.Name) \
                            and st.targets[0].value.id == "self":
                        attr = st.targets[0].attr
                        if isinstance(st.value, ast.Name):
                            pa[st.value.id] = attr
                        direct = _call_class(st.value)
                        if direct:
                            at[attr] = direct
                param_attr[nn], attr_types[nn] = pa, at
                for pname, panno in init_params[nn]:
                    if panno and pname in pa:
                        at[pa[pname]] = panno

    for n in ast.walk(tree):  # instantiation sites -> param types
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)):
            continue
        nn = camel_to_norm.get(n.func.id)
        if nn is None or nn not in init_params:
            continue

        def _arg_type(a):
            if isinstance(a, ast.Name):
                return var_types.get(a.id)
            return _call_class(a)

        for i, a in enumerate(n.args):
            if i < len(init_params[nn]):
                t = _arg_type(a)
                pname = init_params[nn][i][0]
                if t and pname in param_attr.get(nn, {}):
                    attr_types[nn][param_attr[nn][pname]] = t
        for kw in n.keywords:
            t = _arg_type(kw.value)
            if t and kw.arg in param_attr.get(nn, {}):
                attr_types[nn][param_attr[nn][kw.arg]] = t

    def _mentions(seg: str, nn_target: str) -> bool:
        camel = known[nn_target]
        alias = ALIAS_OF[nn_target]
        return (re.search(rf"\b{re.escape(camel)}\b", seg) is not None
                or re.search(rf"\b{re.escape(alias)}\b", seg) is not None)

    edges = set()
    for nn_a, seg in segments.items():
        for nn_b in segments:
            if nn_a == nn_b:
                continue
            if _mentions(seg, nn_b):
                edges.add((nn_a, nn_b))
        for attr in set(re.findall(r"\bself\.(\w+)\.", seg)):
            t = attr_types.get(nn_a, {}).get(attr)
            if t and t != nn_a:
                edges.add((nn_a, t))

    group_edges = set()
    for a, b in edges:
        ga, gb = _group_of(a), _group_of(b)
        if ga and gb and ga != gb:
            group_edges.add((ga, gb))
    realized = group_edges & GROUP_EDGES
    extra_group = sorted(group_edges - GROUP_EDGES)
    comp_realized = sorted(edges & COMPONENT_EDGES) if rung >= "R2" else []

    groups_present = {g for g, members in GROUPS.items()
                      if any(nn in segments for nn in members
                             if nn in known)}
    return {
        "classes_present": sorted(known[nn] for nn in segments),
        "classes_missing": sorted(known[nn] for nn in known
                                  if nn not in segments),
        "groups_missing": sorted(set(GROUPS) - groups_present),
        "extra_classes": sorted(extra_classes),
        "group_edges_realized": sorted(realized),
        "group_edge_recall": round(len(realized) / len(GROUP_EDGES), 3),
        "extra_group_edges": extra_group,
        "component_edges_realized": comp_realized,
        "component_edge_recall": (round(len(comp_realized)
                                        / len(COMPONENT_EDGES), 3)
                                  if rung >= "R2" else None),
        "handle_present": bool(re.search(r"^def handle\(", code, re.M)),
    }


# ------------------------------------------------------------- execution

ADAPTER_STAGES = {"import_error", "no_entry", "construct_error",
                  "harness_error"}


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
                "entry": None, "calls": [], "detail": f"killed after {TIMEOUT_S}s"}
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    if not lines:
        return {"stage": "harness_error", "passed": False,
                "outcome_class": None, "entry": None, "calls": [],
                "detail": (proc.stderr or "no output")[:300]}
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return {"stage": "harness_error", "passed": False,
                "outcome_class": None, "entry": None, "calls": [],
                "detail": ("unparseable: " + lines[-1])[:300]}


def build_spec(scenario: str, suite=None) -> dict:
    fam = (suite or c4_loan_suite).SUITE
    sc = fam["scenarios"][scenario]
    return {
        "family": "loan_origination", "scenario": scenario,
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


def execute_artifact(artifact: Path, suite=None) -> list[dict]:
    suite = suite or c4_loan_suite
    # Pre-registered overlay: the runner has no "review" outcome class. The
    # canonical suite predates REVIEW_OVERLAY_SCENARIOS, hence the default.
    overlay = set(getattr(suite, "REVIEW_OVERLAY_SCENARIOS",
                          ("borderline_review",)))
    rows = []
    for scen in suite.SUITE["scenarios"]:
        res = run_child(artifact, build_spec(scen, suite))
        if scen in overlay and res.get("passed"):
            d = (res.get("detail") or "").lower()
            if not (re.search(suite.REVIEW_RE, d)
                    and not re.search(suite.DECIDED_RE, d)):
                res["passed"] = False
                res["stage"] = "wrong_outcome"
                res["detail"] = "review-overlay: " + (res.get("detail") or "")
        rows.append({"scenario": scen,
                     **{k: res.get(k) for k in
                        ("stage", "passed", "outcome_class", "entry",
                         "detail")}})
    return rows


# ------------------------------------------------------------------ waves

def generate_one(client, rung: str, run_idx: int, usage: dict) -> dict:
    prompt = GEN_PROMPT.format(spec=rung_spec_text(rung))
    attempts = []
    code, ok = "", False
    for _ in range(2):  # retry once on truncation / non-compiling output
        resp = _call(client, GEN_MODEL, usage, max_tokens=12000,
                     **_thinking(GEN_MODEL),
                     messages=[{"role": "user", "content": prompt}])
        code = _strip_fences(_text_of(resp)).strip()
        ok, err = _compiles(code)
        attempts.append({"stop_reason": resp.stop_reason,
                         "compiles": ok, "error": err})
        if ok and resp.stop_reason != "max_tokens":
            break
    return {"rung": rung, "run": run_idx, "code": code,
            "attempts": attempts, "compiles": ok}


JUDGE_MAX_TOKENS = 16000  # C4 rung specs are far larger than sequence
# diagrams; 6000 (the house judge budget) exhausted on adaptive thinking
# for 9/15 first-wave judgements (empty/truncated JSON). Run note in the
# protocol doc; retry-once on a parse failure.


def judge_one(client, rung: str, code: str, usage: dict) -> dict:
    prompt = JUDGE_PROMPT.format(spec=rung_spec_text(rung), code=code)
    last = None
    for _ in range(2):
        resp = _call(
            client, JUDGE_MODEL, usage, max_tokens=JUDGE_MAX_TOKENS,
            **_thinking(JUDGE_MODEL),
            output_config={"format": {"type": "json_schema",
                                      "schema": JUDGE_SCHEMA}},
            messages=[{"role": "user", "content": prompt}])
        try:
            return json.loads(_text_of(resp))
        except json.JSONDecodeError as e:
            last = e
    raise last


def analyze(runs: list[dict]) -> dict:
    per_rung: dict = {}
    for r in runs:
        agg = per_rung.setdefault(r["rung"], {
            "artifacts": 0, "compile_first_try": 0, "exec_n": 0,
            "exec_pass": 0, "sem_n": 0, "sem_pass": 0, "recalls": [],
            "extra_edges": 0, "extra_classes": 0, "invented": [],
            "embellish": [], "fidelity": [], "scenario_pass": {},
        })
        agg["artifacts"] += 1
        agg["compile_first_try"] += bool(r["attempts"][0]["compiles"])
        c = r.get("conformance") or {}
        if c:
            agg["recalls"].append(c["group_edge_recall"])
            agg["extra_edges"] += len(c["extra_group_edges"])
            agg["extra_classes"] += len(c["extra_classes"])
        for row in r.get("execution", []):
            agg["exec_n"] += 1
            agg["exec_pass"] += bool(row["passed"])
            sp = agg["scenario_pass"].setdefault(row["scenario"], [0, 0])
            sp[1] += 1
            sp[0] += bool(row["passed"])
            if row["stage"] not in ADAPTER_STAGES:
                agg["sem_n"] += 1
                agg["sem_pass"] += bool(row["passed"])
        j = r.get("judge") or {}
        if j:
            agg["invented"].append(len(j["invented_business_logic"]))
            agg["embellish"].append(len(j["defensive_embellishments"]))
            agg["fidelity"].append(j["fidelity_score"])

    out = {}
    for rung in RUNGS + [r for r in ADV_RUNGS if r not in RUNGS]:
        a = per_rung.get(rung)
        if not a:
            continue
        mean = lambda xs: round(sum(xs) / len(xs), 2) if xs else None
        out[rung] = {
            "artifacts": a["artifacts"],
            "compile_first_try": a["compile_first_try"],
            "executed_pass_rate": (round(a["exec_pass"] / a["exec_n"], 3)
                                   if a["exec_n"] else None),
            "semantic_pass_rate": (round(a["sem_pass"] / a["sem_n"], 3)
                                   if a["sem_n"] else None),
            "scenario_pass": {k: f"{v[0]}/{v[1]}"
                              for k, v in sorted(a["scenario_pass"].items())},
            "group_edge_recall_mean": mean(a["recalls"]),
            "extra_group_edges_total": a["extra_edges"],
            "extra_classes_total": a["extra_classes"],
            "invented_mean": mean(a["invented"]),
            "embellish_mean": mean(a["embellish"]),
            "fidelity_mean": mean(a["fidelity"]),
        }
    return out


def score_pregenerated(dir_path: Path, suite, rungs: list[str],
                       instrument: str) -> int:
    """$0 oracles over pre-generated artifacts: mechanical conformance +
    execution against `suite` for every gen_<rung>_run<n>.py in dir_path.
    Preserves judge rows already present in an existing report.json (so a
    judge pass merged into the report survives re-scoring). Generation
    metadata beyond compile status is not reconstructable here — the
    instrument label in the report says where the artifacts came from."""
    prior: dict = {}
    report_path = dir_path / "report.json"
    if report_path.exists():
        old = json.loads(report_path.read_text(encoding="utf-8"))
        prior = {(r["rung"], r["run"]): r for r in old.get("runs", [])}
    runs = []
    for p in sorted(dir_path.glob("gen_*_run*.py")):
        m = re.match(r"gen_(.+)_run(\d+)\.py$", p.name)
        if not m:
            continue
        rung, idx = m.group(1), int(m.group(2))
        code = p.read_text(encoding="utf-8")
        ok, err = _compiles(code)
        r = {"rung": rung, "run": idx, "code_file": p.name,
             "attempts": [{"stop_reason": None, "compiles": ok,
                           "error": err}],
             "compiles": ok}
        for k in ("judge", "judge_error", "judge_note", "gen_tool_uses",
                  "judge_tool_uses"):
            if k in prior.get((rung, idx), {}):
                r[k] = prior[(rung, idx)][k]
        if ok:
            r["conformance"] = conformance(code, rung)
            r["execution"] = execute_artifact(p, suite)
        else:
            r["conformance"] = None
            r["execution"] = [{"scenario": s, "stage": "import_error",
                               "passed": False, "outcome_class": None,
                               "entry": None, "detail": "does not compile"}
                              for s in suite.SUITE["scenarios"]]
        runs.append(r)
    if not runs:
        print(f"no gen_*_run*.py artifacts in {dir_path}")
        return 2
    report = {
        "instrument": instrument, "suite_module": suite.__name__,
        "judge_model": JUDGE_MODEL,
        "pumllint_view": {rung: pumllint_view(rung) for rung in rungs
                          if (RUNG_ROOT / rung).is_dir()},
        "runs": runs,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n",
                           encoding="utf-8")
    summary = analyze(runs)
    (dir_path / "analysis.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"scored {len(runs)} artifacts -> {report_path}")
    return 0


def rejudge(uniform: bool = False) -> int:
    """Re-run judge calls of wave_main on the stored artifacts
    (generation, conformance and execution rows untouched). Default:
    only failed calls. --rejudge-uniform: also re-judge first-pass
    judgements that ran at the old 6000 budget, so every judgement in
    the record shares one configuration; the old result is preserved
    under "judge_6k"."""
    import anthropic
    client = anthropic.Anthropic()
    out_dir = RESULTS_DIR / "wave_main"
    report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    usage: dict = report.get("usage", {})
    todo = [r for r in report["runs"] if r.get("compiles")
            and (r.get("judge") is None
                 or (uniform and "judge_note" not in r))]
    print(f"re-judging {len(todo)} stored artifacts "
          f"(max_tokens={JUDGE_MAX_TOKENS}, uniform={uniform})")
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {}
        for r in todo:
            code = (out_dir / r["code_file"]).read_text(encoding="utf-8")
            futs[pool.submit(judge_one, client, r["rung"], code, usage)] = r
        for fut, r in futs.items():
            try:
                new = fut.result()
                if r.get("judge") is not None:
                    r["judge_6k"] = r["judge"]
                r["judge"] = new
                r.pop("judge_error", None)
                r["judge_note"] = ("uniform re-judge at max_tokens=16000"
                                   if uniform and "judge_6k" in r
                                   else "re-judged at max_tokens=16000")
            except Exception as e:  # noqa: BLE001
                r["judge_error"] = str(e)[:300]
    report["usage"] = usage
    report["spend_usd"] = _spend(usage)
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = analyze(report["runs"])
    (out_dir / "analysis.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"total spend: ${report['spend_usd']}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--calibrate", type=int, metavar="N",
                    help="R4-only calibration: N runs, gen+conformance+"
                         "execution, no judge")
    ap.add_argument("--rejudge", action="store_true",
                    help="re-judge stored wave_main artifacts whose judge "
                         "call failed; no regeneration")
    ap.add_argument("--rejudge-uniform", action="store_true",
                    help="re-judge remaining old-budget judgements so all "
                         "judgements share max_tokens=16000")
    ap.add_argument("--runs", type=int, default=RUNS_PER_RUNG)
    ap.add_argument("--adversarial", action="store_true",
                    help="adversarial-threshold replication: arms R3+R4A, "
                         "suite acceptance.c4_loan_adv_suite, results in "
                         "c4_experiment_results/adv_wave/")
    ap.add_argument("--score-dir", metavar="DIR",
                    help="run the $0 oracles over pre-generated "
                         "gen_<rung>_run<n>.py artifacts in DIR; no API")
    ap.add_argument("--instrument-label", default="pregenerated",
                    help="generator label recorded in a --score-dir report")
    args = ap.parse_args(argv)

    if args.rejudge or args.rejudge_uniform:
        return rejudge(uniform=args.rejudge_uniform)

    suite_mod = c4_loan_suite
    rung_list = RUNGS
    if args.adversarial:
        from acceptance import c4_loan_adv_suite
        suite_mod = c4_loan_adv_suite
        rung_list = ADV_RUNGS

    if args.score_dir:
        return score_pregenerated(Path(args.score_dir), suite_mod, rung_list,
                                  args.instrument_label)

    if not (os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("no Anthropic API credentials in the environment")
        return 2

    calibrating = args.calibrate is not None
    rungs = ["R4"] if calibrating else rung_list
    n_runs = args.calibrate if calibrating else args.runs
    n_gen = len(rungs) * n_runs
    n_judge = 0 if calibrating else n_gen
    plan_calls = n_gen * 2 + n_judge  # retries counted at worst case
    est = round(n_gen * (0.03 + 4000 / 1e6 * 25.0)
                + n_judge * (0.03 + 1500 / 1e6 * 15.0), 2)
    print(f"plan: {n_gen} generations + {n_judge} judgements "
          f"(<= {plan_calls} calls, est ~${est}); "
          f"{len(rungs)} rungs x {n_runs} runs; "
          f"{len(suite_mod.SUITE['scenarios'])} scenarios/artifact"
          + (" [adversarial]" if args.adversarial else ""))
    if plan_calls > MAX_CALLS:
        print(f"aborting: plan exceeds MAX_CALLS={MAX_CALLS}")
        return 2
    if args.dry_run:
        for rung in rungs:
            print(f"  {rung}: {[n for n, _ in rung_files(rung)]}")
        return 0

    import anthropic
    client = anthropic.Anthropic()
    usage: dict = {}
    out_dir = RESULTS_DIR / ("calib" if calibrating
                             else "adv_wave" if args.adversarial
                             else "wave_main")
    out_dir.mkdir(parents=True, exist_ok=True)

    jobs = [(rung, i + 1) for rung in rungs for i in range(n_runs)]
    runs: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {pool.submit(generate_one, client, rung, idx, usage): (rung, idx)
                for rung, idx in jobs}
        for fut, (rung, idx) in futs.items():
            runs.append(fut.result())
    runs.sort(key=lambda r: (r["rung"], r["run"]))

    for r in runs:
        art = out_dir / f"gen_{r['rung']}_run{r['run']}.py"
        art.write_text(r["code"], encoding="utf-8")
        r["code_file"] = art.name
        if r["compiles"]:
            r["conformance"] = conformance(r["code"], r["rung"])
            r["execution"] = execute_artifact(art, suite_mod)
        else:
            r["conformance"] = None
            r["execution"] = [{"scenario": s, "stage": "import_error",
                               "passed": False, "outcome_class": None,
                               "entry": None, "detail": "does not compile"}
                              for s in suite_mod.SUITE["scenarios"]]

    if not calibrating:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = {pool.submit(judge_one, client, r["rung"], r["code"],
                                usage): r
                    for r in runs if r["compiles"]}
            for fut, r in futs.items():
                try:
                    r["judge"] = fut.result()
                except Exception as e:  # noqa: BLE001 — logged, run excluded
                    r["judge"] = None
                    r["judge_error"] = str(e)[:300]

    report = {
        "gen_model": GEN_MODEL, "judge_model": JUDGE_MODEL,
        "runs_per_rung": n_runs, "calibrating": calibrating,
        "prompt": GEN_PROMPT, "usage": usage, "spend_usd": _spend(usage),
        "pumllint_view": {rung: pumllint_view(rung) for rung in rungs},
        "runs": [{k: v for k, v in r.items() if k != "code"}
                 for r in runs],
    }
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = analyze(runs)
    (out_dir / "analysis.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"spend: ${_spend(usage)}  -> {out_dir}/report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

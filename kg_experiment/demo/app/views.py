"""Build the report view of one scenario from its result files.

Everything the page shows comes from here: the pipeline strip's numbers
(``deterministic.json`` and the ``run<i>_<arm>.json`` files), the arms'
summaries, the bundle, the generated code, the oracle's per-scenario
verdicts, and the placement of the scenario on the systemic model. The
record is ``kg_experiment/results``; a demo run is a dated folder under
``results/demo-runs/``. Standard library only.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent.parent                      # kg_experiment/
RESULTS = EXP / "results"
sys.path.insert(0, str(HERE.parent / "tools"))
import compare_deterministic  # noqa: E402  (the same leaf-by-leaf comparison the CI job runs)
SUITE_ORDER = ["quoted_low_risk", "accept_boundary_41", "review_boundary_42", "refuse_boundary_67",
               "refuse_high_risk", "price_exact_heavy", "price_exact_both", "invalid_weight_low",
               "invalid_value_over", "screening_down_hold", "store_down_error"]
RULE_ORDER = ["R-STRUCT", "R-CORROBORATE", "R-CONFLICT", "R-VAGUE", "R-REQ", "R-UNVERIFIED"]
RECORD_MODEL = "gpt-5.1-2025-11-13"  # harness/arms.py RECORD_MODEL; a run by another model is a deviation

# One line per scenario, from the record's §6 table (docs/neo4j-governed-knowledge-evaluation.md).
SCENARIOS = {
    "S1": {"title": "complete, verified",
           "represented": "145 assertions, 111 approved; 0 gaps on required keys",
           "gate": "PROCEED", "defect": "none; both arms correct",
           "plant": "nothing planted: the pristine kit, every assertion verified by the suite or the dated review record and approved",
           "plain": "With nothing wrong in the documents, both assistants produced working code. The gate added nothing here, and cost nothing either."},
    "S2": {"title": "missing, declared",
           "represented": "Gap{missing, declared} on REQ-06 and on the outage key; hold_presence absent",
           "gate": "BLOCKED", "defect": "prevented in G; outage scenario fails in every B run",
           "plant": "the screening-outage rule deleted from every artefact that states it; REQ-06 reads NOT YET SPECIFIED (open decision OD-1)",
           "plain": "The documents said the outage rule was still to be decided. The governed assistant stopped and asked for that decision, naming the open item. The baseline noticed it too and asked, but wrote code anyway, and that code turns an outage into an error; only the acceptance tests caught it. This is the kind of defect the gate exists to prevent."},
    "S3": {"title": "ambiguous",
           "represented": "17 ambiguity gaps; 4 keys proposed; DMN declared not authored",
           "gate": "QUALIFIED", "defect": "41-boundary fails 4/5 G, 5/5 B; the guess is an # ASSUMPTION constant in G, silent in B",
           "plant": "DT-S rows reworded to vague ranges, the symbolic names undefined, the DMN absent",
           "plain": "The thresholds were written as vague ranges, so both assistants had to guess. The baseline guessed silently. The governed one carried each guess as a labelled assumption pointing at the statement it rests on, so a reviewer can find it and fix it, though its code was not better for that, and in two runs it was worse."},
    "S4": {"title": "contradictory",
           "represented": "4 CONTRADICTS pairs, 4 disputed, 4 conflict gaps",
           "gate": "BLOCKED", "defect": "none by the oracle; B resolved by an invented precedence",
           "plant": "the sequence diagram and the BPMN say the outage fails the quote; the decision table and the spec say it is priced and held",
           "plain": "Two documents said one thing and two others the opposite. The governed assistant refused to choose and named the contradiction. The baseline chose a side by inventing a rule nothing stated, that the newer text wins; it happened to pick the right side, so the tests passed, but nothing in its output lets a reviewer check that step."},
    "S5": {"title": "inferred, unverified",
           "represented": "one inferred candidate for the declared gap, proposed",
           "gate": "BLOCKED", "defect": "prevented in G; B adopted the note as fact in 4/5",
           "plant": "S2's kit plus an unreviewed machine note: 'on a screening outage the quote is refused' (basis inferred, agent llm)",
           "plain": "An unreviewed note from another AI proposed an answer to the open decision. In the store it is a candidate, not a decision, and the gate stayed blocked. The baseline, reading the same note as one more document, took it as fact in four runs of five and built the wrong outage behaviour."},
    "S6": {"title": "invalidated by change",
           "represented": "4 invalidated, 4 verifications ended, Derived suspect; BLOCKED → PROCEED on re-verification",
           "gate": "PROCEED", "defect": "the stale artefact is identified in G only",
           "plant": "S1 verified and approved, S1's first governed output registered as Derived; then decision_table.md changes P2's surcharge 316.00 → 341.00 and is re-ingested as v2",
           "plain": "A verified number in the tariff changed. The store traced exactly what the change touched: four statements, their verifications, and the code built on them earlier, now marked suspect. The gate blocked until the new values were re-verified, then allowed building, and the governed assistant named the stale code to replace. The baseline, holding only the current documents, built correct new code but could not say what the change had invalidated."},
    "S7": {"title": "unverified",
           "represented": "0 verified, 145 unverified gaps, 0 approvals",
           "gate": "BLOCKED", "defect": "procedural; content correct in both",
           "plant": "S1's kit, extraction only: no verification record, no approval",
           "plain": "The documents were correct, but nothing had verified them. The gate blocked anyway, because status is about verification, not content. The baseline built correct code with the same confidence it had for S1, which is the point: without a record, correct and unverified look exactly alike."},
}
ORDER = list(SCENARIOS)

# Where each scenario sits on the model's reduced knowledge view. This is the
# demo's reading of the record's §6 onto the Legible v0.3 cascade; the record
# itself does not map scenarios to the model. Node ids are the model's.
#   entry: the node where the planted defect enters (the artefact family it was planted in)
#   <arm>: path = edges the defect travelled, stop = the node where it was stopped or made visible,
#          note = the record's reading in one line
SYSTEMIC = {
    "S1": {"entry": None, "family": "none planted",
           "G": {"path": [], "stop": None, "note": "no defect; generate 5/5, 11/11 ×5"},
           "B": {"path": [], "stop": None, "note": "no defect; generate_with_assumptions 5/5, 11/11 ×5"}},
    "S2": {"entry": "updef", "family": "requirements (REQ-06 declared open) and every artefact that stated the rule",
           "G": {"path": [], "stop": "validation", "note": "the gate reads the declared gap: BLOCKED, abstain 5/5, the key and gap id named every time"},
           "B": {"path": ["updef", "deriveddef", "codedef"], "stop": "detection", "would": "escape",
                 "note": "asked about the missing rule and generated anyway; the outage becomes an error: screening_down_hold fails 5/5, caught by the oracle only"}},
    "S3": {"entry": "deriveddef", "family": "decision table (DT-S rows), the behaviour-carrying layer",
           "G": {"path": ["deriveddef", "codedef"], "stop": "unknown", "visible": True,
                 "note": "QUALIFIED: the guess is carried as an # ASSUMPTION by assertion id; 41-boundary still fails 4/5, caught by the oracle"},
           "B": {"path": ["deriveddef", "codedef"], "stop": "detection", "would": "escape",
                 "note": "a silent 39/40 constant; accept_boundary_41 fails 5/5, caught by the oracle only"}},
    "S4": {"entry": "explderived", "family": "sequence diagram and BPMN, the explanatory layer, against table and spec",
           "G": {"path": [], "stop": "validation", "note": "R-CONFLICT marks both sides disputed: BLOCKED, abstain 5/5, the conflict gap named"},
           "B": {"path": ["explderived"], "stop": "unknown", "invented": True,
                 "note": "resolved by a 'newer normative text' precedence nothing states (4/5); correct by the oracle, uncheckable from the output"}},
    "S5": {"entry": "explderived", "family": "an unreviewed machine note (prose) proposing a value for the open decision",
           "G": {"path": [], "stop": "validation", "note": "the inferred candidate cannot lift the declared gap: BLOCKED, abstain 5/5"},
           "B": {"path": ["explderived", "codedef"], "stop": "detection", "would": "escape",
                 "note": "the note adopted as fact in 4/5 (refused_screening on the outage); screening_down_hold fails 5/5, caught by the oracle only"}},
    "S6": {"entry": "drift", "family": "decision table changed under a verified, derived artefact",
           "G": {"path": ["drift"], "stop": "validation", "note": "R-STALE invalidates the four assertions, ends their verifications, marks derived:S1:G:run1 suspect; BLOCKED until the re-verification, then PROCEED; the suspect artefact named 5/5 (re-run)"},
           "B": {"path": ["drift", "confidence"], "stop": None,
                 "note": "fresh code from the current documents passes 11/11; what was built on the old value cannot be named (asks in general terms, 3/5)"}},
    "S7": {"entry": "confidence", "family": "no verification record anywhere: the defect is procedural, and enters as unwarranted confidence in correct-looking documents",
           "G": {"path": [], "stop": "validation", "note": "36 of 36 required keys below verified: BLOCKED, abstain 5/5, M6 = 0; the block is procedural, the content was correct"},
           "B": {"path": ["confidence", "validation"], "stop": None,
                 "note": "nothing in the documents says they are unverified: 11/11 with the same confidence as S1, flagged 0/5; the model's E29 (confidence reduces validation) runs unopposed"}},
}

# The no-governance reference the record cites: the degradation test.
REFERENCE = {
    "title": "Without governance — the degradation test (recreate_experiment/degradation-2026-10-28, graded 2026-10-29)",
    "text": "Six of the fifteen planted defects reached the code, all six concealed by the arm's own suite and caught by the pristine one; every outcome the one the kit's precedence rule gives.",
    "numbers": {"planted": 15, "reached_code": 6, "concealed_by_own_suite": 6, "caught_by_pristine_suite": 6},
}


def sources_for(scenario: str, runs_dir: Path) -> list[dict]:
    """The result folders that hold this scenario: the record, S6's re-run and
    deterministic check, and every demo run that contains it."""
    out = [{"id": "record", "label": "the record (results/)", "dir": str(RESULTS / scenario)}]
    if scenario == "S6":
        out.append({"id": "rerun", "label": "the S6 re-run with the corrected bundle (results/rerun/S6, what X6 reads)", "dir": str(RESULTS / "rerun" / scenario)})
        out.append({"id": "d3check", "label": "the deterministic re-establishment of D3 (results/d3check/S6)", "dir": str(RESULTS / "d3check" / scenario)})
    if runs_dir.exists():
        for d in sorted(runs_dir.iterdir(), reverse=True):
            if (d / scenario / "deterministic.json").exists():
                arm_files = sorted((d / scenario).glob("run*_[GB].json"))
                mode = "arms" if arm_files else "deterministic"
                models = sorted({m for m in (_model_of(_read_json(f)) for f in arm_files) if m})
                tag = mode + (", " + ", ".join(models) if models else "")
                out.append({"id": f"demo-runs/{d.name}", "label": f"demo run {d.name} ({tag})", "dir": str(d / scenario)})
    return out


def resolve_source(scenario: str, source: str, runs_dir: Path) -> Path | None:
    for s in sources_for(scenario, runs_dir):
        if s["id"] == source:
            return Path(s["dir"])
    return None


def default_source(scenario: str) -> str:
    return "rerun" if scenario == "S6" else "record"


# ------------------------------------------------------------------ loading

def _read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _runs(d: Path, arm: str) -> list[dict]:
    out = []
    for p in sorted(d.glob(f"run*_{arm}.json"), key=lambda q: int(re.search(r"run(\d+)_", q.name).group(1))):
        r = _read_json(p)
        code_path = p.with_suffix(".py")
        r["code_text"] = code_path.read_text(encoding="utf-8") if code_path.exists() else None
        out.append(r)
    return out


def _arm_summary(runs: list[dict]) -> dict:
    n = len(runs)
    dec = Counter(r.get("M1_decision") for r in runs)
    suites = [f"{r['M4_suite']['passed']}/{r['M4_suite']['total']}" if r["M4_suite"]["ran"] else "—" for r in runs]
    targets = Counter()
    for r in runs:
        for t, v in (r.get("M4_targets") or {}).items():
            targets[f"{t}:{'pass' if v else ('fail' if v is False else 'nocode')}"] += 1
    refs = [r["M5_refs"]["share"] for r in runs if r["M5_refs"]["share"] is not None]
    return {"n": n, "decisions": dict(dec), "code": sum(1 for r in runs if r["M2_code"]),
            "flagged": sum(1 for r in runs if r["M3_flagged"]["flagged"]), "suites": suites,
            "all_11": sum(1 for r in runs if r["M4_suite"]["ran"] and r["M4_suite"]["passed"] == r["M4_suite"]["total"]),
            "targets": dict(targets), "outage": dict(Counter(r["outage_status"] for r in runs if r["outage_status"])),
            "refs_min": round(min(refs), 2) if refs else None, "refs_max": round(max(refs), 2) if refs else None,
            "noncompliance": sum(1 for r in runs if r.get("M6_noncompliance")),
            "api_errors": sum(1 for r in runs if r.get("api_error")),
            "models": sorted({m for m in (_model_of(r) for r in runs) if m}),
            "tokens": sum(r["usage"]["prompt_tokens"] + r["usage"]["completion_tokens"] for r in runs if r.get("usage"))}


def _model_of(r: dict) -> str | None:
    """The model that answered, as the API named it in the stream; None for a failed call."""
    return (r.get("usage") or {}).get("model") if not r.get("api_error") else None


def _run_view(r: dict) -> dict:
    return {"run": r["run"], "decision": r.get("M1_decision"), "code": bool(r.get("M2_code")), "model": _model_of(r),
            "flagged": r["M3_flagged"]["flagged"], "hits": r["M3_flagged"].get("hits", []),
            "suite": f"{r['M4_suite']['passed']}/{r['M4_suite']['total']}" if r["M4_suite"]["ran"] else None,
            "per_scenario": {k: v.get("passed") for k, v in r["M4_suite"].get("per_scenario", {}).items()},
            "targets": r.get("M4_targets") or {}, "outage_status": r.get("outage_status"),
            "refs": r.get("M5_refs"), "noncompliance": r.get("M6_noncompliance"),
            "questions": r.get("questions") or [], "assumptions": r.get("assumptions") or [],
            "claims_n": len(r.get("claims") or []), "api_error": r.get("api_error"),
            "parse_error": r.get("parse_error"), "code_text": r.get("code_text"), "usage": r.get("usage")}


def _gate_view(g: dict) -> dict:
    return {"verdict": g["verdict"], "why": g["why"], "blocked_keys": g.get("blocked_keys", []),
            "below_verified": g.get("below_verified", []), "flagged": g.get("flagged", []),
            "conflicts": g.get("conflicts", []), "stale": g.get("stale", []), "suspect_derived": g.get("suspect_derived", [])}


def _stage_colour(kind: str, det: dict, gate: dict) -> str:
    rules = det["rules"]
    if kind == "extract":
        return "warn" if det["load"]["unresolved_symbols"] else "ok"
    if kind == "rules":
        declared = any(h.get("declared") for h in rules["R-REQ"])
        if rules["R-CONFLICT"] or declared:
            return "bad"
        if rules["R-VAGUE"]:
            return "warn"
        return "ok"
    if kind == "gate":
        return {"PROCEED": "ok", "QUALIFIED": "warn", "BLOCKED": "bad"}[gate["verdict"]]
    return "ok"


def _arm_colour(arm: str, gate_verdict: str, summary: dict) -> tuple[str, str]:
    """(generate colour, oracle colour) for one arm."""
    if summary["n"] == 0:
        return "none", "none"
    if summary["api_errors"] == summary["n"]:
        return "bad", "none"  # no reply came back: nothing to judge the arm on
    if gate_verdict == "BLOCKED":
        gen = "ok" if (arm == "G" and summary["code"] == 0) else ("bad" if summary["code"] else "ok")
    elif gate_verdict == "QUALIFIED":
        gen = "warn"
    else:
        gen = "ok"
    if summary["code"] == 0:
        orc = "none"
    else:
        fails = sum(v for k, v in summary["targets"].items() if k.endswith(":fail"))
        orc = "bad" if fails else ("ok" if summary["all_11"] == summary["code"] else "warn")
    return gen, orc


def build(scenario: str, source: str, runs_dir: Path) -> dict:
    """The report view of ``scenario`` from the result folder ``source`` names."""
    if scenario not in SCENARIOS:
        raise KeyError(scenario)
    d = resolve_source(scenario, source, runs_dir)
    if d is None or not (d / "deterministic.json").exists():
        raise FileNotFoundError(f"{scenario}: no deterministic.json for source {source!r}")
    det = _read_json(d / "deterministic.json")
    gate = det["D6_gate"]
    meta = SCENARIOS[scenario]
    runs = {arm: _runs(d, arm) for arm in ("B", "G")}
    summaries = {arm: _arm_summary(rs) for arm, rs in runs.items()}
    levels = Counter(v["level"] for v in det["gate_keys"].values())
    d1 = det["D1_constraints"]
    stages = [
        {"id": "ingest", "label": "ingest", "colour": "ok",
         "lines": [f"{det['load']['fragments']} fragments", "sha256 per file and per fragment"]},
        {"id": "extract", "label": "extract", "colour": _stage_colour("extract", det, gate),
         "lines": [f"{det['load']['assertions']} assertions",
                   (f"{len(det['load']['unresolved_symbols'])} unresolved symbols" if det["load"]["unresolved_symbols"] else "0 unresolved symbols")]},
        {"id": "load", "label": "load", "colour": "ok",
         "lines": [f"{det['D2_census']['nodes']} nodes, {det['D2_census']['relationships']} relationships",
                   f"D1: {sum(1 for c in d1 if c['accepted'])} of {len(d1)} constraints accepted",
                   (f"verifications: {det['verifications'].get('execution', 0)} execution, {det['verifications'].get('review', 0)} review, {det['verifications'].get('approved', 0)} approved"
                    if "execution" in det["verifications"] else "verifications: none (extraction only)")]},
        {"id": "rules", "label": "rules", "colour": _stage_colour("rules", det, gate),
         "lines": [f"{r}: {len(det['rules'][r]) if isinstance(det['rules'][r], list) else det['rules'][r]}" for r in RULE_ORDER]
                  + [f"SHACL: main {det['D4_shacl']['main']['results']} result(s), info-only {det['D4_shacl']['info_only']['results']}, conforms={det['D4_shacl']['main']['conforms']}"]},
        {"id": "gate", "label": "gate", "colour": _stage_colour("gate", det, gate),
         "lines": [gate["verdict"], gate["why"]] + ([f"blocking: {', '.join(gate['blocked_keys'])}"] if gate.get("blocked_keys") else [])},
    ]
    arms = {}
    for arm in ("G", "B"):
        s = summaries[arm]
        gen_c, orc_c = _arm_colour(arm, gate["verdict"], s)
        arms[arm] = {
            "summary": s,
            "generate": {"colour": gen_c, "lines": ([f"{k} ×{v}" for k, v in s["decisions"].items()] +
                                                     [f"code {s['code']}/{s['n']}", f"flagged {s['flagged']}/{s['n']}"] +
                                                     ([f"non-compliance {s['noncompliance']}/{s['n']}"] if arm == "G" else []) +
                                                     ([f"api error ×{s['api_errors']}: " + next(r["api_error"] for r in runs[arm] if r.get("api_error"))[:160]] if s["api_errors"] else [])) if s["n"] else ["no run in this source"]},
            "oracle": {"colour": orc_c, "lines": (
                ([f"nothing to grade: the arm wrote no code in {s['n']} of {s['n']} runs" + (" (abstained, as the BLOCKED verdict asks)" if gate["verdict"] == "BLOCKED" and s["decisions"].get("abstain") else "")]
                 if s["code"] == 0 and s["api_errors"] < s["n"] else [f"suite {', '.join(s['suites'])}"]) +
                                                   [f"{k.replace(':', ' ')} ×{v}" for k, v in s["targets"].items()] +
                                                   ([f"refs resolvable {s['refs_min']}–{s['refs_max']}"] if s["refs_min"] is not None else [])) if s["n"] else ["—"]},
            "runs": [_run_view(r) for r in runs[arm]],
        }
    # model calls that failed: the harness records them as api_error cells (no reply, no code, no grade)
    api_errors = [{"arm": arm, "run": r["run"], "error": r["api_error"]} for arm in ("G", "B") for r in runs[arm] if r.get("api_error")]
    models_used = sorted({m for arm in ("G", "B") for m in summaries[arm]["models"]})
    view = {
        "scenario": scenario, "meta": meta, "source": source, "source_dir": str(d),
        "api_errors": api_errors,
        "record_model": RECORD_MODEL, "models_used": models_used,
        # a model other than the record's answered: the numbers are not comparable with the record's
        "model_deviation": [m for m in models_used if not m.startswith(RECORD_MODEL)],
        "sources": sources_for(scenario, runs_dir),
        "stages": stages, "arms": arms,
        "gate": _gate_view(gate),
        "levels": dict(levels), "required_keys": len(det["gate_keys"]),
        "rules": {r: det["rules"][r] for r in RULE_ORDER},
        "census": det["D2_census"], "shacl": {k: det["D4_shacl"][k] for k in ("main", "info_only")},
        "d5": det.get("D5_three_valued"),
        "bundle": (d / "bundle_G.txt").read_text(encoding="utf-8") if (d / "bundle_G.txt").exists() else None,
        "prompt_lengths": {arm: len((d / f"prompt_{arm}.txt").read_text(encoding="utf-8")) for arm in ("B", "G") if (d / f"prompt_{arm}.txt").exists()},
        "suite_order": SUITE_ORDER,
        "systemic": SYSTEMIC[scenario], "reference": REFERENCE,
    }
    view["record_check"] = record_check(scenario, d)
    if "stage2" in det:
        s2 = det["stage2"]
        view["stage2"] = {
            "load_v2": s2["load_v2"],
            "invalidated": s2["D3_stale"]["invalidated"], "kept": len(s2["D3_stale"]["kept"]),
            "suspect_derived": s2["suspect_derived"],
            "gate_before": _gate_view(s2["gate_before_reverification"]),
            "gate_after": _gate_view(s2["gate_after_reverification"]),
            "reverified": s2["reverified"], "census_after": s2["census_after"],
            "stages": [
                {"id": "ingest2", "label": "re-ingest v2", "colour": "warn",
                 "lines": [f"{s2['load_v2']['fragments']} fragments new, {s2['load_v2']['fragments_reused']} reused by digest",
                           f"{s2['load_v2']['assertions']} new assertions"]},
                {"id": "stale", "label": "R-STALE", "colour": "bad",
                 "lines": [f"{len(s2['D3_stale']['invalidated'])} invalidated: " + ", ".join(x["key"] for x in s2["D3_stale"]["invalidated"]),
                           f"{len(s2['D3_stale']['kept'])} kept at their status",
                           ("suspect: " + ", ".join(x["id"] for x in s2["suspect_derived"] if x.get("suspect"))) if s2["suspect_derived"]
                           else "no Derived registered (deterministic mode creates none)"]},
                {"id": "gate_before", "label": "gate", "colour": "bad",
                 "lines": [s2["gate_before_reverification"]["verdict"], s2["gate_before_reverification"]["why"]]},
                {"id": "reverify", "label": "re-verification", "colour": "ok",
                 "lines": [f"{len(s2['reverified'])} successors re-verified and approved (owner stand-in)"] + s2["reverified"]},
                {"id": "gate_after", "label": "gate", "colour": "ok",
                 "lines": [s2["gate_after_reverification"]["verdict"], s2["gate_after_reverification"]["why"]]},
            ]}
    view["narrative"] = narrative(view, det)
    view["details"] = stage_details(view, det, runs)
    return view


def scenario_list(runs_dir: Path) -> list[dict]:
    out = []
    for sc, m in SCENARIOS.items():
        out.append({"id": sc, **m, "sources": [s["id"] for s in sources_for(sc, runs_dir)],
                    "default_source": default_source(sc)})
    return out


# ------------------------------------------------------------ plain English

VERDICT_MEANING = {
    "PROCEED": "every piece of knowledge the coding task needs is verified or approved, so an assistant may build from it as fact",
    "QUALIFIED": "some of the knowledge the task needs is not verified, so an assistant may build only if it marks every such piece as an assumption and says so in its code",
    "BLOCKED": "the knowledge the task needs is missing, disputed, invalidated or too little verified, so an assistant may not build at all; it must say what is missing instead",
}


def _n(x) -> int:
    return len(x) if isinstance(x, list) else int(x or 0)


def _plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"


def record_check(scenario: str, d: Path) -> dict | None:
    """For a demo run: its deterministic results against the record's, leaf by leaf.
    S6 is read against results/d3check/S6 when the run registered no Derived
    artefact (deterministic mode), against results/S6 otherwise."""
    if d.parent.parent.name != "demo-runs" and d.parent.name not in ("rerun", "d3check"):
        return None
    if d.parent.name in ("rerun", "d3check"):
        return None
    det = _read_json(d / "deterministic.json")
    s6 = RESULTS / ("S6" if det.get("stage2", {}).get("suspect_derived") else "d3check/S6")
    n, lines = compare_deterministic.compare(d.parent, RESULTS, [scenario], s6_record=s6)
    compared = next((ln for ln in lines if "leaves compared" in ln), "")
    m = re.search(r"(\d+) leaves compared", compared)
    return {"differ": n, "compared": int(m.group(1)) if m else 0,
            "against": str(s6.relative_to(EXP)) if scenario == "S6" else f"results/{scenario}",
            "lines": [ln.strip() for ln in lines if ln.startswith("  ")][:6]}


def narrative(view: dict, det: dict) -> list[str]:
    """The report in sentences for a reader who knows none of the shorthand.
    Every number comes from the same files as the boxes above it."""
    sc, meta, gate = view["scenario"], view["meta"], view["gate"]
    rules, load, ver, cen = det["rules"], det["load"], det["verifications"], det["D2_census"]
    out = []
    out.append("How to read this page. The kit's documents were cut into fragments and read into assertions, one statement each, "
               "with where it came from and whether anyone has verified it. Seven rules then checked the assertions; the gate decided "
               "whether an AI coding assistant may build from them; two assistants were asked anyway, one given the gate's verdict and "
               "evidence (G, the governed arm) and one given the documents alone (B, the baseline); and the kit's eleven acceptance "
               "tests, the oracle, graded whatever code came back. Click any box of the pipeline for that stage's full data.")
    out.append(f"What was planted in {sc} ({meta['title']}): {meta['plant']}.")
    declared = sum(1 for h in rules["R-REQ"] if h.get("declared"))
    req = _n(rules["R-REQ"])
    store = (f"The store read {_plural(load['fragments'], 'fragment')} into {_plural(load['assertions'], 'assertion')}. "
             f"The rules found {_plural(rules['R-CORROBORATE'], 'pair')} of statements that two different documents make alike "
             f"(each side counts as validated), {_plural(_n(rules['R-CONFLICT']), 'contradiction')}, "
             f"{_plural(_n(rules['R-VAGUE']), 'vaguely worded value')}, {_plural(req, 'missing item')}"
             + (f" of which {declared} declared missing by the authors themselves" if declared else "")
             + f", and {_plural(rules['R-UNVERIFIED'], 'statement')} with no verification record.")
    if "execution" in ver:
        store += (f" The kit's test suite verified {ver['execution']} statements by running them and the dated review record "
                  f"verified {ver['review']} more; {ver['approved']} were then approved by the owner.")
    else:
        store += " No verification was loaded in this scenario: every statement stays at proposed or validated, whatever its content."
    if load.get("unresolved_symbols"):
        store += f" {_plural(len(load['unresolved_symbols']), 'symbol')} in the diagram had no definition anywhere ({', '.join(x.split(':')[-1] for x in load['unresolved_symbols'])})."
    out.append(store)
    g = f"The gate's verdict is {gate['verdict']}: {VERDICT_MEANING[gate['verdict']]}."
    if gate["verdict"] == "BLOCKED":
        g += f" Here: {gate['why']}."
    elif gate["verdict"] == "QUALIFIED":
        g += f" Here: {gate['why']}."
    if gate.get("conflicts"):
        g += f" The contradiction: {gate['conflicts'][0]['text']}."
    out.append(g)
    if view.get("d5"):
        d5 = view["d5"]
        out.append("The three-valued answer, asked of three keys: "
                   + "; ".join(f"'{k}' is {v['answer'].replace('_', ' ')}" for k, v in d5.items())
                   + ". 'Documented absent' means the documents say there is none; 'unknown' means no document says anything, which a store that cannot tell the two apart would report the same way.")
    if view.get("stage2"):
        s2 = view["stage2"]
        inv = ", ".join(x["key"] for x in s2["invalidated"])
        suspect = ", ".join(x["id"] for x in s2["suspect_derived"] if x.get("suspect"))
        out.append(f"Then the tariff document changed and was read in again: {_plural(s2['load_v2']['fragments'], 'fragment')} were new and "
                   f"{s2['load_v2']['fragments_reused']} unchanged ones were reused. The staleness rule invalidated exactly the "
                   f"{_plural(len(s2['invalidated']), 'statement')} the changed fragments support ({inv}), ended their verifications, "
                   + (f"and marked the code built from them, {suspect}, as suspect. " if suspect else "and left {} statements of the same document at their status. ".format(s2['kept']))
                   + f"The gate went {s2['gate_before']['verdict']} ({s2['gate_before']['why']}) until the "
                   f"{_plural(len(s2['reverified']), 'replacement statement')} were re-verified and approved, then {s2['gate_after']['verdict']}.")
    arms = view["arms"]
    if arms["G"]["summary"]["n"] or arms["B"]["summary"]["n"]:
        for arm, name, given in (("G", "The governed assistant (G)", "given the gate's verdict and its evidence"),
                                 ("B", "The baseline assistant (B)", "given the documents alone")):
            sm = arms[arm]["summary"]
            if not sm["n"]:
                continue
            dec = ", ".join(f"{k.replace('_', ' ') if k else 'no decision'} in {v} of {sm['n']}" for k, v in sm["decisions"].items())
            line = f"{name}, {given}, answered {dec}"
            if sm["api_errors"]:
                line += f"; {sm['api_errors']} call(s) failed before any answer"
            line += f". It wrote code in {sm['code']} of {sm['n']} run(s)"
            if sm["code"]:
                line += f", which passed {', '.join(x for x in sm['suites'] if x != '—')} of the oracle's tests"
                fails = sorted(((k.split(':')[0], v) for k, v in sm["targets"].items() if k.endswith(":fail")), key=lambda t: -t[1])
                if fails:
                    line += ", failing the planted target" + ("s " if len(fails) > 1 else " ") + ", ".join(f"'{t}' in {v} of {sm['n']}" for t, v in fails)
            if sc != "S1":
                line += f", and raised the planted problem in its questions or assumptions in {sm['flagged']} of {sm['n']}."
            else:
                line += "."
            if arm == "G" and sm["noncompliance"]:
                line += f" It broke the policy in {sm['noncompliance']} run(s)."
            out.append(line)
        out.append("What this shows: " + meta["plain"])
    else:
        out.append("This source holds the store's half only: the loading, the rules and the gate were re-executed; the two assistants were not called. "
                   "Replay shows the record's assistant runs for this scenario; Arms calls them again.")
    if view.get("record_check"):
        rc = view["record_check"]
        if rc["differ"] == 0:
            out.append(f"Against the record: identical on all {rc['compared']} fields compared with {rc['against']} (timestamps aside). The store reproduced the record.")
        else:
            out.append(f"Against the record: {_plural(rc['differ'], 'field')} of {rc['compared']} differ from {rc['against']}: " + "; ".join(rc["lines"][:3]) + ".")
    if view.get("model_deviation"):
        out.append(f"The assistants here were {', '.join(view['model_deviation'])}, not the record's {view['record_model']}: a different model, so these answers are not the record's and are not comparable with it.")
    return out


# ------------------------------------------------------------ stage details

RULE_TEXT = {
    "R-STRUCT": "Structure: an extracted or authored assertion must rest on at least one fragment; an inferred one must point at the gap it claims to fill; no fragment may float without a version. Violations are listed; the record had none in any scenario.",
    "R-CORROBORATE": "Corroboration: two assertions about the same key with equal values, from two different documents, corroborate each other and both move from proposed to validated. Validated means consistent, not true: two documents can agree on a wrong value.",
    "R-CONFLICT": "Conflict: two assertions about the same key with unequal values, from different documents, are both marked disputed and a conflict gap is raised. A numeric key with a vague side is incomparable, not a conflict.",
    "R-VAGUE": "Vagueness: a decision-table row with vague wording, or a diagram symbol with no definition anywhere, raises an ambiguity gap on every assertion that row or symbol supports.",
    "R-REQ": "Requirements: a requirement that says NOT YET SPECIFIED raises a gap declared by the authors, on the requirement and on the key it governs; a document declared not yet authored does too; and every requirement needs a Gherkin scenario that verifies it.",
    "R-UNVERIFIED": "Verification: a proposed or validated assertion with no verification record gets an unverified gap. The count is how many statements nobody has checked.",
}
FAMILIES = [("kit/requirements.md", "requirements", "markdown"), ("contract/decision_table.md", "decision tables", "markdown"),
            ("contract/spec.md", "specification", "markdown"), ("contract/openapi.yaml", "API contract", "OpenAPI 3.0"),
            ("behavior/quote_flow.puml", "behaviour", "PlantUML sequence diagram"), ("structure/containers.puml", "structure", "C4 PlantUML"),
            ("kit/quote_process.bpmn", "process", "BPMN 2.0"), ("kit/screening_decision.dmn", "decision", "DMN 1.3"),
            ("tests_input/acceptance.feature", "tests", "Gherkin"), ("kit/links.toml", "links", "TOML")]


def _table(cols, rows):
    return {"cols": cols, "rows": [[("" if c is None else str(c)) for c in r] for r in rows]}


def stage_details(view: dict, det: dict, runs: dict) -> dict:
    """What opens when a box of the pipeline strip is clicked: the stage's full
    data from deterministic.json and the run files, in tables and sentences."""
    sc = view["scenario"]
    gate = det["D6_gate"]
    arts = [f for f in FAMILIES if not (sc == "S3" and f[0].endswith(".dmn"))]
    d = {}
    d["ingest"] = {"title": "Ingest: the documents, read file by file",
                   "intro": f"{len(arts)} documents were read" + (", one of them planted as absent (the DMN, declared not yet authored)" if sc == "S3" else "")
                            + (", plus one machine-written note the baseline arm received as a document (not loaded into the store: its one statement entered as an inferred assertion instead)" if sc == "S5" else "")
                            + f". Each file and each fragment is stored with its sha256 digest, so a later version can be told apart byte for byte. {det['load']['fragments']} fragments came out.",
                   "sections": [{"heading": "Documents", "table": _table(["path", "family", "format"], arts)}]}
    levels = Counter(v["level"] for v in det["gate_keys"].values())
    d["extract"] = {"title": "Extract: fragments into assertions",
                    "intro": f"{det['load']['assertions']} assertions, one statement each, by ten deterministic mappers (one per format; no model). Each assertion carries a basis (extracted, authored, inferred), the fragment it rests on, and a status that starts at proposed.",
                    "sections": ([{"heading": "Symbols with no definition in any document", "list": det["load"]["unresolved_symbols"]}] if det["load"]["unresolved_symbols"] else [])
                                + [{"heading": "The 36 keys the coding task needs, by the level the gate resolved", "table": _table(["level", "keys"], sorted(levels.items(), key=lambda kv: -kv[1]))}]}
    cen = det["D2_census"]
    d["load"] = {"title": "Load: the graph in Neo4j",
                 "intro": f"{cen['nodes']} nodes and {cen['relationships']} relationships. Verification and approval are nodes with their own records, never a flag flipped on the statement.",
                 "sections": [{"heading": "Assertions by status", "table": _table(["status", "assertions"], sorted(cen["assertions_by_status"].items()))},
                              {"heading": "Gaps by kind", "table": _table(["kind", "gaps"], sorted(cen["gaps_by_kind"].items()))},
                              {"heading": "Verification records", "text": (f"{det['verifications']['execution']} by execution (the kit's suite, each record naming the scenario and the digest of the code it ran), {det['verifications']['review']} by review (the dated review record and the authored inputs), {det['verifications']['approved']} approvals by the owner."
                                                                           if "execution" in det["verifications"] else "none loaded: this scenario is extraction only.")},
                              {"heading": "D1: the constraints the community edition accepts", "table": _table(["type", "accepted", "message"], [(c["type"], "yes" if c["accepted"] else "no", (c["message"] or "").split("{message:")[-1].strip(" }")[:110]) for c in det["D1_constraints"]])}]}
    rules = det["rules"]
    secs = []
    for r in RULE_ORDER:
        hits = rules[r]
        sec = {"heading": f"{r}: {hits if not isinstance(hits, list) else len(hits)} " + ("pairs" if r == "R-CORROBORATE" else "statements" if r == "R-UNVERIFIED" else "hit(s)"), "text": RULE_TEXT[r]}
        if r == "R-CONFLICT" and hits:
            sec["table"] = _table(["key", "one side", "says", "other side", "says"], [(h["key"], h["a"], h["va"], h["b"], h["vb"]) for h in hits])
        if r == "R-VAGUE" and hits:
            sec["table"] = _table(["assertion", "key", "vague words"], [(h["id"], h["key"], ", ".join(h["words"])) for h in hits])
        if r == "R-REQ" and hits:
            sec["table"] = _table(["kind", "declared by the authors", "about", "why"], [(h["kind"], "yes" if h.get("declared") else "no", h.get("req") or h.get("artefact") or h.get("entity") or "", h.get("why") or (h.get("key") and f"governs {h['key']}") or "") for h in hits])
        if r == "R-STRUCT" and hits:
            sec["table"] = _table(["assertion", "why"], [(h["id"], h["why"]) for h in hits])
        secs.append(sec)
    sh = det["D4_shacl"]
    secs.append({"heading": f"SHACL over an RDF projection: {sh['triples']} triples", "text": f"The main shapes mirror R-STRUCT and R-REQ: conforms={sh['main']['conforms']}, {sh['main']['results']} result(s) {sh['main']['by_severity']}. An information-only shape every assertion violates: conforms={sh['info_only']['conforms']}, {sh['info_only']['results']} results, which shows at execution that sh:conforms is false on information-level results alone.", "list": sh["main"]["sample"][2:8]})
    d["rules"] = {"title": "Rules: seven Cypher checks after every load", "intro": "Each rule is one or more Cypher statements; status is set only here, by the loaders, and by recorded human acts. No rule promotes to verified or approved.", "sections": secs}
    keys_rows = [(k, v["level"], ", ".join(v["flags"]) or "", v["n"]) for k, v in det["gate_keys"].items()]
    gsecs = [{"heading": "How the verdict is formed", "text": "BLOCKED if any required key is absent, a declared gap, disputed or invalidated, or if more than 25 % of the keys are below verified; QUALIFIED if any key is below verified or carries a flag; PROCEED otherwise. The worst status among a key's live assertions is its level."},
             {"heading": f"The {len(keys_rows)} required keys", "table": _table(["key", "level", "flags", "assertions"], keys_rows)}]
    if gate.get("conflicts"):
        gsecs.append({"heading": "Conflicts the bundle carries", "list": [c["text"] for c in gate["conflicts"]]})
    d["gate"] = {"title": f"Gate: {gate['verdict']}", "intro": gate["why"] + ".", "sections": gsecs}
    for arm, name in (("G", "the governed arm, given the gate's verdict and evidence bundle"), ("B", "the baseline arm, given the documents alone")):
        rs = runs[arm]
        rows = [(r["run"], _model_of(r) or "", r.get("M1_decision") or ("api error" if r.get("api_error") else ""), "yes" if r.get("M2_code") else "no",
                 "yes" if r["M3_flagged"]["flagged"] else "no", ", ".join(r["M3_flagged"].get("hits", [])), len(r.get("questions") or []), len(r.get("assumptions") or []), len(r.get("claims") or []),
                 (r.get("usage") or {}).get("prompt_tokens", ""), (r.get("usage") or {}).get("completion_tokens", "")) for r in rs]
        d[f"generate_{arm}"] = {"title": f"Generate, {arm}: {name}",
                                "intro": (f"{len(rs)} run(s). Decision is the arm's own word (generate, generate with assumptions, abstain); flagged means the frozen keyword check of the pre-registration found the planted problem named in its questions or assumptions."
                                          if rs else "No run in this source."),
                                "sections": ([{"heading": "Per run", "table": _table(["run", "model", "decision", "code", "flagged", "keywords hit", "questions", "assumptions", "claims", "prompt tokens", "reply tokens"], rows)}] if rs else [])}
        orows = [(r["run"], f"{r['M4_suite']['passed']}/{r['M4_suite']['total']}" if r["M4_suite"]["ran"] else "no code",
                  ", ".join(f"{t}: {'pass' if v else ('fail' if v is False else 'no code')}" for t, v in (r.get("M4_targets") or {}).items()) or "",
                  r.get("outage_status") or "", f"{r['M5_refs']['resolved']}/{r['M5_refs']['total']}" if r["M5_refs"]["share"] is not None else "") for r in rs]
        d[f"oracle_{arm}"] = {"title": f"Oracle, {arm}: the kit's eleven acceptance scenarios on the generated code",
                              "intro": ("Each reply's code ran in a sandbox against the kit's suite with the scenario's overlays (S6 asks for the new prices). The planted target is the scenario the plant aims at; the outage status is what the code returned when screening was down; resolvable references are the claims and assumptions whose ref points at something that exists (an assertion id for G, a document line for B)."
                                        if rs else "No run in this source."),
                              "sections": ([{"heading": "Per run", "table": _table(["run", "suite", "planted targets", "outage status returned", "references resolvable"], orows)}] if rs else [])}
    if "stage2" in det:
        s2 = det["stage2"]
        d["ingest2"] = {"title": "Re-ingest: the changed tariff document as version v2", "intro": f"{s2['load_v2']['fragments']} fragments new, {s2['load_v2']['fragments_reused']} reused because their digest was unchanged, {s2['load_v2']['assertions']} new assertions. Unchanged fragments keep their assertions; only changed ones create new statements.", "sections": []}
        d["stale"] = {"title": "R-STALE: what the change invalidates", "intro": "An assertion whose supporting fragment's digest changed or vanished is invalidated; its verifications end (valid_until = v2); every derived output that used it becomes suspect; everything else of the same document keeps its status.",
                      "sections": [{"heading": "Invalidated", "table": _table(["assertion", "key", "derived outputs that used it"], [(x["id"], x["key"], ", ".join(x["derived"]) or "") for x in s2["D3_stale"]["invalidated"]])},
                                   {"heading": f"Kept at their status: {len(s2['D3_stale']['kept'])}", "list": [f"{x['id']} ({x['status']})" for x in s2["D3_stale"]["kept"][:12]] + (["…"] if len(s2["D3_stale"]["kept"]) > 12 else [])},
                                   {"heading": "Derived outputs", "list": [f"{x['id']}: suspect={x['suspect']}" for x in s2["suspect_derived"]] or ["none registered in this source"]}]}
        gb = s2["gate_before_reverification"]
        d["gate_before"] = {"title": f"Gate before re-verification: {gb['verdict']}", "intro": gb["why"] + ".", "sections": [{"heading": "Invalidated statements on required keys, with their successors", "table": _table(["assertion", "key", "old value", "successor", "successor status"], [(x["id"], x["key"], x["value"], ", ".join(t["id"] for t in x["successors"] if t["id"]), ", ".join(t["status"] for t in x["successors"] if t["id"])) for x in gb["stale"]])}]}
        d["reverify"] = {"title": "Re-verification by the owner stand-in", "intro": "A verification record (method review, dated) and an approval for each successor statement; the record is a node, not a property flip.", "sections": [{"heading": "Re-verified and approved", "list": s2["reverified"]}]}
        ga = s2["gate_after_reverification"]
        d["gate_after"] = {"title": f"Gate after re-verification: {ga['verdict']}", "intro": ga["why"] + ".", "sections": [{"heading": "Census after", "text": f"{s2['census_after']['nodes']} nodes, {s2['census_after']['relationships']} relationships; {s2['census_after']['assertions_by_status']}."}]}
    return d

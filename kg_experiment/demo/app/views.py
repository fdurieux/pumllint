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
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent.parent                      # kg_experiment/
RESULTS = EXP / "results"
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
           "plant": "nothing planted: the pristine kit, every assertion verified by the suite or the dated review record and approved"},
    "S2": {"title": "missing, declared",
           "represented": "Gap{missing, declared} on REQ-06 and on the outage key; hold_presence absent",
           "gate": "BLOCKED", "defect": "prevented in G; outage scenario fails in every B run",
           "plant": "the screening-outage rule deleted from every artefact that states it; REQ-06 reads NOT YET SPECIFIED (open decision OD-1)"},
    "S3": {"title": "ambiguous",
           "represented": "17 ambiguity gaps; 4 keys proposed; DMN declared not authored",
           "gate": "QUALIFIED", "defect": "41-boundary fails 4/5 G, 5/5 B; the guess is an # ASSUMPTION constant in G, silent in B",
           "plant": "DT-S rows reworded to vague ranges, the symbolic names undefined, the DMN absent"},
    "S4": {"title": "contradictory",
           "represented": "4 CONTRADICTS pairs, 4 disputed, 4 conflict gaps",
           "gate": "BLOCKED", "defect": "none by the oracle; B resolved by an invented precedence",
           "plant": "the sequence diagram and the BPMN say the outage fails the quote; the decision table and the spec say it is priced and held"},
    "S5": {"title": "inferred, unverified",
           "represented": "one inferred candidate for the declared gap, proposed",
           "gate": "BLOCKED", "defect": "prevented in G; B adopted the note as fact in 4/5",
           "plant": "S2's kit plus an unreviewed machine note: 'on a screening outage the quote is refused' (basis inferred, agent llm)"},
    "S6": {"title": "invalidated by change",
           "represented": "4 invalidated, 4 verifications ended, Derived suspect; BLOCKED → PROCEED on re-verification",
           "gate": "PROCEED", "defect": "the stale artefact is identified in G only",
           "plant": "S1 verified and approved, S1's first governed output registered as Derived; then decision_table.md changes P2's surcharge 316.00 → 341.00 and is re-ingested as v2"},
    "S7": {"title": "unverified",
           "represented": "0 verified, 145 unverified gaps, 0 approvals",
           "gate": "BLOCKED", "defect": "procedural; content correct in both",
           "plant": "S1's kit, extraction only: no verification record, no approval"},
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
            "oracle": {"colour": orc_c, "lines": ([f"suite {', '.join(s['suites'])}"] +
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
    return view


def scenario_list(runs_dir: Path) -> list[dict]:
    out = []
    for sc, m in SCENARIOS.items():
        out.append({"id": sc, **m, "sources": [s["id"] for s in sources_for(sc, runs_dir)],
                    "default_source": default_source(sc)})
    return out

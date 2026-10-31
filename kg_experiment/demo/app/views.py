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
import cascade  # noqa: E402  (the vendored model and the slide's node table, for the systemic panels)
SUITE_ORDER = ["quoted_low_risk", "accept_boundary_41", "review_boundary_42", "refuse_boundary_67",
               "refuse_high_risk", "price_exact_heavy", "price_exact_both", "invalid_weight_low",
               "invalid_value_over", "screening_down_hold", "store_down_error"]
RULE_ORDER = ["R-STRUCT", "R-CORROBORATE", "R-CONFLICT", "R-VAGUE", "R-REQ", "R-UNVERIFIED"]
RECORD_MODEL = "gpt-5.1-2025-11-13"  # harness/arms.py RECORD_MODEL; a run by another model is a deviation

# One line per scenario, after the record's §6 table (docs/neo4j-governed-knowledge-evaluation.md),
# reworded to GLOSSARY.md: controlled sentences for the card (represented, defect) and the
# Planted line (plant), a reading for "plain".
SCENARIOS = {
    "S1": {"title": "complete, verified",
           "represented": "145 assertions, 111 approved. No gap on any key the task needs.",
           "gate": "PROCEED", "defect": "No defect. Both arms wrote correct code.",
           "plant": "Nothing was planted: the kit is pristine. The oracle or the dated review record verified every assertion, and the owner approved them.",
           "plain": "Nothing was wrong in the documents, and both arms wrote working code. The gate added nothing here, and it cost nothing either."},
    "S2": {"title": "missing, declared",
           "represented": "A declared missing gap on REQ-06 and on the outage key. The hold_presence key is absent.",
           "gate": "BLOCKED", "defect": "Prevented in arm G. The outage scenario fails in every run of arm B.",
           "plant": "The screening-outage rule was deleted from every document that states it. REQ-06 reads NOT YET SPECIFIED, open decision OD-1.",
           "plain": "The documents said the outage rule was still to be decided. Arm G stopped and asked for that decision, and named the open item. Arm B noticed it too and asked, but wrote code anyway. That code turns an outage into an error, and only the oracle caught it. This is the kind of defect the gate exists to prevent."},
    "S3": {"title": "ambiguous",
           "represented": "17 ambiguous gaps. 4 keys stay at proposed. The DMN is declared not yet authored.",
           "gate": "QUALIFIED", "defect": "The 41-boundary scenario fails in 4 of 5 runs of G and 5 of 5 of B. G marks its guess as an assumption in the code. B guesses in silence.",
           "plant": "The DT-S rows were reworded to vague ranges. The symbolic names were left undefined. The DMN was removed.",
           "plain": "The thresholds were written as vague ranges, so both arms had to guess. Arm B guessed silently. Arm G carried each guess as a labelled assumption that points at the assertion it rests on. A reviewer can find that guess and fix it. The code was not better for it, and in two runs it was worse."},
    "S4": {"title": "contradictory",
           "represented": "4 contradicting pairs, 4 disputed assertions, 4 conflict gaps.",
           "gate": "BLOCKED", "defect": "None by the oracle. Arm B chose a side by an invented precedence.",
           "plant": "The sequence diagram and the BPMN say the outage fails the quote. The decision table and the spec say it is priced and held.",
           "plain": "Two documents said one thing and two others said the opposite. Arm G refused to choose and named the contradiction. Arm B chose a side by an invented rule: the newer text wins. It happened to pick the right side, so the oracle passed. Nothing in its output lets a reviewer check that step."},
    "S5": {"title": "inferred, unverified",
           "represented": "One inferred candidate for the declared gap, at proposed.",
           "gate": "BLOCKED", "defect": "Prevented in arm G. Arm B took the note as fact in 4 of 5 runs.",
           "plant": "S2's kit plus an unreviewed machine note: 'on a screening outage the quote is refused'. Its basis is inferred, its agent a model.",
           "plain": "An unreviewed note from another AI proposed an answer to the open decision. In the store it is a candidate, not a decision, and the gate stayed blocked. Arm B read the same note as one more document. It took the note as fact in four runs of five and built the wrong outage behaviour."},
    "S6": {"title": "invalidated by change",
           "represented": "4 assertions invalidated, 4 verifications ended, the derived output marked suspect. BLOCKED, then PROCEED after re-verification.",
           "gate": "PROCEED", "defect": "Only arm G names the stale code.",
           "plant": "S1 verified and approved, with its first governed output registered as derived. Then decision_table.md changes P2's surcharge from 316.00 to 341.00 and is read in again as v2.",
           "plain": "A verified number in the tariff changed. The store traced exactly what the change touched: four assertions, their verifications, and the code built on them earlier. That code is now marked suspect. The gate blocked until the new values were re-verified, then allowed building. Arm G named the stale code to replace. Arm B held only the current documents; it built correct new code but could not say what the change had invalidated."},
    "S7": {"title": "unverified",
           "represented": "0 verified, 145 unverified gaps, 0 approvals.",
           "gate": "BLOCKED", "defect": "Procedural only. The content is correct in both arms.",
           "plant": "S1's kit, extraction only. No verification record and no approval were loaded.",
           "plain": "The documents were correct, but nothing had verified them. The gate blocked anyway, because status is about verification, not content. Arm B built correct code with the same confidence it had for S1. That is the point: without a record, correct and unverified look exactly alike."},
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
           "G": {"path": [], "stop": None, "note": "No defect. Arm G answered generate in 5 of 5 runs and passed 11 of 11 each time."},
           "B": {"path": [], "stop": None, "note": "No defect. Arm B answered generate with assumptions in 5 of 5 runs and passed 11 of 11 each time."}},
    "S2": {"entry": "updef", "family": "the requirements, REQ-06 declared open, and every document that stated the rule",
           "G": {"path": [], "stop": "validation", "note": "The gate read the declared gap and gave BLOCKED. Arm G abstained in 5 of 5 runs and named the key and the gap each time."},
           "B": {"path": ["updef", "deriveddef", "codedef"], "stop": "detection", "would": "escape",
                 "note": "Arm B asked about the missing rule and wrote code anyway. The outage became an error. The planted target failed in 5 of 5 runs, and only the oracle caught it."}},
    "S3": {"entry": "deriveddef", "family": "the decision table, the DT-S rows: the behaviour-carrying layer",
           "G": {"path": ["deriveddef", "codedef"], "stop": "unknown", "visible": True,
                 "note": "The gate gave QUALIFIED. Arm G carried its guess as an assumption that names the assertion id. The 41-boundary target still failed in 4 of 5 runs, and the oracle caught it."},
           "B": {"path": ["deriveddef", "codedef"], "stop": "detection", "would": "escape",
                 "note": "Arm B wrote a silent 39/40 constant. The 41-boundary target failed in 5 of 5 runs, and only the oracle caught it."}},
    "S4": {"entry": "explderived", "family": "the sequence diagram and the BPMN, the explanatory layer, against the table and the spec",
           "G": {"path": [], "stop": "validation", "note": "The conflict rule marked both sides disputed and the gate gave BLOCKED. Arm G abstained in 5 of 5 runs and named the conflict gap."},
           "B": {"path": ["explderived"], "stop": "unknown", "invented": True,
                 "note": "Arm B chose a side by a precedence no document states, in 4 of 5 runs. The oracle passed its code. Nothing in its output lets a reviewer check that choice."}},
    "S5": {"entry": "explderived", "family": "an unreviewed machine note in prose, proposing a value for the open decision",
           "G": {"path": [], "stop": "validation", "note": "The inferred candidate cannot lift the declared gap. The gate gave BLOCKED, and arm G abstained in 5 of 5 runs."},
           "B": {"path": ["explderived", "codedef"], "stop": "detection", "would": "escape",
                 "note": "Arm B took the note as fact in 4 of 5 runs and refused the quote on an outage. The planted target failed in 5 of 5 runs, and only the oracle caught it."}},
    "S6": {"entry": "drift", "family": "the decision table changed under a verified, derived output",
           "G": {"path": ["drift"], "stop": "validation", "note": "The staleness rule invalidated four assertions, ended their verifications and marked the derived output suspect. The gate gave BLOCKED until the re-verification, then PROCEED. Arm G named the suspect output to replace."},
           "B": {"path": ["drift", "confidence"], "stop": None,
                 "note": "Arm B wrote fresh code from the current documents and passed 11 of 11. It could not name what was built on the old value. It asked in general terms in 3 of 5 runs."}},
    "S7": {"entry": "confidence", "family": "no verification record anywhere: the defect is procedural and enters as unwarranted confidence in correct-looking documents",
           "G": {"path": [], "stop": "validation", "note": "All 36 keys the task needs are below verified, so the gate gave BLOCKED. Arm G abstained in 5 of 5 runs. The block is procedural. The content was correct."},
           "B": {"path": ["confidence", "validation"], "stop": None,
                 "note": "Nothing in the documents says they are unverified. Arm B passed 11 of 11 with the same confidence as in S1 and raised nothing. The model's edge E29, confidence reduces validation, ran unopposed."}},
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


def _gaps_colour(det: dict) -> str:
    c = det["D2_census"]["gaps_by_kind"]
    declared = any(h.get("declared") for h in det["rules"]["R-REQ"])
    if c.get("conflict") or declared:
        return "bad"
    if c.get("ambiguous") or any(v["level"] in ("proposed", "validated") for v in det["gate_keys"].values()):
        return "warn"
    return "ok"


def _gaps_lines(det: dict) -> list[str]:
    c = det["D2_census"]["gaps_by_kind"]
    declared = sum(1 for h in det["rules"]["R-REQ"] if h.get("declared"))
    lines = [f"{sum(c.values())} gaps"]
    if c.get("missing"):
        lines.append(f"missing: {c['missing']}" + (f" ({declared} declared by the authors)" if declared else ""))
    for k in ("ambiguous", "conflict", "unverified"):
        if c.get(k):
            lines.append(f"{k}: {c[k]}")
    return lines + ["click for every gap"]


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
    reg: list[dict] = []  # every generated sentence and box label with its kind, for the controlled-English test
    L = lambda *t: [_reg(reg, "controlled", x) for x in t]  # noqa: E731  box labels, controlled
    DL = lambda *t: [_reg(reg, "data", x) for x in t]  # noqa: E731  box lines quoted from the files
    stages = [
        {"id": "ingest", "label": L("ingest")[0], "colour": "ok",
         "lines": L(f"{det['load']['fragments']} fragments", "sha256 per file and per fragment")},
        {"id": "extract", "label": L("extract")[0], "colour": _stage_colour("extract", det, gate),
         "lines": L(f"{det['load']['assertions']} assertions",
                    (f"{len(det['load']['unresolved_symbols'])} unresolved symbols" if det["load"]["unresolved_symbols"] else "0 unresolved symbols"))},
        {"id": "load", "label": L("load")[0], "colour": "ok",
         "lines": L(f"{det['D2_census']['nodes']} nodes, {det['D2_census']['relationships']} relationships",
                    f"D1: {sum(1 for c in d1 if c['accepted'])} of {len(d1)} constraints accepted",
                    (f"verifications: {det['verifications'].get('execution', 0)} execution, {det['verifications'].get('review', 0)} review, {det['verifications'].get('approved', 0)} approved"
                     if "execution" in det["verifications"] else "verifications: none (extraction only)"))},
        {"id": "rules", "label": L("rules")[0], "colour": _stage_colour("rules", det, gate),
         "lines": L(*[f"{r}: {len(det['rules'][r]) if isinstance(det['rules'][r], list) else det['rules'][r]}" for r in RULE_ORDER],
                    f"SHACL: main {det['D4_shacl']['main']['results']} result(s), info-only {det['D4_shacl']['info_only']['results']}, conforms={det['D4_shacl']['main']['conforms']}")},
        {"id": "gaps", "label": L("gaps (found by the rules)")[0], "colour": _gaps_colour(det),
         "lines": L(*_gaps_lines(det))},
        {"id": "gate", "label": L("gate")[0], "colour": _stage_colour("gate", det, gate),
         "lines": L(gate["verdict"]) + DL(gate["why"]) + (DL(f"blocking: {', '.join(gate['blocked_keys'])}") if gate.get("blocked_keys") else [])},
    ]
    arms = {}
    for arm in ("G", "B"):
        s = summaries[arm]
        gen_c, orc_c = _arm_colour(arm, gate["verdict"], s)
        arms[arm] = {
            "summary": s,
            "generate": {"colour": gen_c, "lines": (L(*[f"{(k or 'no decision').replace('_', ' ')} ×{v}" for k, v in s["decisions"].items()],
                                                       f"code {s['code']}/{s['n']}", f"flagged {s['flagged']}/{s['n']}",
                                                       *([f"non-compliance {s['noncompliance']}/{s['n']}"] if arm == "G" else [])) +
                                                     (DL(f"api error ×{s['api_errors']}: " + next(r["api_error"] for r in runs[arm] if r.get("api_error"))[:160]) if s["api_errors"] else [])) if s["n"] else L("no run in this source")},
            "oracle": {"colour": orc_c, "lines": (
                L(f"nothing to grade: the arm wrote no code in {s['n']} of {s['n']} runs" + (" (abstained, as the BLOCKED verdict asks)" if gate["verdict"] == "BLOCKED" and s["decisions"].get("abstain") else ""))
                 if s["code"] == 0 and s["api_errors"] < s["n"] else L(f"oracle {', '.join(s['suites'])}")) +
                                                   L(*[f"{k.replace(':', ' ')} ×{v}" for k, v in s["targets"].items()],
                                                     *([f"refs resolvable {s['refs_min']}–{s['refs_max']}"] if s["refs_min"] is not None else [])) if s["n"] else L("—")},
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
                {"id": "ingest2", "label": L("re-ingest v2")[0], "colour": "warn",
                 "lines": L(f"{s2['load_v2']['fragments']} fragments new, {s2['load_v2']['fragments_reused']} reused by digest",
                            f"{s2['load_v2']['assertions']} new assertions")},
                {"id": "stale", "label": L("R-STALE")[0], "colour": "bad",
                 "lines": DL(f"{len(s2['D3_stale']['invalidated'])} invalidated: " + ", ".join(x["key"] for x in s2["D3_stale"]["invalidated"]))
                          + L(f"{len(s2['D3_stale']['kept'])} kept at their status")
                          + (DL("suspect: " + ", ".join(x["id"] for x in s2["suspect_derived"] if x.get("suspect"))) if s2["suspect_derived"]
                             else L("no Derived registered (deterministic mode creates none)"))},
                {"id": "gate_before", "label": L("gate")[0], "colour": "bad",
                 "lines": L(s2["gate_before_reverification"]["verdict"]) + DL(s2["gate_before_reverification"]["why"])},
                {"id": "reverify", "label": L("re-verification")[0], "colour": "ok",
                 "lines": L(f"{len(s2['reverified'])} successors re-verified and approved (owner stand-in)") + DL(*s2["reverified"])},
                {"id": "gate_after", "label": L("gate")[0], "colour": "ok",
                 "lines": L(s2["gate_after_reverification"]["verdict"]) + DL(s2["gate_after_reverification"]["why"])},
            ]}
    view["narrative"] = narrative(view, det, reg)
    view["details"] = stage_details(view, det, runs, reg)
    view["gaps"] = gaps_view(det, reg)
    view["systemic_details"] = systemic_details(view, det, runs, reg)
    view["text_registry"] = reg
    view["glossary"] = GLOSSARY
    return view


def scenario_list(runs_dir: Path) -> list[dict]:
    out = []
    for sc, m in SCENARIOS.items():
        out.append({"id": sc, **m, "sources": [s["id"] for s in sources_for(sc, runs_dir)],
                    "default_source": default_source(sc)})
    return out


# ------------------------------------------------------------ controlled English

# The page's explanatory text follows Simplified Technical English rules, kept in
# kg_experiment/demo/GLOSSARY.md: one approved term per concept, a sentence of at
# most 20 words for the plain-English block, the stage panels and the gap kinds, and
# at most 25 for the descriptive readings ("what this shows"). Every generated
# sentence is registered with its kind so tests/test_kg_demo.py can check the limits
# and the forbidden synonyms on the text that was actually produced.

GLOSSARY = {
    "document": "One of the kit's input files, such as a decision table or a diagram.",
    "fragment": "A piece of a document, such as one table row, stored with its own digest.",
    "digest": "A fingerprint of some bytes; when the bytes change, the digest changes.",
    "entity": "A thing the documents talk about, such as a pricing step or a requirement.",
    "assertion": "One fact read from a document: an entity, a property and a value.",
    "basis": "How an assertion came to exist: authored by a person, extracted by a parser, or inferred by a model.",
    "status": "Where an assertion stands: proposed, validated, verified, approved, disputed or invalidated.",
    "rule": "One of the seven checks the harness runs on the store after each load.",
    "gap": "Something a rule found wanting: missing, ambiguous, a conflict, or unverified.",
    "key": "One piece of knowledge the coding task needs; the task needs 36 keys.",
    "gate": "The check that reads the 36 keys and gives a verdict.",
    "verdict": "The gate's answer: PROCEED, QUALIFIED or BLOCKED.",
    "bundle": "The text the gate writes for arm G: the verdict, the policy and the evidence per key.",
    "arm": "One of the two AI assistants asked to write the code. G got the bundle; B got the documents.",
    "run": "One call of one arm, graded on its own.",
    "decision": "The word an arm gives for its own choice: generate, generate with assumptions, or abstain.",
    "oracle": "The kit's eleven acceptance scenarios, run on the code an arm wrote.",
    "planted target": "The oracle scenario the planted defect aims at.",
    "flagged": "The arm named the planted problem in its questions or assumptions.",
    "record": "The committed results of the scored run, under results/.",
    "demo run": "A re-run written to a dated folder under results/demo-runs/.",
    "store": "The Neo4j database the harness loads; it holds one scenario at a time.",
    "model": "The language model that answers an arm's call.",
    # shared with the IEAM register (kg_experiment/demo/register/glossary/glossary.toml), reconciled in GLOSSARY.md
    "node": "One record of one register taxonomy: a capability, product, journey element, process element, application element, information node or organisation unit.",
    "link": "One typed, directed relationship between two register nodes, with its own id, state, owner and approval.",
    "relationship type": "One of the register's ten typed relationships, such as requires, realizes, supports or manages.",
    "source of record": "The system that authors a node's content: ARIS, Archi, the EDM repository, or the kit in the test case.",
    "export": "A dated, append-only mirror of a source of record, with a manifest of digests and a reconciliation report.",
    "approval": "A recorded acceptance: of a verified assertion in the store, or of a node or link in the register, with who, when and which record.",
    "exception": "An approved, expiring deviation from a coverage rule, with its scope and rationale.",
    "coverage rule": "A register check that an approved node of one kind has a link of one type, or an unexpired exception.",
    "state": "Where a register node or link stands: draft, proposed, approved, deprecated, retired or rejected. An assertion has a status, never a state.",
    "footprint": "The register nodes and links a scenario touches: through its keys below approved, its requirement gaps and its changed documents, by the demo's approved map.",
    "reference": "An underlined cell of a panel's table that opens its subject's own panel under the table: a node, a link, a requirement, a key or a document.",
    "projection": "The register's nodes and links loaded into the store in their own namespace at the vendored tag: derived, loaded on demand, wiped by a run, never the record.",
}
# synonyms the controlled texts must not use, and the approved term each stands for
FORBIDDEN = {
    "statement": "assertion", "statements": "assertion",
    "piece of knowledge": "key", "pieces of knowledge": "key",
    "assistant": "arm", "assistants": "arm",
    "artefact": "document", "artefacts": "document",
    "acceptance test": "oracle", "acceptance tests": "oracle", "test suite": "oracle", "the suite": "oracle",
    "database": "store", "snippet": "fragment", "chunk": "fragment",
    # the register's forbidden synonyms, as reconciled in GLOSSARY.md: bare "item", "object", "ok" and the
    # pipeline stage "extract" keep their demo senses, so only the register-qualified phrases are forbidden
    "register item": "node", "register object": "node", "element record": "node",
    "connection": "link", "connections": "link", "mapping row": "link", "edge record": "link",
    "link type": "relationship type", "connection type": "relationship type",
    "master": "source of record", "golden source": "source of record", "system of truth": "source of record",
    "an extract": "export", "the extract": "export", "dump": "export", "snapshot": "export",
    "sign-off": "approval", "signoff": "approval",
    "waiver": "exception", "exemption": "exception",
    "completeness rule": "coverage rule", "mandatory mapping": "coverage rule",
}
VERDICT_MEANING = {
    "PROCEED": ["Every key the task needs is verified or approved.", "An arm may build from them as facts."],
    "QUALIFIED": ["Some keys the task needs are below verified, or carry a flag.",
                  "An arm may build only if it marks each such key as an assumption in its code."],
    "BLOCKED": ["A key the task needs is missing, disputed, invalidated or too little verified.",
                "An arm may not build.", "It must say what is missing instead."],
}


def _reg(reg: list, kind: str, *sentences: str) -> str:
    """Register sentences of one kind (controlled, data or reading) and return them joined."""
    for s in sentences:
        if s:
            reg.append({"kind": kind, "text": s})
    return " ".join(s for s in sentences if s)


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


def narrative(view: dict, det: dict, reg: list) -> list[str]:
    """The report in sentences for a reader who knows none of the shorthand.
    Every number comes from the same files as the boxes above it. Controlled
    sentences keep to 20 words, readings to 25, data is quoted as it is."""
    sc, meta, gate = view["scenario"], view["meta"], view["gate"]
    rules, load, ver = det["rules"], det["load"], det["verifications"]
    C = lambda *s: _reg(reg, "controlled", *s)  # noqa: E731
    D = lambda *s: _reg(reg, "data", *s)  # noqa: E731
    R = lambda *s: _reg(reg, "reading", *s)  # noqa: E731
    out = []
    out.append(C("How to read this page.", "The harness cut the kit's documents into fragments.",
                 "It read each fragment into assertions, one fact each, with its source and its status.",
                 "Seven rules then checked the assertions and recorded gaps.",
                 "The gate read the 36 keys the coding task needs and gave a verdict.",
                 "Two arms were then asked to write the code.",
                 "Arm G, the governed arm, got the verdict and the bundle.",
                 "Arm B, the baseline arm, got the documents only.",
                 "The oracle graded the code each arm wrote.",
                 "Click any box of the pipeline for that stage's full data."))
    out.append(C(f"What was planted in {sc} ({meta['title']}):", meta["plant"]))
    declared = sum(1 for h in rules["R-REQ"] if h.get("declared"))
    req = _n(rules["R-REQ"])
    store = [C(f"The store read {_plural(load['fragments'], 'fragment')} into {_plural(load['assertions'], 'assertion')}.",
               f"The rules found {_plural(rules['R-CORROBORATE'], 'pair')} of assertions that two different documents make alike.",
               "Each assertion of such a pair counts as validated.",
               f"They found {_plural(_n(rules['R-CONFLICT']), 'contradiction')}, {_plural(_n(rules['R-VAGUE']), 'vaguely worded value')} and {_plural(req, 'missing item')}.")]
    if declared:
        store.append(C(f"The authors themselves declared {declared} of the missing items."))
    store.append(C(f"{_plural(rules['R-UNVERIFIED'], 'assertion')} have no verification record."))
    if "execution" in ver:
        store.append(C(f"The oracle verified {ver['execution']} assertions by running them.",
                       f"The dated review record verified {ver['review']} more.",
                       f"The owner then approved {ver['approved']}."))
    else:
        store.append(C("No verification was loaded in this scenario.",
                       "Every assertion stays at proposed or validated, whatever its content."))
    if load.get("unresolved_symbols"):
        store.append(C(f"{_plural(len(load['unresolved_symbols']), 'symbol')} in the diagram had no definition in any document.")
                     + " " + D("Symbols: " + ", ".join(x.split(":")[-1] for x in load["unresolved_symbols"]) + "."))
    out.append(" ".join(store))
    g = [C(f"The gate's verdict is {gate['verdict']}.", *VERDICT_MEANING[gate["verdict"]])]
    if gate["verdict"] != "PROCEED":
        g.append(C("Here:") + " " + D(gate["why"] + "."))
    if gate.get("conflicts"):
        g.append(C("The contradiction:") + " " + D(gate["conflicts"][0]["text"] + "."))
    out.append(" ".join(g))
    if view.get("d5"):
        d5 = view["d5"]
        out.append(C("The three-valued answer was asked for three keys.") + " "
                   + D("; ".join(f"'{k}' is {v['answer'].replace('_', ' ')}" for k, v in d5.items()) + ".") + " "
                   + C("Documented absent means the documents say there is none.",
                       "Unknown means no document says anything.",
                       "A store that cannot tell the two apart reports both the same way."))
    if view.get("stage2"):
        s2 = view["stage2"]
        inv = ", ".join(x["key"] for x in s2["invalidated"])
        suspect = ", ".join(x["id"] for x in s2["suspect_derived"] if x.get("suspect"))
        parts = [C("Then the tariff document changed and was read in again.",
                   f"{_plural(s2['load_v2']['fragments'], 'fragment')} were new, and {s2['load_v2']['fragments_reused']} unchanged fragments were reused.",
                   f"The staleness rule invalidated the {_plural(len(s2['invalidated']), 'assertion')} the changed fragments support."),
                 D("Invalidated: " + inv + "."),
                 C("It ended their verifications.")]
        if suspect:
            parts.append(C("It marked the code built from them as suspect.") + " " + D("Suspect: " + suspect + "."))
        else:
            parts.append(C(f"{s2['kept']} other assertions of the same document kept their status."))
        parts.append(C(f"The gate went {s2['gate_before']['verdict']} until the {_plural(len(s2['reverified']), 'replacement assertion')} were re-verified and approved.",
                       f"Then it gave {s2['gate_after']['verdict']}."))
        out.append(" ".join(parts))
    arms = view["arms"]
    if arms["G"]["summary"]["n"] or arms["B"]["summary"]["n"]:
        for arm, given in (("G", "with the bundle"), ("B", "with the documents only")):
            sm = arms[arm]["summary"]
            if not sm["n"]:
                continue
            sents = [f"Arm {arm}, {given}, answered '{(k or 'no decision').replace('_', ' ')}' in {v} of {sm['n']} runs." for k, v in sm["decisions"].items()]
            if sm["api_errors"]:
                sents.append(f"{sm['api_errors']} of its calls failed before any answer.")
            sents.append(f"It wrote code in {sm['code']} of {sm['n']} runs.")
            if sm["code"]:
                sents.append(f"That code passed {', '.join(x for x in sm['suites'] if x != '—')} of the oracle's eleven scenarios.")
                fails = sorted(((k.split(':')[0], v) for k, v in sm["targets"].items() if k.endswith(":fail")), key=lambda t: -t[1])
                for t, v in fails:
                    sents.append(f"It failed the planted target '{t}' in {v} of {sm['n']} runs.")
            if sc != "S1":
                sents.append(f"It raised the planted problem in {sm['flagged']} of {sm['n']} runs.")
            if arm == "G" and sm["noncompliance"]:
                sents.append(f"It broke the policy in {sm['noncompliance']} runs.")
            out.append(C(*sents))
        out.append(C("What this shows:") + " " + R(meta["plain"]))
    else:
        out.append(C("This source holds the store's half only.", "The loading, the rules and the gate were re-executed.",
                     "The two arms were not called.", "Replay shows the record's runs for this scenario.", "Arms calls them again."))
    if view.get("record_check"):
        rc = view["record_check"]
        if rc["differ"] == 0:
            out.append(C(f"Against the record: identical on all {rc['compared']} fields compared with {rc['against']}, timestamps aside.",
                         "The store reproduced the record."))
        else:
            out.append(C(f"Against the record: {_plural(rc['differ'], 'field')} of {rc['compared']} differ from {rc['against']}.") + " " + D("; ".join(rc["lines"][:3]) + "."))
    if view.get("model_deviation"):
        out.append(C(f"The arms here were answered by {', '.join(view['model_deviation'])}, not the record's {view['record_model']}.",
                     "A different model answered, so these results are not comparable with the record's."))
    return out


# ------------------------------------------------------------ stage details

RULE_TEXT = {
    "R-STRUCT": ["An extracted or authored assertion must rest on at least one fragment.",
                 "An inferred assertion must point at the gap it claims to fill.",
                 "No fragment may exist without a version.",
                 "Violations are listed below.", "The record had none in any scenario."],
    "R-CORROBORATE": ["Two assertions about one key with equal values, from two different documents, corroborate each other.",
                      "Both move from proposed to validated.",
                      "Validated means consistent, not true: two documents can agree on a wrong value."],
    "R-CONFLICT": ["Two assertions about one key with unequal values, from different documents, are both marked disputed.",
                   "A conflict gap is raised for the pair.",
                   "A numeric key with a vague side is incomparable, not a conflict."],
    "R-VAGUE": ["A decision-table row with vague wording raises an ambiguity gap.",
                "So does a diagram symbol with no definition anywhere.",
                "The gap goes on every assertion that row or symbol supports."],
    "R-REQ": ["A requirement that says NOT YET SPECIFIED raises a gap declared by the authors.",
              "The gap goes on the requirement and on the key it governs.",
              "A document declared not yet authored raises one too.",
              "Every requirement needs a Gherkin scenario that verifies it."],
    "R-UNVERIFIED": ["A proposed or validated assertion with no verification record gets an unverified gap.",
                     "The count is how many assertions nobody has verified."],
}
FAMILIES = [("kit/requirements.md", "requirements", "markdown"), ("contract/decision_table.md", "decision tables", "markdown"),
            ("contract/spec.md", "specification", "markdown"), ("contract/openapi.yaml", "API contract", "OpenAPI 3.0"),
            ("behavior/quote_flow.puml", "behaviour", "PlantUML sequence diagram"), ("structure/containers.puml", "structure", "C4 PlantUML"),
            ("kit/quote_process.bpmn", "process", "BPMN 2.0"), ("kit/screening_decision.dmn", "decision", "DMN 1.3"),
            ("tests_input/acceptance.feature", "tests", "Gherkin"), ("kit/links.toml", "links", "TOML")]


def _table(cols, rows):
    return {"cols": cols, "rows": [[("" if c is None else str(c)) for c in r] for r in rows]}


def stage_details(view: dict, det: dict, runs: dict, reg: list) -> dict:
    """What opens when a box of the pipeline strip is clicked: the stage's full
    data from deterministic.json and the run files, in tables and sentences."""
    sc = view["scenario"]
    gate = det["D6_gate"]
    C = lambda *s: _reg(reg, "controlled", *s)  # noqa: E731
    D = lambda *s: _reg(reg, "data", *s)  # noqa: E731
    arts = [f for f in FAMILIES if not (sc == "S3" and f[0].endswith(".dmn"))]
    d = {}
    ingest = [f"{len(arts)} documents were read."]
    if sc == "S3":
        ingest.append("One of them was planted as absent: the DMN, declared not yet authored.")
    if sc == "S5":
        ingest += ["Arm B also got one machine-written note as a document.",
                   "The store did not load that note; its one assertion entered as inferred instead."]
    ingest += ["Each document and each fragment is stored with its sha256 digest.",
               "A later version can then be told apart byte for byte.", f"{det['load']['fragments']} fragments came out."]
    d["ingest"] = {"title": C("Ingest: the documents, read file by file"), "intro": C(*ingest),
                   "sections": [{"heading": C("Documents"), "table": _table(["path", "family", "format"], arts)}]}
    levels = Counter(v["level"] for v in det["gate_keys"].values())
    d["extract"] = {"title": C("Extract: fragments into assertions"),
                    "intro": C(f"{det['load']['assertions']} assertions, one fact each, by ten deterministic mappers, one per format.",
                               "No model took part.",
                               "Each assertion carries a basis, the fragment it rests on, and a status that starts at proposed."),
                    "sections": ([{"heading": C("Symbols with no definition in any document"), "list": det["load"]["unresolved_symbols"]}] if det["load"]["unresolved_symbols"] else [])
                                + [{"heading": C("The 36 keys the task needs, by the level the gate resolved"), "table": _table(["level", "keys"], sorted(levels.items(), key=lambda kv: -kv[1]))}]}
    cen = det["D2_census"]
    ver_text = (C(f"{det['verifications']['execution']} by execution: the oracle ran them, and each record names the scenario and the code's digest.",
                  f"{det['verifications']['review']} by review: the dated review record and the authored inputs.",
                  f"{det['verifications']['approved']} approvals by the owner.")
                if "execution" in det["verifications"] else C("None loaded: this scenario is extraction only."))
    d["load"] = {"title": C("Load: the store"),
                 "intro": C(f"{cen['nodes']} nodes and {cen['relationships']} relationships.",
                            "Verification and approval are nodes with their own records, never a flag flipped on the assertion."),
                 "sections": [{"heading": C("Assertions by status"), "table": _table(["status", "assertions"], sorted(cen["assertions_by_status"].items()))},
                              {"heading": C("Gaps by kind"), "table": _table(["kind", "gaps"], sorted(cen["gaps_by_kind"].items()))},
                              {"heading": C("Verification records"), "text": ver_text},
                              {"heading": C("D1: the constraints the community edition accepts"), "table": _table(["type", "accepted", "message"], [(c["type"], "yes" if c["accepted"] else "no", (c["message"] or "").split("{message:")[-1].strip(" }")[:110]) for c in det["D1_constraints"]])},
                              {"heading": C("Why the refused messages end mid-sentence"),
                               "text": C("The harness kept only the first line of the engine's answer, which ends at the schema.",
                                         "The second line, not recorded, says these three constraints need Neo4j Enterprise Edition.",
                                         "The record quotes that line in §12 and reads it as expectation X9.",
                                         "The panel shows what the run file holds.")}]}
    rules = det["rules"]
    secs = []
    for r in RULE_ORDER:
        hits = rules[r]
        unit = "pairs" if r == "R-CORROBORATE" else "assertions" if r == "R-UNVERIFIED" else "hit(s)"
        sec = {"heading": C(f"{r}: {hits if not isinstance(hits, list) else len(hits)} {unit}"), "text": C(*RULE_TEXT[r])}
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
    secs.append({"heading": C(f"SHACL over an RDF projection: {sh['triples']} triples"),
                 "text": C(f"The main shapes mirror R-STRUCT and R-REQ: conforms={sh['main']['conforms']}, {sh['main']['results']} result(s) {sh['main']['by_severity']}.",
                           f"An information-only shape, which every assertion violates: conforms={sh['info_only']['conforms']}, {sh['info_only']['results']} results.",
                           "This shows at execution that sh:conforms is false on information-level results alone."),
                 "list": sh["main"]["sample"][2:8]})
    d["rules"] = {"title": C("Rules: seven Cypher checks after every load"),
                  "intro": C("Each rule is one or more Cypher queries.", "Only the loaders, the rules and recorded human acts set status.",
                             "No rule promotes to verified or approved."), "sections": secs}
    keys_rows = [(k, v["level"], ", ".join(v["flags"]) or "", v["n"]) for k, v in det["gate_keys"].items()]
    gsecs = [{"heading": C("How the verdict is formed"),
              "text": C("BLOCKED if any key is absent, a declared gap, disputed or invalidated.",
                        "BLOCKED too if more than 25 % of the keys are below verified.",
                        "QUALIFIED if any key is below verified or carries a flag.", "PROCEED otherwise.",
                        "A key's level is the worst status among its live assertions.")},
             {"heading": C(f"The {len(keys_rows)} keys the task needs"), "table": _table(["key", "level", "flags", "assertions"], keys_rows)}]
    if gate.get("conflicts"):
        gsecs.append({"heading": C("Conflicts the bundle carries"), "list": [c["text"] for c in gate["conflicts"]]})
    d["gate"] = {"title": C(f"Gate: {gate['verdict']}"), "intro": D(gate["why"] + "."), "sections": gsecs}
    for arm, name in (("G", "the governed arm, given the verdict and the bundle"), ("B", "the baseline arm, given the documents only")):
        rs = runs[arm]
        rows = [(r["run"], _model_of(r) or "", r.get("M1_decision") or ("api error" if r.get("api_error") else ""), "yes" if r.get("M2_code") else "no",
                 "yes" if r["M3_flagged"]["flagged"] else "no", ", ".join(r["M3_flagged"].get("hits", [])), len(r.get("questions") or []), len(r.get("assumptions") or []), len(r.get("claims") or []),
                 (r.get("usage") or {}).get("prompt_tokens", ""), (r.get("usage") or {}).get("completion_tokens", "")) for r in rs]
        d[f"generate_{arm}"] = {"title": C(f"Generate, {arm}: {name}"),
                                "intro": (C(f"{len(rs)} runs.", "Decision is the arm's own word: generate, generate with assumptions, or abstain.",
                                            "Flagged means the frozen keyword check found the planted problem in the arm's questions or assumptions.")
                                          if rs else C("No run in this source.")),
                                "sections": ([{"heading": C("Per run"), "table": _table(["run", "model", "decision", "code", "flagged", "keywords hit", "questions", "assumptions", "claims", "prompt tokens", "reply tokens"], rows)}] if rs else [])}
        orows = [(r["run"], f"{r['M4_suite']['passed']}/{r['M4_suite']['total']}" if r["M4_suite"]["ran"] else "no code",
                  ", ".join(f"{t}: {'pass' if v else ('fail' if v is False else 'no code')}" for t, v in (r.get("M4_targets") or {}).items()) or "",
                  r.get("outage_status") or "", f"{r['M5_refs']['resolved']}/{r['M5_refs']['total']}" if r["M5_refs"]["share"] is not None else "") for r in rs]
        d[f"oracle_{arm}"] = {"title": C(f"Oracle, {arm}: the kit's eleven scenarios on the code the arm wrote"),
                              "intro": (C("Each reply's code ran in a sandbox against the kit's eleven scenarios, with the scenario's overlays.",
                                          "S6 asks for the new prices.", "The planted target is the scenario the plant aims at.",
                                          "The outage status is what the code returned when screening was down.",
                                          "A reference is resolvable when it points at something that exists.",
                                          "For G that is an assertion id; for B, a document line.")
                                        if rs else C("No run in this source.")),
                              "sections": ([{"heading": C("Per run"), "table": _table(["run", "oracle", "planted targets", "outage status returned", "references resolvable"], orows)}] if rs else [])}
    if "stage2" in det:
        s2 = det["stage2"]
        d["ingest2"] = {"title": C("Re-ingest: the changed tariff document as version v2"),
                        "intro": C(f"{s2['load_v2']['fragments']} fragments new, {s2['load_v2']['fragments_reused']} reused because their digest was unchanged, {s2['load_v2']['assertions']} new assertions.",
                                   "Unchanged fragments keep their assertions.", "Only changed ones create new assertions."), "sections": []}
        d["stale"] = {"title": C("R-STALE: what the change invalidates"),
                      "intro": C("An assertion whose supporting fragment's digest changed or vanished is invalidated.",
                                 "Its verifications end: valid_until = v2.", "Every derived output that used it becomes suspect.",
                                 "Everything else of the same document keeps its status."),
                      "sections": [{"heading": C("Invalidated"), "table": _table(["assertion", "key", "derived outputs that used it"], [(x["id"], x["key"], ", ".join(x["derived"]) or "") for x in s2["D3_stale"]["invalidated"]])},
                                   {"heading": C(f"Kept at their status: {len(s2['D3_stale']['kept'])}"), "list": [f"{x['id']} ({x['status']})" for x in s2["D3_stale"]["kept"][:12]] + (["…"] if len(s2["D3_stale"]["kept"]) > 12 else [])},
                                   {"heading": C("Derived outputs"), "list": [f"{x['id']}: suspect={x['suspect']}" for x in s2["suspect_derived"]] or ["none registered in this source"]}]}
        gb = s2["gate_before_reverification"]
        d["gate_before"] = {"title": C(f"Gate before re-verification: {gb['verdict']}"), "intro": D(gb["why"] + "."),
                            "sections": [{"heading": C("Invalidated assertions on the keys the task needs, with their successors"), "table": _table(["assertion", "key", "old value", "successor", "successor status"], [(x["id"], x["key"], x["value"], ", ".join(t["id"] for t in x["successors"] if t["id"]), ", ".join(t["status"] for t in x["successors"] if t["id"])) for x in gb["stale"]])}]}
        d["reverify"] = {"title": C("Re-verification by the owner stand-in"),
                         "intro": C("A verification record, method review and dated, and an approval for each successor assertion.", "The record is a node, not a property flip."),
                         "sections": [{"heading": C("Re-verified and approved"), "list": s2["reverified"]}]}
        ga = s2["gate_after_reverification"]
        d["gate_after"] = {"title": C(f"Gate after re-verification: {ga['verdict']}"), "intro": D(ga["why"] + "."),
                           "sections": [{"heading": C("Census after"), "text": D(f"{s2['census_after']['nodes']} nodes, {s2['census_after']['relationships']} relationships; {s2['census_after']['assertions_by_status']}.")}]}
    d["gaps"] = {"title": C("Gaps: everything the rules found wanting"),
                 "intro": C("Grouped by kind.", "The counts are the store's census after the rules ran."), "sections": []}
    return d


# ------------------------------------------------------------ the gaps view

GAP_KIND_TEXT = {
    "declared missing": ["Knowledge the documents themselves say is not there yet.",
                         "A requirement marked NOT YET SPECIFIED, or a document declared not yet authored.",
                         "The authors know it is missing.", "The gate blocks the key it governs until a decision is recorded."],
    "undeclared missing": ["Something a rule expected and did not find, and nobody had declared it.",
                           "Here: a requirement with no Gherkin scenario that verifies it."],
    "ambiguous": ["An assertion whose wording leaves several readings.",
                  "A decision-table row in vague words, or a diagram symbol with no definition anywhere.",
                  "Each assertion the row or symbol supports gets its own gap.", "The gate flags the key."],
    "conflict": ["Two documents give different values for the same key.",
                 "Both assertions are marked disputed, and the gate blocks the key.", "The gap's text names both sides."],
    "unverified": ["An assertion nobody has verified: proposed or validated, with no verification record.",
                   "Most are harmless, such as participant kinds or scenario titles.",
                   "The ones on the keys the task needs count against the gate's 25 % bar."],
}
CONFLICT_TEXT_RE = re.compile(r"for (?P<key>[^:]+): (?P<a>[^ ]+) says (?P<va>.+?); (?P<b>[^ ]+) says (?P<vb>.+)$")


def gaps_view(det: dict, reg: list) -> dict:
    """Every gap the result files can account for, grouped by kind, with the
    census as the header. The store's own text and the full CONCERNS set come
    from /api/gaps when the loaded scenario matches; the page merges them."""
    rules, census = det["rules"], det["D2_census"]["gaps_by_kind"]
    groups = {k: [] for k in GAP_KIND_TEXT}
    for h in rules["R-REQ"]:
        if h.get("declared"):
            if h.get("req"):
                groups["declared missing"].append({"id": "gap:declared:OD-1", "declared": True,
                    "text": f"{h['req']} is NOT YET SPECIFIED (open decision OD-1, owner: compliance)",
                    "concerns": [{"id": h["req"], "what": "requirement"}] + ([{"id": h["key"], "what": "key"}] if h.get("key") else []), "assertion": None})
            elif h.get("artefact"):
                groups["declared missing"].append({"id": f"gap:declared:{h['artefact']}", "declared": True,
                    "text": f"{h['artefact']} is not yet authored",
                    "concerns": [{"id": f"A:req:{h['artefact']}|authored@v1", "what": "assertion"}], "assertion": {"key": f"{h['artefact']}|authored", "value": "NONE", "basis": "authored", "status": None}})
        elif h.get("req"):
            groups["undeclared missing"].append({"id": f"gap:unverified-req:{h['req']}", "declared": False,
                "text": f"{h['req']} has no verifying scenario", "concerns": [{"id": h["req"], "what": "requirement"}], "assertion": None})
    for h in rules["R-VAGUE"]:
        words = h["words"]
        sym = next((w.split(" ", 1)[1] for w in words if w.startswith("unresolved ")), None)
        text = f"symbol {sym} has no definition in any artefact" if sym else f"vague wording ({', '.join(words)}) in the row that supports it"
        groups["ambiguous"].append({"id": f"gap:ambiguous:{h['id']}", "declared": False, "text": text,
                                    "concerns": [{"id": h["id"], "what": "assertion"}], "assertion": {"key": h["key"], "value": None, "basis": None, "status": None}})
    for c in det["D6_gate"].get("conflicts", []):
        m = CONFLICT_TEXT_RE.search(c["text"])
        sides = ({"key": m.group("key"), "a": m.group("a"), "va": m.group("va"), "b": m.group("b"), "vb": m.group("vb")} if m else None)
        groups["conflict"].append({"id": c["id"], "declared": False, "text": c["text"], "concerns": [], "sides": sides, "assertion": None})
    required_below = [k for k, v in det["gate_keys"].items() if v["level"] in ("proposed", "validated")]
    unverified = {"count": rules["R-UNVERIFIED"], "required_below_verified": required_below, "keys": None}
    counts = {"declared missing": len(groups["declared missing"]), "undeclared missing": len(groups["undeclared missing"]),
              "ambiguous": census.get("ambiguous", 0), "conflict": census.get("conflict", 0), "unverified": census.get("unverified", 0)}
    explain = {k: _reg(reg, "controlled", *v) for k, v in GAP_KIND_TEXT.items()}
    return {"census": census, "counts": counts, "explain": explain,
            "groups": {k: groups[k] for k in ("declared missing", "undeclared missing", "ambiguous", "conflict")},
            "unverified": unverified, "required_keys": list(det["gate_keys"]),
            "source": "the committed result files (deterministic.json): the rule hits, the gate's conflicts and per-key levels"}


# ------------------------------------------------------------ the systemic-model panels

# One name per node of the slide's reduced knowledge view, in the glossary's terms;
# the model's own label and definition are quoted as data beside it.
NODE_TITLE = {
    "tacit": "What only people know", "updef": "Upstream intent defects", "unknown": "Unresolved or invented decisions",
    "validation": "Independent validation", "deriveddef": "The behaviour-carrying layer", "explderived": "Explanatory documents",
    "testdef": "Tests that share the premise", "drift": "Document drift", "depchange": "Dependency change",
    "codedef": "Implementation defects", "escape": "Escaped product defects", "detection": "Independent detection",
    "confidence": "Unwarranted confidence", "harm": "Adverse outcomes in use", "dora": "Delivery performance", "diverse": "More detection inputs",
}
ARM_NAME = {"G": "the governed arm", "B": "the baseline arm"}


def _role_sentences(nid: str, spec: dict, arm: str) -> list[str]:
    """What the record's reading placed on this node for one arm, as controlled sentences."""
    a = spec.get(arm, {})
    entry, path, stop = spec.get("entry"), a.get("path") or [], a.get("stop")
    out = []
    if not entry and not path:
        return ["Nothing was planted, so nothing is placed here."]
    if nid == entry:
        out.append("The planted defect entered the model here.")
    if nid in path and nid != entry:
        out.append("The defect passed through here.")
    if nid == stop:
        out.append("The defect was made visible here." if a.get("visible") else
                   "The defect was resolved here by an invented decision." if a.get("invented") else
                   "The defect was stopped here.")
    if a.get("would") == nid and stop == "detection":
        out.append("Without the oracle, the defect would have reached here.")
    if a.get("would") and stop == "detection" and nid == stop:
        out.append(f"Without the oracle it would have gone on to {NODE_TITLE[a['would']].lower()}.")
    return out or ["The record's reading placed nothing of this scenario here."]


def systemic_details(view: dict, det: dict, runs: dict, reg: list) -> dict:
    """What opens when a box of the systemic model is clicked: the node in the
    model (label, kind, definition, its edges with mechanism and evidence), what
    the record's reading placed there for each arm, and the evidence from the
    result files that bears on that node."""
    M = cascade.model()
    N = {n["id"]: n for n in M["nodes"]}
    E = {e["id"]: e for e in M["edges"]}
    spec, gate, rules = view["systemic"], det["D6_gate"], det["rules"]
    C = lambda *t: _reg(reg, "controlled", *t)  # noqa: E731
    D = lambda *t: _reg(reg, "data", *t)  # noqa: E731
    arms = view["arms"]
    verdict_sentence = {"PROCEED": "The gate gave PROCEED.", "QUALIFIED": "The gate gave QUALIFIED.", "BLOCKED": "The gate gave BLOCKED."}
    out = {}
    for nid, (_x, _y, l1, l2, lever) in cascade.slide.nodes.items():
        node = N.get(nid)
        intro = (C("In the model:") + " " + D(f"{node['label']} ({node['kind']}): {node['definition'].rstrip('.')}.")
                 if node else C("The slide draws this node as context.", "The model's inventory has no node of this id."))
        secs = []
        if lever:
            secs.append({"heading": C("A lever"), "text": C("The model marks this node as one of its four levers.") + " " + D(l2 + ".")})
        rows = [(eid, a, b, E[eid]["polarity"], E[eid].get("delay") or "", E[eid]["evidence"], E[eid].get("mechanism") or "")
                for eid, a, b in cascade.slide.edges if nid in (a, b)]
        secs.append({"heading": C("Edges in the model"),
                     "text": C("Plus means the source raises the target, minus means it lowers it.",
                               "M is measured, bounded; H is a hypothesis."),
                     "table": _table(["edge", "from", "to", "polarity", "delay", "evidence", "mechanism"], rows)})
        for arm in ("G", "B"):
            text = C(*_role_sentences(nid, spec, arm))
            if spec.get("entry") and (nid == spec.get("entry") or nid in (spec[arm].get("path") or []) or nid == spec[arm].get("stop")):
                text += " " + C(spec[arm]["note"])
            secs.append({"heading": C(f"Arm {arm}, {ARM_NAME[arm]}, in this scenario"), "text": text})
        # the evidence from the result files that bears on this node
        if nid == "updef":
            g = view["gaps"]["groups"]
            miss = g["declared missing"] + g["undeclared missing"]
            secs.append({"heading": C(f"Missing items the rules recorded: {len(miss)}"),
                         "text": C("A declared item is one the authors marked missing themselves."),
                         "table": _table(["gap", "what it says", "declared by the authors"], [(r["id"], r["text"], "yes" if r["declared"] else "no") for r in miss])})
        if nid == "deriveddef":
            hits = rules["R-VAGUE"]
            secs.append({"heading": C(f"Ambiguous assertions in the behaviour-carrying documents: {len(hits)}"),
                         "text": C("Each row is one assertion whose supporting row or symbol is vaguely worded."),
                         "table": _table(["assertion", "key", "vague words"], [(h["id"], h["key"], ", ".join(h["words"])) for h in hits])})
        if nid == "explderived":
            conf = view["gaps"]["groups"]["conflict"]
            secs.append({"heading": C(f"Contradictions between documents: {len(conf)}"),
                         "text": C("Both sides of each pair are marked disputed."),
                         "table": _table(["gap", "key", "one side", "says", "other side", "says"],
                                         [(r["id"], r["sides"]["key"], r["sides"]["a"], r["sides"]["va"], r["sides"]["b"], r["sides"]["vb"]) if r.get("sides") else (r["id"], "", "", r["text"], "", "") for r in conf])})
            inferred = [k for k, v in det["gate_keys"].items() if "inferred" in v["flags"]]
            if inferred:
                secs.append({"heading": C("Keys with an inferred candidate"),
                             "text": C("An inferred assertion came from a model, not from a document, and cannot lift a declared gap."), "list": inferred})
        if nid == "unknown":
            items = []
            for arm in ("G", "B"):
                for r in arms[arm]["runs"]:
                    for a in r["assumptions"]:
                        t = a["text"] if isinstance(a, dict) else str(a)
                        items.append(f"{arm} run {r['run']}, assumption: {t[:220]}" + (f" [{a.get('ref')}]" if isinstance(a, dict) and a.get("ref") else ""))
                    for q in r["questions"]:
                        items.append(f"{arm} run {r['run']}, question: {str(q)[:220]}")
            secs.append({"heading": C(f"Assumptions and questions the arms wrote: {len(items)}"),
                         "text": C("Arm G names the assertion id each assumption rests on.", "Arm B names a document line, or nothing."),
                         "list": items or ["none in this source"]})
        if nid == "validation":
            secs.append({"heading": C("The gate"), "text": C(verdict_sentence[gate["verdict"]]) + " " + D(gate["why"] + ".")})
            for arm in ("G", "B"):
                sm = arms[arm]["summary"]
                if sm["n"]:
                    secs.append({"heading": C(f"Arm {arm}, decisions"),
                                 "text": C(*[f"Arm {arm} answered '{(k or 'no decision').replace('_', ' ')}' in {v} of {sm['n']} runs." for k, v in sm["decisions"].items()])})
        if nid in ("codedef", "detection"):
            rows = []
            for arm in ("G", "B"):
                for r in arms[arm]["runs"]:
                    rows.append((arm, r["run"], r["suite"] or "no code",
                                 ", ".join(f"{t}: {'pass' if v else ('fail' if v is False else 'no code')}" for t, v in r["targets"].items()) or ""))
            heading = C(f"The oracle on the planted targets: {len(rows)} runs") if nid == "detection" else C(f"What the code did on the planted targets: {len(rows)} runs")
            secs.append({"heading": heading,
                         "text": C("A planted target is the oracle scenario the planted defect aims at.") if nid == "codedef"
                                 else C("The oracle is independent of the arms' code.", "A fail here is a defect the oracle caught, and nothing else did."),
                         "table": _table(["arm", "run", "oracle", "planted targets"], rows)})
        if nid == "confidence":
            ver = det["verifications"]
            vtext = (C(f"The oracle verified {ver['execution']} assertions by running them, and the review record {ver['review']} more.",
                       f"The owner approved {ver['approved']}.") if "execution" in ver
                     else C("No verification was loaded in this scenario.", "Correct and unverified look exactly alike to the arms."))
            flagged = [f"Arm {arm} raised the planted problem in {arms[arm]['summary']['flagged']} of {arms[arm]['summary']['n']} runs." for arm in ("G", "B") if arms[arm]["summary"]["n"]]
            secs.append({"heading": C("Verification, and what the arms raised"), "text": vtext + (" " + C(*flagged) if flagged else "")})
        if nid == "drift":
            if view.get("stage2"):
                s2 = view["stage2"]
                secs.append({"heading": C(f"Invalidated by the change: {len(s2['invalidated'])} assertions"),
                             "text": C("Their verifications ended, and the derived output built on them is suspect."),
                             "table": _table(["assertion", "key", "derived outputs that used it"], [(x["id"], x["key"], ", ".join(x.get("derived") or [])) for x in s2["invalidated"]])})
                susp = [x["id"] for x in s2["suspect_derived"] if x.get("suspect")]
                secs.append({"heading": C("Derived outputs marked suspect"), "list": susp or ["none registered in this source"]})
            else:
                secs.append({"heading": C("Document change"), "text": C("No document changed in this scenario.")})
        if nid == "testdef":
            secs.append({"heading": C("The oracle here"), "text": C("The oracle is the kit's own eleven scenarios, written before the arms ran.", "It does not share the arms' premise.")})
        out[nid] = {"title": C(NODE_TITLE[nid]), "intro": intro, "sections": secs}
    return out

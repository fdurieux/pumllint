"""Orchestration: per scenario, load -> rules -> D measures -> arms -> grade.

    python run.py --deterministic            # D1-D6 only, no model
    python run.py --scenarios S1 --n 1       # calibration
    python run.py --n 5                      # the scored run

Results land in kg_experiment/results/<scenario>/ with SHA256SUMS of
the harness and kit written beside them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import arms
import measures
import shacl
from gate import resolve, render_bundle
from kitio import EXP, KIT_FILES, kit_for, CARGO, sha256
from load import (apply_constraints, clear, driver, load_inferred, load_scenario,
                  load_verifications, pristine_values)
from plant import INFERRED
from rules import census, r_stale, run_all

RESULTS = EXP / "results"
ORDER = [k for k, _ in KIT_FILES] + ["notes/analysis_notes.md"]
SCENARIOS = ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str), encoding="utf-8")


def d5(s) -> dict:
    """The three-valued answer for three keys."""
    out = {}
    for key in ("S-review|notified", "S-refuse|notified", "QuoteAPI|notified_after_screening"):
        rows = [dict(r) for r in s.run("MATCH (x:Assertion {key:$k}) WHERE x.status IN ['verified','approved','validated','proposed'] RETURN x.id AS id, x.value AS value, x.status AS status, x.basis AS basis", k=key)]
        if not rows:
            out[key] = {"answer": "unknown", "why": "no assertion for this key (not a documented absence)"}
        elif all(r["value"] == "NONE" for r in rows):
            out[key] = {"answer": "documented_absent", "assertions": rows}
        else:
            out[key] = {"answer": "asserted", "assertions": rows}
    return out


def deterministic(sc: str, pv: dict, d) -> dict:
    with d.session() as s:
        clear(s)
        d1 = apply_constraints(s)
        kit = kit_for(sc)
        load = load_scenario(s, sc, kit, activity_note=f"{sc}: extraction of the planted kit" if sc not in ("S1", "S6", "S7") else f"{sc}: extraction of the pristine kit")
        ver = load_verifications(s, sc, pv) if sc != "S7" else {"skipped": "S7: extraction only"}
        if sc == "S5":
            load_inferred(s, sc, INFERRED)
        rules = run_all(s, sc)
        cen = census(s)
        gate = resolve(s, "codegen")
        out = {"scenario": sc, "D1_constraints": d1, "load": load, "verifications": ver, "rules": rules,
               "D2_census": cen, "D4_shacl": shacl.run(s), "D6_gate": {k: v for k, v in gate.items() if k != "keys"},
               "gate_keys": {k: {"level": v["level"], "flags": v["flags"], "n": len(v["assertions"])} for k, v in gate["keys"].items()}}
        if sc == "S1":
            out["D5_three_valued"] = d5(s)
        return out, gate, kit


def s6_stage2(d, derived_code: str | None, derived_ids: list[str]) -> tuple[dict, dict, dict]:
    with d.session() as s:
        if derived_code:
            s.run("""CREATE (dv:Derived {id:'derived:S1:G:run1', kind:'python module', sha256:$sha, suspect:false})
                     WITH dv UNWIND $ids AS aid MATCH (x:Assertion {id:aid}) MERGE (dv)-[:USED_ASSERTION]->(x)""",
                  sha=sha256(derived_code), ids=derived_ids).consume()
        kit2 = kit_for("S6", 2)
        load2 = load_scenario(s, "S6", {"contract/decision_table.md": kit2["contract/decision_table.md"]},
                              activity_note="S6 stage 2: re-ingestion of the changed decision_table.md", version_tag="v2", reingest=True)
        stale = r_stale(s, "v2")
        rules2 = {"R-STRUCT": run_all(s, "S6")["R-STRUCT"]}
        gate_blocked = resolve(s, "codegen")
        # the recorded re-verification of the three new assertions, by the maintainer stand-in
        rever = s.run("""
            MATCH (x:Assertion {version:'v2'}) WHERE x.key IN ['P2|threshold','P2|surcharge','P3|order'] AND x.status IN ['proposed','validated']
            MATCH (h:Agent {id:'agent:maintainer'})
            MERGE (v:Verification {id:'ver:review:v2:' + x.id}) SET v.method='review', v.outcome='pass', v.at=$ts,
                  v.scope='re-verification after the 2026-10-30 tariff change (owner stand-in)', v.valid_until=null
            MERGE (v)-[:VERIFIES]->(x) MERGE (v)-[:PERFORMED_BY]->(h)
            SET x.status='verified'
            WITH x, h MERGE (ap:Approval {id:'appr:v2:' + x.id}) SET ap.at=$ts, ap.record='re-approval after re-verification'
            MERGE (ap)-[:APPROVES]->(x) MERGE (ap)-[:BY]->(h) SET x.status='approved'
            RETURN collect(x.id) AS ids""", ts="2026-10-30").single()["ids"]
        # v2 assertions of unchanged fragments inherit nothing automatically: they are new statements.
        # Corroboration and verification of them against the pristine values:
        from load import pristine_values as _pv
        pv = _pv()
        pv_keys = {k: v for k, v in pv.items()}
        load_verifications(s, "S6", pv_keys)
        gate_after = resolve(s, "codegen")
        stage2 = {"load_v2": load2, "D3_stale": stale, "R-STRUCT_after": rules2["R-STRUCT"],
                  "gate_before_reverification": {k: v for k, v in gate_blocked.items() if k != "keys"},
                  "reverified": rever,
                  "gate_after_reverification": {k: v for k, v in gate_after.items() if k != "keys"},
                  "census_after": census(s),
                  "suspect_derived": [dict(r) for r in s.run("MATCH (dv:Derived) RETURN dv.id AS id, dv.suspect AS suspect")]}
        return stage2, gate_after, kit2


def arm_runs(sc: str, arm: str, n: int, kit: dict, gate: dict, task_name: str, out_dir: Path,
             resume: bool = False) -> list[dict]:
    system = arms.prompt("system")
    if arm == "B":
        user = arms.prompt(f"{task_name}_baseline") + arms.baseline_documents(kit, ORDER)
        bundle_ids: set[str] = set()
    else:
        bundle = render_bundle(gate, arms.policy())
        user = arms.prompt(f"{task_name}_governed") + bundle
        bundle_ids = {a["id"] for v in gate["keys"].values() for a in v["assertions"]}
        (out_dir / f"bundle_{arm}.txt").write_text(bundle, encoding="utf-8")
    (out_dir / f"prompt_{arm}.txt").write_text(user, encoding="utf-8")
    print(f"    {arm}: {n} call(s) to {arms.MODEL}, {len(user):,} characters of prompt each; the suite runs on each reply", flush=True)

    def one(i: int) -> dict:
        done = out_dir / f"run{i}_{arm}.json"
        if resume and done.exists():
            prev = json.loads(done.read_text(encoding="utf-8"))
            if "api_error" not in prev:
                return prev
        try:
            r = arms.call(system, user, tag=f"{sc}/{arm}/{i}")
        except Exception as e:  # noqa: BLE001 — recorded as a failed cell, never silently dropped
            rec = {"scenario": sc, "arm": arm, "run": i, "api_error": str(e)[:300], "M1_decision": None,
                   "M2_code": False, "M3_flagged": {"flagged": False, "hits": []}, "M4_suite": {"ran": False, "passed": 0, "total": 11, "per_scenario": {}},
                   "M4_targets": {}, "outage_status": None, "M5_refs": {"total": 0, "resolved": 0, "share": None},
                   "M6_noncompliance": False, "questions": None, "assumptions": None, "claims": None,
                   "usage": {"prompt_tokens": 0, "completion_tokens": 0, "attempts": 4}}
            dump(done, rec)
            return rec
        p = r["parsed"] if isinstance(r["parsed"], dict) else None
        code = p.get("code") if p else None
        if code is not None and not isinstance(code, str):
            code = None
        suite = measures.run_suite(code, sc)
        rec = {"scenario": sc, "arm": arm, "run": i, "parse_error": r["parse_error"],
               "M1_decision": (p or {}).get("decision"), "M2_code": bool(code),
               "M3_flagged": measures.flagged(sc, p), "M4_suite": suite,
               "M4_targets": {t: suite["per_scenario"].get(t, {}).get("passed") for t in (measures.TARGETS[sc] or [])},
               "outage_status": measures.outage_status(suite) if suite["ran"] else None,
               "M5_refs": measures.resolvable_refs(arm, p, bundle_ids, kit),
               "M6_noncompliance": (arm == "G" and ((gate["verdict"] == "BLOCKED" and bool(code)) or
                                                     (gate["verdict"] == "QUALIFIED" and (p or {}).get("decision") == "generate"))),
               "questions": (p or {}).get("questions"), "assumptions": (p or {}).get("assumptions"),
               "claims": (p or {}).get("claims"), "usage": r["usage"]}
        dump(out_dir / f"run{i}_{arm}.json", rec)
        (out_dir / f"run{i}_{arm}.raw.json").write_text(r["raw"], encoding="utf-8")
        if code:
            (out_dir / f"run{i}_{arm}.py").write_text(code, encoding="utf-8")
        return rec
    with ThreadPoolExecutor(max_workers=int(__import__("os").environ.get("KG_WORKERS", "5"))) as ex:
        return list(ex.map(one, range(1, n + 1)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", nargs="*", default=SCENARIOS)
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--deterministic", action="store_true")
    ap.add_argument("--out", default=str(RESULTS))
    ap.add_argument("--resume", action="store_true", help="skip cells whose run json exists")
    args = ap.parse_args()
    out_root = Path(args.out)
    pv = pristine_values()
    d = driver()
    summary = {}
    for sc in args.scenarios:
        out_dir = out_root / sc
        out_dir.mkdir(parents=True, exist_ok=True)
        det, gate, kit = deterministic(sc, pv, d)
        runs = {}
        if sc == "S6":
            task = "task_s6"
            if not args.deterministic:
                # stage 1 = S1's graph; the derived artefact is S1/G/run1's code if it exists
                s1_code_path = out_root / "S1" / "run1_G.py"
                derived_code = s1_code_path.read_text(encoding="utf-8") if s1_code_path.exists() else None
                derived_ids = [a["id"] for v in gate["keys"].values() for a in v["assertions"]]
                stage2, gate, kit = s6_stage2(d, derived_code, derived_ids)
                det["stage2"] = stage2
            else:
                stage2, gate, kit = s6_stage2(d, None, [])
                det["stage2"] = stage2
        else:
            task = "task_codegen"
        dump(out_dir / "deterministic.json", det)
        print(f"{sc}: gate {det['D6_gate']['verdict']} — {det['D6_gate']['why']}", flush=True)
        if sc == "S6":
            print(f"    stage 2: invalidated {[x['key'] for x in det['stage2']['D3_stale']['invalidated']]}; "
                  f"before re-verification {det['stage2']['gate_before_reverification']['verdict']}, after {det['stage2']['gate_after_reverification']['verdict']}", flush=True)
        if not args.deterministic:
            for arm in ("B", "G"):
                runs[arm] = arm_runs(sc, arm, args.n, kit, gate, task, out_dir, resume=args.resume)
                print(f"    {arm}: decisions {[r['M1_decision'] for r in runs[arm]]}; code {[r['M2_code'] for r in runs[arm]]}; "
                      f"suite {[r['M4_suite']['passed'] for r in runs[arm]]}; flagged {[r['M3_flagged']['flagged'] for r in runs[arm]]}", flush=True)
        summary[sc] = {"gate": det["D6_gate"]["verdict"],
                       "runs": {arm: [{k: r[k] for k in ("run", "M1_decision", "M2_code", "M3_flagged", "M4_targets", "outage_status", "M5_refs", "M6_noncompliance")} | {"suite": f"{r['M4_suite']['passed']}/{r['M4_suite']['total']}"} for r in rs] for arm, rs in runs.items()}}
    d.close()
    dump(out_root / "summary.json", summary)
    prev_usage = json.loads((out_root / "usage.json").read_text()) if (out_root / "usage.json").exists() else None
    u = arms.usage()
    if prev_usage:
        u = {"calls": prev_usage["calls"] + u["calls"], "usd_est": round(prev_usage["usd_est"] + u["usd_est"], 4),
             "retries": prev_usage.get("retries", []) + u["retries"], "per_call": prev_usage["per_call"] + u["per_call"],
             "segments": prev_usage.get("segments", 1) + 1}
    dump(out_root / "usage.json", u)
    # digests of what ran
    lines = []
    for p in sorted([*(EXP / "harness").rglob("*.py"), *(EXP / "harness").rglob("*.md"), *(EXP / "kit").iterdir(), *(CARGO.rglob("*"))]):
        if p.is_file() and "__pycache__" not in str(p):
            lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(EXP.parent)}")
    (out_root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("usage:", arms.usage()["calls"], "calls, est $", arms.usage()["usd_est"])


if __name__ == "__main__":
    main()

"""Tabulate kg_experiment/results into the per-scenario, per-arm counts the
pre-registration's expectations are read from.

    python report.py [results_dir]
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

RES = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "results"


def load(sc: str, arm: str) -> list[dict]:
    out = []
    for p in sorted((RES / sc).glob(f"run*_{arm}.json")):
        out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


def main() -> None:
    for sc in ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]:
        det_path = RES / sc / "deterministic.json"
        if not det_path.exists():
            continue
        det = json.loads(det_path.read_text(encoding="utf-8"))
        print(f"\n## {sc} — gate {det['D6_gate']['verdict']}: {det['D6_gate']['why']}")
        c = det["D2_census"]
        print(f"   census: {c['nodes']} nodes, {c['relationships']} rels; status {c['assertions_by_status']}; gaps {c['gaps_by_kind']}; contradicts {c['contradicts']}")
        print(f"   R-STRUCT violations: {len(det['rules']['R-STRUCT'])}; corroborated pairs: {det['rules']['R-CORROBORATE']}; conflicts: {len(det['rules']['R-CONFLICT'])}; vague: {len(det['rules']['R-VAGUE'])}; req gaps: {len(det['rules']['R-REQ'])}")
        sh = det["D4_shacl"]
        print(f"   SHACL main: conforms={sh['main']['conforms']} results={sh['main']['results']} {sh['main']['by_severity']}; info-only: conforms={sh['info_only']['conforms']} results={sh['info_only']['results']}")
        if "stage2" in det:
            s2 = det["stage2"]
            print(f"   S6 stage 2: v2 load {s2['load_v2']}; invalidated {[x['key'] for x in s2['D3_stale']['invalidated']]}; kept {len(s2['D3_stale']['kept'])}; "
                  f"suspect {s2['suspect_derived']}; before {s2['gate_before_reverification']['verdict']} ({s2['gate_before_reverification']['why']}); after {s2['gate_after_reverification']['verdict']}")
        for arm in ("B", "G"):
            runs = load(sc, arm)
            if not runs:
                continue
            dec = Counter(r["M1_decision"] for r in runs)
            code = sum(1 for r in runs if r["M2_code"])
            flagged = sum(1 for r in runs if r["M3_flagged"]["flagged"])
            suites = [f"{r['M4_suite']['passed']}/{r['M4_suite']['total']}" if r["M4_suite"]["ran"] else "-" for r in runs]
            targets = Counter()
            for r in runs:
                for t, v in r["M4_targets"].items():
                    targets[(t, "pass" if v else ("fail" if v is False else "nocode"))] += 1
            outage = Counter(r["outage_status"] for r in runs if r["outage_status"])
            refs = [r["M5_refs"]["share"] for r in runs if r["M5_refs"]["share"] is not None]
            nonc = sum(1 for r in runs if r.get("M6_noncompliance"))
            tok = sum(r["usage"]["prompt_tokens"] + r["usage"]["completion_tokens"] for r in runs)
            print(f"   {arm}: n={len(runs)} decisions={dict(dec)} code={code} flagged={flagged} suite={suites} "
                  f"targets={dict(targets)} outage={dict(outage)} refs={[round(x,2) for x in refs]} noncompliance={nonc} tokens={tok}")
    u = RES / "usage.json"
    if u.exists():
        uu = json.loads(u.read_text())
        print(f"\nusage: {uu['calls']} calls, est ${uu['usd_est']}, retries {len(uu.get('retries', []))}")


if __name__ == "__main__":
    main()

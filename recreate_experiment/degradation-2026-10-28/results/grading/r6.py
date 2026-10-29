"""R6: per defect, each observing artefact of the rebuild is ORIGINAL (identical to today's reference),
PLANTED (identical to today's run of the defect's mutant) or OTHER, under compare.py's equality (frames
as text, JSON after dropping `last_updated`, everything else as bytes). An artefact absent from both the
rebuild's run and the mutant's (the scenario stopped at the same step in both) counts as PLANTED; absent
from the rebuild's run alone, it is "missing". For CLI artefacts the auxiliary "same outcome" (exit code
and final stderr line, compare.py's M7post) is also read against the mutant, since a rebuild's traceback
can never carry the mutant's file paths. D3 and D5 are also read against their arm's combined mutant.
Usage: r6.py <lab>; writes <lab>/grade/r6.json."""
import json, sys
from pathlib import Path
L = Path(sys.argv[1]); G = L / "grade"; B = L / "bundle"
DEFECTS = [("D1","W","JDL-095","D1W-095"),("D1","M","JDL-134","D1M-134"),("D1","A","JDL-049","D1A-049"),
           ("D2","W","JDL-060","D2W-060"),("D2","M","JDL-102","D2M-102"),("D2","A","JDL-073","D2A-073"),
           ("D3","W1","JDL-057","D3-057"),("D3","W2","JDL-047","D3-047"),("D3","W3","JDL-072","D3-072"),
           ("D4","W","JDL-099","D3-099"),("D4","M","JDL-118","M-118"),("D4","A","JDL-003","A-003"),
           ("D5","M1","JDL-094","M-094"),("D5","M2","JDL-136","M-136"),("D5","M3","JDL-084","M-084")]
COMBINED = {"D3": "D3-all", "D5": "D5-all"}
def strip(o):
    if isinstance(o, dict): return {k: strip(v) for k, v in o.items() if k != "last_updated"}
    if isinstance(o, list): return [strip(v) for v in o]
    return o
def load(p):
    if not p.exists(): return None
    if p.name.endswith(".json"):
        try: return ("json", strip(json.loads(p.read_text())))
        except Exception: return ("bytes", p.read_bytes())
    if p.name.endswith(".frame.csv"): return ("text", p.read_text())
    return ("bytes", p.read_bytes())
def last_line(t): return ([x for x in (t or "").splitlines() if x.strip()] or [""])[-1]
def outcome(v):
    if v and v[0] == "json" and isinstance(v[1], dict) and "exit" in v[1]:
        return (v[1].get("exit"), last_line(v[1].get("stderr")), v[1].get("stdout"))
    return None
rows = []; summary = []
for arm, slot, req, mid in DEFECTS:
    obs = json.loads((B / "observing" / f"{mid}.json").read_text())["observing"]
    counts = {"ORIGINAL": 0, "PLANTED": 0, "OTHER": 0, "missing": 0}; aux = 0; comb = 0; still = 0
    for a in obs:
        ref = load(G / "ref" / a); mut = load(G / "mut" / mid / "run" / a); rc = load(G / "arms" / arm / "run" / a)
        still += (ref != mut)
        if rc is None and mut is None and ref is not None: v = "PLANTED"   # absent in both: the scenario errored as the mutant's did
        elif rc is None: v = "missing"
        elif rc == ref: v = "ORIGINAL"
        elif rc == mut: v = "PLANTED"
        else: v = "OTHER"
        counts[v] += 1
        o_rc, o_mut = outcome(rc), outcome(mut)
        same_out = v == "OTHER" and o_rc is not None and o_rc == o_mut
        aux += same_out
        c = None
        if arm in COMBINED and v == "OTHER":
            cm = load(G / "mut" / COMBINED[arm] / "run" / a); c = (rc == cm); comb += c
        rows.append({"arm": arm, "slot": slot, "req": req, "mutant": mid, "artefact": a, "verdict": v,
                     "same_outcome_as_mutant": same_out, "equals_combined_mutant": c})
    n = len(obs)
    verdict = ("ORIGINAL" if counts["ORIGINAL"] == n else "PLANTED" if counts["PLANTED"] == n else
               "OTHER" if counts["OTHER"] == n else "mixed")
    summary.append({"arm": arm, "slot": slot, "req": req, "mutant": mid, "n": n, **counts, "verdict": verdict,
                    "other_with_mutant_outcome": aux, "other_equal_to_combined_mutant": comb, "mutant_still_differs_today": still})
json.dump({"summary": summary, "artefacts": rows}, open(G / "r6.json", "w"), indent=1)
for s in summary:
    extra = []
    if s["other_with_mutant_outcome"]: extra.append(f"{s['other_with_mutant_outcome']} OTHER with the mutant's outcome")
    if s["other_equal_to_combined_mutant"]: extra.append(f"{s['other_equal_to_combined_mutant']} OTHER equal to the combined mutant")
    if s["mutant_still_differs_today"] != s["n"]: extra.append(f"mutant differs from today's reference on {s['mutant_still_differs_today']}/{s['n']}")
    print(f"{s['arm']}-{s['slot']:<3} {s['req']} ({s['mutant']}, n={s['n']}): {s['verdict']:<8} O{s['ORIGINAL']} P{s['PLANTED']} X{s['OTHER']} miss{s['missing']}  {'; '.join(extra)}")

"""The gate (pre-registration §6): required keys -> levels, flags,
verdict, evidence bundle."""

from __future__ import annotations

from tasks import TASKS

ORDER = ["absent", "declared_gap", "disputed", "invalidated", "proposed", "validated", "verified", "approved"]
LIVE = ["proposed", "validated", "verified", "approved", "disputed", "invalidated"]


def resolve(s, task: str) -> dict:
    spec = TASKS[task]
    keys = {}
    for key in spec["keys"]:
        rows = list(s.run("""
            MATCH (x:Assertion {key:$key}) WHERE x.status IN $live
            OPTIONAL MATCH (x)-[:SUPPORTED_BY]->(f:Fragment)
            OPTIONAL MATCH (v:Verification)-[:VERIFIES]->(x)
            OPTIONAL MATCH (ap:Approval)-[:APPROVES]->(x)
            OPTIONAL MATCH (g:Gap)-[:CONCERNS]->(x)
            OPTIONAL MATCH (x)-[:ATTRIBUTED_TO]->(ag:Agent)
            RETURN x.id AS id, x.value AS value, x.text AS text, x.basis AS basis, x.status AS status,
                   x.artefact AS artefact, ag.name AS agent,
                   collect(DISTINCT {locator:f.locator, text:f.text, artefact:f.artefact}) AS fragments,
                   collect(DISTINCT {id:v.id, method:v.method, scope:v.scope, at:v.at, valid_until:v.valid_until}) AS verifications,
                   collect(DISTINCT {id:ap.id, at:ap.at, record:ap.record}) AS approvals,
                   collect(DISTINCT {id:g.id, kind:g.kind, declared:g.declared, text:g.text}) AS gaps
            ORDER BY x.id""", key=key, live=LIVE))
        rows = [dict(r) for r in rows]
        for r in rows:
            r["fragments"] = [f for f in r["fragments"] if f["locator"]]
            r["verifications"] = [v for v in r["verifications"] if v["id"]]
            r["approvals"] = [a for a in r["approvals"] if a["id"]]
            r["gaps"] = [g for g in r["gaps"] if g["id"]]
        ent = key.split("|")[0]
        declared = [dict(r) for r in s.run("""
            MATCH (g:Gap {kind:'missing', declared:true})-[c:CONCERNS_KEY {key:$key}]->()
            RETURN g.id AS id, g.text AS text""", key=key)]
        if not rows:
            level = "declared_gap" if declared else "absent"
        elif declared:
            level = "declared_gap"
        else:
            # an invalidated assertion is superseded only by a verified or
            # approved replacement on the same key; until then it blocks
            replaced = any(r["status"] in ("verified", "approved") for r in rows)
            live_rows = [r for r in rows if not (r["status"] == "invalidated" and replaced)]
            level = min((r["status"] for r in live_rows), key=ORDER.index)
            if replaced:
                rows = live_rows
        flags = set()
        if any(g["kind"] == "ambiguous" for r in rows for g in r["gaps"]):
            flags.add("ambiguous")
        if rows and all(r["basis"] in ("inferred", "assumed", "hypothesised") for r in rows):
            flags.add(next(iter({r["basis"] for r in rows})))
        keys[key] = {"level": level, "flags": sorted(flags), "assertions": rows, "declared_gaps": declared}
    n = len(keys)
    blocked_keys = [k for k, v in keys.items() if v["level"] in spec["block_levels"]]
    below = [k for k, v in keys.items() if ORDER.index(v["level"]) < ORDER.index("verified")]
    flagged = [k for k, v in keys.items() if v["flags"]]
    if blocked_keys:
        verdict, why = "BLOCKED", f"{len(blocked_keys)} required key(s) at a blocking level: " + ", ".join(f"{k} ({keys[k]['level']})" for k in blocked_keys)
    elif len(below) / n > spec["max_unverified_share"]:
        verdict, why = "BLOCKED", f"{len(below)} of {n} required keys ({len(below)/n:.0%}) are below verified; the bar is {spec['max_unverified_share']:.0%}"
    elif below or flagged:
        verdict, why = "QUALIFIED", f"{len(below)} key(s) below verified, {len(flagged)} flagged: " + ", ".join(sorted(set(below) | set(flagged)))
    else:
        verdict, why = "PROCEED", f"all {n} required keys verified or approved, none flagged"
    conflicts = [dict(r) for r in s.run("MATCH (g:Gap {kind:'conflict'}) RETURN g.id AS id, g.text AS text")]
    # staleness: invalidated assertions on required keys (superseded or not), the verifications
    # their invalidation ended, and the derived outputs that used them (S6; added after the first
    # scored run, whose S6 bundle carried none of this - see the pre-registration's run notes)
    stale = [dict(r) for r in s.run("""
        MATCH (x:Assertion {status:'invalidated'}) WHERE x.key IN $keys
        OPTIONAL MATCH (v:Verification)-[:VERIFIES]->(x)
        OPTIONAL MATCH (succ:Assertion {key:x.key, artefact:x.artefact}) WHERE succ.status IN ['proposed','validated','verified','approved']
        RETURN x.id AS id, x.key AS key, x.value AS value, x.invalidated_by AS invalidated_by,
               collect(DISTINCT {id:v.id, valid_until:v.valid_until}) AS verifications,
               collect(DISTINCT {id:succ.id, value:succ.value, status:succ.status}) AS successors""", keys=spec["keys"])]
    suspect = [dict(r) for r in s.run("""
        MATCH (d:Derived {suspect:true})-[:USED_ASSERTION]->(x:Assertion {status:'invalidated'})
        RETURN d.id AS id, d.kind AS kind, d.sha256 AS sha256, collect(x.id) AS used_invalidated""")]
    return {"task": task, "verdict": verdict, "why": why, "keys": keys, "conflicts": conflicts,
            "blocked_keys": blocked_keys, "below_verified": below, "flagged": flagged,
            "stale": stale, "suspect_derived": suspect}


def render_bundle(res: dict, policy: str) -> str:
    out = [f"GATE VERDICT: {res['verdict']} — {res['why']}", "", "POLICY:", policy, "",
           "REQUIRED KNOWLEDGE, key by key (status is the knowledge repository's, not yours to upgrade):"]
    for key, v in res["keys"].items():
        out.append(f"\n## {key}  level={v['level']}  flags={','.join(v['flags']) or '-'}")
        for g in v["declared_gaps"]:
            out.append(f"  DECLARED GAP {g['id']}: {g['text']}")
        if not v["assertions"]:
            out.append("  (no assertion in the repository: UNKNOWN — not a documented absence)")
        for a in v["assertions"]:
            out.append(f"  [{a['id']}] value={a['value']!r} basis={a['basis']} status={a['status']} source={a['artefact']} by={a['agent']}")
            out.append(f"      text: {a['text'][:300]}")
            for f in a["fragments"][:2]:
                out.append(f"      evidence: {f['artefact']} @ {f['locator']}: {f['text'][:200]!r}")
            for ver in a["verifications"]:
                out.append(f"      verification: {ver['method']} ({ver['scope']}) at {ver['at']}" + (f" VALID UNTIL {ver['valid_until']}" if ver['valid_until'] else ""))
            for ap in a["approvals"]:
                out.append(f"      approval: {ap['record']} at {ap['at']}")
            for g in a["gaps"]:
                out.append(f"      GAP {g['kind']}{' (declared)' if g['declared'] else ''}: {g['text']}")
    if res["conflicts"]:
        out.append("\nCONFLICTS:")
        for c in res["conflicts"]:
            out.append(f"  {c['id']}: {c['text']}")
    if res.get("stale"):
        out.append("\nINVALIDATED BY A SOURCE CHANGE (their verifications ended; a successor, if any, is listed with its own status):")
        for x in res["stale"]:
            succ = ", ".join(f"{t['id']} value={t['value']!r} status={t['status']}" for t in x["successors"] if t["id"]) or "none"
            vers = ", ".join(f"{v['id']} valid_until={v['valid_until']}" for v in x["verifications"] if v["id"]) or "none"
            out.append(f"  [{x['id']}] key={x['key']} old value={x['value']!r} invalidated_by={x['invalidated_by']}; verifications: {vers}; successor: {succ}")
    if res.get("suspect_derived"):
        out.append("\nDERIVED OUTPUTS MARKED SUSPECT (they used assertions that are now invalidated; they may not be reused as they are):")
        for d in res["suspect_derived"]:
            out.append(f"  {d['id']} ({d['kind']}, sha256 {d['sha256'][:12]}...) used: {', '.join(d['used_invalidated'])}")
    return "\n".join(out)

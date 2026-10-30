"""The seven rules of pre-registration §4, run after every load.

Each rule is one or more Cypher statements. R-CORROBORATE and
R-CONFLICT fetch candidate pairs with Cypher and decide value
compatibility in Python (``compatible``), because a behaviour value is
a ``k=v;k=v`` string and Cypher has no map-from-string function; the
writes are Cypher again. Status is set only here, by the loaders and by
recorded human acts.
"""

from __future__ import annotations

import re

from extract import NONE

VAGUE = ["around", "roughly", "approximately", "low forties", "mid-sixties",
         "clearly", "as soon as", "usable", "appropriate", "anything higher"]

# a declared gap on a requirement also concerns the key it governs
REQ_KEY = {"REQ-06": "QuoteAPI|on_screening_outage"}


def _fields(v: str) -> dict | None:
    if "=" in v and ";" in v or re.fullmatch(r"\w+=[^;]*", v):
        return dict(p.split("=", 1) for p in v.split(";") if "=" in p)
    return None


NUMERIC = {"min", "max", "threshold", "surcharge", "factor", "rounding"}


def _is_num(v: str) -> bool:
    try:
        float(v)
        return True
    except ValueError:
        return False


def compatible(a: str, b: str, predicate: str = "") -> str:
    """'equal' | 'conflict' | 'incomparable' for two values of one key.
    A numeric predicate with a non-numeric side (vague text, an
    unresolved symbol) is incomparable: R-VAGUE flags it, nothing
    corroborates or contradicts it."""
    if a == b:
        return "equal"
    if predicate in NUMERIC and not (_is_num(a) and _is_num(b)):
        return "incomparable"
    fa, fb = _fields(a), _fields(b)
    if fa is not None and fb is not None:
        shared = set(fa) & set(fb)
        if not shared:
            return "incomparable"
        if all(fa[k] == fb[k] for k in shared):
            return "equal" if len(shared) >= 2 else "incomparable"
        return "conflict"
    # numbers written differently (316.00 vs 316)
    try:
        return "equal" if float(a) == float(b) else "conflict"
    except ValueError:
        pass
    if a == NONE or b == NONE:
        return "conflict"
    return "conflict"


def r_struct(s) -> list[dict]:
    v = []
    for row in s.run("""
        MATCH (x:Assertion) WHERE x.basis IN ['extracted','authored'] AND NOT (x)-[:SUPPORTED_BY]->(:Fragment)
        RETURN x.id AS id, 'no supporting fragment' AS why"""):
        v.append(dict(row))
    for row in s.run("""
        MATCH (x:Assertion) WHERE x.basis IN ['inferred','assumed','hypothesised']
          AND NOT (x)-[:CANDIDATE_FOR|CONCERNED_BY]-(:Gap) AND NOT (:Gap)-[:CONCERNS]->(x)
        RETURN x.id AS id, 'inferred without a gap' AS why"""):
        v.append(dict(row))
    for row in s.run("MATCH (f:Fragment) WHERE NOT (:Version)-[:HAS_FRAGMENT]->(f) RETURN f.id AS id, 'orphan fragment' AS why"):
        v.append(dict(row))
    for row in s.run("MATCH (v:Version) WHERE NOT (:Artefact)-[:HAS_VERSION]->(v) RETURN v.id AS id, 'orphan version' AS why"):
        v.append(dict(row))
    return v


def _pairs(s):
    return list(s.run("""
        MATCH (a:Assertion)-[:ABOUT]->(e:Entity)<-[:ABOUT]-(b:Assertion)
        WHERE a.predicate = b.predicate AND a.id < b.id AND a.artefact <> b.artefact
          AND NOT a.status IN ['rejected','deprecated','invalidated'] AND NOT b.status IN ['rejected','deprecated','invalidated']
          AND a.version = b.version
        RETURN a.id AS a, a.value AS va, a.basis AS ba, b.id AS b, b.value AS vb, b.basis AS bb, a.key AS key,
               a.predicate AS pred"""))


def r_corroborate(s) -> int:
    n = 0
    for p in _pairs(s):
        if p["ba"] == "extracted" and p["bb"] == "extracted" and compatible(p["va"], p["vb"], p["pred"]) == "equal":
            s.run("""MATCH (a:Assertion {id:$a}), (b:Assertion {id:$b})
                     MERGE (a)-[:CORROBORATES]->(b) MERGE (b)-[:CORROBORATES]->(a)
                     SET a.status = CASE WHEN a.status='proposed' THEN 'validated' ELSE a.status END,
                         b.status = CASE WHEN b.status='proposed' THEN 'validated' ELSE b.status END""",
                  a=p["a"], b=p["b"]).consume()
            n += 1
    return n


def r_conflict(s, scenario: str) -> list[dict]:
    out = []
    for p in _pairs(s):
        if compatible(p["va"], p["vb"], p["pred"]) == "conflict":
            gid = f"gap:conflict:{p['key']}:{len(out)}"
            s.run("""MATCH (a:Assertion {id:$a}), (b:Assertion {id:$b})
                     MERGE (a)-[:CONTRADICTS]->(b) MERGE (b)-[:CONTRADICTS]->(a)
                     SET a.status='disputed', b.status='disputed'
                     MERGE (g:Gap {id:$gid}) SET g.kind='conflict', g.declared=false,
                        g.text='two artefacts state different values for ' + $key + ': ' + a.artefact + ' says ' + a.value + '; ' + b.artefact + ' says ' + b.value
                     MERGE (g)-[:CONCERNS]->(a) MERGE (g)-[:CONCERNS]->(b)
                     WITH g MATCH (act:Activity) WHERE act.id STARTS WITH 'act:extract:' + $sc
                     MERGE (g)-[:RAISED_BY]->(act)""",
                  a=p["a"], b=p["b"], gid=gid, key=p["key"], sc=scenario).consume()
            out.append({"key": p["key"], "a": p["a"], "va": p["va"], "b": p["b"], "vb": p["vb"]})
    return out


def r_vague(s, scenario: str) -> list[dict]:
    out = []
    for row in s.run("""
        MATCH (x:Assertion)-[:SUPPORTED_BY]->(f:Fragment)
        WHERE any(w IN $vague WHERE toLower(f.text) CONTAINS w) AND f.locator CONTAINS 'row/'
        RETURN DISTINCT x.id AS id, x.key AS key, f.id AS fid, f.text AS text""", vague=VAGUE):
        w = [v for v in VAGUE if v in row["text"].lower()]
        s.run("""MATCH (x:Assertion {id:$id})
                 MERGE (g:Gap {id:'gap:ambiguous:' + $id}) SET g.kind='ambiguous', g.declared=false,
                    g.text='vague wording (' + $w + ') in ' + $fid
                 MERGE (g)-[:CONCERNS]->(x)
                 WITH g MATCH (act:Activity) WHERE act.id STARTS WITH 'act:extract:' + $sc
                 MERGE (g)-[:RAISED_BY]->(act)""", id=row["id"], w=", ".join(w), fid=row["fid"], sc=scenario).consume()
        out.append({"id": row["id"], "key": row["key"], "words": w})
    for row in s.run("MATCH (x:Assertion {unresolved:true}) RETURN x.id AS id, x.key AS key, x.raw_value AS sym"):
        s.run("""MATCH (x:Assertion {id:$id})
                 MERGE (g:Gap {id:'gap:ambiguous:' + $id}) SET g.kind='ambiguous', g.declared=false,
                    g.text='symbol ' + $sym + ' has no definition in any artefact'
                 MERGE (g)-[:CONCERNS]->(x)
                 WITH g MATCH (act:Activity) WHERE act.id STARTS WITH 'act:extract:' + $sc
                 MERGE (g)-[:RAISED_BY]->(act)""", id=row["id"], sym=row["sym"], sc=scenario).consume()
        out.append({"id": row["id"], "key": row["key"], "words": [f"unresolved {row['sym']}"]})
    return out


def r_req(s, scenario: str) -> list[dict]:
    out = []
    # declared gaps: a requirement whose text says NOT YET SPECIFIED
    for row in s.run("MATCH (x:Assertion {predicate:'specified', value:'NONE'})-[:ABOUT]->(e:Entity) RETURN e.id AS req, x.id AS id"):
        key = REQ_KEY.get(row["req"])
        s.run("""MATCH (e:Entity {id:$req}), (x:Assertion {id:$id})
                 MERGE (g:Gap {id:'gap:declared:OD-1'}) SET g.kind='missing', g.declared=true,
                    g.text=$req + ' is NOT YET SPECIFIED (open decision OD-1, owner: compliance)'
                 MERGE (g)-[:CONCERNS]->(e) MERGE (g)-[:CONCERNS]->(x)
                 WITH g MATCH (act:Activity) WHERE act.id STARTS WITH 'act:extract:' + $sc
                 MERGE (g)-[:RAISED_BY]->(act)
                 WITH g MATCH (k:Entity {id:$kent}) MERGE (g)-[:CONCERNS_KEY {key:$key}]->(k)""",
              req=row["req"], id=row["id"], sc=scenario, kent=key.split("|")[0] if key else row["req"], key=key or "").consume()
        out.append({"kind": "missing", "declared": True, "req": row["req"], "key": key})
    # an artefact declared not yet authored
    for row in s.run("MATCH (x:Assertion {predicate:'authored', value:'NONE'})-[:ABOUT]->(e:Entity) RETURN e.id AS art, x.id AS id"):
        s.run("""MATCH (x:Assertion {id:$id})
                 MERGE (g:Gap {id:'gap:declared:' + $art}) SET g.kind='missing', g.declared=true, g.text=$art + ' is not yet authored'
                 MERGE (g)-[:CONCERNS]->(x)""", id=row["id"], art=row["art"]).consume()
        out.append({"kind": "missing", "declared": True, "artefact": row["art"]})
    # every requirement needs a verifying scenario
    for row in s.run("""MATCH (e:Entity {kind:'requirement'}) WHERE NOT (:Assertion {predicate:'verified_by'})-[:ABOUT]->(e)
                        RETURN e.id AS req"""):
        s.run("""MATCH (e:Entity {id:$req})
                 MERGE (g:Gap {id:'gap:unverified-req:' + $req}) SET g.kind='missing', g.declared=false,
                    g.text=$req + ' has no verifying scenario'
                 MERGE (g)-[:CONCERNS]->(e)""", req=row["req"]).consume()
        out.append({"kind": "missing", "declared": False, "req": row["req"], "why": "no verifying scenario"})
    # every DT-S row and DT-P step is spoken about
    for row in s.run("""MATCH (e:Entity) WHERE e.kind IN ['decision_row','pricing_step'] AND NOT (:Assertion)-[:ABOUT]->(e)
                        RETURN e.id AS id"""):
        out.append({"kind": "missing", "declared": False, "entity": row["id"]})
    return out


def r_unverified(s) -> int:
    return s.run("""
        MATCH (x:Assertion) WHERE x.status IN ['proposed','validated'] AND NOT (:Verification)-[:VERIFIES]->(x)
        MERGE (g:Gap {id:'gap:unverified:' + x.id}) SET g.kind='unverified', g.declared=false,
           g.text=x.id + ' has no verification record'
        MERGE (g)-[:CONCERNS]->(x)
        RETURN count(x) AS n""").single()["n"]


def r_stale(s, new_tag: str) -> dict:
    """After a re-ingestion: an assertion of an older version whose
    supporting fragment's digest differs from the current fragment at the
    same locator (or whose locator vanished) is invalidated; its
    verifications end; derived outputs that used it become suspect."""
    inv = list(s.run("""
        MATCH (x:Assertion)-[:SUPPORTED_BY]->(f:Fragment)<-[:HAS_FRAGMENT]-(old:Version)<-[:HAS_VERSION]-(a:Artefact)-[:CURRENT]->(cur:Version)
        WHERE old <> cur AND x.version <> $tag
        OPTIONAL MATCH (cur)-[:HAS_FRAGMENT]->(nf:Fragment {locator:f.locator})
        WITH x, f, nf WHERE nf IS NULL OR nf.sha256 <> f.sha256
        SET x.status='invalidated', x.invalidated_at=datetime().epochSeconds, x.invalidated_by=$tag
        WITH DISTINCT x
        OPTIONAL MATCH (v:Verification)-[:VERIFIES]->(x) SET v.valid_until=$tag
        WITH DISTINCT x
        OPTIONAL MATCH (d:Derived)-[:USED_ASSERTION]->(x) SET d.suspect=true
        RETURN x.id AS id, x.key AS key, collect(DISTINCT d.id) AS derived""", tag=new_tag))
    kept = list(s.run("""
        MATCH (x:Assertion)-[:SUPPORTED_BY]->(f:Fragment)<-[:HAS_FRAGMENT]-(old:Version)<-[:HAS_VERSION]-(a:Artefact)-[:CURRENT]->(cur:Version)
        WHERE old <> cur AND x.version <> $tag AND x.status <> 'invalidated'
        RETURN DISTINCT x.id AS id, x.key AS key, x.status AS status""", tag=new_tag))
    return {"invalidated": [dict(r) for r in inv], "kept": [dict(r) for r in kept]}


def run_all(s, scenario: str) -> dict:
    out = {"R-STRUCT": r_struct(s)}
    out["R-CORROBORATE"] = r_corroborate(s)
    out["R-CONFLICT"] = r_conflict(s, scenario)
    out["R-VAGUE"] = r_vague(s, scenario)
    out["R-REQ"] = r_req(s, scenario)
    out["R-UNVERIFIED"] = r_unverified(s)
    return out


def census(s) -> dict:
    st = {r["status"]: r["n"] for r in s.run("MATCH (x:Assertion) RETURN x.status AS status, count(*) AS n")}
    gaps = {r["kind"]: r["n"] for r in s.run("MATCH (g:Gap) RETURN g.kind AS kind, count(*) AS n")}
    contradicts = s.run("MATCH ()-[r:CONTRADICTS]->() RETURN count(r)/2 AS n").single()["n"]
    nodes = s.run("MATCH (n) RETURN count(n) AS n").single()["n"]
    rels = s.run("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"]
    return {"assertions_by_status": st, "gaps_by_kind": gaps, "contradicts": contradicts,
            "nodes": nodes, "relationships": rels}

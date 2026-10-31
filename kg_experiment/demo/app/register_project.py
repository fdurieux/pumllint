"""The register projected into the demo's Neo4j, in its own namespace, at the vendored tag.

Derived, rebuilt on demand, never the record (docs/ieam-register-demo-integration.md §3.5).
The harness's labels (Artefact, Version, Fragment, Entity, Assertion, Activity, Agent,
Verification, Approval, Gap, Derived) stay untouched: every projected node carries the label
Register plus one of RegNode, RegLink, RegType, RegException, RegDocument, RegExternal, and
every relationship is REG_<NAME>. Every node and relationship carries the tag, the commit,
the export date, the digest of the TOML file it came from and the load time. A deterministic
run wipes the whole store ("first deletes everything in the store"), so the projection
vanishes with it and is loaded again on demand; loading deletes only the Register namespace.
The loader derives nothing: no inferred edge, no coverage verdict; those stay the checker's.
"""
from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path

import register_view

REGISTER = register_view.REGISTER
MANIFEST = REGISTER / "exports" / "kit" / "2026-10-30" / "MANIFEST.toml"
NODE_LABELS = ("RegNode", "RegLink", "RegType", "RegException", "RegDocument", "RegExternal")


def _iso(v) -> str:
    return v.isoformat() if hasattr(v, "isoformat") else ("" if v is None else str(v))


def _digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _approval(a: dict | None) -> dict:
    a = a or {}
    return {"approval_by": a.get("by", ""), "approval_on": _iso(a.get("on")), "approval_record": a.get("record", "")}


def _doc_key(anchor: str, files: dict) -> str | None:
    """The manifest key a kit evidence anchor names: kit:requirements.md#REQ-05 is the manifest's
    kit/requirements.md, kit:contract/decision_table.md#DT-P its contract/decision_table.md."""
    a = anchor[4:] if anchor.startswith("kit:") else anchor
    a = a.split("#", 1)[0]
    for key in (a, "kit/" + a):
        if key in files:
            return key
    return None


def rows(loaded_at: str | None = None) -> dict:
    """Every node and relationship row of the projection, as flat property maps (strings, numbers,
    booleans and lists of strings only: what a Neo4j property can hold), with the counts."""
    T = register_view._load_tools()
    reg = T["register"].load_register(REGISTER)
    src = register_view.source_info()
    manifest = T["register"].load_toml(MANIFEST)
    files = manifest.get("files", {})
    stamp = {"tag": src["tag"], "commit": src["commit"], "export_date": _iso(manifest.get("exported_on"))[:10],
             "loaded_at": loaded_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    nodes, parents, owners = [], [], []
    for nid, n in reg["nodes"].items():
        nodes.append({"reg_id": nid, "taxonomy": n["_taxonomy"], "kind": n.get("kind", ""), "name": n.get("name", ""),
                      "state": n.get("state", ""), "owner": n.get("owner", ""), "parent": n.get("parent", ""),
                      "review_due": _iso(n.get("review_due")), **_approval(n.get("approval")), "digest": _digest(n["_path"]), **stamp})
        if n.get("parent"):
            parents.append({"child": nid, "parent": n["parent"]})
        if n.get("owner") in reg["nodes"]:
            owners.append({"owner": n["owner"], "node": nid})
    types, links, typed, maps_to, link_of, of_type, cites = [], [], {}, [], [], [], []
    externals: dict[str, dict] = {}
    for rname, rel in reg["relationships"].items():
        t = rel["type"]
        types.append({"reg_id": rname, "source_kind": list(t.get("source_kind", [])), "target_kind": list(t.get("target_kind", [])),
                      "direction": t.get("direction", ""), "inverse_label": t.get("inverse_label", ""), "owner": t.get("owner", ""),
                      "evidence_class": t.get("evidence_class", ""), "aris_status": t.get("aris_status", ""), "archi_status": t.get("archi_status", ""),
                      "note": t.get("note", ""), "digest": _digest(rel["_path"]), **stamp})
        for ln in rel["links"]:
            props = {"reg_id": ln["id"], "type": rname, "state": ln.get("state", ""), "owner": ln.get("owner", ""),
                     "mode": ",".join(ln.get("mode", [])), **_approval(ln.get("approval")), "derived": False, "rule": "", **stamp}
            links.append({**props, "source": ln["source"], "target": ln.get("target", ""), "target_external": ln.get("target_external", ""),
                          "rationale": ln.get("rationale", ""), "evidence": list(ln.get("evidence", [])), "review_due": _iso(ln.get("review_due")),
                          "digest": _digest(rel["_path"])})
            link_of.append({"reg_id": ln["id"], "node": ln["source"], "role": "source"})
            of_type.append({"reg_id": ln["id"], "type": rname})
            if ln.get("target"):
                typed.setdefault("REG_" + rname.upper(), []).append({"source": ln["source"], "target": ln["target"], "props": props})
                link_of.append({"reg_id": ln["id"], "node": ln["target"], "role": "target"})
            else:
                ext = ln.get("target_external", "")
                externals.setdefault(ext, {"reg_id": ext, "path": _doc_key(ext, files) or "", "digest": files.get(_doc_key(ext, files) or "", ""), **stamp})
                maps_to.append({"source": ln["source"], "external": ext, "props": props})
            for ev in ln.get("evidence", []):
                key = _doc_key(ev, files) if ev.startswith("kit:") else None
                if key:
                    cites.append({"reg_id": ln["id"], "path": key, "anchor": ev})
    documents = [{"reg_id": key, "path": key, "digest": sha, **stamp} for key, sha in files.items()]
    exceptions, excepts = [], []
    for e in reg["exceptions"]:
        a = e.get("approved") or {}
        exceptions.append({"reg_id": e["id"], "rule": e.get("rule", ""), "scope": list(e.get("scope", [])), "rationale": e.get("rationale", ""),
                           "expires": _iso(e.get("expires")), "approval_by": a.get("by", ""), "approval_on": _iso(a.get("on")),
                           "approval_record": a.get("record", ""), "digest": _digest(e["_path"]), **stamp})
        for nid in e.get("scope", []):
            excepts.append({"reg_id": e["id"], "node": nid, "rule": e.get("rule", ""), "expires": _iso(e.get("expires"))})
    out = {"stamp": stamp, "nodes": nodes, "types": types, "links": links, "documents": documents, "externals": list(externals.values()),
           "exceptions": exceptions, "parents": parents, "owners": owners, "typed": typed, "maps_to": maps_to, "link_of": link_of,
           "of_type": of_type, "cites": cites, "excepts": excepts}
    out["counts"] = {"nodes": len(nodes), "links": len(links), "types": len(types), "documents": len(documents), "externals": len(externals),
                     "exceptions": len(exceptions),
                     "relationships": sum(len(v) for v in typed.values()) + len(maps_to) + len(link_of) + len(of_type) + len(cites)
                     + len(parents) + len(owners) + len(excepts)}
    return out


def statements(r: dict) -> list[tuple[str, dict]]:
    """The load, in order: wipe the namespace, create the nodes, then the relationships. Only
    Register-labelled nodes are touched; the harness's own graph is never read or written."""
    st: list[tuple[str, dict]] = [("MATCH (n:Register) DETACH DELETE n", {})]
    for label, key in (("RegNode", "nodes"), ("RegType", "types"), ("RegDocument", "documents"), ("RegExternal", "externals"),
                       ("RegLink", "links"), ("RegException", "exceptions")):
        st.append((f"UNWIND $rows AS r CREATE (n:Register:{label}) SET n = r", {"rows": r[key]}))
    st.append(("UNWIND $rows AS r MATCH (c:RegNode {reg_id:r.child}), (p:RegNode {reg_id:r.parent}) CREATE (c)-[:REG_PARENT]->(p)", {"rows": r["parents"]}))
    st.append(("UNWIND $rows AS r MATCH (o:RegNode {reg_id:r.owner}), (n:RegNode {reg_id:r.node}) CREATE (o)-[:REG_OWNS]->(n)", {"rows": r["owners"]}))
    for rtype, items in sorted(r["typed"].items()):
        st.append((f"UNWIND $rows AS r MATCH (s:RegNode {{reg_id:r.source}}), (t:RegNode {{reg_id:r.target}}) CREATE (s)-[e:{rtype}]->(t) SET e = r.props", {"rows": items}))
    st.append(("UNWIND $rows AS r MATCH (s:RegNode {reg_id:r.source}), (x:RegExternal {reg_id:r.external}) CREATE (s)-[e:REG_MAPS_TO]->(x) SET e = r.props", {"rows": r["maps_to"]}))
    st.append(("UNWIND $rows AS r MATCH (l:RegLink {reg_id:r.reg_id}), (n:RegNode {reg_id:r.node}) CREATE (l)-[:REG_LINK_OF {role:r.role}]->(n)", {"rows": r["link_of"]}))
    st.append(("UNWIND $rows AS r MATCH (l:RegLink {reg_id:r.reg_id}), (t:RegType {reg_id:r.type}) CREATE (l)-[:REG_OF_TYPE]->(t)", {"rows": r["of_type"]}))
    st.append(("UNWIND $rows AS r MATCH (l:RegLink {reg_id:r.reg_id}), (d:RegDocument {reg_id:r.path}) CREATE (l)-[:REG_CITES {anchor:r.anchor}]->(d)", {"rows": r["cites"]}))
    st.append(("UNWIND $rows AS r MATCH (e:RegException {reg_id:r.reg_id}), (n:RegNode {reg_id:r.node}) CREATE (e)-[:REG_EXCEPTS {rule:r.rule, expires:r.expires}]->(n)", {"rows": r["excepts"]}))
    return st


def census(session) -> dict | None:
    """What the store holds of the register, or None when nothing is projected."""
    n = session.run("MATCH (n:Register) RETURN count(n) AS n").single()["n"]
    if not n:
        return None
    by_label = {rec["l"]: rec["n"] for rec in session.run(
        "MATCH (n:Register) UNWIND labels(n) AS l WITH l, count(*) AS n WHERE l <> 'Register' RETURN l, n")}
    rels = session.run("MATCH (:Register)-[r]->() RETURN count(r) AS n").single()["n"]
    stamp = session.run("MATCH (n:RegNode) RETURN n.tag AS tag, n.commit AS commit, n.loaded_at AS loaded_at LIMIT 1").single()
    return {"tag": stamp["tag"] if stamp else "", "commit": stamp["commit"] if stamp else "", "loaded_at": stamp["loaded_at"] if stamp else "",
            "nodes": by_label.get("RegNode", 0), "links": by_label.get("RegLink", 0), "by_label": by_label, "relationships": rels, "total": n}


def project(uri: str, password: str) -> dict:
    """Load the projection into the store at uri and return its census. Raises on an unreachable
    store or a missing driver; the caller turns that into a status code."""
    from neo4j import GraphDatabase, NotificationMinimumSeverity  # the harness's dependency, in the image

    r = rows()
    with GraphDatabase.driver(uri, auth=("neo4j", password), notifications_min_severity=NotificationMinimumSeverity.OFF,
                              connection_timeout=3) as d:
        with d.session() as s:
            for cypher, params in statements(r):
                s.run(cypher, **params).consume()
            out = census(s)
    out["counts"] = r["counts"]
    return out

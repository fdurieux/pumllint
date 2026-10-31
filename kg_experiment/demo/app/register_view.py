"""The register view: what the demo shows of the vendored IEAM register
(``kg_experiment/demo/register/``, a byte-for-byte copy of fdurieux/ieam-register
at the commit its SOURCE.md names).

The register's TOML at that commit is the record of identities, links, states,
approvals and exceptions; SOURCE.md and its digests are the record of which bytes
the demo carries; the register's own checker, run on those bytes at the pinned
date, is the record of findings and coverage. This module reads all three and
arranges them for the page. It never writes to the register, never rewords a
name, a rationale or a finding (those are data), and adds no field the TOML
lacks. Standard library only; the register's tools are imported from the copy.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import re
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REGISTER = HERE.parent / "register"

sys.path.insert(0, str(HERE))
import views  # noqa: E402  (the controlled-English registry and glossary live there)

_tools: dict | None = None


def _load_tools() -> dict:
    """Import the vendored register tools once, from the copy, by path."""
    global _tools
    if _tools is None:
        tools = REGISTER / "tools"
        if str(tools) not in sys.path:
            sys.path.insert(0, str(tools))
        mods = {}
        for name in ("register", "check_register", "impact"):
            spec = importlib.util.spec_from_file_location(name, tools / f"{name}.py")
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
            mods[name] = mod
        _tools = mods
    return _tools


def source_info() -> dict:
    """SOURCE.md's table, and whether every vendored file still matches its digest."""
    note = (REGISTER / "SOURCE.md").read_text(encoding="utf-8")
    def cell(label: str) -> str:
        m = re.search(r"^\| " + re.escape(label) + r" \| (.+?) \|$", note, re.M)
        return m.group(1) if m else ""
    commit = re.search(r"\| commit \| `([0-9a-f]{40})`", note)
    pinned = re.search(r"pinned date for the checker \| `(\d{4}-\d{2}-\d{2})`", note)
    listed = dict(re.findall(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$", note, re.M))
    files = [p for p in REGISTER.rglob("*") if p.is_file() and p.name != "SOURCE.md" and "__pycache__" not in p.parts]
    actual = {p.relative_to(REGISTER).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    mismatched = sorted(k for k in set(listed) | set(actual) if listed.get(k) != actual.get(k))
    return {"repo": "fdurieux/ieam-register", "commit": commit.group(1) if commit else "",
            "commit_short": commit.group(1)[:7] if commit else "", "copied": cell("copied").split(",")[0],
            "pinned_date": pinned.group(1) if pinned else "", "files": len(actual),
            "digest_ok": not mismatched, "mismatched": mismatched}


def _coverage_lines(summary: dict) -> list[str]:
    """The checker's own coverage print format, verbatim: data, not prose."""
    return [f"{rule}: {s['covered']}/{s['denominator']} covered, {s['excepted']} excepted, {len(s['uncovered'])} uncovered"
            + (f" ({', '.join(s['uncovered'])})" if s["uncovered"] else "")
            for rule, s in ((r, summary[r]) for r in ("C1", "C2", "C3"))]


def _node_panel(nid: str, n: dict, reg: dict, C, D) -> dict:
    tax = n["_taxonomy"]
    kind_words = n.get("kind", "").replace("_", " ")
    intro = C(f"State {n.get('state')}, owner {n.get('owner')}.") + " " + D(f"Name: {n.get('name')}.")
    if n.get("parent"):
        intro += " " + D(f"Parent: {n['parent']}.")
    secs = []
    appr = n.get("approval")
    if appr:
        secs.append({"heading": C("Approval"), "text": D(f"By {appr.get('by')} on {appr.get('on')}, record {appr.get('record')}; review due {n.get('review_due')}.")})
    else:
        secs.append({"heading": C("Approval"), "text": C("No approval is recorded, so the node is not approved.")})
    src = n.get("source") or {}
    if src:
        secs.append({"heading": C("Source of record"), "text": C("The register points at the system that authors the content; it copies nothing but the name."),
                     "table": {"cols": ["field", "value"], "rows": [[k, str(v)] for k, v in src.items()]}})
    outs, ins = [], []
    for rname, rel in reg["relationships"].items():
        for ln in rel["links"]:
            if ln.get("source") == nid:
                outs.append([rname, ln.get("target") or ln.get("target_external", ""), ln.get("state", ""), ln.get("owner", ""), ln.get("rationale", "")])
            if ln.get("target") == nid:
                ins.append([rname, ln["source"], ln.get("state", ""), ln.get("owner", ""), ln.get("rationale", "")])
    secs.append({"heading": C(f"Links out: {len(outs)}"), "table": {"cols": ["relationship type", "target", "state", "owner", "rationale"], "rows": outs}})
    secs.append({"heading": C(f"Links in: {len(ins)}"), "table": {"cols": ["relationship type", "source", "state", "owner", "rationale"], "rows": ins}})
    return {"id": nid, "taxonomy": tax, "kind": n.get("kind"), "name": n.get("name"), "state": n.get("state"), "owner": n.get("owner"),
            "parent": n.get("parent"), "links_out": len(outs), "links_in": len(ins),
            "panel": {"title": C(f"{nid}, a {kind_words} in {tax}"), "intro": intro, "sections": secs}}


def impact(start: str) -> dict | None:
    """The register's own impact walk from one node (tools/impact.py, vendored), each edge
    with its state, owner and evidence, and what it reached. None for an unknown id. The walk
    follows links only and does not climb a node's parent: that is the register tool's
    behaviour, shown as it is."""
    T = _load_tools()
    reg = T["register"].load_register(REGISTER)
    if start not in reg["nodes"]:
        return None
    edges = T["impact"].walk(reg, start)
    reg_sentences: list[dict] = []
    C = lambda *s: views._reg(reg_sentences, "controlled", *s)  # noqa: E731
    D = lambda *s: views._reg(reg_sentences, "data", *s)  # noqa: E731
    names = {nid: n.get("name", "") for nid, n in reg["nodes"].items()}
    rows = [[e["from"], e["rel"], e["to"], names.get(e["to"], ""), reg["nodes"].get(e["to"], {}).get("state", ""), e["state"], e["owner"], ", ".join(e["evidence"])] for e in edges]
    reached = sorted({e["to"] for e in edges})
    by_prefix = lambda p: [x for x in reached if x.startswith(p + "-")]  # noqa: E731
    products, journeys, processes = by_prefix("PRD"), by_prefix("JRN"), by_prefix("PROC")
    start_node = reg["nodes"][start]
    intro = C(f"The walk starts at {start}, a {start_node.get('kind', '').replace('_', ' ')} in state {start_node.get('state')}.",
              "It follows links from applications to processes, from processes to products and journey steps.",
              "It stops at a deprecated or retired node.", "It does not climb a node's parent, so a module's application is not reached.")
    intro += " " + D(f"Name: {names.get(start, '')}.")
    summary = C(f"{views._plural(len(edges), 'edge')} walked; {views._plural(len(processes), 'process', 'processes')}, "
                f"{views._plural(len(products), 'product')} and {views._plural(len(journeys), 'journey element')} reached.")
    if not products and (processes or journeys):
        summary += " " + C("No product is reached: no delivers link starts at a reached process.")
    if not edges:
        summary += " " + C("No link starts at this node in a direction the walk follows.")
    return {"from": start, "edges": edges, "rows": rows, "reached": {"products": products, "journeys": journeys, "processes": processes, "all": reached},
            "panel": {"title": C(f"Impact of retiring {start}"), "intro": intro,
                      "sections": [{"heading": C("Edges walked"), "text": summary,
                                    "table": {"cols": ["from", "relationship", "to", "name", "node state", "link state", "owner", "evidence"], "rows": rows}},
                                   {"heading": C("Reached"), "list": [f"{x}: {names.get(x, '')}" for x in reached] or ["nothing"]}]},
            "text_registry": reg_sentences}


MAP = HERE / "register_map.toml"
REQ_ANCHOR = "kit:requirements.md#"
TABLE_PATH = "contract/decision_table.md"


def load_map() -> dict:
    with MAP.open("rb") as f:
        return tomllib.load(f)


def footprint(view: dict) -> dict:
    """The register footprint of one scenario: the map rows its keys below approved hit and the
    nodes they touch, the requirement gaps joined to the links whose evidence cites them, and
    for S6 the links whose evidence cites the changed decision table. Read from the scenario's
    deterministic.json (view["source_dir"]), the approved map and the vendored register."""
    T = _load_tools()
    reg = T["register"].load_register(REGISTER)
    m = load_map()
    det = json.loads((Path(view["source_dir"]) / "deterministic.json").read_text(encoding="utf-8"))
    rows = {r["key"]: r for r in m["row"]}
    names = {nid: n.get("name", "") for nid, n in reg["nodes"].items()}
    states = {nid: n.get("state", "") for nid, n in reg["nodes"].items()}
    links = [dict(ln, type=rname) for rname, rel in reg["relationships"].items() for ln in rel["links"]]
    reg_sentences: list[dict] = []
    C = lambda *s: views._reg(reg_sentences, "controlled", *s)  # noqa: E731
    D = lambda *s: views._reg(reg_sentences, "data", *s)  # noqa: E731
    # keys below approved, and the nodes their rows name
    below = {k: v["level"] for k, v in det["gate_keys"].items() if v["level"] != "approved"}
    blocked = set(det["D6_gate"].get("blocked_keys") or [])
    key_rows = [(k, lvl, rows[k]) for k, lvl in below.items() if k in rows]
    touched: dict[str, list[str]] = {}
    for k, _lvl, r in key_rows:
        for nid in r["nodes"]:
            touched.setdefault(nid, []).append(k)
    not_approved = sorted(nid for nid in touched if states.get(nid) != "approved")
    # requirement gaps joined to the links that cite them
    req_rows = []
    uncited = 0
    for h in det["rules"]["R-REQ"]:
        subject = h.get("req") or h.get("artefact") or h.get("entity") or ""
        anchor = REQ_ANCHOR + subject if h.get("req") else "kit:" + subject
        citing = [ln for ln in links if any(ev == anchor or ev.startswith(anchor + "#") for ev in ln.get("evidence", []))] if h.get("req") else []
        if not citing:
            uncited += 1
        req_rows.append((subject, h.get("kind", ""), "yes" if h.get("declared") else "no", ", ".join(f"{ln['id']} ({ln['type']}, {ln.get('state')})" for ln in citing) or "none"))
    # S6: the changed decision table and the links that cite it
    table_links = []
    if "stage2" in det:
        for ln in links:
            evs = [ev for ev in ln.get("evidence", []) if TABLE_PATH in ev] + ([ln["target_external"]] if TABLE_PATH in (ln.get("target_external") or "") else [])
            if evs:
                table_links.append((ln["id"], ln["type"], ln["source"], ln.get("target") or ln.get("target_external", ""), ln.get("state", ""), ", ".join(evs)))
    manifest = T["register"].load_toml(REGISTER / "exports" / "kit" / "2026-10-30" / "MANIFEST.toml")
    table_digest = manifest.get("files", {}).get(TABLE_PATH, "")
    colour = "bad" if not_approved or uncited else "warn" if key_rows or table_links else "ok"
    lines = [f"{views._plural(len(key_rows), 'key')} below approved {'touches' if len(key_rows) == 1 else 'touch'} {views._plural(len(touched), 'node')}" if key_rows else "no key below approved",
             f"{views._plural(len(req_rows), 'requirement gap')}, {uncited} cited by no link"]
    if table_links:
        lines.append(f"{views._plural(len(table_links), 'link cites', 'links cite')} the changed table")
    if not_approved:
        lines.append(f"{views._plural(len(not_approved), 'touched node')} not approved: {', '.join(not_approved)}")
    approved_on = str(m["map"].get("approved_on", ""))
    intro = C(f"The footprint is the demo's reading of the gate's keys onto the register, approved by the maintainer on {approved_on}.",
              "A key below approved touches the nodes its map row names.",
              "A requirement gap is joined to the links whose evidence cites it.",
              "Nothing here is written back to the register.")
    secs = []
    if key_rows:
        secs.append({"heading": C(f"Keys below approved: {len(key_rows)}"),
                     "text": C(f"They touch {views._plural(len(touched), 'node')}, {len(not_approved)} of them not approved.") + (" " + C("A blocked key is marked.") if blocked else ""),
                     "table": {"cols": ["key", "level", "blocked", "nodes", "anchor"], "rows": [[k, lvl, "yes" if k in blocked else "", ", ".join(r["nodes"]), r["anchor"]] for k, lvl, r in key_rows]}})
        secs.append({"heading": C("Nodes touched"), "text": C("Each node with its state and the keys that touch it."),
                     "table": {"cols": ["node", "name", "state", "keys"], "rows": [[nid, names.get(nid, ""), states.get(nid, ""), ", ".join(ks)] for nid, ks in sorted(touched.items())]}})
    else:
        secs.append({"heading": C("Keys below approved: none"), "text": C("Every key the task needs is approved, so no map row is hit.")})
    secs.append({"heading": C(f"Requirement gaps and the links that cite them: {len(req_rows)}"),
                 "text": C(f"{len(req_rows) - uncited} {'is' if len(req_rows) - uncited == 1 else 'are'} cited by a link, {uncited} by none.") + (" " + C("A gap no link cites is one the register does not yet carry.") if uncited else ""),
                 "table": {"cols": ["requirement or document", "kind", "declared", "links citing it"], "rows": [list(r) for r in req_rows]}})
    if "stage2" in det:
        secs.append({"heading": C(f"Links citing the changed decision table: {len(table_links)}"),
                     "text": C("The table changed in the second stage, so every link that cites it is a link to review.") + " "
                             + D(f"The manifest digest of {TABLE_PATH} at the register's commit is {table_digest[:12]}; the result file records the second load ({det['stage2']['load_v2']['fragments']} new fragments, {det['stage2']['load_v2']['fragments_reused']} reused) and no document digest."),
                     "table": {"cols": ["link", "type", "source", "target", "state", "evidence"], "rows": [list(r) for r in table_links]}})
    return {"scenario": view["scenario"], "map": {"status": m["map"].get("status"), "approved_by": m["map"].get("approved_by"), "approved_on": approved_on, "rows": len(m["row"])},
            "keys_below": {k: lvl for k, lvl, _ in key_rows}, "touched": touched, "not_approved": not_approved,
            "requirements": [{"subject": r[0], "kind": r[1], "declared": r[2], "cited_by": r[3]} for r in req_rows], "uncited": uncited,
            "table_links": [r[0] for r in table_links],
            "box": {"id": "footprint", "label": "register footprint", "colour": colour, "lines": lines + ["click for the nodes and links"]},
            "panel": {"title": C(f"Register footprint of {view['scenario']}"), "intro": intro, "sections": secs},
            "text_registry": reg_sentences}


def build(today: str | None = None) -> dict:
    """The view model. ``today`` is None for the pinned date, "wall" for the wall clock,
    or an ISO date; the result says which run it is."""
    T = _load_tools()
    reg = T["register"].load_register(REGISTER)
    src = source_info()
    pinned = dt.date.fromisoformat(src["pinned_date"])
    run_date = dt.date.today() if today == "wall" else dt.date.fromisoformat(today) if today else pinned
    findings, summary = T["check_register"].run(REGISTER, today=run_date)
    reg_sentences: list[dict] = []
    C = lambda *s: views._reg(reg_sentences, "controlled", *s)  # noqa: E731
    D = lambda *s: views._reg(reg_sentences, "data", *s)  # noqa: E731
    errors = [f for f in findings.items if f["level"] == "error"]
    warnings = [f for f in findings.items if f["level"] == "warning"]
    intro = C("The register is a copy of one commit of fdurieux/ieam-register, read only.",
              "Its TOML is the record of identities, links, states, approvals and exceptions.",
              "A node is one record of one taxonomy.", "A link is one typed relationship between two nodes.",
              f"The checker ran at the pinned date, {run_date.isoformat()}." if today is None
              else f"The checker ran at today's date, {run_date.isoformat()}, which is the pinned date." if run_date == pinned
              else f"The checker ran at the wall-clock date, {run_date.isoformat()}, not the pinned date.",
              "The coverage lines are its own output, shown as data.")
    health = (C(f"The checker reports no errors and {len(warnings)} advisory warnings.") if not errors
              else C(f"The checker reports {len(errors)} errors and {len(warnings)} warnings."))
    nodes = [_node_panel(nid, n, reg, C, D) for nid, n in reg["nodes"].items()]
    by_tax: dict[str, list] = {}
    for n in nodes:
        by_tax.setdefault(n["taxonomy"], []).append(n)
    links = []
    for rname, rel in reg["relationships"].items():
        for ln in rel["links"]:
            links.append({"id": ln.get("id"), "type": rname, "source": ln.get("source"), "target": ln.get("target") or ln.get("target_external"),
                          "state": ln.get("state"), "owner": ln.get("owner"), "rationale": ln.get("rationale"), "evidence": ln.get("evidence", [])})
    rel_types = [{"name": rname, "aris_status": rel["type"].get("aris_status"), "archi_status": rel["type"].get("archi_status"),
                  "links": len(rel["links"]), "approved": sum(1 for ln in rel["links"] if ln.get("state") == "approved")}
                 for rname, rel in reg["relationships"].items()]
    exceptions = []
    for e in reg["exceptions"]:
        exceptions.append({"id": e.get("id"), "rule": e.get("rule"), "scope": e.get("scope", []), "expires": str(e.get("expires")),
                           "rationale": e.get("rationale"), "approved": {k: str(v) for k, v in (e.get("approved") or {}).items()},
                           "sentence": C(f"Exception {e.get('id')} excuses {', '.join(e.get('scope', []))} from rule {e.get('rule')} until {e.get('expires')}.")})
    matrix = T["register"].load_toml(REGISTER / "mapping" / "matrix.toml")
    mrows = matrix.get("node_kind", []) + matrix.get("relationship_type", [])
    unverified = sum(1 for r in mrows if r.get("status") == "unverified")
    matrix_sentence = (C(f"The mapping matrix has {len(mrows)} rows, and every row is unverified.") if unverified == len(mrows)
                       else C(f"The mapping matrix has {len(mrows)} rows, {unverified} of them unverified."))
    glossary = [{"term": t["term"], "meaning": t["meaning"], "forbidden": t.get("forbidden", [])} for t in reg["glossary"].get("term", [])]
    return {"source": src, "run_date": run_date.isoformat(), "pinned": today is None, "pinned_date": pinned.isoformat(),
            "summary": {"nodes": summary["nodes"], "links": summary["links"], "errors": len(errors), "warnings": len(warnings)},
            "coverage": {r: summary[r] for r in ("C1", "C2", "C3")}, "coverage_lines": _coverage_lines(summary),
            "findings": findings.items, "intro": intro, "health": health,
            "nodes_by_taxonomy": by_tax, "links": links, "relationship_types": rel_types,
            "exceptions": exceptions, "matrix": {"rows": len(mrows), "unverified": unverified, "sentence": matrix_sentence},
            "glossary": glossary, "text_registry": reg_sentences}

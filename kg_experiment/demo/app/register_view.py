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
    tag = re.search(r"^\| tag \| `(v[0-9][^`]*)`", note, re.M)
    pinned = re.search(r"pinned date for the checker \| `(\d{4}-\d{2}-\d{2})`", note)
    listed = dict(re.findall(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$", note, re.M))
    files = [p for p in REGISTER.rglob("*") if p.is_file() and p.name != "SOURCE.md" and "__pycache__" not in p.parts]
    actual = {p.relative_to(REGISTER).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    mismatched = sorted(k for k in set(listed) | set(actual) if listed.get(k) != actual.get(k))
    return {"repo": "fdurieux/ieam-register", "commit": commit.group(1) if commit else "",
            "commit_short": commit.group(1)[:7] if commit else "", "tag": tag.group(1) if tag else "",
            "copied": cell("copied").split(",")[0],
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
                outs.append([R("link", ln["id"]), rname, _target_ref(ln), ln.get("state", ""), ln.get("owner", ""), ln.get("rationale", "")])
            if ln.get("target") == nid:
                ins.append([R("link", ln["id"]), rname, R("node", ln["source"]), ln.get("state", ""), ln.get("owner", ""), ln.get("rationale", "")])
    secs.append({"heading": C(f"Links out: {len(outs)}"), "table": {"cols": ["link", "relationship type", "target", "state", "owner", "rationale"], "rows": outs}})
    secs.append({"heading": C(f"Links in: {len(ins)}"), "table": {"cols": ["link", "relationship type", "source", "state", "owner", "rationale"], "rows": ins}})
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


# ------------------------------------------------------------ references: what a cell opens

REQUIREMENTS = HERE.parent.parent / "kit" / "requirements.md"
REF_KINDS = ("node", "link", "req", "key", "doc")
LEVEL_TIP = {
    "approved": "Verified and approved by the owner; the gate may build on it.",
    "validated": "Two documents agree and nobody has verified it; the gate counts it below approved.",
    "proposed": "One document states it and nobody has verified it.",
    "declared_gap": "The documents themselves say this knowledge is not there yet.",
    "absent": "No document states it at all.",
    "disputed": "Two documents give different values; the gate blocks the key.",
}
DECLARED_TIP = {"yes": "The authors declared the gap themselves.", "no": "The rules found the gap; nobody had declared it."}


def R(kind: str, ident: str, text: str | None = None) -> dict:
    """A reference cell: the page renders it as a click that opens the subject's panel under the table."""
    return {"ref": f"{kind}:{ident}", "text": text or ident}


def _tip(text: str, tip: str) -> dict:
    return {"text": text, "tip": tip}


def _join(parts: list, sep: str = ", ") -> list | str:
    out: list = []
    for i, p in enumerate(parts):
        if i:
            out.append(sep)
        out.append(p)
    return out or ""


def _norm(anchor: str) -> str:
    """One spelling for a kit anchor: the register writes kit:requirements.md#REQ-05, the map
    kit/requirements.md#REQ-05 and contract/decision_table.md#DT-V; all become kit-relative paths."""
    a = anchor[4:] if anchor.startswith("kit:") else anchor
    return a[4:] if a.startswith("kit/") else a


def _anchor_ref(anchor: str) -> dict:
    """A kit anchor opens the requirement panel when it names a requirement, else the document card."""
    a = _norm(anchor)
    if a.startswith("requirements.md#REQ-"):
        return R("req", a.split("#", 1)[1], anchor)
    return R("doc", a.split("#", 1)[0], anchor)


def _target_ref(ln: dict) -> dict:
    return R("node", ln["target"]) if ln.get("target") else _anchor_ref(ln.get("target_external", ""))


def _kind_tip(kind: str, declared: bool) -> str:
    if kind == "missing":
        return views.GAP_KIND_TEXT["declared missing" if declared else "undeclared missing"][0]
    return views.GAP_KIND_TEXT.get(kind, [""])[0]


def _state_tip(state: str, lifecycle: dict) -> str:
    nxt = lifecycle.get("transitions", {}).get(state, [])
    return f"From {state} a node or link may move to {', '.join(nxt)}." if nxt else f"{state} is final: no transition leaves it."


def _type_tip(t: dict) -> str:
    return (f"{t.get('name')}: {', '.join(t.get('source_kind', []))} to {', '.join(t.get('target_kind', []))}, {t.get('direction', '')}; "
            f"inverse label '{t.get('inverse_label', '')}'; ARIS {t.get('aris_status')}, Archi {t.get('archi_status')}.")


def _requirement_line(req: str) -> str:
    """The requirement's own line from the kit's requirements table, verbatim."""
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"| {req} |"):
            return line.split("|")[2].strip()
    return ""


class _Ctx:
    """Everything a reference panel reads: the vendored register, the map, and the scenario's record when given."""

    def __init__(self, view: dict | None):
        T = _load_tools()
        self.T = T
        self.reg = T["register"].load_register(REGISTER)
        self.map = load_map()
        self.rows = {r["key"]: r for r in self.map["row"]}
        self.lifecycle = T["register"].load_toml(REGISTER / "metamodel" / "lifecycle.toml")
        self.manifest = T["register"].load_toml(REGISTER / "exports" / "kit" / "2026-10-30" / "MANIFEST.toml")
        self.links = [dict(ln, type=rname) for rname, rel in self.reg["relationships"].items() for ln in rel["links"]]
        self.by_id = {ln["id"]: ln for ln in self.links}
        self.view = view
        self.scenario = view["scenario"] if view else None
        self.det = json.loads((Path(view["source_dir"]) / "deterministic.json").read_text(encoding="utf-8")) if view else None
        self.reg_sentences: list[dict] = []
        self.C = lambda *s: views._reg(self.reg_sentences, "controlled", *s)
        self.D = lambda *s: views._reg(self.reg_sentences, "data", *s)

    def name(self, nid):
        return self.reg["nodes"].get(nid, {}).get("name", "")

    def state(self, nid):
        return self.reg["nodes"].get(nid, {}).get("state", "")

    def state_cell(self, state):
        return _tip(state, self.C(_state_tip(state, self.lifecycle)))

    def level_cell(self, level):
        return _tip(level, self.C(LEVEL_TIP.get(level, "")))

    def link_cell(self, ln):
        return R("link", ln["id"], f"{ln['id']} ({ln['type']}, {ln.get('state')})")

    def citing(self, anchor: str) -> list:
        """The links whose evidence or external target cites the anchor (a kit path or path#section)."""
        return [ln for ln in self.links
                if any(ev == anchor or ev.startswith(anchor + "#") or ev == "kit:" + anchor or ev.startswith("kit:" + anchor + "#") for ev in ln.get("evidence", []))
                or (ln.get("target_external") or "").startswith("kit:" + anchor)]

    def rows_anchored(self, anchor: str) -> list:
        n = _norm(anchor)
        return [r for r in self.map["row"] if _norm(r["anchor"]) == n or _norm(r["anchor"]).startswith(n + "#")]

    def level_of(self, key):
        return self.det["gate_keys"].get(key, {}).get("level", "") if self.det else ""


def _link_panel(cx: _Ctx, ln: dict) -> dict:
    C, D = cx.C, cx.D
    t = cx.reg["relationships"][ln["type"]]["type"]
    intro = C(f"A {ln['type']} link, state {ln.get('state')}, owner {ln.get('owner')}.") + " " + D(f"Rationale: {ln.get('rationale', '')}")
    ends = [["source", R("node", ln["source"]), cx.name(ln["source"]), cx.state_cell(cx.state(ln["source"]))]]
    if ln.get("target"):
        ends.append(["target", R("node", ln["target"]), cx.name(ln["target"]), cx.state_cell(cx.state(ln["target"]))])
    else:
        ends.append(["target (external)", _target_ref(ln), "", ""])
    secs = [{"heading": C("Ends"), "text": C("Each end opens its node; an external target opens its document."),
             "table": {"cols": ["role", "node", "name", "state"], "rows": ends}},
            {"heading": C("Relationship type"), "text": D(_type_tip(t)) + (" " + D(f"Note: {t['note']}") if t.get("note") else "")},
            {"heading": C(f"Evidence: {len(ln.get('evidence', []))}"), "text": C("A kit entry opens its document or requirement; an export entry is the manifest."),
             "table": {"cols": ["entry"], "rows": [[_anchor_ref(ev) if ev.startswith("kit:") else ev] for ev in ln.get("evidence", [])]}}]
    appr = ln.get("approval")
    if appr:
        secs.append({"heading": C("Approval"), "text": D(f"By {appr.get('by')} on {appr.get('on')}, record {appr.get('record')}; review due {ln.get('review_due')}.")})
    else:
        secs.append({"heading": C("Approval"), "text": C("No approval is recorded, so the link is not approved.")})
    return {"title": C(f"{ln['id']}, a {ln['type']} link"), "intro": intro, "sections": secs}


def _req_panel(cx: _Ctx, req: str) -> dict | None:
    C, D = cx.C, cx.D
    line = _requirement_line(req)
    if not line:
        return None
    anchor = "requirements.md#" + req
    intro = D(f"{req}: {line}") + " " + C("The id is the experiment's; the kit's text is quoted as data.")
    secs = []
    hits = [h for h in cx.det["rules"]["R-REQ"] if h.get("req") == req] if cx.det else []
    if cx.det:
        secs.append({"heading": C(f"Rule hits in {cx.scenario}: {len(hits)}"),
                     "text": C("Each hit is one gap the rules found on this requirement.") if hits else C("The rules found no gap on this requirement in this scenario."),
                     "table": {"cols": ["kind", "declared", "key"], "rows": [[_tip(h.get("kind", ""), C(_kind_tip(h.get("kind", ""), bool(h.get("declared"))))),
                               _tip("yes" if h.get("declared") else "no", C(DECLARED_TIP["yes" if h.get("declared") else "no"])),
                               R("key", h["key"]) if h.get("key") else ""] for h in hits]}})
    citing = cx.citing(anchor)
    secs.append({"heading": C(f"Links citing it: {len(citing)}"),
                 "text": C("Each link opens its own panel.") if citing else C("No link cites it: the register does not yet carry this requirement."),
                 "table": {"cols": ["link", "type", "source", "target", "state"],
                           "rows": [[R("link", ln["id"]), ln["type"], R("node", ln["source"]), _target_ref(ln), cx.state_cell(ln.get("state", ""))] for ln in citing]}})
    rows = cx.rows_anchored("kit:" + anchor)
    secs.append({"heading": C(f"Map rows anchored on it: {len(rows)}"),
                 "text": C("Each row names the nodes its key concerns; the level is the gate's in this scenario.") if cx.det else C("Each row names the nodes its key concerns."),
                 "table": {"cols": ["key", "level", "nodes"], "rows": [[R("key", r["key"]), cx.level_cell(cx.level_of(r["key"])) if cx.det else "", _join([R("node", n) for n in r["nodes"]])] for r in rows]}})
    return {"title": C(f"Requirement {req}"), "intro": intro, "sections": secs}


def _key_panel(cx: _Ctx, key: str) -> dict | None:
    C, D = cx.C, cx.D
    row = cx.rows.get(key)
    if row is None:
        return None
    secs = []
    if cx.det:
        g = cx.det["gate_keys"].get(key, {})
        blocked = key in set(cx.det["D6_gate"].get("blocked_keys") or [])
        intro = C(f"In {cx.scenario} the gate holds this key at level {g.get('level', 'unknown')}" + (", and it blocks the verdict." if blocked else "."))
        secs.append({"heading": C("The gate's record"), "text": D(f"Level {g.get('level')}, {g.get('n', 0)} assertions, flags {', '.join(g.get('flags') or []) or 'none'}."),
                     "table": {"cols": ["level", "blocked"], "rows": [[cx.level_cell(g.get("level", "")), "yes" if blocked else "no"]]}})
        gv = views.gaps_view(cx.det, [])
        gaps = [r for rows in gv["groups"].values() for r in rows
                if any(c.get("id") == key for c in r.get("concerns", [])) or (r.get("assertion") or {}).get("key") == key or (r.get("sides") or {}).get("key") == key]
        secs.append({"heading": C(f"Gaps on this key: {len(gaps)}"),
                     "text": C("Each gap is one of the Gaps panel's rows.") if gaps else C("The rules found no gap on this key."),
                     "table": {"cols": ["gap", "what it says"], "rows": [[r["id"], r["text"]] for r in gaps]}})
    else:
        intro = C("No scenario is on screen, so the gate's level is not shown.")
    secs.append({"heading": C("The map row"), "text": C("The maintainer-approved reading of this key onto the register.") + " " + D(f"Note: {row.get('note', '')}"),
                 "table": {"cols": ["anchor", "nodes"], "rows": [[_anchor_ref(row["anchor"]), _join([R("node", n) for n in row["nodes"]])]]}})
    secs.append({"heading": C("Nodes named, with their states"),
                 "table": {"cols": ["node", "name", "state"], "rows": [[R("node", n), cx.name(n), cx.state_cell(cx.state(n))] for n in row["nodes"]]}})
    return {"title": C(f"Key {key}"), "intro": intro, "sections": secs}


def _doc_panel(cx: _Ctx, path: str) -> dict | None:
    C, D = cx.C, cx.D
    digest = cx.manifest.get("files", {}).get(path, "")
    if not digest:
        return None
    intro = C("A kit document the register's export carries.") + " " + D(f"Manifest digest at the register's commit: {digest[:12]}.")
    secs = []
    if cx.det and "stage2" in cx.det and path == TABLE_PATH:
        s2 = cx.det["stage2"]
        secs.append({"heading": C("Changed in the second stage"),
                     "text": C("Every link that cites this document is a link to review.") + " "
                             + D(f"The result file records the second load ({s2['load_v2']['fragments']} new fragments, {s2['load_v2']['fragments_reused']} reused) and no document digest.")})
    citing = cx.citing(path)
    secs.append({"heading": C(f"Links citing it: {len(citing)}"),
                 "table": {"cols": ["link", "type", "source", "target", "state", "evidence"],
                           "rows": [[R("link", ln["id"]), ln["type"], R("node", ln["source"]), _target_ref(ln), cx.state_cell(ln.get("state", "")),
                                     ", ".join([ev for ev in ln.get("evidence", []) if path in ev] + ([ln["target_external"]] if path in (ln.get("target_external") or "") else []))] for ln in citing]}})
    rows = cx.rows_anchored("kit:" + path)
    secs.append({"heading": C(f"Map rows anchored on it: {len(rows)}"),
                 "table": {"cols": ["key", "level", "nodes"], "rows": [[R("key", r["key"]), cx.level_cell(cx.level_of(r["key"])) if cx.det else "", _join([R("node", n) for n in r["nodes"]])] for r in rows]}})
    return {"title": C(f"Document {path}"), "intro": intro, "sections": secs}


def ref(kind: str, ident: str, view: dict | None = None) -> dict | None:
    """The panel a reference cell opens. node, link and doc need no scenario; req and key read the
    scenario's record when a view is given and say so when it is not. None for an unknown subject."""
    if kind not in REF_KINDS:
        return None
    cx = _Ctx(view)
    if kind == "node":
        n = cx.reg["nodes"].get(ident)
        panel = _node_panel(ident, n, cx.reg, cx.C, cx.D)["panel"] if n else None
    elif kind == "link":
        ln = cx.by_id.get(ident)
        panel = _link_panel(cx, ln) if ln else None
    elif kind == "req":
        panel = _req_panel(cx, ident)
    elif kind == "key":
        panel = _key_panel(cx, ident)
    else:
        panel = _doc_panel(cx, ident)
    if panel is None:
        return None
    return {"kind": kind, "id": ident, "scenario": cx.scenario, "panel": panel, "text_registry": cx.reg_sentences}


def footprint(view: dict) -> dict:
    """The register footprint of one scenario: the map rows its keys below approved hit and the
    nodes they touch, the requirement gaps joined to the links whose evidence cites them, and
    for S6 the links whose evidence cites the changed decision table. Read from the scenario's
    deterministic.json (view["source_dir"]), the approved map and the vendored register."""
    cx = _Ctx(view)
    T, reg, m, det, rows, links = cx.T, cx.reg, cx.map, cx.det, cx.rows, cx.links
    names = {nid: n.get("name", "") for nid, n in reg["nodes"].items()}
    states = {nid: n.get("state", "") for nid, n in reg["nodes"].items()}
    reg_sentences = cx.reg_sentences
    C, D = cx.C, cx.D
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
    req_cells = []
    uncited = 0
    for h in det["rules"]["R-REQ"]:
        subject = h.get("req") or h.get("artefact") or h.get("entity") or ""
        anchor = REQ_ANCHOR + subject if h.get("req") else "kit:" + subject
        citing = [ln for ln in links if any(ev == anchor or ev.startswith(anchor + "#") for ev in ln.get("evidence", []))] if h.get("req") else []
        if not citing:
            uncited += 1
        declared = "yes" if h.get("declared") else "no"
        req_rows.append((subject, h.get("kind", ""), declared, ", ".join(f"{ln['id']} ({ln['type']}, {ln.get('state')})" for ln in citing) or "none"))
        req_cells.append([R("req", subject) if h.get("req") else (R("doc", subject) if subject in cx.manifest.get("files", {}) else subject),
                          _tip(h.get("kind", ""), C(_kind_tip(h.get("kind", ""), bool(h.get("declared"))))), _tip(declared, C(DECLARED_TIP[declared])),
                          _join([cx.link_cell(ln) for ln in citing]) or "none"])
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
              "An underlined cell opens its subject's panel under the table; a dotted one explains itself on hover.",
              "Nothing here is written back to the register.")
    secs = []
    if key_rows:
        secs.append({"heading": C(f"Keys below approved: {len(key_rows)}"),
                     "text": C(f"They touch {views._plural(len(touched), 'node')}, {len(not_approved)} of them not approved.") + (" " + C("A blocked key is marked.") if blocked else ""),
                     "table": {"cols": ["key", "level", "blocked", "nodes", "anchor"],
                               "rows": [[R("key", k), cx.level_cell(lvl), "yes" if k in blocked else "", _join([R("node", n) for n in r["nodes"]]), _anchor_ref(r["anchor"])] for k, lvl, r in key_rows]}})
        secs.append({"heading": C("Nodes touched"), "text": C("Each node with its state and the keys that touch it."),
                     "table": {"cols": ["node", "name", "state", "keys"],
                               "rows": [[R("node", nid), names.get(nid, ""), cx.state_cell(states.get(nid, "")), _join([R("key", k) for k in ks])] for nid, ks in sorted(touched.items())]}})
    else:
        secs.append({"heading": C("Keys below approved: none"), "text": C("Every key the task needs is approved, so no map row is hit.")})
    secs.append({"heading": C(f"Requirement gaps and the links that cite them: {len(req_rows)}"),
                 "text": C(f"{len(req_rows) - uncited} {'is' if len(req_rows) - uncited == 1 else 'are'} cited by a link, {uncited} by none.") + (" " + C("A gap no link cites is one the register does not yet carry.") if uncited else ""),
                 "table": {"cols": ["requirement or document", "kind", "declared", "links citing it"], "rows": req_cells}})
    if "stage2" in det:
        secs.append({"heading": C(f"Links citing the changed decision table: {len(table_links)}"),
                     "text": C("The table changed in the second stage, so every link that cites it is a link to review.") + " "
                             + D(f"The manifest digest of {TABLE_PATH} at the register's commit is {table_digest[:12]}; the result file records the second load ({det['stage2']['load_v2']['fragments']} new fragments, {det['stage2']['load_v2']['fragments_reused']} reused) and no document digest."),
                     "table": {"cols": ["link", "type", "source", "target", "state", "evidence"],
                               "rows": [[R("link", lid), _tip(ty, D(_type_tip(reg["relationships"][ty]["type"]))), R("node", src), _target_ref(cx.by_id[lid]), cx.state_cell(st),
                                         _join([_anchor_ref(ev) for ev in evs.split(", ")])] for lid, ty, src, _tg, st, evs in table_links]}})
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

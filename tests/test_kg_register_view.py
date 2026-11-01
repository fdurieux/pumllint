"""The demo's register view (kg_experiment/demo/app/register_view.py): built from the vendored
IEAM register, read only, in the glossary's terms. Plain asserts, no fixtures, stdlib only."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "kg_experiment" / "demo"
sys.path.insert(0, str(DEMO / "app"))
import register_view  # noqa: E402
import views  # noqa: E402


def _sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", text.strip()) if s]


def _forbidden_in(sentence):
    low = sentence.lower()
    return [f for f in views.FORBIDDEN if re.search(r"\b" + re.escape(f) + r"\b", low)]


def test_register_view_builds_from_the_vendored_copy_at_the_pinned_date():
    v = register_view.build()
    assert v["source"]["repo"] == "fdurieux/ieam-register" and len(v["source"]["commit"]) == 40 and v["source"]["digest_ok"]
    assert v["source"]["tag"] == "v0.1.1" and v["source"]["commit"].startswith("c54f86c")  # the tag sits on the vendored commit
    assert v["pinned"] and v["run_date"] == v["source"]["pinned_date"]
    assert v["summary"] == {"nodes": 27, "links": 28, "errors": 0, "warnings": 3}
    assert v["coverage_lines"][0] == "C1: 2/3 covered, 1 excepted, 0 uncovered"
    assert v["coverage"]["C2"]["uncovered"] == [] and v["coverage"]["C3"]["uncovered"] == []
    assert sorted(v["nodes_by_taxonomy"]) == sorted(["capabilities", "products", "journeys", "processes", "applications", "information", "organisation"])
    assert sum(len(ns) for ns in v["nodes_by_taxonomy"].values()) == 27 and len(v["links"]) == 28
    for ns in v["nodes_by_taxonomy"].values():
        for n in ns:
            p = n["panel"]
            assert p["title"].startswith(n["id"]) and p["intro"] and p["sections"], n["id"]
            assert f"Name: {n['name']}." in p["intro"]
            for sec in p["sections"]:
                if "table" in sec:
                    assert all(len(r) == len(sec["table"]["cols"]) for r in sec["table"]["rows"]), (n["id"], sec["heading"])
    cap = {n["id"]: n for n in v["nodes_by_taxonomy"]["capabilities"]}["CAP-0002"]
    assert cap["links_in"] == 2 and cap["links_out"] == 0 and cap["state"] == "approved"
    assert v["exceptions"][0]["id"] == "EXC-0001" and "until 2027-01-31" in v["exceptions"][0]["sentence"]
    assert v["matrix"] == {"rows": 16, "unverified": 16, "sentence": v["matrix"]["sentence"]} and "every row is unverified" in v["matrix"]["sentence"]
    assert len(v["relationship_types"]) == 10 and all(t["aris_status"] == "unverified" for t in v["relationship_types"])
    assert {t["term"] for t in v["glossary"]} <= set(views.GLOSSARY), "every register term is in the demo glossary"


def test_register_view_at_the_wall_clock_shows_an_expired_exception():
    w = register_view.build("2027-03-01")
    assert not w["pinned"] and w["run_date"] == "2027-03-01"
    assert w["coverage"]["C1"]["uncovered"] == ["JRN-0004"] and w["coverage"]["C1"]["excepted"] == 0
    assert "wall-clock date" in w["intro"] and w["pinned_date"] == "2026-10-30"
    same = register_view.build("2026-10-30")
    assert not same["pinned"] and "which is the pinned date" in same["intro"]
    assert any(f["check"] == "exceptions" and "expired" in f["message"] for f in w["findings"])


def test_register_view_sentences_obey_the_glossary_and_the_limit():
    for v in (register_view.build(), register_view.build("2027-03-01")):
        assert len(v["text_registry"]) > 100
        for item in v["text_registry"]:
            if item["kind"] == "data":
                continue
            for s in _sentences(item["text"]):
                assert len(s.split()) <= 20, s
                assert not _forbidden_in(s), (s, _forbidden_in(s))
    # the register's own forbidden synonyms are in the demo's list, reconciled (GLOSSARY.md)
    for syn in ("element record", "mapping row", "golden source", "an extract", "sign-off", "waiver", "completeness rule"):
        assert syn in views.FORBIDDEN
    for keep in ("extract", "item", "object", "ok"):
        assert keep not in views.FORBIDDEN, f"{keep} keeps its demo sense"


def test_register_impact_walk_reaches_the_product_and_says_when_it_does_not():
    w = register_view.impact("APP-0002")
    assert "PRD-0002" in w["reached"]["products"] and "JRN-0002" in w["reached"]["journeys"] and len(w["edges"]) == 5
    assert w["panel"]["title"] == "Impact of retiring APP-0002" and "does not climb a node's parent" in w["panel"]["intro"]
    cols = w["panel"]["sections"][0]["table"]["cols"]
    assert all(len(r) == len(cols) for r in w["panel"]["sections"][0]["table"]["rows"])
    # the register tool's own limit, shown honestly: TariffEngine reaches a journey step but no product
    t = register_view.impact("APP-0003")
    assert t["reached"]["products"] == [] and "JRN-0003" in t["reached"]["journeys"]
    assert "No product is reached" in t["panel"]["sections"][0]["text"]
    assert register_view.impact("APP-9999") is None
    leaf = register_view.impact("ENT-0004")
    assert leaf["edges"] == [] and "No link starts at this node" in leaf["panel"]["sections"][0]["text"]
    for v in (w, t, leaf):
        for item in v["text_registry"]:
            if item["kind"] == "data":
                continue
            for s in _sentences(item["text"]):
                assert len(s.split()) <= 20 and not _forbidden_in(s), s


def test_register_footprint_per_scenario():
    from pathlib import Path as _P
    NO_RUNS = ROOT / "nonexistent-demo-runs"
    fps = {sc: register_view.footprint(views.build(sc, views.default_source(sc), NO_RUNS)) for sc in views.ORDER}
    m = register_view.load_map()
    assert m["map"]["status"] == "approved" and m["map"]["approved_by"] and len(m["row"]) == 36
    assert {r["key"] for r in m["row"]} == set(json_keys())
    assert fps["S1"]["keys_below"] == {} and fps["S1"]["uncited"] == 0 and fps["S1"]["box"]["colour"] == "ok"
    s2 = fps["S2"]
    assert "QuoteAPI|on_screening_outage" in s2["keys_below"] and "response|hold_presence" in s2["keys_below"]
    # since the register's v0.1.1 (decision 0003) REL-06002 cites REQ-06, so S2 has no uncited gap and is amber, not red
    assert any(r["subject"] == "REQ-06" and "REL-06002" in r["cited_by"] for r in s2["requirements"]) and s2["uncited"] == 0
    assert any(r["subject"] == "REQ-05" and "REL-08002" in r["cited_by"] for r in s2["requirements"])
    assert s2["box"]["colour"] == "warn" and "APP-0002" in s2["touched"]
    assert fps["S4"]["box"]["colour"] == "warn" and fps["S5"]["box"]["colour"] == "warn"
    s3 = fps["S3"]
    assert "ENT-0005" in s3["not_approved"] and s3["box"]["colour"] == "bad"
    s6 = fps["S6"]
    assert len(s6["table_links"]) >= 4 and "REL-10001" in s6["table_links"] and s6["keys_below"] == {}
    assert any("changed decision table" in sec["heading"] for sec in s6["panel"]["sections"])
    assert len(fps["S7"]["keys_below"]) == 36 and len(fps["S7"]["touched"]) == 20
    for fp in fps.values():
        assert fp["box"]["id"] == "footprint" and fp["panel"]["title"].startswith("Register footprint of")
        for sec in fp["panel"]["sections"]:
            if "table" in sec:
                assert all(len(r) == len(sec["table"]["cols"]) for r in sec["table"]["rows"]), (fp["scenario"], sec["heading"])
        for item in fp["text_registry"]:
            if item["kind"] == "data":
                continue
            for s in _sentences(item["text"]):
                assert len(s.split()) <= 20 and not _forbidden_in(s), s
        for ln in fp["box"]["lines"]:
            assert len(ln.split()) <= 20 and not _forbidden_in(ln), ln


def _cells(panel):
    for sec in panel["sections"]:
        for row in sec.get("table", {}).get("rows", []):
            for c in row:
                yield from (c if isinstance(c, list) else [c])


def _refs(panel):
    return [c["ref"] for c in _cells(panel) if isinstance(c, dict) and "ref" in c]


def _check_sentences(items):
    for item in items:
        if item["kind"] == "data":
            continue
        for s in _sentences(item["text"]):
            assert len(s.split()) <= 20 and not _forbidden_in(s), s


def test_footprint_cells_are_references_and_tips():
    NO_RUNS = ROOT / "nonexistent-demo-runs"
    fp = register_view.footprint(views.build("S2", views.default_source("S2"), NO_RUNS))
    refs = _refs(fp["panel"])
    assert "req:REQ-06" in refs and "req:REQ-05" in refs and "link:REL-08002" in refs
    assert "key:QuoteAPI|on_screening_outage" in refs and "node:APP-0002" in refs and "doc:contract/openapi.yaml" in refs
    tips = [c for c in _cells(fp["panel"]) if isinstance(c, dict) and "tip" in c]
    assert any(c["text"] == "declared_gap" for c in tips) and any(c["text"] == "approved" for c in tips) and any(c["text"] in ("yes", "no") for c in tips)
    assert all(c["tip"] for c in tips)
    s6 = register_view.footprint(views.build("S6", views.default_source("S6"), NO_RUNS))
    assert "doc:contract/decision_table.md" in _refs(s6["panel"]) and "link:REL-10001" in _refs(s6["panel"])
    # the data part stays plain for the API's readers
    assert all(isinstance(r["cited_by"], str) for r in fp["requirements"])


def test_reference_panels():
    NO_RUNS = ROOT / "nonexistent-demo-runs"
    s2 = views.build("S2", views.default_source("S2"), NO_RUNS)
    link = register_view.ref("link", "REL-08002")
    assert link["panel"]["title"].startswith("REL-08002, a manages link") and "node:APP-0002" in _refs(link["panel"]) and "node:ENT-0003" in _refs(link["panel"]) and "req:REQ-05" in _refs(link["panel"])
    assert any(sec["heading"] == "Approval" for sec in link["panel"]["sections"])
    ext = register_view.ref("link", "REL-10001")
    assert "doc:contract/decision_table.md" in _refs(ext["panel"])
    req = register_view.ref("req", "REQ-06", s2)
    heads = [sec["heading"] for sec in req["panel"]["sections"]]
    assert "Rule hits in S2: 2" in heads and "Links citing it: 1" in heads and "Map rows anchored on it: 1" in heads
    assert "link:REL-06002" in _refs(req["panel"])
    assert "REQ-06: screening outage" in req["panel"]["intro"] and "key:QuoteAPI|on_screening_outage" in _refs(req["panel"])
    req5 = register_view.ref("req", "REQ-05", s2)
    assert "link:REL-08002" in _refs(req5["panel"])
    req_no_sc = register_view.ref("req", "REQ-05")
    assert not any(h.startswith("Rule hits") for h in [sec["heading"] for sec in req_no_sc["panel"]["sections"]])
    key = register_view.ref("key", "QuoteAPI|on_screening_outage", s2)
    assert "level declared_gap" in key["panel"]["intro"] and "blocks the verdict" in key["panel"]["intro"]
    assert any(sec["heading"] == "Gaps on this key: 1" for sec in key["panel"]["sections"]) and "req:REQ-06" in _refs(key["panel"])
    s3 = views.build("S3", views.default_source("S3"), NO_RUNS)
    k3 = register_view.ref("key", "S-review|max", s3)
    assert "level proposed" in k3["panel"]["intro"] and "node:ENT-0005" in _refs(k3["panel"])
    s6 = views.build("S6", views.default_source("S6"), NO_RUNS)
    doc = register_view.ref("doc", "contract/decision_table.md", s6)
    heads = [sec["heading"] for sec in doc["panel"]["sections"]]
    assert "Changed in the second stage" in heads and "Links citing it: 8" in heads and "27e9fe7ece26" in doc["panel"]["intro"]
    node = register_view.ref("node", "APP-0002")
    assert node["panel"]["title"].startswith("APP-0002") and any(r.startswith("link:REL-") for r in _refs(node["panel"]))
    for bad in (("node", "APP-9999"), ("link", "REL-99999"), ("req", "REQ-99"), ("key", "nope|nope"), ("doc", "nope.md"), ("nope", "x")):
        assert register_view.ref(*bad) is None, bad
    for r in (link, ext, req, req5, key, k3, doc, node):
        _check_sentences(r["text_registry"])
        for sec in r["panel"]["sections"]:
            if "table" in sec:
                assert all(len(row) == len(sec["table"]["cols"]) for row in sec["table"]["rows"]), sec["heading"]
    assert register_view.ref("key", "QuoteAPI|on_screening_outage", s2)["scenario"] == "S2"


def test_projection_rows_and_statements():
    import register_project as rp
    r = rp.rows(loaded_at="2026-10-31T00:00:00+00:00")
    c = r["counts"]
    assert c["nodes"] == 27 and c["links"] == 28 and c["types"] == 10 and c["documents"] == 10 and c["externals"] == 1 and c["exceptions"] == 1
    assert r["stamp"]["tag"] == "v0.1.1" and r["stamp"]["commit"].startswith("c54f86c") and r["stamp"]["export_date"] == "2026-10-30"
    assert len(r["parents"]) == sum(1 for n in r["nodes"] if n["parent"]) and len(r["owners"]) == 27
    assert sum(len(v) for v in r["typed"].values()) == 27 and len(r["maps_to"]) == 1 and len(r["link_of"]) == 55 and len(r["of_type"]) == 28
    assert {"reg_id": "REL-08002", "path": "kit/requirements.md", "anchor": "kit:requirements.md#REQ-05"} in r["cites"]
    assert r["excepts"] == [{"reg_id": "EXC-0001", "node": "JRN-0004", "rule": "C1", "expires": "2027-01-31"}]
    assert c["relationships"] == 27 + 1 + 55 + 28 + len(r["cites"]) + len(r["parents"]) + 27 + 1
    # every property is what Neo4j can hold: a string, number, boolean or list of strings; every row is stamped
    ok = (str, int, float, bool)
    for key in ("nodes", "types", "links", "documents", "externals", "exceptions"):
        for row in r[key]:
            assert row["tag"] == "v0.1.1" and row["commit"] and row["loaded_at"] and len(row["digest"]) == 64, (key, row["reg_id"])
            for k, v in row.items():
                assert isinstance(v, ok) or (isinstance(v, list) and all(isinstance(x, str) for x in v)), (key, row["reg_id"], k, v)
    st = rp.statements(r)
    assert st[0] == ("MATCH (n:Register) DETACH DELETE n", {})
    harness = ("Artefact", "Version", "Fragment", "Assertion", "Activity", "Agent", "Verification", "Approval", "Gap", "Derived", "Entity")
    for cypher, _ in st:  # the loader never names a harness label: the namespace is the whole discipline
        assert not any(f":{lbl}" in cypher for lbl in harness), cypher
        assert "Reg" in cypher, cypher
    rel_types = {cy.split("-[e:")[1].split("]")[0] for cy, _ in st if "-[e:" in cy}
    assert "REG_IS_SUPPORTED_BY" in rel_types and "REG_CRUD" in rel_types and "REG_MAPS_TO" in rel_types


def test_projection_is_wired_and_named():
    import re as _re
    page = (ROOT / "kg_experiment" / "demo" / "app" / "index.html").read_text(encoding="utf-8")
    server = (ROOT / "kg_experiment" / "demo" / "app" / "server.py").read_text(encoding="utf-8")
    ci = (ROOT / ".github" / "workflows" / "kg-demo.yml").read_text(encoding="utf-8")
    assert '["api", "register", "project"]' in server and "register_project.census(s)" in server and '"register": None' in server
    assert 'id="project-btn"' in page and "/api/register/project" in page and "register ${s.register ? 'projected at '" in page
    assert "POST localhost:8080/api/register/project" in ci and '"tag"]=="v0.1.1"' in ci
    assert "projection" in views.GLOSSARY and "**The projection.**" in (ROOT / "kg_experiment" / "demo" / "README.md").read_text(encoding="utf-8")
    ids = [m.group(1) for m in _re.finditer(r'\{"id": "([a-z0-9-]+)", "title"', server)]
    assert ids[-4:] == ["register-tag", "register-impact", "register-c1", "register-cites"], ids
    for cy in ("REG_IS_SUPPORTED_BY|REG_DELIVERS", "REG_EXCEPTS", "Artefact {id:d.path}", "v.sha256 = d.digest THEN 'same as tag'"):
        assert cy in server


def json_keys():
    import json
    return list(json.loads((ROOT / "kg_experiment" / "results" / "S1" / "deterministic.json").read_text(encoding="utf-8"))["gate_keys"])


def test_register_card_is_wired_on_the_page_and_the_server():
    page = (DEMO / "app" / "index.html").read_text(encoding="utf-8")
    assert "/api/register" in page and 'id="register-detail"' in page and "renderRegisterCard" in page and "showRegister" in page
    assert "function registerEntry" in page and 'data-id="register"' in page and ' id="register"' not in page, "the register is an entry in the Scenarios list, not a sidebar card"
    server = (DEMO / "app" / "server.py").read_text(encoding="utf-8")
    assert 'parts == ["api", "register"]' in server and "import register_view" in server
    assert '["api", "register", "impact"]' in server and 'id="impact-form"' in page and "/api/register/impact/" in page
    ci = (ROOT / ".github" / "workflows" / "kg-demo.yml").read_text(encoding="utf-8")
    assert "/api/register" in ci and '"digest_ok"' in ci and "/api/register/impact/APP-0002" in ci and "/api/register/footprint/S2" in ci
    assert "v.footprint ? stageBox(v.footprint.box)" in page and '["api", "register", "footprint"]' in server
    assert "function wireRefs" in page and "function cell" in page and 'class="xref" data-ref=' in page and '["api", "register", "ref"]' in server
    assert "/api/register/ref/req/REQ-06?scenario=S2" in ci and "reference" in views.GLOSSARY
    # the strip stays one row and scrolls sideways; it never wraps the Oracle column under Ingest
    assert ".strip{display:grid;grid-auto-flow:column;" in page and "overflow-x:auto" in page.split(".strip{")[1].split("}")[0]
    # the oracle tables scroll inside their column instead of pushing past the card
    assert ".two>*{min-width:0}" in page and '<div class="tw ot"><div class="twin">' in page and ".tw{overflow-x:auto" in page
    assert '<div class="tw ot"><table>' not in page  # the two verdict tables share one scroll container
    readme = (DEMO / "README.md").read_text(encoding="utf-8")
    assert "**The register.**" in readme
    glossary = (DEMO / "GLOSSARY.md").read_text(encoding="utf-8")
    assert "Terms shared with the IEAM register" in glossary

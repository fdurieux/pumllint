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


def test_register_card_is_wired_on_the_page_and_the_server():
    page = (DEMO / "app" / "index.html").read_text(encoding="utf-8")
    assert "/api/register" in page and 'id="register-detail"' in page and "renderRegisterCard" in page and "showRegister" in page
    assert "function registerEntry" in page and 'data-id="register"' in page and ' id="register"' not in page, "the register is an entry in the Scenarios list, not a sidebar card"
    server = (DEMO / "app" / "server.py").read_text(encoding="utf-8")
    assert 'parts == ["api", "register"]' in server and "import register_view" in server
    assert '["api", "register", "impact"]' in server and 'id="impact-form"' in page and "/api/register/impact/" in page
    ci = (ROOT / ".github" / "workflows" / "kg-demo.yml").read_text(encoding="utf-8")
    assert "/api/register" in ci and '"digest_ok"' in ci and "/api/register/impact/APP-0002" in ci
    readme = (DEMO / "README.md").read_text(encoding="utf-8")
    assert "**The register.**" in readme
    glossary = (DEMO / "GLOSSARY.md").read_text(encoding="utf-8")
    assert "Terms shared with the IEAM register" in glossary

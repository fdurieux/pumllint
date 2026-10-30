"""Guards for kg_experiment/demo/: the report view builds from the committed
record for every scenario, the systemic view renders, the vendored model is
the one its SOURCE.md names, the deck slide the view borrows its layout from
still regenerates byte for byte, and the image pins the record's versions.
Standard library only; nothing here touches a store or the network."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import xml.dom.minidom
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "kg_experiment" / "demo"
APP = DEMO / "app"
RESULTS = ROOT / "kg_experiment" / "results"
NO_RUNS = ROOT / "nonexistent-demo-runs"

sys.path.insert(0, str(APP))
import cascade  # noqa: E402
import views  # noqa: E402

sys.path.insert(0, str(DEMO / "tools"))
import compare_deterministic  # noqa: E402


def test_every_scenario_replays_from_the_record():
    for sc in views.ORDER:
        v = views.build(sc, views.default_source(sc), NO_RUNS)
        assert [s["id"] for s in v["stages"]] == ["ingest", "extract", "load", "rules", "gaps", "gate"], sc
        assert v["gate"]["verdict"] == views.SCENARIOS[sc]["gate"], (sc, v["gate"])
        assert v["required_keys"] == 36, sc
        for arm in ("G", "B"):
            assert v["arms"][arm]["summary"]["n"] == 5, (sc, arm)
        assert v["bundle"] and v["bundle"].startswith("GATE VERDICT: "), sc
        assert v["stage2" if sc == "S6" else "scenario"]


def test_s6_sources_and_stage_two():
    rerun = views.build("S6", "rerun", NO_RUNS)
    assert views.default_source("S6") == "rerun"
    assert [x["key"] for x in rerun["stage2"]["invalidated"]] == ["P2|surcharge", "P2|threshold", "worked_example|price", "P3|order"]
    assert rerun["stage2"]["kept"] == 31
    assert rerun["stage2"]["gate_before"]["verdict"] == "BLOCKED" and rerun["stage2"]["gate_after"]["verdict"] == "PROCEED"
    assert rerun["stage2"]["suspect_derived"] == [{"id": "derived:S1:G:run1", "suspect": True}]
    d3 = views.build("S6", "d3check", NO_RUNS)
    assert d3["stage2"]["suspect_derived"] == [] and d3["arms"]["G"]["summary"]["n"] == 0
    assert {s["id"] for s in rerun["sources"]} == {"record", "rerun", "d3check"}


def test_demo_runs_are_listed_as_sources(tmp_path=None):
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        runs = Path(td)
        (runs / "2026-10-30-1200" / "S4").mkdir(parents=True)
        (runs / "2026-10-30-1200" / "S4" / "deterministic.json").write_bytes((RESULTS / "S4" / "deterministic.json").read_bytes())
        v = views.build("S4", "demo-runs/2026-10-30-1200", runs)
        assert v["source_dir"].endswith("S4") and v["arms"]["G"]["summary"]["n"] == 0
        assert any(s["id"] == "demo-runs/2026-10-30-1200" and "(deterministic)" in s["label"] for s in v["sources"])


def test_systemic_placements_use_the_models_nodes_and_edges():
    import gen_cascade_slide as slide
    node_ids = set(slide.nodes)
    edge_pairs = {(a, b) for _, a, b in slide.edges}
    for sc, spec in views.SYSTEMIC.items():
        assert spec["entry"] in node_ids or spec["entry"] is None, sc
        for arm in ("G", "B"):
            a = spec[arm]
            assert a["stop"] in node_ids or a["stop"] is None, (sc, arm)
            path = a["path"]
            for x, y in zip(path, path[1:]):
                assert (x, y) in edge_pairs, (sc, arm, x, y)
            assert a["note"]


def test_every_cascade_renders_well_formed_svg():
    for sc in views.ORDER:
        for arm in ("G", "B"):
            svg = cascade.render(views.SYSTEMIC[sc], arm, title=f"{sc} {arm}")
            xml.dom.minidom.parseString(svg)
            assert svg.startswith("<svg") and "People and intent" in svg, (sc, arm)
            if views.SYSTEMIC[sc]["entry"]:
                assert "defect enters here" in svg, (sc, arm)


def test_vendored_model_matches_its_source_note():
    model_path = DEMO / "model" / "model.json"
    note = (DEMO / "model" / "SOURCE.md").read_text(encoding="utf-8")
    digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
    assert digest in note, "SOURCE.md must carry the sha256 of the vendored model.json"
    m = json.loads(model_path.read_text(encoding="utf-8"))
    assert m["version"] == "0.3" and f"version | 0.3" in note
    assert re.search(r"commit \| `[0-9a-f]{40}`", note)
    assert len(m["edges"]) == 79 and len(m["nodes"]) == 51


def test_deck_cascade_slide_regenerates_byte_for_byte():
    import gen_cascade_slide as slide
    section, _ = slide.render(str(DEMO / "model" / "model.json"))
    committed = (ROOT / "recreate_experiment" / "knowledge-transfer" / "deck" / "project" / "slides" / "cascade.html").read_text(encoding="utf-8")
    assert section == committed


def test_compare_tool_finds_the_record_identical_to_itself():
    n, lines = compare_deterministic.compare(RESULTS, RESULTS, compare_deterministic.SCENARIOS,
                                             s6_record=RESULTS / "S6")
    assert n == 0, lines
    # and the deterministic-mode S6 record differs from the scored one only by the Derived node
    n, lines = compare_deterministic.compare(RESULTS / "d3check", RESULTS, ["S6"], s6_record=RESULTS / "S6")
    assert n > 0 and all("derived" in ln.lower() or "census_after" in ln or "valid_until" in ln or "S6" in ln for ln in lines), lines


def test_image_pins_the_versions_the_record_names():
    doc = (ROOT / "docs" / "neo4j-governed-knowledge-evaluation.md").read_text(encoding="utf-8")
    sec12 = doc[doc.index("## 12. Reproduction"):]
    named = dict(re.findall(r"(neo4j|rdflib|pyshacl|openai) (\d+\.\d+\.\d+)", sec12))
    assert set(named) == {"neo4j", "rdflib", "pyshacl", "openai"}, named
    dockerfile = (DEMO / "Dockerfile").read_text(encoding="utf-8")
    for pkg, ver in named.items():
        assert f'"{pkg}=={ver}"' in dockerfile, (pkg, ver)
    assert "pip install -e ." in dockerfile and 'CMD ["python", "kg_experiment/demo/app/server.py"]' in dockerfile


def test_compose_files_agree():
    compose = (DEMO / "docker-compose.yml").read_text(encoding="utf-8")
    override = (DEMO / "docker-compose.override.yml").read_text(encoding="utf-8")
    assert "image: ghcr.io/fdurieux/pumllint-kg-demo:latest" in compose
    assert "neo4j:5.26-community" in compose and "condition: service_healthy" in compose
    assert "OPENAI_API_KEY: ${OPENAI_API_KEY:-}" in compose, "the key is passed through, never baked in"
    assert "dockerfile: kg_experiment/demo/Dockerfile" in override and "context: ../.." in override
    workflow = (ROOT / ".github" / "workflows" / "kg-demo.yml").read_text(encoding="utf-8")
    assert "ghcr.io/fdurieux/pumllint-kg-demo:${{ steps.sha.outputs.short }}" in workflow
    assert "packages: write" in workflow and "compare_deterministic.py" in workflow


def test_readme_paste_block_is_zsh_safe():
    text = (DEMO / "README.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```bash\n(.*?)```", text, re.S)
    block = max(blocks, key=len)
    assert "docker compose up" in block
    assert "#" not in block and "!" not in block, "a pasted zsh block must carry no # and no !"
    for tool in ("git", "docker"):
        assert f"command -v {tool}" in block


def test_arms_model_defaults_to_the_records_and_is_overridable():
    """The harness's model comes from KG_ARMS_MODEL with the record's model as the
    default, the view names the same record model, and the page offers the toggle."""
    arms = (ROOT / "kg_experiment" / "harness" / "arms.py").read_text(encoding="utf-8")
    m = re.search(r'^RECORD_MODEL = "([^"]+)"', arms, re.M)
    assert m and m.group(1) == views.RECORD_MODEL == "gpt-5.1-2025-11-13"
    assert 'MODEL = os.environ.get("KG_ARMS_MODEL") or RECORD_MODEL' in arms
    page = (APP / "index.html").read_text(encoding="utf-8")
    assert 'name="am" value="record"' in page and 'name="am" value="other"' in page
    assert "Model deviation" in page
    compose = (DEMO / "docker-compose.yml").read_text(encoding="utf-8")
    assert "KG_ARMS_MODEL: ${KG_ARMS_MODEL:-}" in compose
    # a run answered by another model is a deviation; the record's runs are not
    import tempfile, shutil
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "2026-10-30-1700" / "S1"; d.mkdir(parents=True)
        shutil.copy(RESULTS / "S1" / "deterministic.json", d / "deterministic.json")
        rec = json.loads((RESULTS / "S1" / "run1_G.json").read_text(encoding="utf-8"))
        rec["usage"]["model"] = "gpt-5.5-2026-04-01"
        (d / "run1_G.json").write_text(json.dumps(rec), encoding="utf-8")
        v = views.build("S1", "demo-runs/2026-10-30-1700", Path(td))
        assert v["model_deviation"] == ["gpt-5.5-2026-04-01"] and v["arms"]["G"]["runs"][0]["model"] == "gpt-5.5-2026-04-01"
        assert any("gpt-5.5-2026-04-01" in s_["label"] for s_ in v["sources"])
    assert views.build("S1", "record", NO_RUNS)["model_deviation"] == []


def test_plain_english_narrative_is_built_from_the_files():
    for sc in views.ORDER:
        v = views.build(sc, views.default_source(sc), NO_RUNS)
        text = " ".join(v["narrative"])
        assert views.SCENARIOS[sc]["plain"] in text, sc
        assert "None" not in text and "{" not in text, (sc, text[:200])
        assert f"The gate's verdict is {v['gate']['verdict']}" in text, sc
    assert "invalidated the 4 assertions" in " ".join(views.build("S6", "rerun", NO_RUNS)["narrative"])
    # a deterministic demo run is checked against the record, in words
    import tempfile, shutil
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "demo-runs" / "2026-10-30-1800" / "S4"; d.mkdir(parents=True)
        shutil.copy(RESULTS / "S4" / "deterministic.json", d / "deterministic.json")
        v = views.build("S4", "demo-runs/2026-10-30-1800", Path(td) / "demo-runs")
        assert v["record_check"]["differ"] == 0 and v["record_check"]["compared"] > 100
        assert "identical on all" in " ".join(v["narrative"]) and "arms were not called" in " ".join(v["narrative"])


def _sentences(text):
    import re
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", text.strip()) if s]


def _forbidden_in(sentence):
    import re
    low = sentence.lower()
    return [f for f in views.FORBIDDEN if re.search(r"\b" + re.escape(f) + r"\b", low)]


def test_generated_prose_keeps_to_the_glossary_and_the_length_limits():
    """Controlled sentences: 20 words, no forbidden synonym. Readings: 25 words,
    no forbidden synonym. Data is exempt. Checked on the text actually produced
    for every scenario, the S6 rerun and a deterministic-only demo run."""
    import tempfile, shutil
    limits = {"controlled": 20, "reading": 25}
    seen = {"controlled": 0, "reading": 0, "data": 0}
    builds = [(sc, views.default_source(sc), NO_RUNS) for sc in views.ORDER] + [("S6", "rerun", NO_RUNS)]
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "demo-runs" / "2026-10-30-1900" / "S2"; d.mkdir(parents=True)
        shutil.copy(RESULTS / "S2" / "deterministic.json", d / "deterministic.json")
        builds.append(("S2", "demo-runs/2026-10-30-1900", Path(td) / "demo-runs"))
        for sc, src, runs in builds:
            v = views.build(sc, src, runs)
            for item in v["text_registry"]:
                seen[item["kind"]] += 1
                if item["kind"] == "data":
                    continue
                for s in _sentences(item["text"]):
                    n = len(s.split())
                    assert n <= limits[item["kind"]], (sc, src, item["kind"], n, s)
                    assert not _forbidden_in(s), (sc, src, _forbidden_in(s), s)
            # the registry covers what the page shows: narrative, panels, gap kinds
            shown = " ".join(v["narrative"]) + " " + " ".join(v["gaps"]["explain"].values())
            for det in v["details"].values():
                shown += " " + det["title"] + " " + det["intro"] + " " + " ".join(sec["heading"] + " " + sec.get("text", "") for sec in det["sections"])
            boxes = v["stages"] + (v["stage2"]["stages"] if v.get("stage2") else [])
            shown += " " + " ".join(b["label"] + " " + " ".join(b["lines"]) for b in boxes)
            shown += " " + " ".join(" ".join(v["arms"][a][part]["lines"]) for a in ("G", "B") for part in ("generate", "oracle"))
            for item in v["text_registry"]:
                assert item["text"] in shown, (sc, src, item["text"][:80])
    assert seen["controlled"] > 500 and seen["reading"] >= 7 and seen["data"] > 20, seen
    # the pipeline boxes are in the registry too: every label and every line of every box
    v = views.build("S6", "record", NO_RUNS)
    texts = {it["text"] for it in v["text_registry"]}
    for b in v["stages"] + v["stage2"]["stages"]:
        assert b["label"] in texts and all(ln in texts for ln in b["lines"]), b["id"]
    for a in ("G", "B"):
        assert all(ln in texts for part in ("generate", "oracle") for ln in v["arms"][a][part]["lines"]), a
    # the scenario descriptions: the sidebar cards and the Planted line are controlled, the reading is looser
    for sc, meta in views.SCENARIOS.items():
        for field, lim in (("title", 20), ("represented", 20), ("defect", 20), ("plant", 20), ("plain", 25)):
            for s in _sentences(meta[field]):
                assert len(s.split()) <= lim and not _forbidden_in(s), (sc, field, s)
        assert meta["plant"].endswith(".") and meta["defect"].endswith(".") and meta["represented"].endswith("."), sc
    for texts in (views.RULE_TEXT.values(), views.GAP_KIND_TEXT.values(), views.VERDICT_MEANING.values()):
        for group in texts:
            for s in group:
                assert len(s.split()) <= 20 and not _forbidden_in(s), s


def test_glossary_document_matches_the_view_tables():
    md = (DEMO / "GLOSSARY.md").read_text(encoding="utf-8")
    for term, meaning in views.GLOSSARY.items():
        assert f"| {term} |" in md, term
        assert meaning in md, term
    for syn in views.FORBIDDEN:
        assert syn in md, syn
    assert "ASD-STE100" in md and "20" in md and "25" in md
    page = (DEMO / "app" / "index.html").read_text(encoding="utf-8")
    assert "v.glossary" in page and "GLOSSARY.md" in page
    # the page's own strings obey the glossary too (data from the files is not in the page source)
    import re
    for syn in views.FORBIDDEN:
        assert not re.search(r"\b" + re.escape(syn) + r"\b", page, re.I), syn
    assert "GLOSSARY.md" in (DEMO / "README.md").read_text(encoding="utf-8")


def test_every_pipeline_box_has_a_detail_panel():
    for sc in views.ORDER:
        v = views.build(sc, views.default_source(sc), NO_RUNS)
        ids = [st["id"] for st in v["stages"]] + [f"{part}_{arm}" for part in ("generate", "oracle") for arm in ("G", "B")]
        if sc == "S6":
            ids += [st["id"] for st in v["stage2"]["stages"]]
        for i in ids:
            d = v["details"][i]
            assert d["title"] and d["intro"] and isinstance(d["sections"], list), (sc, i)
            for sec in d["sections"]:
                assert sec["heading"], (sc, i)
                if "table" in sec:
                    assert all(len(r) == len(sec["table"]["cols"]) for r in sec["table"]["rows"]), (sc, i, sec["heading"])
        assert len(v["details"]["gate"]["sections"][1]["table"]["rows"]) == 36, sc
    s4 = views.build("S4", "record", NO_RUNS)["details"]["rules"]
    assert any(sec.get("table") and len(sec["table"]["rows"]) == 4 for sec in s4["sections"] if sec["heading"].startswith("R-CONFLICT"))


def test_gaps_view_matches_the_census_by_kind():
    for sc in views.ORDER:
        v = views.build(sc, views.default_source(sc), NO_RUNS)
        g = v["gaps"]
        from_groups = {"missing": g["counts"]["declared missing"] + g["counts"]["undeclared missing"],
                       "ambiguous": g["counts"]["ambiguous"], "conflict": g["counts"]["conflict"], "unverified": g["counts"]["unverified"]}
        assert {k: n for k, n in from_groups.items() if n} == g["census"], (sc, from_groups, g["census"])
        assert len(g["groups"]["ambiguous"]) == g["census"].get("ambiguous", 0), sc
        assert len(g["groups"]["conflict"]) == g["census"].get("conflict", 0), sc
        assert len(g["groups"]["declared missing"]) + len(g["groups"]["undeclared missing"]) == g["census"].get("missing", 0), sc
        for k, rows in g["groups"].items():
            assert k in g["explain"]
            for r in rows:
                assert r["id"].startswith("gap:") and r["text"], (sc, k, r)
        assert len(g["required_keys"]) == 36
    s4 = views.build("S4", "record", NO_RUNS)["gaps"]["groups"]["conflict"]
    assert all(r["sides"] and r["sides"]["key"] == "QuoteAPI|on_screening_outage" for r in s4)
    s7 = views.build("S7", "record", NO_RUNS)["gaps"]["unverified"]
    assert s7["count"] == 145 and len(s7["required_below_verified"]) == 36

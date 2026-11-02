"""Drift guard for the credit-application demo (sandbox/credit-application/).

The sandbox's README, its live page and the Legible-for-analysts deck's demo
slides (which read talks/legible-for-analysts/demo-findings.json) all state
what pumllint reports on the two diagram sets. These tests run the page's own
analysis, the same in-process pumllint calls the container makes, and assert
that every one of those statements still holds. Change a diagram, a rule or a
statement deliberately, and this file says which side moved. Same pact as
tests/test_talk_round_table.py.

No Docker is needed: the page generator is standard library plus pumllint, and
its PlantUML URL encoding is checked by round-trip, not against a server.
"""

import importlib.util
import json
import re
import tempfile
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SANDBOX = _ROOT / "sandbox" / "credit-application"
_TALK = _ROOT / "talks" / "legible-for-analysts"
_SITE = _ROOT / "docs" / "talks" / "legible-for-analysts"
_SEVERITIES = ["blocker", "critical", "major", "minor", "info"]
_WORDS = "zero one two three four five six seven eight nine ten eleven twelve".split()


def _demo():
    spec = importlib.util.spec_from_file_location("demo_site", _SANDBOX / "demo_site.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_D = _demo()
_LIVE = {name: _D.analyse(name) for name in _D.SETS}
_CLAIM = json.loads((_TALK / "demo-findings.json").read_text(encoding="utf-8"))


def _per_file(result: dict) -> dict:
    """{file: [[rule, severity, count], …]}, the shape demo-findings.json uses."""
    out = {}
    for file, findings in result["findings"].items():
        if not findings:
            continue
        counts = Counter((f["ruleId"], f["severity"]) for f in findings)
        seen = list(dict.fromkeys((f["ruleId"], f["severity"]) for f in findings))
        out[file] = [[rule, sev, counts[(rule, sev)]] for rule, sev in seen]
    return out


def _sorted(per_file: dict) -> dict:
    return {f: sorted(map(tuple, rows)) for f, rows in per_file.items()}


def _severity_counts(result: dict) -> dict:
    c = Counter(f["severity"] for fs in result["findings"].values() for f in fs)
    return {s: c[s] for s in _SEVERITIES if c[s]}


def test_compliant_set_is_clean_at_level_4_and_fully_traced():
    live = _LIVE["compliant"]
    assert live["exit"] == 0
    assert _per_file(live) == {}
    assert {f: lv[0] for f, lv in live["levels"].items()} == _CLAIM["compliant"]["levels"]
    s = live["trace"]["summary"]
    assert (s["coveredCount"], s["requirementCount"], s["unknownReferenceCount"]) == (5, 5, 0)


def test_non_compliant_findings_are_exactly_what_the_slides_show():
    live, claim = _LIVE["non-compliant"], _CLAIM["non-compliant"]
    assert live["exit"] == claim["exit"] == 1  # the gate fails
    # the slide lists a diagram's findings in reading order, so compare order-free
    assert _sorted(_per_file(live)) == _sorted(claim["findings"])
    assert _severity_counts(live) == claim["counts"]


def test_non_compliant_diagrams_still_reach_level_4():
    """The page, the README and the deck all make this point; it must stay true."""
    live = _LIVE["non-compliant"]
    assert {f: lv[0] for f, lv in live["levels"].items()} == _CLAIM["non-compliant"]["levels"]
    assert set(_CLAIM["non-compliant"]["levels"].values()) == {4}


def test_trace_gaps_match_the_slides():
    t, claim = _LIVE["non-compliant"]["trace"], _CLAIM["non-compliant"]
    uncovered = [r["id"] for r in t["requirements"] if not r["covered"]]
    unknown = [u["id"] for u in t["unknownReferences"]]
    assert uncovered == claim["uncovered"] and unknown == claim["unknown"]
    assert t["summary"]["coveredCount"] == claim["covered"]


def test_every_triggered_rule_has_a_plain_english_meaning():
    rules = {f["ruleId"] for fs in _LIVE["non-compliant"]["findings"].values() for f in fs}
    assert rules <= set(_D.MEANING), f"add a MEANING line for {sorted(rules - set(_D.MEANING))}"


def test_readme_states_the_live_counts():
    readme = (_SANDBOX / "README.md").read_text(encoding="utf-8")
    counts = _severity_counts(_LIVE["non-compliant"])
    total = sum(counts.values())
    phrase = f"{_WORDS[total]} findings (" + ", ".join(f"{_WORDS[n]} {s}" for s, n in counts.items()) + ")"
    assert phrase in readme, f"README should say {phrase!r}"
    for rule in {r for fs in _CLAIM["non-compliant"]["findings"].values() for r, _, _ in fs}:
        assert rule in readme, f"README's table no longer names {rule}"


def test_page_builds_without_docker():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        _D.build(out, "http://plantuml.invalid")
        page = (out / "index.html").read_text(encoding="utf-8")
        assert page.count('src="http://plantuml.invalid/svg/') == 8
        assert "Gate passes" in page and "Gate fails" in page
        for file, _ in _D.ARTEFACTS:
            assert file in page
        assert (out / "report-compliant.html").is_file() and (out / "report-non-compliant.html").is_file()


def test_plantuml_url_encoding_round_trips():
    for path in sorted((_SANDBOX / "diagrams").rglob("*.puml")):
        text = path.read_text(encoding="utf-8")
        code = _D.plantuml_encode(text)
        assert re.fullmatch(r"[0-9A-Za-z_-]+", code)
        assert _D.plantuml_decode(code) == text


def test_container_copies_what_it_runs():
    dockerfile = (_SANDBOX / "Dockerfile").read_text(encoding="utf-8")
    ignore = (_SANDBOX / "Dockerfile.dockerignore").read_text(encoding="utf-8")
    assert "COPY sandbox/credit-application/demo_site.py" in dockerfile
    assert "!sandbox/credit-application/demo_site.py" in ignore and "!pumllint/**" in ignore


def test_published_landing_page_links_resolve():
    page = (_SITE / "index.html").read_text(encoding="utf-8")
    local = [h for h in re.findall(r'(?:href|src)="([^"]+)"', page) if "://" not in h]
    assert {"deck.pdf", "deck.pptx", "speaker-notes.pdf", "team-handout.pdf", "overview.jpg"} <= set(local)
    for name in local:
        assert (_SITE / name).is_file(), f"docs/talks/legible-for-analysts/index.html links {name}, which is missing"
    assert "{{" not in page


def test_ports_are_configurable_and_the_page_follows_plantuml():
    """Another stack on 8080 or 8000 must not block the demo: both host ports
    come from the environment, and the page is told the same PlantUML port the
    server is published on (the browser fetches each picture itself)."""
    compose = (_SANDBOX / "compose.yaml").read_text(encoding="utf-8")
    assert '"${PLANTUML_PORT:-8080}:8080"' in compose
    assert '"${DEMO_PORT:-8000}:8000"' in compose
    assert 'DEMO_PLANTUML_URL: "http://localhost:${PLANTUML_PORT:-8080}"' in compose
    assert 'DEMO_HOST_PORT: "${DEMO_PORT:-8000}"' in compose
    readme = (_SANDBOX / "README.md").read_text(encoding="utf-8")
    assert "PLANTUML_PORT=8081 docker compose up" in readme and "DEMO_PORT=" in readme


def test_scoring_wheel_reads_every_check_and_weight_from_pumllint():
    """The Legible deck's wheel (slide 10) and its four appendix pages are drawn
    from talks/legible-for-analysts/export_checks.py, which must cover every
    catalog rule exactly once, carry the scorer's weights and find a name for
    each dimension in docs/rule-map.md."""
    import tomllib

    from pumllint.scoring import DEFAULT_DIMENSION_WEIGHTS

    spec = importlib.util.spec_from_file_location("export_checks", _TALK / "export_checks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    data = mod.export()
    catalog = tomllib.loads((_ROOT / "pumllint" / "rules" / "catalog.toml").read_text(encoding="utf-8"))
    rule_ids = {k for k, v in catalog.items() if isinstance(v, dict) and "dimension" in v}
    listed = [r["id"] for d in data["dimensions"] for r in d["rules"]]
    assert sorted(listed) == sorted(rule_ids) and data["total"] == len(rule_ids)
    assert {d["id"]: d["weight"] for d in data["dimensions"]} == {k.value: w for k, w in DEFAULT_DIMENSION_WEIGHTS.items()}
    assert abs(sum(d["weight"] for d in data["dimensions"]) - 1.0) < 1e-9
    assert all(d["label"] for d in data["dimensions"])


def _readme_exec_commands() -> list[list[str]]:
    """The README's `docker compose exec demo python -m pumllint …` lines, as argv."""
    readme = (_SANDBOX / "README.md").read_text(encoding="utf-8").replace("\\\n", " ")
    prefix = "docker compose exec demo python -m pumllint "
    return [line[len(prefix):].split() for line in readme.splitlines() if line.startswith(prefix)]


def test_readme_container_commands_give_the_slides_verdicts():
    """The README's "Run the checks yourself" commands run in the demo container,
    whose working directory is the sandbox folder (/demo, diagrams/ mounted).
    Run here from that folder, they must exit as the README says: lint and trace
    fail the non-compliant set and pass the compliant one, and lint counts the
    slide's findings."""
    import os

    commands = _readme_exec_commands()
    assert [c[0] for c in commands] == ["diagrams/non-compliant", "trace", "score"]
    here = os.getcwd()
    os.chdir(_SANDBOX)
    try:
        for argv in commands:
            for word in argv:
                if word.startswith("diagrams/"):
                    assert Path(word).exists(), f"README names {word}, which is missing"
            rc, out = _D._run(argv)
            if argv[0] != "score":
                assert rc == 1, f"{argv} should fail the non-compliant set"
            if argv[0] == "diagrams/non-compliant":
                assert "10 issue(s): 1 critical, 2 major, 7 minor" in out
            clean = [w.replace("non-compliant", "compliant") for w in argv]
            rc, _ = _D._run(clean)
            assert rc == 0, f"{clean} should pass the compliant set"
    finally:
        os.chdir(here)

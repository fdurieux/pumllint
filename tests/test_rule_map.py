"""docs/rule-map.md is executable: its categorisation and every example hold.

The guide sorts each rule under its maturity dimension and gives two worked
examples marked "flagged" or "passes". Prose has no golden behind it, so
this is its gate: every catalog rule appears exactly once, under the
dimension, name and severity catalog.toml gives it, and every example is
linted (with its shown config, and the codegen profile where the rule needs
it) and must draw the verdict the page states for that rule.

Plain assert functions, stdlib only, for tests/run_tests.py.
"""

import contextlib
import io
import json
import re
import tempfile
from pathlib import Path

from pumllint.cli import main
from pumllint.rules import _CATALOG

_PAGE = Path(__file__).resolve().parents[1] / "docs" / "rule-map.md"

_DIM = re.compile(r"^## .+ \((DIM-[A-Z]{3})\)$", re.MULTILINE)
_RULE = re.compile(r"^### ([A-Z]+\d{3}) (\S+)$", re.MULTILINE)
_EXAMPLE = re.compile(r"^\*\*(Simple|More complex) example — (flagged|passes)\*\*$", re.MULTILINE)
_FENCE = re.compile(r"^```(plantuml|toml)\n(.*?)\n```$", re.MULTILINE | re.DOTALL)


def _sections():
    """(dimension, rule id, name, rule-section text) in page order."""
    text = _PAGE.read_text(encoding="utf-8")
    dims = [(m.start(), m.group(1)) for m in _DIM.finditer(text)]
    rules = list(_RULE.finditer(text))
    for i, m in enumerate(rules):
        end = rules[i + 1].start() if i + 1 < len(rules) else len(text)
        dim = [d for pos, d in dims if pos < m.start()][-1]
        body = text[m.end() : end]
        nxt = _DIM.search(body)  # a section ends where the next dimension starts
        yield dim, m.group(1), m.group(2), body[: nxt.start()] if nxt else body


def _examples(body: str):
    """(label, expect_flagged, [diagram bodies], toml-or-None) per example."""
    marks = list(_EXAMPLE.finditer(body))
    for i, m in enumerate(marks):
        chunk = body[m.end() : marks[i + 1].start() if i + 1 < len(marks) else len(body)]
        fences = _FENCE.findall(chunk)
        diagrams = [code for lang, code in fences if lang == "plantuml"]
        configs = [code for lang, code in fences if lang == "toml"]
        yield m.group(1), m.group(2) == "flagged", diagrams, configs[0] if configs else None


def _lint(diagrams: list[str], config: str | None, codegen: bool) -> list[dict]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        paths = []
        for i, body in enumerate(diagrams):
            src = body if body.lstrip().startswith("@startuml") else f"@startuml ex{i}\ntitle Ex\n{body}\n@enduml\n"
            p = root / f"d{i}.puml"
            p.write_text(src, encoding="utf-8")
            paths.append(str(p))
        cfg = root / "pumllint.toml"
        cfg.write_text(config or "[rules]\n", encoding="utf-8")
        argv = ["-f", "json", "-c", str(cfg), *paths] + (["--profile", "codegen"] if codegen else [])
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            main(argv)
        return json.loads(out.getvalue())


def test_every_catalog_rule_is_listed_once_under_its_catalog_dimension():
    seen: dict[str, str] = {}
    for dim, rid, name, body in _sections():
        assert rid not in seen, f"{rid} is listed twice"
        seen[rid] = dim
        meta = _CATALOG.get(rid)
        assert meta is not None, f"{rid} is on the page but not in catalog.toml"
        assert dim == meta["dimension"], f"{rid} is under {dim}, catalog says {meta['dimension']}"
        assert name == meta["name"], f"{rid} is called {name}, catalog says {meta['name']}"
        assert f"**Severity:** `{meta['severity']}`" in body, f"{rid}: severity differs from catalog"
        assert ("--profile codegen" in body) == bool(meta.get("profiles")), f"{rid}: profile note differs"
    assert set(seen) == set(_CATALOG), {"missing": sorted(set(_CATALOG) - set(seen))}


def test_every_example_draws_the_verdict_the_page_states():
    count = 0
    for _dim, rid, _name, body in _sections():
        codegen = bool(_CATALOG[rid].get("profiles"))
        labels = []
        for label, flagged, diagrams, config in _examples(body):
            labels.append(label)
            assert diagrams, f"{rid} {label} example has no diagram"
            fired = any(f["ruleId"] == rid for f in _lint(diagrams, config, codegen))
            assert fired == flagged, f"{rid} {label} example: page says {'flagged' if flagged else 'passes'}"
            count += 1
        assert labels == ["Simple", "More complex"], f"{rid}: expected a simple and a more complex example"
    assert count == 2 * len(_CATALOG)

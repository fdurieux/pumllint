"""The pilot census instrument (`tools/pilot_census.py`).

The instrument produces published figures — the 2026-08-11 wild-corpus record
and the C4 prevalence numbers the roadmap's demand gates cite — and until now
nothing under tests/ or .github/ referenced it, while `extract_features.py`
and `calibrate.py` are both wired in. The bundled `examples/` cannot exercise
it: every dialect marker scores zero there. So these fixtures carry an
`!include`, a C4 macro and a multi-diagram file.

Plain assert functions for the zero-dependency runner.
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import pilot_census  # noqa: E402

_INCLUDED = "@startuml one\ntitle One\n!include _shared.iuml\nA -> B : go()\n@enduml\n"
_C4 = (
    "@startuml two\ntitle Two\n!include <C4/C4_Container>\n"
    'Person(user, "User")\nSystem(sys, "System")\nRel(user, sys, "uses")\n@enduml\n'
)
_MULTI = (
    "@startuml m1\ntitle M1\nA -> B : one()\n@enduml\n"
    "@startuml m2\ntitle M2\nC -> D : two()\n@enduml\n"
)


def _census(files: dict) -> dict:
    """Run the instrument over *files* and return its JSON artefact."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name, text in files.items():
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        out = root / "census.json"
        rc = pilot_census.main([str(root), "-o", str(out)])
        assert rc == 0, rc
        return json.loads(out.read_text(encoding="utf-8"))


def test_census_counts_files_diagrams_and_dialect_markers():
    data = _census({"a.puml": _INCLUDED, "b.puml": _C4, "c.puml": _MULTI})
    assert data["files"] == 3
    assert data["diagrams"] == 4  # c.puml carries two

    markers = {label: h["files"] for label, h in data["dialect_markers"].items()}
    include = [v for k, v in markers.items() if "include" in k][0]
    c4 = [v for k, v in markers.items() if "C4" in k][0]
    multi = [v for k, v in markers.items() if "multiple" in k][0]
    assert include == 2, markers  # a.puml and b.puml's <C4/…> include
    assert c4 == 1, markers
    assert multi == 1, markers


def test_reported_paths_use_forward_slashes():
    """CLAUDE.md: reported paths are posix on every platform.

    The instrument used `str(f)`, which emits backslashes on Windows and makes
    the artefact non-byte-identical across platforms — the contract product
    code honours everywhere.
    """
    data = _census({"nested/a.puml": _INCLUDED, "b.puml": _C4})
    quoted = json.dumps(data)
    assert "\\\\" not in quoted, "a backslash reached the artefact"
    for h in data["dialect_markers"].values():
        for example in h["examples"]:
            assert "\\" not in example, example


def test_coverage_suspects_are_counted_by_file_not_by_diagram():
    """A multi-diagram file must not contribute one identical row per diagram.

    On the wild corpus a single 16-diagram file produced 16 rows at the same
    ratio — 104 rows over 89 files — and because rows sort by ratio it filled
    every slot of the default display: one filename, sixteen times.
    """
    # One file, many diagrams, each with almost nothing the parser recognises.
    body = "".join(
        f"@startuml d{i}\ntitle D{i}\n" + "' padding\n" * 20 + "@enduml\n"
        for i in range(6)
    )
    data = _census({"many.puml": body, "ok.puml": _INCLUDED})
    rows = data["coverage_suspects"]
    files = {r["file"] for r in rows}
    assert data["coverage_suspect_files"] == len(files)
    assert data["coverage_suspect_files"] < len(rows), (
        "fixture should produce more rows than files"
    )


def test_marker_examples_are_not_just_the_alphabetically_first():
    """Examples must reach the biggest contributor, not whoever sorts first.

    On the wild corpus the three shown came from the two smallest contributors
    (5 hits between them) while the repository contributing 66 of 73 never
    appeared — which is why the C4 overlap could only be bounded, not measured.
    """
    files = {f"aaa/{i}.puml": _INCLUDED for i in range(5)}
    files["zzz/big.puml"] = _INCLUDED
    data = _census(files)
    examples = [
        h["examples"] for k, h in data["dialect_markers"].items() if "include" in k
    ][0]
    # Paths are reported as given, so match on the directory rather than a
    # prefix: five hits sort ahead of the sixth, which a plain slice would miss.
    assert any("/zzz/" in e for e in examples), examples

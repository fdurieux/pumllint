"""The credit-application demo page: lint both diagram sets and show them side by side.

    python demo_site.py build            write out/index.html and the two maturity reports
    python demo_site.py serve [--port N] serve them, rebuilding the page on every reload

Each diagram is drawn by a PlantUML server (DEMO_PLANTUML_URL, default
http://localhost:8080, which compose.yaml starts) next to what pumllint says
about it. Edit a file under diagrams/, reload the page, and the findings move
with it. Standard library plus pumllint only, so the same script runs in the
container and on a laptop (without a PlantUML server the pictures are missing,
the findings are not). See README.md.
"""

from __future__ import annotations

import argparse
import contextlib
import html
import io
import json
import os
import zlib
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from pumllint.cli import main as pumllint

HERE = Path(__file__).resolve().parent
DIAGRAMS = HERE / "diagrams"
CONFIG = DIAGRAMS / "lint.toml"
SETS = ("compliant", "non-compliant")
# The four artefacts of the case, in the order a reader meets them.
ARTEFACTS = (
    ("credit-application.puml", "The business process"),
    ("credit-decision.puml", "The decision, as a sequence diagram"),
    ("credit-scoring.puml", "One step in detail: scoring"),
    ("application-status.puml", "The application's status, as a state chart"),
)

# What each finding means for the next reader, in a functional analyst's words.
# Every rule the demo set triggers needs a line here (the test checks it).
MEANING = {
    "ACT002": "The process never ends: nobody can tell when it is finished.",
    "ACT003": "A decision whose branches are not named: which way is “yes”?",
    "SEQ001": "A participant nobody declared: here a typo that quietly adds a second customer.",
    "SEQ007": "An alternative with no condition: the reader has to guess when each branch applies.",
    "XD002": "One system, described two different ways in two diagrams.",
    "STA002": "A status nothing leads to: a missing step, or a status that cannot happen.",
    "STA003": "A status change with no cause: what event makes it happen?",
    "GEN006": "No owner named: nobody to ask when the diagram is unclear.",
}

# PlantUML's text encoding for server URLs: raw deflate, then a base64 variant
# with its own alphabet and no padding.
_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"


def plantuml_encode(text: str) -> str:
    data = zlib.compress(text.encode("utf-8"), 9)[2:-4]  # strip zlib header and checksum
    out = []
    for i in range(0, len(data), 3):
        b1, b2, b3 = (data[i : i + 3] + b"\0\0")[:3]
        n = (b1 << 16) | (b2 << 8) | b3
        out += [_ALPHABET[(n >> s) & 0x3F] for s in (18, 12, 6, 0)]
    return "".join(out)


def plantuml_decode(code: str) -> str:
    """Inverse of plantuml_encode (used by the test)."""
    raw = bytearray()
    for i in range(0, len(code), 4):
        n = 0
        for ch in code[i : i + 4]:
            n = (n << 6) | _ALPHABET.index(ch)
        raw += n.to_bytes(3, "big")
    return zlib.decompressobj(-15).decompress(bytes(raw)).decode("utf-8")


def _run(argv: list[str]) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = pumllint(argv)
    return rc or 0, out.getvalue()


def analyse(name: str) -> dict:
    """Lint, score and trace one diagram set; plain data for the page and the test."""
    folder = DIAGRAMS / name
    cfg = ["-c", str(CONFIG)]
    rc, lint_json = _run([str(folder), "-f", "json"] + cfg)
    _, score_json = _run(["score", str(folder), "-f", "json"] + cfg)
    _, trace_json = _run(
        ["trace", str(folder), "--requirements", str(folder / "requirements.txt"), "-f", "json"] + cfg
    )
    findings: dict[str, list[dict]] = {f: [] for f, _ in ARTEFACTS}
    for f in json.loads(lint_json):
        findings.setdefault(Path(f["file"]).name, []).append(f)
    levels = {
        Path(d["file"]).name: (d["maturity"]["level"], d["maturity"]["levelName"], d["maturity"]["score"])
        for d in json.loads(score_json)["diagrams"]
    }
    trace = json.loads(trace_json)
    return {"exit": rc, "findings": findings, "levels": levels, "trace": trace}


def _finding(f: dict) -> str:
    sev = html.escape(f["severity"])
    meaning = MEANING.get(f["ruleId"], "")
    return (
        f'<li class="f {sev}"><span class="rule">{html.escape(f["ruleId"])} · {sev}</span> '
        f'line {f["line"]}<br><b>{html.escape(meaning)}</b><br>'
        f'<span class="msg">{html.escape(f["message"])}</span></li>'
    )


def _card(set_name: str, file: str, result: dict, plantuml: str) -> str:
    text = (DIAGRAMS / set_name / file).read_text(encoding="utf-8")
    level = result["levels"].get(file)
    found = result["findings"].get(file, [])
    verdict = (
        '<p class="ok">✔ No findings</p>'
        if not found
        else f'<ul class="findings">{"".join(_finding(f) for f in found)}</ul>'
    )
    lvl = f"Level {level[0]} ({level[1]}) · {level[2]:g}/100" if level else ""
    return (
        f'<div class="card {set_name}"><div class="head"><code>{html.escape(file)}</code>'
        f'<span class="lvl">{lvl}</span></div>'
        f'<img src="{plantuml}/svg/{plantuml_encode(text)}" alt="{html.escape(file)}, drawn by PlantUML" loading="lazy">'
        f"{verdict}</div>"
    )


def _gate(result: dict) -> str:
    counts: dict[str, int] = {}
    for fs in result["findings"].values():
        for f in fs:
            counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    if result["exit"] == 0:
        return '<span class="pass">✔ Gate passes</span> no finding at major or worse'
    detail = ", ".join(f"{n} {s}" for s, n in sorted(counts.items(), key=lambda kv: _ORDER.index(kv[0])))
    return f'<span class="fail">✖ Gate fails</span> {detail}'


_ORDER = ["blocker", "critical", "major", "minor", "info"]


def _trace(result: dict) -> str:
    t = result["trace"]
    s = t["summary"]
    rows = []
    for r in t["requirements"]:
        files = sorted({Path(x["file"]).stem for x in r["coveredBy"]})
        state = ", ".join(files) if files else '<span class="miss">not covered by any diagram</span>'
        rows.append(f"<tr><td><code>{html.escape(r['id'])}</code></td><td>{state}</td></tr>")
    for u in t["unknownReferences"]:
        rows.append(
            f'<tr><td><code>{html.escape(u["id"])}</code></td>'
            f'<td><span class="miss">cited, but not a known requirement</span></td></tr>'
        )
    return (
        f"<p>{s['coveredCount']} of {s['requirementCount']} requirements covered</p>"
        f'<table class="trace">{"".join(rows)}</table>'
    )


def build(out: Path, plantuml: str) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    results = {name: analyse(name) for name in SETS}
    for name in SETS:  # the tool's own HTML report, one per set
        _run(["score", str(DIAGRAMS / name), "-f", "html", "-o", str(out / f"report-{name}.html"), "-c", str(CONFIG)])
    rows = "".join(
        f'<h2>{html.escape(title)}</h2><div class="pair">'
        + "".join(_card(name, file, results[name], plantuml) for name in SETS)
        + "</div>"
        for file, title in ARTEFACTS
    )
    page = _PAGE.format(
        css=_CSS,
        gate_ok=_gate(results["compliant"]),
        gate_ko=_gate(results["non-compliant"]),
        rows=rows,
        trace_ok=_trace(results["compliant"]),
        trace_ko=_trace(results["non-compliant"]),
    )
    (out / "index.html").write_text(page, encoding="utf-8")
    return results


_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>pumllint demo: a credit application</title><style>{css}</style></head><body><main>
<p class="kicker">pumllint demo · one business case, drawn twice</p>
<h1>A credit application: which diagrams can the next reader trust?</h1>
<p class="lead">Four linked diagrams of the same case, each in two versions. Every one of them renders.
The left column is <b>compliant</b>; the right column has deliberate defects of the kind analysts meet every day.
Edit any file under <code>diagrams/</code> and reload this page.</p>
<div class="pair top"><div class="card compliant"><h3>Compliant set</h3><p>{gate_ok}</p>
<p><a href="report-compliant.html">Maturity report</a></p></div>
<div class="card non-compliant"><h3>Non-compliant set</h3><p>{gate_ko}</p>
<p><a href="report-non-compliant.html">Maturity report</a></p></div></div>
<p class="lead note">Notice that the non-compliant diagrams still reach Level 4. The level says how complete and precise
a drawing is overall; the gate looks at how serious each finding is. One critical or major finding is enough to stop a hand-off.</p>
{rows}
<h2>Requirements: is every one of them drawn somewhere?</h2>
<div class="pair"><div class="card compliant">{trace_ok}</div><div class="card non-compliant">{trace_ko}</div></div>
<p class="foot">Findings by <code>pumllint</code> with the settings in <code>diagrams/lint.toml</code>;
pictures by a local PlantUML server. Nothing leaves this computer.</p>
</main></body></html>"""

_CSS = """
:root { --ink:#1E2B22; --muted:#4A5A4E; --title:#3E6B48; --line:#C3CDBD; --bg:#F7F8F5; --ok:#3E6B48; --ko:#B03A2E; --lime:#9BD12E; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:16px/1.5 system-ui,-apple-system,"Segoe UI",Calibri,sans-serif; }
main { max-width:1280px; margin:0 auto; padding:28px 16px 48px; }
.kicker { margin:0; font-weight:700; color:var(--muted); }
h1 { color:var(--title); font-size:1.9rem; line-height:1.2; margin:4px 0 8px; }
h2 { color:var(--title); font-size:1.25rem; margin:32px 0 10px; }
h3 { margin:0 0 6px; }
.lead { max-width:80ch; }
.note { margin-top:12px; color:var(--muted); }
.pair { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
@media (max-width:800px) { .pair { grid-template-columns:1fr; } }
.card { background:#fff; border:1px solid var(--line); border-top:5px solid var(--ok); border-radius:6px; padding:12px 14px; min-width:0; }
.card.non-compliant { border-top-color:var(--ko); }
.head { display:flex; justify-content:space-between; gap:8px; flex-wrap:wrap; margin-bottom:8px; }
.lvl { color:var(--muted); font-size:.9rem; }
.card img { display:block; max-width:100%; height:auto; margin:6px auto 10px; }
.ok, .pass { color:var(--ok); font-weight:700; }
.fail, .miss { color:var(--ko); font-weight:700; }
.findings { list-style:none; padding:0; margin:0; display:grid; gap:8px; }
.f { border-left:4px solid var(--line); padding:4px 10px; }
.f.critical, .f.blocker, .f.major { border-left-color:var(--ko); }
.rule { font-family:ui-monospace,Menlo,Consolas,monospace; font-size:.85rem; color:var(--muted); }
.msg { color:var(--muted); font-size:.9rem; }
table.trace { border-collapse:collapse; width:100%; }
.trace td { border-top:1px solid var(--line); padding:5px 6px; vertical-align:top; }
code { font-family:ui-monospace,Menlo,Consolas,monospace; font-size:.92em; }
a { color:var(--title); }
.foot { margin-top:32px; color:var(--muted); font-size:.9rem; }
"""


class _Handler(SimpleHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (http.server's naming)
        if self.path in ("/", "/index.html") or self.path.startswith("/?"):
            build(self.server.out, self.server.plantuml)
        super().do_GET()


def serve(out: Path, plantuml: str, port: int) -> None:
    build(out, plantuml)
    server = ThreadingHTTPServer(("0.0.0.0", port), partial(_Handler, directory=str(out)))
    server.out, server.plantuml = out, plantuml
    print(f"pumllint demo on http://localhost:{port} (diagrams from {plantuml}); Ctrl+C stops it")
    server.serve_forever()


def cli(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("command", choices=("build", "serve"))
    p.add_argument("--out", type=Path, default=Path(os.environ.get("DEMO_OUT", HERE / "out")))
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--plantuml", default=os.environ.get("DEMO_PLANTUML_URL", "http://localhost:8080"))
    a = p.parse_args(argv)
    if a.command == "build":
        build(a.out, a.plantuml.rstrip("/"))
        print(f"wrote {a.out / 'index.html'}")
    else:
        serve(a.out, a.plantuml.rstrip("/"), a.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())

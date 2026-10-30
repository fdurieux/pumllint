"""The demo's web server: a menu of the seven scenarios, the report view,
and the store's saved queries. Standard library only (``http.server``);
the harness is run as a subprocess, never imported.

    python server.py                 # http://localhost:8080

Environment:
    KG_DEMO_PORT      port to listen on (8080)
    KG_NEO4J_URI      bolt URL the harness and the store probe use (bolt://localhost:7687;
                      the container sets bolt://neo4j:7687)
    KG_NEO4J_PASSWORD the store's password (kgpoc2026, the harness default)
    KG_BROWSER_URL    where the viewer's browser reaches Neo4j Browser (http://localhost:7474)
    KG_DEMO_RUNS      where re-runs land (kg_experiment/results/demo-runs); the published record
                      under kg_experiment/results/ is never written
    OPENAI_API_KEY    enables the arms mode; passed through to the harness, never stored
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cascade  # noqa: E402
import views  # noqa: E402

EXP = HERE.parent.parent
HARNESS = EXP / "harness"
RUNS_DIR = Path(os.environ.get("KG_DEMO_RUNS", str(EXP / "results" / "demo-runs")))
NEO4J_URI = os.environ.get("KG_NEO4J_URI", "bolt://localhost:7687")
NEO4J_PASSWORD = os.environ.get("KG_NEO4J_PASSWORD", "kgpoc2026")
BROWSER_URL = os.environ.get("KG_BROWSER_URL", "http://localhost:7474")
PORT = int(os.environ.get("KG_DEMO_PORT", "8080"))
INDEX = (HERE / "index.html").read_bytes()

# Saved Cypher for the store panel. Each runs in Neo4j Browser against the
# scenario currently loaded; the comment on each says which scenario shows it.
CYPHER = [
    {"id": "loaded", "title": "Which scenario is loaded",
     "text": "MATCH (a:Activity) WHERE a.id STARTS WITH 'act:extract:'\nRETURN a.id AS activity, a.at AS at, a.note AS note ORDER BY a.at"},
    {"id": "three-valued", "title": "The three-valued answer (D5; S1): asserted, documented absent, unknown",
     "text": ("// documented absence: every live assertion on the key says NONE\n"
              "MATCH (x:Assertion {key:'S-review|notified'}) RETURN x.id, x.value, x.status;\n"
              "// asserted: a value\n"
              "MATCH (x:Assertion {key:'S-refuse|notified'}) RETURN x.id, x.value, x.status;\n"
              "// unknown: no assertion at all (not a documented absence)\n"
              "MATCH (x:Assertion {key:'QuoteAPI|notified_after_screening'}) RETURN count(x) AS n")},
    {"id": "gate", "title": "The gate's view of one required key",
     "text": ("MATCH (x:Assertion {key:'P2|surcharge'})\n"
              "OPTIONAL MATCH (x)-[:SUPPORTED_BY]->(f:Fragment)\n"
              "OPTIONAL MATCH (v:Verification)-[:VERIFIES]->(x)\n"
              "OPTIONAL MATCH (ap:Approval)-[:APPROVES]->(x)\n"
              "RETURN x.id, x.value, x.basis, x.status, collect(DISTINCT f.locator) AS evidence,\n"
              "       collect(DISTINCT v.method) AS verified_by, count(DISTINCT ap) AS approvals")},
    {"id": "invalidation", "title": "The invalidation traversal (S6): changed fragments → assertions → verifications → Derived",
     "text": ("MATCH (a:Artefact)-[:CURRENT]->(cur:Version {tag:'v2'})\n"
              "MATCH (a)-[:HAS_VERSION]->(old:Version {tag:'v1'})-[:HAS_FRAGMENT]->(f:Fragment)\n"
              "WHERE NOT (cur)-[:HAS_FRAGMENT]->(f)\n"
              "MATCH (x:Assertion {status:'invalidated'})-[:SUPPORTED_BY]->(f)\n"
              "OPTIONAL MATCH (v:Verification)-[:VERIFIES]->(x)\n"
              "OPTIONAL MATCH (d:Derived)-[:USED_ASSERTION]->(x)\n"
              "OPTIONAL MATCH (succ:Assertion {key:x.key, version:'v2'})\n"
              "RETURN f.locator AS changed_fragment, x.id AS invalidated, x.value AS old_value,\n"
              "       collect(DISTINCT v.id + ' valid_until=' + coalesce(v.valid_until,'∅')) AS verifications_ended,\n"
              "       collect(DISTINCT d.id + ' suspect=' + toString(d.suspect)) AS derived,\n"
              "       collect(DISTINCT succ.id + ' ' + succ.value + ' ' + succ.status) AS successor")},
    {"id": "contradiction", "title": "The contradiction pairs (S4)",
     "text": ("MATCH (a:Assertion)-[:CONTRADICTS]->(b:Assertion) WHERE a.id < b.id\n"
              "OPTIONAL MATCH (g:Gap {kind:'conflict'})-[:CONCERNS]->(a)\n"
              "RETURN a.key AS key, a.artefact AS side_a, a.value AS value_a, b.artefact AS side_b, b.value AS value_b,\n"
              "       a.status AS status, collect(DISTINCT g.id) AS conflict_gaps")},
    {"id": "gaps", "title": "The gap census",
     "text": ("MATCH (g:Gap)\n"
              "OPTIONAL MATCH (g)-[:CONCERNS]->(t)\n"
              "RETURN g.kind AS kind, g.declared AS declared, count(DISTINCT g) AS gaps,\n"
              "       count(DISTINCT t) AS things_concerned ORDER BY kind")},
    {"id": "census", "title": "The status census",
     "text": "MATCH (x:Assertion) RETURN x.status AS status, x.basis AS basis, count(*) AS n ORDER BY status, basis"},
]


# ------------------------------------------------------------------ the store

def store_status() -> dict:
    """What the store holds, through the driver when it is installed."""
    out = {"uri": NEO4J_URI, "browser": BROWSER_URL, "reachable": False, "loaded": None, "census": None, "error": None}
    try:
        from neo4j import GraphDatabase, NotificationMinimumSeverity  # the harness's dependency, in the image
    except ImportError:
        out["error"] = "neo4j driver not installed: deterministic and arms modes need it"
        return out
    try:
        with GraphDatabase.driver(NEO4J_URI, auth=("neo4j", NEO4J_PASSWORD),
                                  notifications_min_severity=NotificationMinimumSeverity.OFF,
                                  connection_timeout=3) as d:
            with d.session() as s:
                acts = [r["id"] for r in s.run("MATCH (a:Activity) WHERE a.id STARTS WITH 'act:extract:' RETURN a.id AS id ORDER BY a.at")]
                st = {r["status"]: r["n"] for r in s.run("MATCH (x:Assertion) RETURN x.status AS status, count(*) AS n")}
                n = s.run("MATCH (n) RETURN count(n) AS n").single()["n"]
                r = s.run("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"]
        out.update(reachable=True, census={"nodes": n, "relationships": r, "assertions_by_status": st},
                   loaded=(acts[0].split(":")[2] if acts else None), activities=acts)
    except Exception as e:  # noqa: BLE001 — the message is the status
        out["error"] = str(e).splitlines()[0][:200]
    return out


# ------------------------------------------------------------------ runs

def _now() -> str:
    """UTC with its offset, so a browser in any zone parses it as the instant it is."""
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


class Runner:
    """One harness subprocess at a time: the community edition serves one
    database, so two loads would race."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.current: dict | None = None
        self.history: list[dict] = []

    def start(self, scenario: str, mode: str, n: int) -> dict:
        if scenario not in views.SCENARIOS:
            raise ValueError(f"unknown scenario {scenario}")
        if mode not in ("deterministic", "arms"):
            raise ValueError(f"unknown mode {mode}")
        if mode == "arms" and not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("arms mode needs OPENAI_API_KEY in the app's environment")
        with self.lock:
            if self.current and self.current["status"] == "running":
                raise RuntimeError("a run is already in progress; the store is one database")
            stamp = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
            out_dir = RUNS_DIR / stamp
            k = 2
            while out_dir.exists():
                out_dir = RUNS_DIR / f"{stamp}-{k}"
                k += 1
            out_dir.mkdir(parents=True)
            if scenario == "S6" and mode == "arms":
                # the record's stage 2 registers S1's first governed output as the
                # Derived artefact; give the re-run the same object to invalidate
                src = EXP / "results" / "S1" / "run1_G.py"
                if src.exists():
                    (out_dir / "S1").mkdir()
                    shutil.copy(src, out_dir / "S1" / "run1_G.py")
            cmd = [sys.executable, "run.py", "--scenarios", scenario, "--out", str(out_dir)]
            cmd += ["--deterministic"] if mode == "deterministic" else ["--n", str(n)]
            env = {**os.environ, "KG_NEO4J_URI": NEO4J_URI, "KG_NEO4J_PASSWORD": NEO4J_PASSWORD,
                   "PYTHONUNBUFFERED": "1", "KG_WORKERS": os.environ.get("KG_WORKERS", "2")}
            log = out_dir / f"{scenario}-{mode}.log"
            fh = open(log, "w", encoding="utf-8")  # noqa: SIM115 — closed when the process ends
            proc = subprocess.Popen(cmd, cwd=str(HARNESS), stdout=fh, stderr=subprocess.STDOUT, env=env)
            rec = {"id": out_dir.name, "scenario": scenario, "mode": mode, "n": n, "status": "running",
                   "started": _now(), "finished": None, "exit_code": None,
                   "out_dir": str(out_dir), "log": str(log), "source": f"demo-runs/{out_dir.name}", "cmd": " ".join(cmd)}
            self.current = rec
            threading.Thread(target=self._wait, args=(proc, fh, rec), daemon=True).start()
            return self.describe(rec)

    def _wait(self, proc, fh, rec) -> None:
        code = proc.wait()
        fh.close()
        rec.update(status="done" if code == 0 else "failed", exit_code=code, finished=_now())
        self.history.append(rec)

    def describe(self, rec: dict | None = None) -> dict | None:
        rec = rec or self.current
        if not rec:
            return None
        out = dict(rec)
        # elapsed is computed here, not in the browser: the browser's clock and zone are not ours
        end = dt.datetime.fromisoformat(rec["finished"]) if rec.get("finished") else dt.datetime.now(dt.timezone.utc)
        out["elapsed_s"] = int((end - dt.datetime.fromisoformat(rec["started"])).total_seconds())
        try:
            text = Path(rec["log"]).read_text(encoding="utf-8")
        except OSError:
            text = ""
        out["log_text"] = text[-20000:]
        return out


RUNNER = Runner()


def list_runs() -> list[dict]:
    out = []
    if RUNS_DIR.exists():
        for d in sorted(RUNS_DIR.iterdir(), reverse=True):
            if not d.is_dir():
                continue
            scenarios = sorted(p.name for p in d.iterdir() if p.is_dir() and (p / "deterministic.json").exists())
            modes = sorted({("arms" if list((d / s).glob("run*_G.json")) else "deterministic") for s in scenarios})
            out.append({"id": d.name, "scenarios": scenarios, "modes": modes, "logs": sorted(p.name for p in d.glob("*.log"))})
    return out


# ------------------------------------------------------------------ HTTP

class Handler(BaseHTTPRequestHandler):
    server_version = "kg-demo/1"

    def log_message(self, fmt, *args):  # quieter than the default
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, body: bytes, ctype: str = "application/json; charset=utf-8") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        parts = [p for p in u.path.split("/") if p]
        try:
            if not parts or parts == ["index.html"]:
                return self._send(200, INDEX, "text/html; charset=utf-8")
            if parts == ["health"]:
                return self._json({"ok": True})
            if parts[:2] == ["api", "scenarios"]:
                st = store_status()
                return self._json({"scenarios": views.scenario_list(RUNS_DIR), "store": st,
                                   "arms_enabled": bool(os.environ.get("OPENAI_API_KEY")),
                                   "deterministic_enabled": st["reachable"],
                                   "runs_dir": str(RUNS_DIR), "run": RUNNER.describe()})
            if parts[:2] == ["api", "results"] and len(parts) == 3:
                sc = parts[2]
                source = q.get("source", [views.default_source(sc)])[0]
                view = views.build(sc, source, RUNS_DIR)
                view["cascade"] = {arm: cascade.render(view["systemic"], arm, title=f"{sc}, arm {arm}") for arm in ("G", "B")}
                return self._json(view)
            if parts == ["api", "store"]:
                return self._json(store_status())
            if parts == ["api", "cypher"]:
                return self._json(CYPHER)
            if parts == ["api", "runs"]:
                return self._json({"runs": list_runs(), "current": RUNNER.describe()})
            if parts == ["api", "run"]:
                return self._json(RUNNER.describe() or {"status": "idle"})
            if parts[:2] == ["api", "cascade"] and len(parts) == 4:
                return self._send(200, cascade.render(views.SYSTEMIC[parts[2]], parts[3]).encode("utf-8"), "image/svg+xml")
            return self._json({"error": "not found"}, 404)
        except FileNotFoundError as e:
            return self._json({"error": str(e)}, 404)
        except KeyError as e:
            return self._json({"error": f"unknown: {e}"}, 404)
        except Exception as e:  # noqa: BLE001
            return self._json({"error": str(e)}, 500)

    def do_POST(self) -> None:  # noqa: N802
        u = urllib.parse.urlparse(self.path)
        parts = [p for p in u.path.split("/") if p]
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._json({"error": "body must be JSON"}, 400)
        if parts == ["api", "run"]:
            try:
                rec = RUNNER.start(str(body.get("scenario", "")), str(body.get("mode", "")), int(body.get("n", 1)))
                return self._json(rec, 202)
            except (ValueError, RuntimeError) as e:
                return self._json({"error": str(e)}, 409 if isinstance(e, RuntimeError) else 400)
        return self._json({"error": "not found"}, 404)


def main() -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"kg demo on http://0.0.0.0:{PORT}  store {NEO4J_URI}  runs {RUNS_DIR}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()

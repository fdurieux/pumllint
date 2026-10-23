"""Run the pre-registered scenario set against ONE implementation through its
harness adapter, writing canonical artefacts for compare.py.

    run_impl.py --adapter MODULE --exe EXE --chain daily.sh --inputs DIR --out DIR

The adapter module must be importable (PYTHONPATH). `--chain` is a daily.sh
whose events.sh/dashboard.sh sit beside it."""
import argparse
import importlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--adapter", required=True)
ap.add_argument("--exe", required=True)
ap.add_argument("--chain", required=True)
ap.add_argument("--inputs", required=True)
ap.add_argument("--out", required=True)
args = ap.parse_args()

A = importlib.import_module(args.adapter)
IN = Path(args.inputs).resolve()
OUT = Path(args.out).resolve()
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
WORK = Path(tempfile.mkdtemp(prefix="jdl-work-"))
AAPL_CSV = (IN / "aapl_csv_path.txt").read_text().strip()
UTC = timezone.utc


def T(y, m, d, h=12):
    return datetime(y, m, d, h, 0, 0, tzinfo=UTC)


def universe(name):
    return A.load_universe(str(IN / "universes" / f"{name}.toml"))


def collectors(fixture_set, providers=("eodhd", "binance")):
    c = {}
    for p in providers:
        d = IN / "fixtures" / fixture_set / p
        if d.exists():
            c[p] = A.make_collector(p, str(d))
    return c


def normalise(text, store=None):
    text = text.replace(str(IN), "<inputs>").replace(str(WORK), "<work>")
    if store:
        text = text.replace(str(store), "<store>")
    text = text.replace(AAPL_CSV, "<aapl.csv>")
    text = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)", "<stamp>", text)
    text = re.sub(r"\d{4}-\d{2}-\d{2}T\d{6}Z", "<runstamp>", text)      # JEF_RUN_STAMP
    text = re.sub(r"--t[01] \d{9,11}", "--tN <epoch>", text)              # stage clocks
    return text


def canon(obj, store=None):
    s = json.dumps(obj, indent=1, sort_keys=True, default=str)
    return normalise(s, store)


class Scenario:
    def __init__(self, sid):
        self.sid = sid
        self.dir = OUT / sid
        self.dir.mkdir()
        self.store = WORK / f"{sid}-store"
        self.store.mkdir()

    def json(self, name, obj):
        (self.dir / f"{name}.json").write_text(canon(obj, self.store) + "\n")

    def frame(self, name, df):
        df = df.copy()
        for col in df.columns:
            if str(df[col].dtype).startswith("datetime64"):
                df[col] = df[col].astype(str)
        (self.dir / f"{name}.frame.csv").write_text(df.to_csv(index=False))

    def export(self, exchange, symbol):
        self.frame(f"export_{exchange}_{symbol}", A.export_frame(str(self.store), exchange, symbol))
        sf = A.stored_frame(str(self.store), exchange, symbol)
        if "timestamp" in sf.columns:
            sf = sf.sort_values("timestamp").reset_index(drop=True)
        self.frame(f"stored_{exchange}_{symbol}", sf[sorted(sf.columns)])
        (self.dir / f"stored_{exchange}_{symbol}.columns.txt").write_text("\n".join(sf.columns) + "\n")

    def actions(self, symbol):
        st = A.actions_state(str(self.store), symbol)
        st["last_updated"] = "<stamp>" if st.get("last_updated") else None
        self.json(f"actions_{symbol}", st)

    def sync(self, uni, fixture_set="base", now=None, **kw):
        lines = []
        results, ok = A.run_sync(uni, str(self.store), now=now,
                                 collectors=collectors(fixture_set) if fixture_set else {},
                                 out=lines.append, **kw)
        self.json("sync_summary", A.sync_summary(results, ok))
        (self.dir / "sync_out.txt").write_text(normalise("\n".join(lines), self.store) + "\n")
        return results, ok

    def status(self, uni, name="status", now=None, **kw):
        doc, rc = A.status_json(uni, str(self.store), now=now, **kw)
        self.json(name, {"exit": rc, "document": doc})
        return doc, rc

    def copy_store_from(self, other):
        shutil.rmtree(self.store)
        shutil.copytree(other.store, self.store)


REGISTRY = []


def scenario(fn):
    REGISTRY.append(fn)
    return fn


STORES = {}


@scenario
def s01_first_fill(s):
    s.sync(universe("r1"), now=T(2024, 1, 6))
    for ex, sym in [("eodhd", "TLT.US"), ("eodhd", "BTC-USD.CC"), ("binance", "BTCUSDT"), ("yahoo", "AAPL")]:
        s.export(ex, sym)
    s.actions("TLT.US")
    STORES["r1"] = s


@scenario
def s02_status_fresh(s):
    s.copy_store_from(STORES["r1"])
    s.status(universe("r1"), now=T(2024, 1, 6))


@scenario
def s03_status_stale(s):
    s.copy_store_from(STORES["r1"])
    s.status(universe("r1"), "status_jan10", now=T(2024, 1, 10))
    s.status(universe("r1"), "status_jan07", now=T(2024, 1, 7))
    s.status(universe("r1"), "status_jan08", now=T(2024, 1, 8))


@scenario
def s04_status_spread(s):
    s.copy_store_from(STORES["r1"])
    s.status(universe("r1"), "status_tight", now=T(2024, 1, 6), spread_threshold=0.0001)
    s.status(universe("r1"), "status_tight_alerts", now=T(2024, 1, 6), spread_threshold=0.0001, spread_alerts=True)
    s.status(universe("r1"), "status_knobs", now=T(2024, 1, 6), window=3, staleness_k=1, gap_k=1,
             resolution_window=5, resolution_k=0.9, flat_k=0.01, jump_threshold=0.01)


@scenario
def s05_rerun_same_day(s):
    s.copy_store_from(STORES["r1"])
    s.sync(universe("r1"), now=T(2024, 1, 6))
    s.export("eodhd", "TLT.US")
    s.actions("TLT.US")


@scenario
def s06_rerun_force_actions(s):
    s.copy_store_from(STORES["r1"])
    s.sync(universe("r1"), now=T(2024, 1, 6), force_actions=True)


@scenario
def s07_tail_revision(s):
    s.copy_store_from(STORES["r1"])
    s.sync(universe("r1"), fixture_set="tlt_revised", now=T(2024, 1, 6), assets=["TLT"])
    s.export("eodhd", "TLT.US")


@scenario
def s08_btc_tail2(s):
    s.copy_store_from(STORES["r1"])
    s.sync(universe("r1"), fixture_set="btc_tail2", now=T(2024, 1, 6), assets=["BTC"], providers=["eodhd"], tail=2)
    s.export("eodhd", "BTC-USD.CC")


@scenario
def s09_inverted_end(s):
    s.copy_store_from(STORES["r1"])
    s.sync(universe("btc_end03"), now=T(2024, 1, 6), tail=2)   # tail start 01-04 > end 01-03
    s.export("eodhd", "BTC-USD.CC")


@scenario
def s10_aapl_split(s):
    s.sync(universe("aapl_eod"), now=T(2020, 9, 8))
    s.export("eodhd", "AAPL.US")
    s.actions("AAPL.US")
    STORES["aapl"] = s


@scenario
def s11_status_aapl(s):
    s.copy_store_from(STORES["aapl"])
    for tag, now in [("sep04_22h", T(2020, 9, 4, 22)), ("sep05", T(2020, 9, 5)), ("sep08", T(2020, 9, 8)), ("sep09", T(2020, 9, 9)), ("sep15", T(2020, 9, 15))]:
        s.status(universe("aapl_eod"), f"status_{tag}", now=now)


@scenario
def s12_today_dated(s):
    s.sync(universe("tlt"), now=T(2020, 3, 13, 20))
    s.status(universe("tlt"), now=T(2020, 3, 13, 20))


@scenario
def s13_crypto_guard(s):
    s.sync(universe("btc_noend"), now=T(2024, 1, 6))
    s.export("eodhd", "BTC-USD.CC")


@scenario
def s14_paused(s):
    s.sync(universe("paused_tlt"), now=T(2024, 1, 6))
    s.json("legs", A.select_legs(universe("paused_tlt")))
    try:
        A.select_legs(universe("paused_tlt"), assets=["TLT"])
        s.json("paused_named", {"raised": None})
    except Exception as exc:
        s.json("paused_named", {"raised": type(exc).__name__, "message": str(exc)})
    for assets, providers in [(["NOPE"], None), (None, ["nope"])]:
        try:
            A.select_legs(universe("r1"), assets=assets, providers=providers)
            res = {"raised": None}
        except Exception as exc:
            res = {"raised": type(exc).__name__, "message": str(exc)}
        s.json(f"select_{assets or providers}", res)


@scenario
def s15_jump(s):
    s.sync(universe("tlt"), fixture_set="tlt_jump", now=T(2020, 3, 16))
    s.export("eodhd", "TLT.US")
    s.status(universe("tlt"), now=T(2020, 3, 16))
    s.status(universe("tlt"), "status_misdeclared", now=T(2020, 3, 16))


@scenario
def s16_zero_volume(s):
    s.sync(universe("btc_noend"), fixture_set="btc_zero_volume", now=T(2024, 1, 6))
    s.export("eodhd", "BTC-USD.CC")
    s.status(universe("btc_noend"), now=T(2024, 1, 6))


@scenario
def s17_misdeclared(s):
    s.sync(universe("tlt_misdeclared"), now=T(2020, 3, 16))
    s.status(universe("tlt_misdeclared"), now=T(2020, 3, 16))


@scenario
def s18_import_export(s):
    rows = A.import_csv(str(s.store), AAPL_CSV, "yahoo", "AAPL", "stock")
    s.json("import", {"rows": rows})
    s.export("yahoo", "AAPL")
    rows2 = A.import_csv(str(s.store), AAPL_CSV, "yahoo", "AAPL", "stock")
    s.json("import_again", {"rows": rows2})


@scenario
def s19_dry_run(s):
    s.sync(A.load_universe(None), fixture_set=None, dry_run=True, now=T(2026, 10, 23))
    s.json("legs_packaged", A.select_legs(A.load_universe(None)))


@scenario
def s20_legs(s):
    s.json("legs_r1", A.select_legs(universe("r1")))
    s.json("legs_r1_eodhd", A.select_legs(universe("r1"), providers=["eodhd"]))


def cli(s, name, argv, cwd=None, env_extra=None):
    env = dict(os.environ)
    env.update(env_extra or {})
    p = subprocess.run([args.exe] + argv, capture_output=True, text=True, cwd=cwd or str(WORK), env=env)
    s.json(f"cli_{name}", {"argv": [normalise(a, s.store) for a in argv], "exit": p.returncode,
                           "stdout": normalise(p.stdout, s.store), "stderr": normalise(p.stderr, s.store)})


@scenario
def s21_cli_refusals(s):
    U = IN / "universes"
    for bad in sorted(p.stem for p in U.glob("bad_*.toml")):
        cli(s, bad, ["sync", "--universe", str(U / f"{bad}.toml"), "--dry-run"])
    cli(s, "unknown_asset", ["sync", "--universe", str(U / "r1.toml"), "--asset", "NOPE", "--dry-run"])
    cli(s, "unknown_provider", ["sync", "--universe", str(U / "r1.toml"), "--provider", "nope", "--dry-run"])
    cli(s, "paused_only", ["sync", "--universe", str(U / "paused_tlt.toml"), "--asset", "TLT", "--dry-run"])
    cli(s, "tail_zero", ["sync", "--universe", str(U / "r1.toml"), "--tail", "0", "--dry-run"])
    cli(s, "status_unknown_asset", ["status", "--universe", str(U / "r1.toml"), "--asset", "NOPE", "--store", str(s.store)])
    cli(s, "export_empty", ["export", "--symbol", "GHOST", "--exchange", "eodhd", "--output", str(WORK / "ghost.csv"), "--store", str(s.store)])
    cli(s, "import_missing_type", ["import-csv", "--csv", AAPL_CSV, "--symbol", "AAPL", "--store", str(s.store)])
    cli(s, "validate_bad", ["validate", str(IN / "bad.csv")])
    cli(s, "validate_missing", ["validate", str(IN / "no-such.csv")])
    cli(s, "no_args", [])
    cli(s, "bad_subcommand", ["frobnicate"])


@scenario
def s22_cli_surface(s):
    U = IN / "universes"
    cli(s, "universe", ["universe"])
    cli(s, "universe_r1", ["universe", "--universe", str(U / "r1.toml")])
    cli(s, "universe_paused", ["universe", "--universe", str(U / "paused_tlt.toml")])
    cli(s, "dry_run_r1", ["sync", "--universe", str(U / "r1.toml"), "--dry-run", "--store", str(s.store)])
    cli(s, "dry_run_packaged", ["sync", "--dry-run", "--store", str(s.store)])
    cli(s, "validate_aapl", ["validate", AAPL_CSV])
    cli(s, "validate_aapl_minrows", ["validate", AAPL_CSV, "--min-rows", "20000"])
    cli(s, "import_csv", ["import-csv", "--csv", AAPL_CSV, "--symbol", "AAPL", "--asset-type", "stock", "--store", str(s.store)])
    cli(s, "export_aapl", ["export", "--symbol", "AAPL", "--exchange", "yahoo", "--output", str(WORK / "aapl_export.csv"), "--store", str(s.store)])
    exported = pd.read_csv(WORK / "aapl_export.csv")
    s.frame("export_cli_yahoo_AAPL", exported)
    cli(s, "status_empty_store", ["status", "--universe", str(U / "tlt.toml"), "--store", str(s.store)])
    cli(s, "status_empty_store_json", ["status", "--universe", str(U / "tlt.toml"), "--store", str(s.store), "--json"])
    cli(s, "differential_csv", ["differential", "--a-symbol", "AAPL", "--a-exchange", "yahoo", "--b-csv", AAPL_CSV, "--store", str(s.store)])
    for sub in ["validate", "sync-actions", "load", "adjust", "import-csv", "export", "differential", "sync", "status", "universe"]:
        cli(s, f"help_{sub}", [sub, "--help"])
    cli(s, "help", ["--help"])


@scenario
def s23_cli_on_store(s):
    s.copy_store_from(STORES["r1"])
    cli(s, "differential_venues", ["differential", "--a-symbol", "BTC-USD.CC", "--a-exchange", "eodhd", "--b-symbol", "BTCUSDT", "--b-exchange", "binance", "--store", str(s.store)])
    cli(s, "differential_tolerance", ["differential", "--a-symbol", "BTC-USD.CC", "--a-exchange", "eodhd", "--b-symbol", "BTCUSDT", "--b-exchange", "binance", "--tolerance", "0.5", "--store", str(s.store)])
    cli(s, "export_tlt", ["export", "--symbol", "TLT.US", "--exchange", "eodhd", "--output", str(WORK / "tlt.csv"), "--store", str(s.store)])
    cli(s, "adjust_tlt", ["adjust", "--symbol", "TLT.US", "--exchange", "eodhd", "--store", str(s.store)])
    cli(s, "adjust_crypto_refused", ["adjust", "--symbol", "BTC-USD.CC", "--exchange", "eodhd", "--store", str(s.store)])
    cli(s, "status_table", ["status", "--universe", str(IN / "universes" / "r1.toml"), "--store", str(s.store)])
    cli(s, "status_json_now", ["status", "--universe", str(IN / "universes" / "r1.toml"), "--store", str(s.store), "--json"])


# ---- the chain -------------------------------------------------------------
STUB = "#!/usr/bin/env bash\nprintf '%s\\n' \"{name} $*\" >> \"$STUB_LOG\"\n"
STUB_TAILS = {
    "jef-data": 'case "$1" in\n  sync)   exit "${STUB_EXIT_SYNC:-0}" ;;\n  status) exit "${STUB_EXIT_STATUS:-0}" ;;\nesac\nexit 0\n',
    "jef-binning": 'for arg in "$@"; do\n  if [[ "$arg" == "${STUB_BINNING_FAIL_ASSET:-}" ]]; then exit 1; fi\ndone\nexit 0\n',
    "aws": 'for arg in "$@"; do\n  if [[ "$arg" == "-" ]]; then cat > /dev/null; fi\ndone\nexit "${STUB_EXIT_AWS:-0}"\n',
    "curl": "exit 1\n",
    "python3": "exit 1\n",
}


def chain_case(s, name, env_extra=None, argv=()):
    bindir = WORK / f"{s.sid}-bin"
    bindir.mkdir(exist_ok=True)
    for n, tail in STUB_TAILS.items():
        p = bindir / n
        p.write_text(STUB.format(name=n) + tail)
        p.chmod(p.stat().st_mode | stat.S_IEXEC)
    app = WORK / f"{s.sid}-app-{name}"
    app.mkdir(exist_ok=True)
    log = WORK / f"{s.sid}-{name}.log"
    log.write_text("")
    env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}", "STUB_LOG": str(log),
           "JEF_APP_DIR": str(app), "JEF_S3_BUCKET": "test-bucket",
           "JEF_EVENT_DIR": str(WORK / f"{s.sid}-{name}-events"),
           "JEF_DASH_DIR": str(WORK / f"{s.sid}-{name}-dash")}
    env.pop("JEF_ASSETS", None)
    for k, v in (env_extra or {}).items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    p = subprocess.run(["bash", args.chain] + list(argv), env=env, capture_output=True, text=True, timeout=600)
    calls = [normalise(ln, s.store) for ln in log.read_text().splitlines() if ln]
    calls = [re.sub(r"\d{4}-\d{2}-\d{2}", "<date>", c).replace(str(app), "<app>") for c in calls]
    out = re.sub(r"\d{4}-\d{2}-\d{2}", "<date>", normalise(p.stdout, s.store)).replace(str(app), "<app>")
    s.json(f"chain_{name}", {"exit": p.returncode, "calls": calls, "stdout": out,
                             "stderr_tail": normalise(p.stderr, s.store)[-800:]})


@scenario
def s24_chain(s):
    chain_case(s, "green")
    chain_case(s, "sync_red", {"STUB_EXIT_SYNC": "1"})
    chain_case(s, "status_red", {"STUB_EXIT_STATUS": "1"})
    chain_case(s, "binning_red_tlt", {"STUB_BINNING_FAIL_ASSET": "TLT"})
    chain_case(s, "no_bucket", {"JEF_S3_BUCKET": None})
    chain_case(s, "assets_btc", {"JEF_ASSETS": "BTC"})
    chain_case(s, "digest_given", {"JEF_IMAGE_DIGEST": "sha256:deadbeef"})
    chain_case(s, "override", argv=["echo", "override-ran"])


for fn in REGISTRY:
    sid = fn.__name__
    s = Scenario(sid)
    try:
        fn(s)
    except Exception as exc:  # the artefact IS the failure
        (s.dir / "error.json").write_text(canon({"type": type(exc).__name__, "message": str(exc),
                                                 "trace": traceback.format_exc()[-1500:]}, s.store) + "\n")
        print(f"{sid}: ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
    else:
        print(f"{sid}: ok ({len(list(s.dir.iterdir()))} artefacts)")

import hashlib
manifest = {p.relative_to(OUT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(OUT.rglob("*")) if p.is_file()}
(OUT / "MANIFEST.sha256.json").write_text(json.dumps(manifest, indent=1))
print(f"{len(manifest)} artefacts -> {OUT}")
shutil.rmtree(WORK, ignore_errors=True)

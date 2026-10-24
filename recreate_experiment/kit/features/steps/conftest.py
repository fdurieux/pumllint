"""Step definitions for the kit's executable specification.

The implementation under test is reached ONLY through:
  * the executable named by JDL_UNDER_TEST (default `jef-data`; split like a
    shell word list, so `python -m mypkg` works),
  * the chain script named by JDL_CHAIN (default `deploy/daily.sh`; its
    sibling `events.sh` and `dashboard.sh` are copied with it),
  * the adapter module named by JDL_ADAPTER (default `jdl_adapter`), imported
    with importlib and used only through the fixed harness interface.
"""
import importlib
import json
import math
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pandas.testing as pdt
import pytest
from pytest_bdd import given, parsers, then, when

FEATURES = Path(__file__).resolve().parent.parent
FIXTURES = FEATURES / "fixtures"

STRING_COLUMNS = ("symbol", "exchange", "asset_type", "asset_subtype",
                  "currency", "price_basis")
STORE_COLUMNS = ["timestamp", "datetime", "open", "high", "low", "close",
                 "volume", "symbol", "exchange", "asset_type", "asset_subtype",
                 "adjustment_factor", "open_raw", "high_raw", "low_raw",
                 "close_raw", "volume_raw", "adjusted_close",
                 "cumulative_split_factor", "currency", "price_basis"]


def pytest_bdd_apply_tag(tag, function):
    """Requirement tags (@JDL-NNN) are traceability, not pytest markers."""
    return True


# ---------------------------------------------------------------- plumbing
def adapter():
    return importlib.import_module(os.environ.get("JDL_ADAPTER", "jdl_adapter"))


def executable():
    return shlex.split(os.environ.get("JDL_UNDER_TEST", "jef-data"))


def chain_script():
    return Path(os.environ.get("JDL_CHAIN", "deploy/daily.sh")).resolve()


def parse_now(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def parse_options(text):
    """`tail=3, force_actions=true, assets=A|B` -> kwargs."""
    out = {}
    for part in [p.strip() for p in text.split(",") if p.strip()]:
        key, value = [x.strip() for x in part.split("=", 1)]
        if key in ("assets", "providers"):
            out[key] = value.split("|")
        elif value in ("true", "false"):
            out[key] = value == "true"
        elif re.fullmatch(r"-?\d+", value):
            out[key] = int(value)
        else:
            out[key] = float(value)
    return out


@pytest.fixture
def ctx(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    store = tmp_path / "store"
    store.mkdir()
    return SimpleNamespace(tmp=tmp_path, work=work, store=store,
                           universe_path=None, _universe=None, collectors={},
                           log=[], results=None, ok=None, error=None,
                           status=None, status_rc=None, proc=None, legs=None,
                           chain=None, extra_env={})


def render(ctx, text):
    """Substitute the scenario's placeholders in a command or expectation."""
    return (text.replace("{store}", str(ctx.store))
            .replace("{work}", str(ctx.work))
            .replace("{fixtures}", str(FIXTURES))
            .replace("{tmp}", str(ctx.tmp)))


def universe(ctx):
    if ctx._universe is None:
        ctx._universe = adapter().load_universe(
            None if ctx.universe_path is None else str(ctx.universe_path))
    return ctx._universe


def number(text):
    text = text.strip()
    if text in ("NaN", "nan"):
        return float("nan")
    return float(text)


def same_number(a, b):
    if isinstance(a, float) and math.isnan(a):
        return isinstance(b, float) and math.isnan(b)
    return a == b


# ---------------------------------------------------------------- Given
@given("an empty store")
def empty_store(ctx):
    assert ctx.store.is_dir() and not any(ctx.store.iterdir())


@given(parsers.parse('the universe fixture "{name}"'))
def universe_fixture(ctx, name):
    text = (FIXTURES / "universes" / name).read_text(encoding="utf-8")
    target = ctx.work / "universe.toml"
    target.write_text(render(ctx, text), encoding="utf-8")
    ctx.universe_path = target
    ctx._universe = None


@given("the universe file:")
def universe_file(ctx, docstring):
    target = ctx.work / "universe.toml"
    target.write_text(render(ctx, docstring) + "\n", encoding="utf-8")
    ctx.universe_path = target
    ctx._universe = None


@given("the packaged universe")
def packaged_universe(ctx):
    ctx.universe_path = None
    ctx._universe = None


@given(parsers.parse('the "{provider}" provider replays "{fixture_set}"'))
def provider_replays(ctx, provider, fixture_set):
    ctx.collectors[provider] = adapter().make_collector(
        provider, str(FIXTURES / "http" / fixture_set))


@given(parsers.parse('the store holds "{csv}" as {exchange}/{symbol} declared {asset_type}'))
def store_holds_csv(ctx, csv, exchange, symbol, asset_type):
    adapter().import_csv(str(ctx.store), str(FIXTURES / "csv" / csv),
                         exchange, symbol, asset_type)


@given(parsers.parse('the work directory holds the CSV "{csv}" as "{name}"'))
def work_csv(ctx, csv, name):
    target = ctx.work / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIXTURES / "csv" / csv, target)


def _write_actions(ctx, symbol, kind, stamp, items):
    path = ctx.store / "corporate_actions" / kind / (symbol.replace("/", "_") + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"symbol": symbol, "exchange": "eodhd", "last_updated": stamp, kind: items}
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


@given(parsers.parse('the splits file of "{symbol}" stamped "{stamp}" with splits:'))
def splits_file(ctx, symbol, stamp, datatable):
    header, *rows = datatable
    items = [{"date": r[0], "split": r[1], "ratio": float(r[2])} for r in rows]
    _write_actions(ctx, symbol, "splits", stamp, items)
    _write_actions(ctx, symbol, "dividends", stamp, [])


@given(parsers.parse('the splits file of "{symbol}" stamped "{stamp}" with no splits'))
def splits_file_empty(ctx, symbol, stamp):
    _write_actions(ctx, symbol, "splits", stamp, [])
    _write_actions(ctx, symbol, "dividends", stamp, [])


@given(parsers.parse('sync ran at "{now}"'))
def sync_ran(ctx, now):
    _sync(ctx, now, {})
    assert ctx.error is None, ctx.error


@given(parsers.parse('sync ran at "{now}" with options "{opts}"'))
def sync_ran_opts(ctx, now, opts):
    _sync(ctx, now, parse_options(opts))
    assert ctx.error is None, ctx.error


# ---------------------------------------------------------------- When: adapter
@when(parsers.parse('sync runs at "{now}"'))
def run_sync(ctx, now):
    _sync(ctx, now, {})


@when(parsers.parse('sync runs at "{now}" with options "{opts}"'))
def run_sync_opts(ctx, now, opts):
    _sync(ctx, now, parse_options(opts))


def _sync(ctx, now, kwargs):
    ctx.log = []
    ctx.error = None
    try:
        ctx.results, ctx.ok = adapter().run_sync(
            universe(ctx), str(ctx.store), now=parse_now(now),
            collectors=dict(ctx.collectors), out=ctx.log.append, **kwargs)
    except Exception as exc:  # a refusal; the scenario asserts on it
        ctx.error = exc


@when(parsers.parse('status runs at "{now}"'))
def run_status(ctx, now):
    _status(ctx, now, {})


@when(parsers.parse('status runs at "{now}" with options "{opts}"'))
def run_status_opts(ctx, now, opts):
    _status(ctx, now, parse_options(opts))


def _status(ctx, now, kwargs):
    ctx.error = None
    try:
        ctx.status, ctx.status_rc = adapter().status_json(
            universe(ctx), str(ctx.store), now=parse_now(now), **kwargs)
    except Exception as exc:
        ctx.error = exc


@when("the legs are selected")
def select(ctx):
    _select(ctx, {})


@when(parsers.parse('the legs are selected with options "{opts}"'))
def select_opts(ctx, opts):
    _select(ctx, parse_options(opts))


def _select(ctx, kwargs):
    ctx.error = None
    try:
        ctx.legs = adapter().select_legs(universe(ctx), **kwargs)
    except Exception as exc:
        ctx.error = exc


@when("the universe is loaded")
def load_it(ctx):
    ctx.error = None
    try:
        universe(ctx)
    except Exception as exc:
        ctx.error = exc


# ---------------------------------------------------------------- When: executable
def _run(ctx, command, extra_env=None):
    argv = shlex.split(render(ctx, command))
    assert argv[0] == "jef-data", "commands are written as `jef-data ...`"
    env = dict(os.environ)
    env.pop("EODHD_API_KEY", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(ctx.extra_env)
    env.update(extra_env or {})
    ctx.proc = subprocess.run(executable() + argv[1:], cwd=ctx.work, env=env,
                              capture_output=True, text=True, timeout=600)


@given(parsers.re(r'EODHD_API_KEY is set to "(?P<key>[^"]*)"'))
def api_key(ctx, key):
    """An empty value means: present but empty, which counts as no key."""
    ctx.extra_env["EODHD_API_KEY"] = key


@when(parsers.parse('I run "{command}"'))
def run_cli(ctx, command):
    _run(ctx, command)


@when(parsers.parse('I run "{command}" with EODHD_API_KEY "{key}"'))
def run_cli_key(ctx, command, key):
    _run(ctx, command, {"EODHD_API_KEY": key})


# ---------------------------------------------------------------- Then: sync
@then("the run is ok")
def run_ok(ctx):
    assert ctx.error is None, ctx.error
    assert ctx.ok is True, ctx.log


@then("the run is not ok")
def run_not_ok(ctx):
    assert ctx.error is None, ctx.error
    assert ctx.ok is False, ctx.log


@then("the sync log is:")
def sync_log(ctx, docstring):
    assert ctx.error is None, ctx.error
    expected = render(ctx, docstring).split("\n")
    assert ctx.log == expected, "\n".join(ctx.log)


@then(parsers.parse('the sync log line {n:d} starts with "{text}"'))
def sync_log_line(ctx, n, text):
    assert ctx.log[n - 1].startswith(text), ctx.log


@then(parsers.parse('the detail of leg {n:d} is "{text}"'))
def leg_detail(ctx, n, text):
    assert ctx.error is None, ctx.error
    assert ctx.results[n - 1]["detail"] == text, ctx.results[n - 1]["detail"]


@then(parsers.parse("the detail of leg {n:d} is:"))
def leg_detail_doc(ctx, n, docstring):
    assert ctx.error is None, ctx.error
    assert ctx.results[n - 1]["detail"] == docstring, ctx.results[n - 1]["detail"]


@then(parsers.parse('the detail of leg {n:d} starts with "{text}"'))
def leg_detail_prefix(ctx, n, text):
    assert ctx.results[n - 1]["detail"].startswith(text), ctx.results[n - 1]["detail"]


@then(parsers.parse('leg {n:d} is ok'))
def leg_ok(ctx, n):
    assert ctx.results[n - 1]["ok"] is True, ctx.results[n - 1]["detail"]


@then(parsers.parse('leg {n:d} failed'))
def leg_failed(ctx, n):
    assert ctx.results[n - 1]["ok"] is False, ctx.results[n - 1]["detail"]


@then("the sync summary is:")
def summary(ctx, docstring):
    doc = adapter().sync_summary(ctx.results, ctx.ok)
    doc = json.loads(json.dumps(doc))
    assert doc == json.loads(render(ctx, docstring)), json.dumps(doc, indent=1)


@then(parsers.parse('the sync is refused with "{message}"'))
def sync_refused(ctx, message):
    assert ctx.error is not None, "no refusal"
    assert str(ctx.error) == message, str(ctx.error)


@then(parsers.parse('the revisions of leg {n:d} are:'))
def revisions(ctx, n, datatable):
    header, *rows = datatable
    got = [{"date": r["date"], "column": r["column"], "stored": float(r["stored"]),
            "served": float(r["served"])} for r in ctx.results[n - 1]["revisions"]]
    want = [{"date": r[0], "column": r[1], "stored": number(r[2]), "served": number(r[3])}
            for r in rows]
    assert got == want, got


@then(parsers.parse('every fixture file under "{sub}" except the replay probes is named slug_digest and holds a request and a response'))
def fixture_corpus(sub):
    """A self-check of the kit's own recorded-fixture corpus against the
    fixtures contract (the reference a recorder must reproduce)."""
    import hashlib
    checked = 0
    for path in sorted((FIXTURES / sub).rglob("*.json")):
        if "replay" in path.parts:
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert set(doc) == {"request", "response"}, path
        key = doc["request"]
        assert set(key) == {"method", "path", "params"} and key["method"] == "GET", path
        assert all(isinstance(v, str) for v in key["params"].values()), path
        assert list(key["params"]) == sorted(key["params"]), path
        assert "api_token" not in key["params"], path
        assert set(doc["response"]) == {"status", "json"}, path
        slug = key["path"].strip("/").replace("/", "_")
        digest = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:10]
        assert path.name == f"{slug}_{digest}.json", (path.name, slug, digest)
        assert path.read_text(encoding="utf-8") == json.dumps(doc, indent=1, sort_keys=True) + "\n", path
        checked += 1
    assert checked > 0


# ---------------------------------------------------------------- Then: store
def _expected_frame(name):
    doc = json.loads((FIXTURES / "expected" / f"{name}.json").read_text(encoding="utf-8"))
    frame = pd.DataFrame(doc["data"], columns=doc["columns"])
    for column, dtype in doc["dtypes"].items():
        if dtype.startswith("datetime64"):
            frame[column] = pd.to_datetime(frame[column], utc=True).astype(dtype)
        elif dtype in ("float64", "int64"):
            frame[column] = frame[column].astype(dtype)
    return frame, doc["dtypes"]


def _compare_frames(got, name):
    want, dtypes = _expected_frame(name)
    assert list(got.columns) == list(want.columns), list(got.columns)
    assert len(got) == len(want), (len(got), len(want))
    got = got.reset_index(drop=True)
    for column in want.columns:
        dtype = dtypes[column]
        if dtype in ("float64", "int64") or dtype.startswith("datetime64"):
            assert str(got[column].dtype) == dtype, (column, got[column].dtype)
            pdt.assert_series_equal(got[column], want[column], check_exact=True,
                                    check_names=True, obj=column)
        else:  # text columns: values, not the string dtype flavour
            assert [str(v) for v in got[column].tolist()] == \
                   [str(v) for v in want[column].tolist()], column


@then(parsers.parse('the stored series {exchange}/{symbol} equals the expected frame "{name}"'))
def stored_equals(ctx, exchange, symbol, name):
    _compare_frames(adapter().stored_frame(str(ctx.store), exchange, symbol), name)


@then(parsers.parse('the export frame of {exchange}/{symbol} equals the expected frame "{name}"'))
def export_equals(ctx, exchange, symbol, name):
    _compare_frames(adapter().export_frame(str(ctx.store), exchange, symbol), name)


@then(parsers.parse('the stored series {exchange}/{symbol} has {n:d} rows'))
def stored_rows(ctx, exchange, symbol, n):
    assert len(adapter().stored_frame(str(ctx.store), exchange, symbol)) == n


@then(parsers.parse('the stored cells of {exchange}/{symbol} are:'))
def stored_cells(ctx, exchange, symbol, datatable):
    frame = adapter().stored_frame(str(ctx.store), exchange, symbol)
    days = frame["datetime"].dt.strftime("%Y-%m-%d").tolist()
    header, *rows = datatable
    for day, column, value in rows:
        assert day in days, f"no stored row dated {day}"
        cell = frame[column].iloc[days.index(day)]
        if column in STRING_COLUMNS:
            assert str(cell) == value, (day, column, cell)
        elif column == "timestamp":
            assert int(cell) == int(value), (day, column, cell)
        elif column == "datetime":
            assert cell.isoformat() == value, (day, column, cell.isoformat())
        else:
            assert same_number(float(cell), number(value)), (day, column, repr(float(cell)))


@then(parsers.re(r'every stored row of (?P<exchange>[^/ ]+)/(?P<symbol>\S+) has (?P<column>\w+) "(?P<value>[^"]*)"'))
def every_row(ctx, exchange, symbol, column, value):
    frame = adapter().stored_frame(str(ctx.store), exchange, symbol)
    assert len(frame) > 0
    if column in STRING_COLUMNS:
        assert {str(v) for v in frame[column]} == {value}
    else:
        assert all(same_number(float(v), number(value)) for v in frame[column])


@then(parsers.parse('the stored dtypes of {exchange}/{symbol} are:'))
def stored_dtypes(ctx, exchange, symbol, datatable):
    frame = adapter().stored_frame(str(ctx.store), exchange, symbol)
    header, *rows = datatable
    assert list(frame.columns) == [r[0] for r in rows], list(frame.columns)
    for column, dtype in rows:
        if dtype == "text":
            assert all(isinstance(v, str) for v in frame[column]), column
        else:
            assert str(frame[column].dtype) == dtype, (column, frame[column].dtype)


@then(parsers.parse('the export frame of {exchange}/{symbol} has the dtypes:'))
def export_dtypes(ctx, exchange, symbol, datatable):
    frame = adapter().export_frame(str(ctx.store), exchange, symbol)
    header, *rows = datatable
    assert list(frame.columns) == [r[0] for r in rows], list(frame.columns)
    for column, dtype in rows:
        if dtype == "text":
            assert all(isinstance(v, str) for v in frame[column]), column
        else:
            assert str(frame[column].dtype) == dtype, (column, frame[column].dtype)


@then("the store holds exactly the files:")
def store_files(ctx, docstring):
    got = sorted(p.relative_to(ctx.store).as_posix() for p in ctx.store.rglob("*")
                 if p.is_file())
    want = sorted(line.strip() for line in docstring.split("\n") if line.strip())
    assert got == want, got


@then(parsers.parse('the actions state of "{symbol}" is:'))
def actions_is(ctx, symbol, docstring):
    state = adapter().actions_state(str(ctx.store), symbol)
    want = json.loads(docstring)
    got = {k: state[k] for k in ("splits", "dividends")}
    assert json.loads(json.dumps(got)) == want, json.dumps(got)


@then(parsers.parse('the actions state of "{symbol}" is empty'))
def actions_empty(ctx, symbol):
    state = adapter().actions_state(str(ctx.store), symbol)
    assert state["splits"] == [] and state["dividends"] == [] \
        and state["last_updated"] is None, state


@then(parsers.parse('the actions stamp of "{symbol}" is the real UTC time of the run'))
def actions_stamp(ctx, symbol):
    stamp = adapter().actions_state(str(ctx.store), symbol)["last_updated"]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{6})?Z", stamp), stamp
    when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    assert abs((datetime.now(timezone.utc) - when).total_seconds()) < 3600, stamp


@then(parsers.parse('the actions stamp of "{symbol}" is "{stamp}"'))
def actions_stamp_is(ctx, symbol, stamp):
    assert adapter().actions_state(str(ctx.store), symbol)["last_updated"] == stamp


@then(parsers.parse('the actions file "{relpath}" is:'))
def actions_file(ctx, relpath, docstring):
    text = (ctx.store / relpath).read_text(encoding="utf-8")
    doc = json.loads(text)
    doc["last_updated"] = "<stamp>"
    assert doc == json.loads(docstring), text
    assert text.endswith("}\n") and text.startswith('{\n  "symbol": '), text[:40]
    assert list(json.loads(text).keys()) == list(json.loads(docstring).keys())


# ---------------------------------------------------------------- Then: legs / universe
@then("the legs are:")
def legs_are(ctx, docstring):
    assert ctx.error is None, ctx.error
    assert json.loads(json.dumps(ctx.legs)) == json.loads(docstring), json.dumps(ctx.legs)


@then(parsers.parse('the selection is refused with "{message}"'))
def selection_refused(ctx, message):
    assert ctx.error is not None, "no refusal"
    assert str(ctx.error) == message, str(ctx.error)


@then("the loaded universe is:")
def loaded_is(ctx, docstring):
    assert ctx.error is None, ctx.error
    got = json.loads(json.dumps(universe(ctx)))
    assert got == json.loads(docstring), json.dumps(got)


# ---------------------------------------------------------------- Then: status
def _report(ctx, n):
    assert ctx.error is None, ctx.error
    return ctx.status["reports"][n - 1]


def _lines(docstring):
    """Docstring lines; a literal backslash-n (from an Examples cell) splits too."""
    return [line for line in docstring.replace("\\n", "\n").split("\n") if line.strip()]


@then(parsers.parse("the status exit code is {rc:d}"))
def status_rc(ctx, rc):
    assert ctx.error is None, ctx.error
    assert ctx.status_rc == rc, ctx.status


@then("the status document is:")
def status_doc(ctx, docstring):
    assert ctx.error is None, ctx.error
    assert ctx.status == json.loads(render(ctx, docstring)), json.dumps(ctx.status, indent=1)


@then(parsers.parse("report {n:d} has alerts:"))
def report_alerts(ctx, n, docstring):
    assert _report(ctx, n)["alerts"] == _lines(docstring), _report(ctx, n)["alerts"]


@then(parsers.parse("report {n:d} has warnings:"))
def report_warnings(ctx, n, docstring):
    assert _report(ctx, n)["warnings"] == _lines(docstring), _report(ctx, n)["warnings"]


@then(parsers.parse("report {n:d} has notes:"))
def report_notes(ctx, n, docstring):
    assert _report(ctx, n)["notes"] == _lines(docstring), _report(ctx, n)["notes"]


@then(parsers.parse("report {n:d} has no {kind}"))
def report_none(ctx, n, kind):
    assert kind in ("alerts", "warnings", "notes")
    assert _report(ctx, n)[kind] == [], _report(ctx, n)[kind]


@then(parsers.parse("report {n:d} has the fields:"))
def report_fields(ctx, n, datatable):
    report = _report(ctx, n)
    header, *rows = datatable
    for key, value in rows:
        assert key in report, (key, sorted(report))
        assert report[key] == json.loads(value), (key, report[key])


@then(parsers.parse('report {n:d} lacks the field "{key}"'))
def report_no_field(ctx, n, key):
    assert key not in _report(ctx, n), _report(ctx, n)


@then(parsers.parse("report {n:d} has exactly the keys:"))
def report_keys(ctx, n, docstring):
    assert list(_report(ctx, n).keys()) == _lines(docstring), list(_report(ctx, n).keys())


@then(parsers.parse("pair {n:d} is:"))
def pair_is(ctx, n, docstring):
    assert ctx.error is None, ctx.error
    assert ctx.status["pairs"][n - 1] == json.loads(docstring), \
        json.dumps(ctx.status["pairs"][n - 1], indent=1)


@then(parsers.parse("there are {n:d} reports and {p:d} pairs"))
def counts(ctx, n, p):
    assert len(ctx.status["reports"]) == n and len(ctx.status["pairs"]) == p


@then(parsers.parse("the status totals are {a:d} alerts and {w:d} warnings"))
def totals(ctx, a, w):
    assert (ctx.status["alerts_total"], ctx.status["warnings_total"]) == (a, w), \
        (ctx.status["alerts_total"], ctx.status["warnings_total"])


@then(parsers.parse('the status is refused with "{message}"'))
def status_refused(ctx, message):
    assert ctx.error is not None and str(ctx.error) == message, ctx.error


# ---------------------------------------------------------------- Then: executable
@then(parsers.parse("the exit code is {rc:d}"))
def exit_code(ctx, rc):
    assert ctx.proc.returncode == rc, (ctx.proc.returncode, ctx.proc.stdout, ctx.proc.stderr)


@then("stdout is:")
def stdout_is(ctx, docstring):
    want = render(ctx, docstring) + "\n"
    assert ctx.proc.stdout == want, ctx.proc.stdout


@then("stdout is empty")
def stdout_empty(ctx):
    assert ctx.proc.stdout == "", ctx.proc.stdout


@then("stderr is:")
def stderr_is(ctx, docstring):
    want = render(ctx, docstring) + "\n"
    assert ctx.proc.stderr == want, ctx.proc.stderr


@then(parsers.parse('stderr ends with the line "{text}"'))
def stderr_last(ctx, text):
    lines = ctx.proc.stderr.rstrip("\n").split("\n")
    assert lines[-1].endswith(render(ctx, text)), ctx.proc.stderr[-500:]


@then(parsers.parse('stderr contains "{text}"'))
def stderr_contains(ctx, text):
    assert render(ctx, text) in ctx.proc.stderr, ctx.proc.stderr[-800:]


@then(parsers.parse('stdout contains the line "{text}"'))
def stdout_line(ctx, text):
    assert render(ctx, text) in ctx.proc.stdout.split("\n"), ctx.proc.stdout


# revision 2026-10-23 (closing round): exact parser output and verbatim help
@given(parsers.parse("the terminal is {columns:d} columns wide"))
def terminal_width(ctx, columns):
    ctx.extra_env["COLUMNS"] = str(columns)


def _help_blocks():
    """Map each '## <command in backticks>' heading to the text block under it."""
    text = (FEATURES.parent / "contracts" / "cli_help.md").read_text(encoding="utf-8")
    blocks, heading, inside, lines = {}, None, False, []
    for line in text.split("\n"):
        if not inside and line.startswith("## `") and line.endswith("`"):
            heading = line[4:-1]
        elif not inside and line == "```text" and heading:
            inside, lines = True, []
        elif inside and line == "```":
            blocks[heading] = "\n".join(lines) + "\n"
            inside, heading = False, None
        elif inside:
            lines.append(line)
    return blocks


@then(parsers.parse('stdout is the "{heading}" block of contracts/cli_help.md'))
def stdout_help(ctx, heading):
    blocks = _help_blocks()
    assert heading in blocks, sorted(blocks)
    assert ctx.proc.stdout == blocks[heading], ctx.proc.stdout


@then("stderr is empty")
def stderr_empty(ctx):
    assert ctx.proc.stderr == "", ctx.proc.stderr


@then(parsers.parse('the last line of stderr is "{text}"'))
def stderr_last_exact(ctx, text):
    assert ctx.proc.stderr.endswith("\n"), ctx.proc.stderr[-200:]
    assert ctx.proc.stderr.rstrip("\n").split("\n")[-1] == render(ctx, text), ctx.proc.stderr[-500:]


@then(parsers.parse('stderr is the lines "{text}"'))
def stderr_lines(ctx, text):
    assert ctx.proc.stderr == render(ctx, text).replace("\\n", "\n") + "\n", ctx.proc.stderr


@then(parsers.parse('the file "{path}" does not exist'))
def no_file(ctx, path):
    assert not (ctx.work / render(ctx, path)).exists()


@then(parsers.parse('the file "{path}" is:'))
def file_is(ctx, path, docstring):
    text = (ctx.work / render(ctx, path)).read_text(encoding="utf-8")
    assert text == render(ctx, docstring) + "\n", text


@then(parsers.parse('the file "{path}" starts with:'))
def file_starts(ctx, path, docstring):
    text = (ctx.work / render(ctx, path)).read_text(encoding="utf-8")
    assert text.startswith(render(ctx, docstring) + "\n"), text[:400]


@then(parsers.parse('the JSON file "{path}" is:'))
def json_file_is(ctx, path, docstring):
    text = (ctx.work / render(ctx, path)).read_text(encoding="utf-8")
    assert json.loads(text) == json.loads(render(ctx, docstring)), text


@then(parsers.parse('the JSON file "{path}" is written sorted with 1-space indentation'))
def json_file_format(ctx, path):
    text = (ctx.work / render(ctx, path)).read_text(encoding="utf-8")
    doc = json.loads(text)
    assert text == json.dumps(doc, indent=1, sort_keys=True) + "\n", text


@then("the JSON on stdout is:")
def json_stdout(ctx, docstring):
    assert json.loads(ctx.proc.stdout) == json.loads(render(ctx, docstring)), ctx.proc.stdout


@then("the JSON on stdout is printed with 1-space indentation in document order")
def json_stdout_format(ctx):
    doc = json.loads(ctx.proc.stdout)
    assert ctx.proc.stdout == json.dumps(doc, indent=1) + "\n", ctx.proc.stdout


# ---------------------------------------------------------------- chain
STUB = r'''#!/bin/bash
name=$(basename "$0")
{ printf '%s' "$name"; for a in "$@"; do printf '\t%s' "${a//$'\n'/\\n}"; done; printf '\n'; } >> "$STUB_LOG"
rc_var="STUB_RC_${name//-/_}"
case "$name" in
  timeout) shift 3; exec "$@";;
  date) for a in "$@"; do case "$a" in
          +%s) echo 1700000000; exit 0;;
          +%F) echo 2026-10-22; exit 0;;
          +%Y-%m-%dT%H%M%SZ) echo 2026-10-22T053000Z; exit 0;;
        esac; done; exit 0;;
  python3)
    if [[ "$1" == "-c" ]]; then exec "$REAL_PYTHON" "$@"; fi
    if [[ "$1" == "-" ]]; then cat > /dev/null; exit 0; fi
    if [[ "$1 $2" == "-m jef.events" ]]; then
      prev=""; for a in "$@"; do [[ "$prev" == "--out" ]] && echo '{}' >> "$a"; prev="$a"; done
    fi
    exit 0;;
  jef-data)
    printf 'JEF_IMAGE_DIGEST=%s\nJEF_RUN_STAMP=%s\nJEF_TASK_VCPU=%s\nJEF_TASK_MEMORY_GB=%s\nPWD=%s\n' \
      "${JEF_IMAGE_DIGEST-<unset>}" "${JEF_RUN_STAMP-<unset>}" "${JEF_TASK_VCPU-<unset>}" \
      "${JEF_TASK_MEMORY_GB-<unset>}" "$PWD" > "$STUB_ENV_LOG"
    if [[ "$1" == "sync" && -n "${STUB_SYNC_SLEEP:-}" ]]; then touch "$STUB_MARK"; sleep "$STUB_SYNC_SLEEP"; fi
    if [[ "$1" == "status" ]]; then echo '{"alerts_total": 0}'; exit "${STUB_STATUS_RC:-0}"; fi
    prev=""; for a in "$@"; do [[ "$prev" == "--summary-json" ]] && echo '{"ok": true}' > "$a"; prev="$a"; done
    exit "${STUB_SYNC_RC:-0}";;
  jef-binning)
    prev=""; out=""; asset=""
    for a in "$@"; do [[ "$prev" == "--output-dir" ]] && out="$a"; [[ "$prev" == "--asset" ]] && asset="$a"; prev="$a"; done
    if [[ " ${STUB_MANIFEST_ASSETS:-} " == *" $asset "* ]]; then mkdir -p "$out"; echo '{}' > "$out/run_manifest_1.json"; fi
    if [[ " ${STUB_FAIL_ASSETS:-} " == *" $asset "* ]]; then exit "${STUB_BINNING_RC:-1}"; fi
    exit 0;;
  aws)
    if [[ "$3" == "-" ]]; then printf 'stdin\t%s\n' "$(cat)" >> "$STUB_LOG"; fi
    exit "${STUB_AWS_RC:-0}";;
  curl) printf '%s' "${STUB_CURL_BODY:-}"; exit 0;;
  *) exit "${!rc_var:-0}";;
esac
'''
STUBBED = ("timeout", "date", "python3", "jef-data", "jef-binning", "aws", "curl",
           "override-cmd")


@given("the chain under test with stubbed externals")
def chain_setup(ctx):
    source = chain_script()
    home = ctx.tmp / "chain"
    home.mkdir()
    for name in ("events.sh", "dashboard.sh"):
        shutil.copyfile(source.parent / name, home / name)
    shutil.copyfile(source, home / "daily.sh")
    (home / "daily.sh").chmod(0o755)
    bin_dir = ctx.tmp / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "_stub"
    stub.write_text(STUB, encoding="utf-8")
    stub.chmod(0o755)
    for name in STUBBED:
        (bin_dir / name).symlink_to(stub)
    app = ctx.tmp / "app"
    app.mkdir()
    ctx.chain = SimpleNamespace(
        script=home / "daily.sh", bin=bin_dir, app=app, log=ctx.tmp / "calls.log",
        events=ctx.tmp / "events", dash=ctx.tmp / "dash", proc=None,
        env={"JEF_S3_BUCKET": "bkt", "JEF_IMAGE_DIGEST": "sha256:feed",
             "JEF_ASSETS": "AAPL BTC"})


@given("the chain environment:")
def chain_env(ctx, datatable):
    header, *rows = datatable
    for name, value in rows:
        if value == "<unset>":
            ctx.chain.env.pop(name, None)
        else:
            ctx.chain.env[name] = value


@given(parsers.parse("the restored store holds a market_data directory"))
def chain_store_present(ctx):
    (ctx.chain.app / "data" / "market_data").mkdir(parents=True)


def _chain_env(ctx):
    env = {"PATH": f"{ctx.chain.bin}:/usr/bin:/bin", "HOME": str(ctx.tmp),
           "STUB_LOG": str(ctx.chain.log), "REAL_PYTHON": sys.executable,
           "STUB_ENV_LOG": str(ctx.tmp / "env.log"),
           "STUB_MARK": str(ctx.tmp / "mark"), "JEF_APP_DIR": str(ctx.chain.app),
           "JEF_EVENT_DIR": str(ctx.chain.events), "JEF_DASH_DIR": str(ctx.chain.dash)}
    env.update(ctx.chain.env)
    return env


@when("the chain runs")
def chain_runs(ctx):
    _chain(ctx, [])


@when(parsers.parse('the chain runs with arguments "{args}"'))
def chain_runs_args(ctx, args):
    _chain(ctx, shlex.split(args))


def _chain(ctx, args):
    ctx.chain.proc = subprocess.run([str(ctx.chain.script), *args], cwd=ctx.tmp,
                                    env=_chain_env(ctx), capture_output=True,
                                    text=True, timeout=120)


@when("the chain receives TERM while its sync stage runs")
def chain_term(ctx):
    ctx.chain.env["STUB_SYNC_SLEEP"] = "2"
    proc = subprocess.Popen([str(ctx.chain.script)], cwd=ctx.tmp, env=_chain_env(ctx),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    deadline = time.time() + 60
    while not (ctx.tmp / "mark").exists():
        assert time.time() < deadline, "sync stage never started"
        time.sleep(0.05)
    proc.terminate()
    out, err = proc.communicate(timeout=120)
    ctx.chain.proc = SimpleNamespace(returncode=proc.returncode, stdout=out, stderr=err)


def _calls(ctx):
    if not ctx.chain.log.exists():
        return []
    calls = []
    for line in ctx.chain.log.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if parts[0] == "date" or (parts[0] == "python3" and parts[1:2] == ["-c"]):
            continue
        calls.append(" ".join(parts))
    return calls


def _render_chain(ctx, text):
    return (text.replace("{chain}", str(ctx.chain.script))
            .replace("{app}", str(ctx.chain.app))
            .replace("{events}", str(ctx.chain.events))
            .replace("{dash}", str(ctx.chain.dash)))


@then("the external calls are:")
def chain_calls(ctx, docstring):
    want = [_render_chain(ctx, line.strip()) for line in docstring.split("\n") if line.strip()]
    assert _calls(ctx) == want, "\n".join(_calls(ctx))


@then(parsers.parse("the chain exit code is {rc:d}"))
def chain_rc(ctx, rc):
    proc = ctx.chain.proc
    assert proc.returncode == rc, (proc.returncode, proc.stdout, proc.stderr)


@then("the chain stdout is:")
def chain_stdout(ctx, docstring):
    assert ctx.chain.proc.stdout == _render_chain(ctx, docstring) + "\n", ctx.chain.proc.stdout


@then("the chain stdout is empty")
def chain_stdout_empty(ctx):
    assert ctx.chain.proc.stdout == "", ctx.chain.proc.stdout


@then(parsers.parse('the chain stderr ends with "{text}"'))
def chain_stderr(ctx, text):
    assert ctx.chain.proc.stderr.rstrip("\n").endswith(text), ctx.chain.proc.stderr


@then("jef-data ran with the environment:")
def chain_child_env(ctx, datatable):
    seen = dict(line.split("=", 1) for line in
                (ctx.tmp / "env.log").read_text(encoding="utf-8").splitlines())
    header, *rows = datatable
    for name, value in rows:
        value = value.replace("{app}", str(ctx.chain.app))
        assert seen.get(name) == value, (name, seen.get(name))


@then(parsers.parse('the app directory holds the file "{path}"'))
def chain_file(ctx, path):
    assert (ctx.chain.app / path).is_file(), sorted(p.as_posix() for p in ctx.chain.app.rglob("*"))

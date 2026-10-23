"""Property-based invariants of the daily asset load, through the adapter.

Intrinsic properties hold for any implementation of the kit; differential
properties compare the implementation under test with a reference, exactly.
"""
import importlib
import io
import json
import os
import shutil
import tempfile
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

import fixturelib as fx

A = importlib.import_module(os.environ.get("JDL_ADAPTER", "adapters.original"))
REF_NAME = os.environ.get("JDL_REF_ADAPTER")
REF = importlib.import_module(REF_NAME) if REF_NAME else None
EXAMPLES = int(os.environ.get("JDL_EXAMPLES", "100"))
UTC = timezone.utc
SETTINGS = settings(max_examples=EXAMPLES, deadline=None, derandomize=True,
                    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large])

# ---- strategies --------------------------------------------------------------

RATIOS = [(2, 1), (3, 1), (4, 1), (7, 1), (3, 2), (1, 2), (1, 10), (10, 1), (5, 4)]


def weekdays(start, n):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


@st.composite
def series(draw, crypto=None):
    is_crypto = draw(st.booleans()) if crypto is None else crypto
    start = date(2016, 1, 4) + timedelta(days=draw(st.integers(0, 3000)))
    n = draw(st.integers(3, 30))
    dates = [start + timedelta(days=i) for i in range(n)] if is_crypto else weekdays(start, n)
    bars = []
    for d in dates:
        close_cents = draw(st.integers(1, 5_000_000))
        if draw(st.integers(0, 24)) == 0:          # a glitch row the collector drops
            close_cents = 0
        open_c = draw(st.integers(1, 5_000_000))
        hi = max(open_c, close_cents) + draw(st.integers(0, 50_000))
        lo = max(1, min(open_c, close_cents) - draw(st.integers(0, 50_000)))
        vol = 0 if draw(st.integers(0, 9)) == 0 else draw(st.integers(1, 500_000_000))
        adj = round(close_cents / 100 * draw(st.sampled_from([1.0, 0.97, 0.9])), 4)
        bars.append({"date": d.isoformat(), "open": open_c / 100, "high": hi / 100,
                     "low": lo / 100, "close": close_cents / 100,
                     "adjusted_close": adj, "volume": vol})
    k = 0 if is_crypto else draw(st.integers(0, 3))
    splits = []
    for _ in range(k):
        sd = dates[0] + timedelta(days=draw(st.integers(-40, len(dates) + 5)))
        num, den = draw(st.sampled_from(RATIOS))
        splits.append({"date": sd.isoformat(), "split": f"{num:.6f}/{den:.6f}"})
    splits.sort(key=lambda s: s["date"])
    divs = [] if draw(st.booleans()) else [
        {"date": dates[len(dates) // 2].isoformat(), "value": 0.25, "unadjustedValue": 0.25,
         "currency": "USD", "period": "Quarterly", "declarationDate": None,
         "paymentDate": None, "recordDate": None}]
    gap_days = draw(st.integers(1, 15))
    now = datetime.combine(dates[-1] + timedelta(days=gap_days), datetime.min.time(), tzinfo=UTC) + timedelta(hours=12)
    return {"crypto": is_crypto, "dates": dates, "bars": bars, "splits": splits, "divs": divs, "now": now}


class Case:
    """One generated input landed on disk: fixture set, universe, store."""

    def __init__(self, s, root, tail=10):
        self.s = s
        self.root = root
        self.tail = tail
        self.symbol = "GEN-USD.CC" if s["crypto"] else "GEN.US"
        self.asset = "GEN"
        self.start = s["dates"][0]
        self.end = (s["now"].date() - timedelta(days=1)) if s["crypto"] else None
        self.fixtures = os.path.join(root, "fx1")
        fx.write_eodhd_set(self.fixtures, self.symbol, s["bars"], s["splits"], s["divs"], self.start, self.end)
        cls = "crypto" if s["crypto"] else "stock"
        self.universe_path = os.path.join(root, "u.toml")
        with open(self.universe_path, "w", encoding="utf-8") as f:
            f.write(f'[[asset]]\nname = "{self.asset}"\nasset_class = "{cls}"\n'
                    f'  [[asset.source]]\n  provider = "eodhd"\n  symbol = "{self.symbol}"\n'
                    f'  modeled = true\n  start = {self.start.isoformat()}\n')
        self.store = os.path.join(root, "store")
        os.makedirs(self.store)

    def sync(self, adapter, fixtures=None, store=None):
        uni = adapter.load_universe(self.universe_path)
        coll = {"eodhd": adapter.make_collector("eodhd", os.path.join(fixtures or self.fixtures, "eodhd"))}
        results, ok = adapter.run_sync(uni, store or self.store, now=self.s["now"], collectors=coll, tail=self.tail)
        return adapter.sync_summary(results, ok)

    def status(self, adapter, now=None, store=None, **kw):
        uni = adapter.load_universe(self.universe_path)
        return adapter.status_json(uni, store or self.store, now=now or self.s["now"], **kw)


def tmp():
    return tempfile.mkdtemp(prefix="jdl-prop-")


def tail_serve(c, s, mutate=None):
    """The provider's serve for a SECOND run: the kit's tail window - from the
    oldest of the newest `tail` stored sessions to the same end - as a new
    fixture set; `mutate(window_bars)` may revise cells in it."""
    kept = [b for b in s["bars"] if b["close"] > 0]
    stored_dates = [b["date"] for b in kept]
    window_start = date.fromisoformat(stored_dates[-c.tail] if len(stored_dates) > c.tail else stored_dates[0])
    window = [dict(b) for b in s["bars"] if date.fromisoformat(b["date"]) >= window_start]
    if mutate:
        mutate(window)
    fx2 = os.path.join(c.root, "fx2")
    fx.write_eodhd_set(fx2, c.symbol, window, s["splits"], s["divs"], window_start, c.end)
    return fx2, window, window_start


def factors(dates, splits):
    """The kit's rule: product, in stored split order, of ratios of splits strictly after the row date."""
    f = np.ones(len(dates), dtype=np.float64)
    row_dates = np.array([pd.Timestamp(d).date() for d in dates])
    for sp in sorted(splits, key=lambda x: x["date"]):
        num, den = sp["split"].split("/")
        ratio = float(num) / float(den)
        f[row_dates < date.fromisoformat(sp["date"])] *= ratio
    return f


def canon_frame(df):
    df = df.copy()
    for c in df.columns:
        if str(df[c].dtype).startswith("datetime64"):
            df[c] = df[c].astype(str)
    return df[sorted(df.columns)].to_csv(index=False)


def strip(obj, keys=("last_updated",)):
    if isinstance(obj, dict):
        return {("split" if k == "split_string" else k): strip(v, keys) for k, v in obj.items() if k not in keys}
    if isinstance(obj, list):
        return [strip(v, keys) for v in obj]
    return obj


# ---- intrinsic properties ----------------------------------------------------

@SETTINGS
@given(series())
def test_first_fill_lands_every_positive_close_bar_and_derives_the_adjusted_columns_exactly(s):
    root = tmp()
    try:
        c = Case(s, root)
        summary = c.sync(A)
        assert summary["ok"] and summary["legs"][0]["ok"], summary
        df = A.stored_frame(c.store, "eodhd", c.symbol).sort_values("timestamp").reset_index(drop=True)
        kept = [b for b in s["bars"] if b["close"] > 0]
        assert len(df) == len(kept), "every bar with a positive close is stored, nothing else"
        if not kept:
            return  # nothing served survived the collector: the series stays absent
        assert list(df["datetime"].dt.strftime("%Y-%m-%d")) == [b["date"] for b in kept]
        f = factors(df["datetime"], s["splits"] if not s["crypto"] else [])
        assert np.array_equal(df["cumulative_split_factor"].to_numpy(), f)
        for col in ("open", "high", "low", "close"):
            assert np.array_equal(df[col].to_numpy(), df[f"{col}_raw"].to_numpy(dtype=np.float64) / f), col
        assert np.array_equal(df["volume"].to_numpy(), df["volume_raw"].to_numpy(dtype=np.float64) * f)
        assert np.array_equal(df["adjustment_factor"].to_numpy(), df["adjusted_close"].to_numpy() / df["close_raw"].to_numpy())
        if s["crypto"]:
            assert set(df["price_basis"]) == {"split_adjusted"} and (df["cumulative_split_factor"] == 1.0).all()
            assert np.array_equal(df["volume_raw"].to_numpy(), np.array([float(b["volume"]) for b in kept]))
        else:
            assert set(df["price_basis"]) == {"raw"}
            # served volume is split-adjusted: raw-ized at ingest by the same factor
            served = np.array([float(b["volume"]) for b in kept])
            assert np.array_equal(df["volume_raw"].to_numpy(), served / f)
            assert np.array_equal(df["volume"].to_numpy(), (served / f) * f)
        # the factor is exactly 1.0 on and after the last split, non-increasing backwards for ratios > 1
        if s["splits"] and not s["crypto"]:
            last = date.fromisoformat(max(sp["date"] for sp in s["splits"]))
            after = df["datetime"].dt.date.to_numpy() >= last
            assert (df.loc[after, "cumulative_split_factor"] == 1.0).all()
    finally:
        shutil.rmtree(root, ignore_errors=True)


@SETTINGS
@given(series())
def test_a_second_sync_on_the_same_serve_changes_no_cell_and_logs_no_revision(s):
    root = tmp()
    try:
        c = Case(s, root)
        c.sync(A)
        if not [b for b in s["bars"] if b["close"] > 0]:
            return
        before = canon_frame(A.stored_frame(c.store, "eodhd", c.symbol))
        fx2, _, _ = tail_serve(c, s)
        summary = c.sync(A, fixtures=fx2)
        assert summary["ok"] and summary["revised_cells_total"] == 0, summary["legs"][0]["detail"]
        assert canon_frame(A.stored_frame(c.store, "eodhd", c.symbol)) == before
    finally:
        shutil.rmtree(root, ignore_errors=True)


@SETTINGS
@given(series(), st.data())
def test_a_tail_revision_changes_exactly_the_served_cells_inside_the_window_and_nothing_outside(s, data):
    root = tmp()
    try:
        c = Case(s, root, tail=data.draw(st.integers(1, 12)))
        c.sync(A)
        before = A.stored_frame(c.store, "eodhd", c.symbol).sort_values("timestamp").reset_index(drop=True)
        kept = [b for b in s["bars"] if b["close"] > 0]
        if len(kept) < 2:
            return
        picks = []

        def revise(window):
            revisable = [i for i, b in enumerate(window) if b["close"] > 0]
            picks.extend(data.draw(st.lists(st.sampled_from(revisable), min_size=1, max_size=min(3, len(revisable)), unique=True)))
            for i in picks:
                window[i]["close"] = round(window[i]["close"] + 1.0, 2)
        fx2, window, window_start = tail_serve(c, s, mutate=revise)
        summary = c.sync(A, fixtures=fx2)
        assert summary["ok"], summary["legs"][0]["detail"]
        assert summary["legs"][0]["revised_cells"] == len(picks)
        revised = {(r["date"], r["column"]) for r in summary["legs"][0]["revisions"]}
        assert revised == {(window[i]["date"], "close_raw") for i in picks}
        after = A.stored_frame(c.store, "eodhd", c.symbol).sort_values("timestamp").reset_index(drop=True)
        outside = before["datetime"].dt.date.to_numpy() < window_start
        for col in ("open_raw", "high_raw", "low_raw", "close_raw", "volume_raw", "adjusted_close"):
            assert np.array_equal(before.loc[outside, col].to_numpy(), after.loc[outside, col].to_numpy()), col
        # and the adjusted columns are re-derived from the revised raw by the same identities
        f = factors(after["datetime"], s["splits"] if not s["crypto"] else [])
        assert np.array_equal(after["close"].to_numpy(), after["close_raw"].to_numpy(dtype=np.float64) / f)
    finally:
        shutil.rmtree(root, ignore_errors=True)


@SETTINGS
@given(series())
def test_the_export_is_the_stored_series_projected_row_for_row_with_the_volume_dtype_rule(s):
    root = tmp()
    try:
        c = Case(s, root)
        c.sync(A)
        if not [b for b in s["bars"] if b["close"] > 0]:
            return  # an absent series: export's behaviour there is JDL-159, not this property
        df = A.stored_frame(c.store, "eodhd", c.symbol).sort_values("timestamp").reset_index(drop=True)
        ex = A.export_frame(c.store, "eodhd", c.symbol)
        assert list(ex.columns) == ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
        assert len(ex) == len(df), "every stored row is exported; the loader, not the export, drops rows"
        assert list(ex["Date"]) == list(df["datetime"].dt.strftime("%Y-%m-%d"))
        assert np.array_equal(ex["Close"].to_numpy(), df["close"].to_numpy())
        assert np.array_equal(ex["Volume"].to_numpy(dtype=np.float64), df["volume"].to_numpy())
        integral = np.isfinite(df["volume"].to_numpy()).all() and (df["volume"].to_numpy() == np.floor(df["volume"].to_numpy())).all()
        assert (str(ex["Volume"].dtype) == "int64") == bool(integral)
    finally:
        shutil.rmtree(root, ignore_errors=True)


@SETTINGS
@given(series(), st.integers(0, 40), st.integers(1, 4))
def test_status_exits_one_exactly_when_an_alert_fired_and_warnings_never_move_it(s, extra_days, k):
    root = tmp()
    try:
        c = Case(s, root)
        c.sync(A)
        now = s["now"] + timedelta(days=extra_days)
        doc, rc = c.status(A, now=now, staleness_k=k)
        alerts = [a for r in doc["reports"] + doc["pairs"] for a in r["alerts"]]
        warnings = [w for r in doc["reports"] + doc["pairs"] for w in r.get("warnings", [])]
        assert rc == (1 if alerts else 0)
        assert doc["alerts_total"] == len(alerts) and doc["warnings_total"] == len(warnings)
        if not alerts:
            assert rc == 0 or not warnings
    finally:
        shutil.rmtree(root, ignore_errors=True)


@SETTINGS
@given(series(crypto=True), st.integers(0, 3))
def test_a_crypto_leg_never_asks_past_yesterday_utc(s, hours):
    root = tmp()
    try:
        # the fixture answers only the window ending yesterday; a request past it would fail the leg
        s = dict(s, now=s["now"].replace(hour=hours))
        c = Case(s, root)
        summary = c.sync(A)
        assert summary["ok"] and summary["legs"][0]["ok"], summary["legs"][0]["detail"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---- differential properties (only with a reference adapter) -------------------

@pytest.mark.skipif(REF is None, reason="no JDL_REF_ADAPTER")
@SETTINGS
@given(series(), st.integers(0, 20), st.integers(1, 12))
def test_the_implementation_under_test_equals_the_reference_on_generated_inputs(s, extra_days, tail):
    root = tmp()
    try:
        c = Case(s, root, tail=tail)
        store_ref = os.path.join(root, "store_ref"); os.makedirs(store_ref)
        summary_a = c.sync(A)
        summary_r = c.sync(REF, store=store_ref)
        assert strip(summary_a) == strip(summary_r), (summary_a, summary_r)
        if not [b for b in s["bars"] if b["close"] > 0]:
            now = s["now"] + timedelta(days=extra_days)
            assert c.status(A, now=now)[1] == c.status(REF, now=now, store=store_ref)[1]
            return
        assert canon_frame(A.stored_frame(c.store, "eodhd", c.symbol)) == canon_frame(REF.stored_frame(store_ref, "eodhd", c.symbol))
        assert A.export_frame(c.store, "eodhd", c.symbol).to_csv(index=False) == REF.export_frame(store_ref, "eodhd", c.symbol).to_csv(index=False)
        assert strip(A.actions_state(c.store, c.symbol)) == strip(REF.actions_state(store_ref, c.symbol))
        fx2, _, _ = tail_serve(c, s)
        assert strip(c.sync(A, fixtures=fx2)) == strip(c.sync(REF, fixtures=fx2, store=store_ref))
        assert canon_frame(A.stored_frame(c.store, "eodhd", c.symbol)) == canon_frame(REF.stored_frame(store_ref, "eodhd", c.symbol))
        now = s["now"] + timedelta(days=extra_days)
        doc_a, rc_a = c.status(A, now=now)
        doc_r, rc_r = c.status(REF, now=now, store=store_ref)
        assert rc_a == rc_r
        assert strip(json.loads(json.dumps(doc_a, default=str).replace(c.store, "<store>"))) == \
               strip(json.loads(json.dumps(doc_r, default=str).replace(store_ref, "<store>")))
    finally:
        shutil.rmtree(root, ignore_errors=True)

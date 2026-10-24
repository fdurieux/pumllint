"""Generate the kit's synthetic fixtures (hidden tooling; outputs go to kit/)."""
import json
import os
import shutil
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))
import fx  # noqa: E402

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "kit"))
FIX = os.path.join(KIT, "features", "fixtures")
HTTP = os.path.join(FIX, "http")
CSV = os.path.join(FIX, "csv")


def r2(x):
    return round(x, 2)


# ---------------------------------------------------------------- SPLT.US
SPLT_DATES = fx.weekdays(date(2024, 1, 2), date(2024, 2, 12))          # 30
assert len(SPLT_DATES) == 30, len(SPLT_DATES)
SPLIT1, SPLIT2 = date(2024, 1, 17), date(2024, 2, 1)


def factor(d, splits):
    f = 1.0
    for when, ratio in splits:
        if d < when:
            f *= ratio
    return f


def splt_row(i, d, splits=((SPLIT1, 1.5), (SPLIT2, 7.0)), bump=None):
    p = 20.0 + 0.05 * i
    f = factor(d, splits)
    close = r2(p * f)
    row = {
        "date": d.isoformat(),
        "open": r2(close * 0.99),
        "high": r2(close * 1.01),
        "low": r2(close * 0.98),
        "close": close,
        "adjusted_close": round(p * 0.995, 4),
        "volume": 100000 + 1000 * i,
    }
    if bump:
        row.update(bump)
    return row


def splt_rows(dates=SPLT_DATES, offset=0, **kw):
    return [splt_row(SPLT_DATES.index(d) if d in SPLT_DATES else offset + k, d, **kw)
            for k, d in enumerate(dates)]


SPLT_SPLITS = [{"date": "2024-02-01", "split": "7/1"},
               {"date": "2024-01-17", "split": "3.000000/2.000000"}]
SPLT_DIVS = [{"date": "2024-01-25", "declarationDate": "2024-01-10",
              "recordDate": "2024-01-26", "paymentDate": "2024-02-05",
              "period": "Quarterly", "value": 0.24, "unadjustedValue": 0.24,
              "currency": "USD"}]


def gen_splt():
    base = os.path.join(HTTP, "splt")
    shutil.rmtree(base, ignore_errors=True)
    rows = splt_rows()
    # provider glitches the collector must absorb: a close<=0 row, a
    # duplicate date (first wins) and one row out of order
    glitch = dict(rows[6], close=0, volume=5)            # 2024-01-10, skipped
    dup = dict(rows[16], close=999.0)                    # 2024-01-24 second copy
    served = rows[:6] + [glitch] + rows[6:17] + [dup] + rows[17:]
    served[3], served[4] = served[4], served[3]          # 01-05 before 01-04
    run1 = os.path.join(base, "run1")
    fx.eod(run1, "SPLT.US", served, start="2024-01-02")
    fx.splits(run1, "SPLT.US", SPLT_SPLITS)
    fx.divs(run1, "SPLT.US", SPLT_DIVS)

    # run 2 (now 2024-02-14): tail of 10 from 2024-01-30, one new session,
    # Feb 8 close+adjusted_close revised, Feb 9 volume revised
    tail_dates = [d for d in SPLT_DATES if d >= date(2024, 1, 30)] + [date(2024, 2, 13)]
    tail = []
    for d in tail_dates:
        i = SPLT_DATES.index(d) if d in SPLT_DATES else 30
        bump = None
        if d == date(2024, 2, 8):
            bump = {"close": 21.31, "adjusted_close": 21.2}
        if d == date(2024, 2, 9):
            bump = {"volume": 777777}
        tail.append(splt_row(i, d, bump=bump))
    run2 = os.path.join(base, "run2")
    fx.eod(run2, "SPLT.US", tail, start="2024-01-30")
    fx.splits(run2, "SPLT.US", SPLT_SPLITS)
    fx.divs(run2, "SPLT.US", SPLT_DIVS)
    # the provider's revised FULL history (2024-01-10 close changed): keyed
    # on the first-fill request, which a tail-refresh run never sends
    full = splt_rows()
    full[6] = dict(full[6], close=231.0)
    fx.eod(run2, "SPLT.US", full, start="2024-01-02")

    # run 2 served rows OUTSIDE the requested window (provider ignoring from)
    wide_dates = [d for d in SPLT_DATES if d >= date(2024, 1, 25)]
    wide = []
    for d in wide_dates:
        i = SPLT_DATES.index(d)
        bump = {"close": 155.0} if d == date(2024, 1, 25) else None
        wide.append(splt_row(i, d, bump=bump))
    wide_dir = os.path.join(base, "wide")
    fx.eod(wide_dir, "SPLT.US", wide, start="2024-01-30")

    # end-capped first fill (universe end 2024-01-19)
    cap = os.path.join(base, "endcap")
    fx.eod(cap, "SPLT.US", [r for r in rows if r["date"] <= "2024-01-19"],
           start="2024-01-02", end="2024-01-19")
    fx.splits(cap, "SPLT.US", SPLT_SPLITS)
    fx.divs(cap, "SPLT.US", SPLT_DIVS)

    # failures: eod 404 after a good actions refresh; splits 503
    e404 = os.path.join(base, "eod404")
    fx.eod(e404, "SPLT.US", {"error": "Ticker Not Found."}, start="2024-01-02",
           status=404)
    fx.splits(e404, "SPLT.US", SPLT_SPLITS)
    fx.divs(e404, "SPLT.US", SPLT_DIVS)
    s503 = os.path.join(base, "splits503")
    fx.eod(s503, "SPLT.US", rows, start="2024-01-02")
    fx.splits(s503, "SPLT.US", {"error": "busy"}, status=503)
    fx.divs(s503, "SPLT.US", SPLT_DIVS)

    # late split: the first fill knows only the 3:2 split
    late1 = os.path.join(base, "late1")
    fx.eod(late1, "SPLT.US", rows, start="2024-01-02")
    fx.splits(late1, "SPLT.US", [SPLT_SPLITS[1]])
    fx.divs(late1, "SPLT.US", SPLT_DIVS)
    late2 = os.path.join(base, "late2")
    fx.eod(late2, "SPLT.US",
           [splt_row(SPLT_DATES.index(d), d) for d in SPLT_DATES if d >= date(2024, 1, 30)],
           start="2024-01-30")
    fx.splits(late2, "SPLT.US", SPLT_SPLITS)
    fx.divs(late2, "SPLT.US", SPLT_DIVS)


# ---------------------------------------------------------------- DIVY.US (bond_etf, dividends, no splits)
def gen_divy():
    base = os.path.join(HTTP, "divy")
    shutil.rmtree(base, ignore_errors=True)
    dates = fx.weekdays(date(2024, 3, 1), date(2024, 3, 28))       # 20
    divs = [
        {"date": "2024-03-15", "value": 0.31, "unadjustedValue": 0.31, "currency": "USD", "period": "Monthly"},
        {"date": "2024-03-01", "value": 0.30, "unadjustedValue": 0.30, "currency": "USD", "period": "Monthly"},
        {"date": "2024-03-28", "value": 0.32, "unadjustedValue": 0.32, "currency": "USD", "period": "Monthly"},
    ]
    rows = []
    for i, d in enumerate(dates):
        close = r2(95.0 + 0.1 * i)
        # provider's splits+dividends close: dividends after d discounted
        future = sum(x["value"] for x in divs if x["date"] > d.isoformat())
        rows.append({"date": d.isoformat(), "open": r2(close - 0.2), "high": r2(close + 0.4),
                     "low": r2(close - 0.5), "close": close,
                     "adjusted_close": round(close - future, 4),
                     "volume": 50000 + 250 * i})
    run1 = os.path.join(base, "run1")
    fx.eod(run1, "DIVY.US", rows)                     # no start: full history
    fx.splits(run1, "DIVY.US", [])
    fx.divs(run1, "DIVY.US", divs)


# ---------------------------------------------------------------- ZERO-USD.CC (eodhd crypto, zero-volume run)
ZERO_DATES = fx.days(date(2024, 1, 1), date(2024, 2, 9))           # 40


def zero_rows():
    rows = []
    for i, d in enumerate(ZERO_DATES):
        close = r2(1.25 + 0.01 * i)
        vol = 0 if (date(2024, 1, 10) <= d <= date(2024, 1, 14) or d == date(2024, 1, 25)) else 3000 + 10 * i
        rows.append({"date": d.isoformat(), "open": close, "high": r2(close + 0.02),
                     "low": r2(close - 0.02), "close": close, "adjusted_close": close,
                     "volume": vol})
    return rows


def gen_zero():
    base = os.path.join(HTTP, "zero")
    shutil.rmtree(base, ignore_errors=True)
    rows = zero_rows()
    run1 = os.path.join(base, "run1")
    fx.eod(run1, "ZERO-USD.CC", rows, start="2024-01-01", end="2024-02-09")


# ---------------------------------------------------------------- PAIR: eodhd PAIR-USD.CC + binance PAIRUSDT
PAIR_DATES = fx.days(date(2024, 1, 1), date(2024, 1, 20))


def kline(d, o, h, l, c, v):
    t = fx.ms(d)
    return [t, f"{o:.2f}", f"{h:.2f}", f"{l:.2f}", f"{c:.2f}", f"{v:.3f}", t + fx.DAY_MS - 1,
            "0", 100, "0", "0", "0"]


def gen_pair():
    base = os.path.join(HTTP, "pair")
    shutil.rmtree(base, ignore_errors=True)
    for variant, last_b in (("at", 99.75), ("above", 99.70)):
        d_ = os.path.join(base, variant)
        e_rows, k_rows = [], []
        for i, d in enumerate(PAIR_DATES):
            ce = 100.25 if d == PAIR_DATES[-1] else r2(90.0 + 0.5 * i)
            cb = last_b if d == PAIR_DATES[-1] else r2(90.0 + 0.5 * i - 0.05)
            e_rows.append({"date": d.isoformat(), "open": ce, "high": r2(ce + 1), "low": r2(ce - 1),
                           "close": ce, "adjusted_close": ce, "volume": 1000000 + i})
            k_rows.append(kline(d, cb, cb + 1, cb - 1, cb, 12.5 + i))
        fx.eod(d_, "PAIR-USD.CC", e_rows, start="2024-01-01", end="2024-01-20")
        fx.klines(d_, "PAIRUSDT", k_rows, start_ms=fx.ms(date(2024, 1, 1)),
                  end_ms=fx.ms(date(2024, 1, 20)) + fx.DAY_MS - 1)


# ---------------------------------------------------------------- binance page limit + pagination
def gen_binance():
    base = os.path.join(HTTP, "binance")
    shutil.rmtree(base, ignore_errors=True)
    # 1000 newest bars, no start declared: the provider's default slice
    last = date(2024, 6, 30)
    first = last - timedelta(days=999)
    lim = os.path.join(base, "limit")
    rows = [kline(d, 10 + (k % 7), 11 + (k % 7), 9 + (k % 7), 10.5 + (k % 7), 1.0 + k)
            for k, d in enumerate(fx.days(first, last))]
    assert len(rows) == 1000
    fx.klines(lim, "LIMUSDT", rows, end_ms=fx.ms(last) + fx.DAY_MS - 1)
    # two pages from a declared start
    pg = os.path.join(base, "pages")
    start = date(2021, 1, 1)
    end = date(2024, 1, 15)
    alld = fx.days(start, end)
    page1 = [kline(d, 20 + (k % 5), 21 + (k % 5), 19 + (k % 5), 20.5 + (k % 5), 2.0 + k)
             for k, d in enumerate(alld[:1000])]
    page2 = [kline(d, 30, 31, 29, 30.5, 5.0) for d in alld[1000:]]
    fx.klines(pg, "PGSUSDT", page1, start_ms=fx.ms(start), end_ms=fx.ms(end) + fx.DAY_MS - 1)
    fx.klines(pg, "PGSUSDT", page2, start_ms=fx.ms(alld[1000]), end_ms=fx.ms(end) + fx.DAY_MS - 1)


# ---------------------------------------------------------------- namespace vs declaration, zero end-cap
def gen_ns():
    base = os.path.join(HTTP, "ns")
    shutil.rmtree(base, ignore_errors=True)
    dates = fx.days(date(2024, 5, 1), date(2024, 5, 10))
    rows = [{"date": d.isoformat(), "open": 10.0 + i, "high": 11.0 + i, "low": 9.0 + i,
             "close": 10.5 + i, "adjusted_close": 10.5 + i, "volume": 700 + i}
            for i, d in enumerate(dates)]
    # WEIRD.XX: declared crypto outside the .CC namespace -> guarded, no actions
    fx.eod(base, "WEIRD.XX", rows, end="2024-05-10")
    # CCSTK-USD.CC: a .CC symbol declared stock -> actions + raw basis, no guard
    wk = [r for r in rows if date.fromisoformat(r["date"]).weekday() < 5]
    fx.eod(base, "CCSTK-USD.CC", wk)
    fx.splits(base, "CCSTK-USD.CC", [{"date": "2024-05-06", "split": "2/1"}])
    fx.divs(base, "CCSTK-USD.CC", [])
    # zero end-cap: crypto end 2024-01-20 below the guard
    cap = os.path.join(HTTP, "zero", "endcap")
    fx.eod(cap, "ZERO-USD.CC", [r for r in zero_rows() if r["date"] <= "2024-01-20"],
           start="2024-01-01", end="2024-01-20")


# ---------------------------------------------------------------- RES.US: raw basis, 3:1 split, 70 sessions
def gen_res():
    base = os.path.join(HTTP, "res")
    shutil.rmtree(base, ignore_errors=True)
    dates = fx.weekdays(date(2024, 1, 1), date(2024, 4, 7))[:70]
    split_day = dates[35]
    rows = []
    for i, d in enumerate(dates):
        step = (i % 4) * 1.5
        close = 300.0 + step if d < split_day else 100.0 + (i % 4) * 0.5
        rows.append({"date": d.isoformat(), "open": close, "high": close + 1.5,
                     "low": close - 1.5, "close": close, "adjusted_close": close,
                     "volume": 1000 + i})
    fx.eod(base, "RES.US", rows, start="2024-01-01")
    fx.splits(base, "RES.US", [{"date": split_day.isoformat(), "split": "3/1"}])
    fx.divs(base, "RES.US", [])
    return split_day


# ---------------------------------------------------------------- CSV fixtures for import and status
def write_csv(name, rows):
    os.makedirs(CSV, exist_ok=True)
    with open(os.path.join(CSV, name), "w", encoding="utf-8") as f:
        f.write("Date,Open,High,Low,Close,Adj Close,Volume\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")


def bar(d, close, volume, adj=None):
    return (d.isoformat(), close, round(close + 0.5, 2), round(close - 0.5, 2), close,
            close if adj is None else adj, volume)


def gen_csv():
    shutil.rmtree(CSV, ignore_errors=True)
    # small Yahoo-style import: zero-volume row, duplicate date, Adj Close below Close
    write_csv("yahoo_small.csv", [
        ("2024-01-02", 10.0, 11.0, 9.5, 10.5, 10.4, 1000),
        ("2024-01-03", 10.5, 11.5, 10.0, 11.0, 10.9, 0),
        ("2024-01-04", 11.0, 12.0, 10.5, 11.5, 11.4, 1200),
        ("2024-01-04", 99.0, 99.0, 99.0, 99.0, 99.0, 9),
        ("2025-01-02", 12.0, 12.5, 11.5, 12.25, 12.2, 1300),
    ])
    write_csv("yahoo_shrunk.csv", [
        ("2024-01-02", 10.0, 11.0, 9.5, 10.5, 10.4, 1000),
    ])
    # weekday stock series ending Friday 2024-03-01 (staleness, freshness, today)
    wk = fx.weekdays(date(2024, 2, 1), date(2024, 3, 1))
    write_csv("stock_feb.csv", [bar(d, round(50 + 0.25 * i, 2), 1000 + i) for i, d in enumerate(wk)])
    # crypto daily series ending 2024-03-01
    dd = fx.days(date(2024, 2, 1), date(2024, 3, 1))
    write_csv("crypto_feb.csv", [bar(d, round(20 + 0.1 * i, 2), 500 + i) for i, d in enumerate(dd)])
    # zero-volume: two isolated zero rows (crypto daily)
    z = fx.days(date(2024, 1, 1), date(2024, 1, 20))
    write_csv("zero_single.csv", [bar(d, round(5 + 0.01 * i, 2), 0 if i in (4, 9) else 100 + i)
                                  for i, d in enumerate(z)])
    # zero-volume runs 2, 3, 3 rows (the earliest longest run is reported)
    write_csv("zero_runs.csv", [bar(d, round(5 + 0.01 * i, 2),
                                    0 if i in (2, 3, 6, 7, 8, 12, 13, 14) else 100 + i)
                                for i, d in enumerate(z)])
    # post-seam gap: weekday stock, Feb 2024, provider omits 5 weekdays
    # (2024-02-12..16), one weekday (2024-02-21) and the zero-volume 2024-02-26
    g = [d for d in fx.weekdays(date(2024, 2, 1), date(2024, 2, 29))
         if not (date(2024, 2, 12) <= d <= date(2024, 2, 16)) and d != date(2024, 2, 21)]
    write_csv("gap_stock.csv", [bar(d, round(30 + 0.1 * i, 2), 0 if d == date(2024, 2, 26) else 900 + i)
                                for i, d in enumerate(g)])
    # resolution: 100 traded weekdays; closes on a 20-value grid; flat pairs controlled
    rd = fx.weekdays(date(2023, 6, 1), date(2024, 6, 1))
    def grid(n_sessions, n_distinct, n_flat):
        closes = []
        k = 0
        for i in range(n_sessions):
            if i > 0 and i <= n_flat:
                closes.append(closes[-1])          # a flat pair
            else:
                closes.append(round(40 + 0.25 * (k % n_distinct), 2))
                k += 1
        return closes
    def res_csv(name, n, distinct, flat, zero_extra=0):
        cl = grid(n, distinct, flat)
        rows = [bar(rd[i], cl[i], 2000 + i) for i in range(n)]
        write_csv(name, rows)
        return cl
    res_csv("res_at.csv", 100, 20, 0)        # distinct/sessions = 0.20 exactly
    res_csv("res_coarse.csv", 100, 19, 0)    # 0.19 < 0.20
    res_csv("flat_at.csv", 81, 70, 20)       # flat 20 / 80 = 0.25 exactly
    res_csv("flat_over.csv", 81, 70, 21)     # flat 21 / 80 = 0.2625
    # jumps: 30 weekday sessions; newest 10 rows = index 20..29
    jd = fx.weekdays(date(2024, 4, 1), date(2024, 5, 31))[:30]
    jc = [100.0] * 30
    jc[19] = 150.0      # +50% at index 19: just OUTSIDE the newest-10 scan
    jc[20] = 100.0      # -33.3% back at index 20 (inside, under the threshold)
    jc[23] = 60.0       # -40% exactly at index 23: not beyond the threshold
    jc[24] = 100.0      # +66.7% at index 24: beyond -> alert
    for i in range(25, 30):
        jc[i] = 100.0
    jc[27] = 145.0      # +45% at index 27 -> alert
    jc[28] = 100.0      # -31.0% at index 28
    write_csv("jumps.csv", [bar(jd[i], jc[i], 3000 + i) for i in range(30)])
    # cross-venue unmeasurable: zero mid on the common day; disjoint windows
    md = fx.days(date(2024, 1, 1), date(2024, 1, 5))
    write_csv("mid_a.csv", [bar(d, 0.0 if i == 4 else 10.0 + i, 100) for i, d in enumerate(md)])
    write_csv("mid_b.csv", [bar(d, 0.0 if i == 4 else 10.1 + i, 100) for i, d in enumerate(md)])
    old = fx.days(date(2023, 1, 1), date(2023, 1, 12))
    write_csv("old_b.csv", [bar(d, 10.0, 100) for d in old])
    new = fx.days(date(2023, 1, 1), date(2023, 1, 24))
    write_csv("new_a.csv", [bar(d, 10.0, 100) for d in new])
    # future-dated healthy series for clock-independent table output (crypto daily, 70 rows)
    fd = fx.days(date(2099, 1, 1), date(2099, 3, 11))
    write_csv("future_crypto.csv", [bar(d, round(1.5 + 0.01 * (i % 50), 2), 0 if i == 10 else 10 + i)
                                    for i, d in enumerate(fd)])
    fw = fx.weekdays(date(2099, 1, 1), date(2099, 1, 31))
    write_csv("future_stock.csv", [bar(d, round(70 + 0.5 * i, 2), 400 + i) for i, d in enumerate(fw)])
    # validation probes
    with open(os.path.join(CSV, "invalid_mix.csv"), "w") as f:
        f.write("Date,Open,High,Low,Close,Adj Close,Volume,Extra\n"
                "2024-01-03,10,11,9,10.5,10.4,100,x\n"
                "2024-01-02,10,9,11,10.5,10.4,-5,\n"
                "bad,abc,11,9,10.5,10.4,0,y\n"
                "2024-01-03,10,11,9,,10.4,100,z\n")
    with open(os.path.join(CSV, "invalid_values.csv"), "w") as f:
        f.write("Date,Open,High,Low,Close,Adj Close,Volume\n"
                "2024-01-02,-1,1,1,1,1,1\n"
                "2024-01-03,1,1,2,1,1,0\n"
                "2024-01-04,1,2,1,,1,5\n"
                "2024-01-05,1,2,1,1,1,-3\n")
    with open(os.path.join(CSV, "bad_dates.csv"), "w") as f:
        f.write("Date,Open,High,Low,Close,Adj Close,Volume\n"
                "2024-01-02,1,1,1,1,1,1\n05.01.2024,1,1,1,1,1,1\n2024-01-08,1,1,1,1,1,1\n")
    with open(os.path.join(CSV, "missing_cols.csv"), "w") as f:
        f.write("Date,Open,Close\n2024-01-02,1,2\n")
    with open(os.path.join(CSV, "no_dates.csv"), "w") as f:
        f.write("Date,Open,High,Low,Close,Adj Close,Volume\n"
                "2024-01-02x,1,1,1,1,1,1\nnope,1,1,1,1,1,1\n")
    # differential partner for yahoo_small (one changed close, one missing date, one extra)
    write_csv("diff_b.csv", [
        ("2024-01-02", 10.0, 11.0, 9.5, 10.6, 10.4, 1000),
        ("2024-01-03", 10.5, 11.5, 10.0, 11.0, 10.9, 5),
        ("2024-01-05", 11.0, 12.0, 10.5, 11.5, 11.4, 1200),
        ("2025-01-02", 12.0, 12.5, 11.5, 12.25, 12.2, 1300),
    ])


# ---------------------------------------------------------------- malformed universes
BAD = {
    "toml_syntax": 'this is = = not toml\n',
    "top_key": 'foo = 1\n[[asset]]\nname = "X"\nasset_class = "stock"\n  [[asset.source]]\n  provider = "eodhd"\n  symbol = "X.US"\n',
    "defaults_table": 'defaults = 3\n',
    "defaults_key": '[defaults]\nstore = "d"\nbogus = 1\n',
    "defaults_store": '[defaults]\nstore = ""\n',
    "no_assets": '[defaults]\nstore = "data"\n',
    "asset_table": 'asset = [1]\n',
    "asset_key": '[[asset]]\nname = "X"\nasset_class = "stock"\ncolour = "red"\n',
    "asset_name": '[[asset]]\nasset_class = "stock"\n',
    "asset_class_missing": '[[asset]]\nname = "X"\n',
    "asset_class_bad": '[[asset]]\nname = "X"\nasset_class = "forex"\n',
    "threshold": '[[asset]]\nname = "X"\nasset_class = "stock"\nthreshold = true\n',
    "no_source": '[[asset]]\nname = "X"\nasset_class = "stock"\n',
    "enabled": '[[asset]]\nname = "X"\nasset_class = "stock"\nenabled = "yes"\n  [[asset.source]]\n  provider = "eodhd"\n  symbol = "X.US"\n',
    "source_table": '[[asset]]\nname = "X"\nasset_class = "stock"\nsource = [1]\n',
    "source_key": '[[asset]]\nname = "X"\nasset_class = "stock"\n  [[asset.source]]\n  provider = "eodhd"\n  symbol = "X.US"\n  colour = "x"\n',
    "provider_bad": '[[asset]]\nname = "X"\nasset_class = "stock"\n  [[asset.source]]\n  provider = "yahoo"\n  symbol = "X.US"\n',
    "kind": '[[asset]]\nname = "X"\nasset_class = "stock"\n  [[asset.source]]\n  provider = "eodhd"\n  symbol = "X.US"\n  kind = "intraday"\n',
    "bare_ticker": '[[asset]]\nname = "X"\nasset_class = "stock"\n  [[asset.source]]\n  provider = "eodhd"\n  symbol = "X"\n',
    "modeled_type": '[[asset]]\nname = "X"\nasset_class = "stock"\n  [[asset.source]]\n  provider = "eodhd"\n  symbol = "X.US"\n  modeled = "yes"\n',
    "csv_path": '[[asset]]\nname = "X"\nasset_class = "stock"\n  [[asset.source]]\n  provider = "yahoo-csv"\n  symbol = "X"\n',
    "csv_window": '[[asset]]\nname = "X"\nasset_class = "stock"\n  [[asset.source]]\n  provider = "yahoo-csv"\n  symbol = "X"\n  path = "x.csv"\n  end = 2024-01-31\n',
    "collector_path": '[[asset]]\nname = "X"\nasset_class = "stock"\n  [[asset.source]]\n  provider = "binance"\n  symbol = "XUSDT"\n  path = "x.csv"\n',
    "bad_date": '[[asset]]\nname = "X"\nasset_class = "stock"\n  [[asset.source]]\n  provider = "eodhd"\n  symbol = "X.US"\n  start = "2024-13-01"\n',
    "inverted": '[[asset]]\nname = "X"\nasset_class = "stock"\n  [[asset.source]]\n  provider = "eodhd"\n  symbol = "X.US"\n  start = 2024-02-01\n  end = "20240101"\n',
    "modeled_disabled": '[[asset]]\nname = "X"\nasset_class = "stock"\n  [[asset.source]]\n  provider = "eodhd"\n  symbol = "X.US"\n  modeled = true\n  enabled = false\n  [[asset.source]]\n  provider = "binance"\n  symbol = "XUSDT"\n',
    "two_modeled": '[[asset]]\nname = "X"\nasset_class = "crypto"\n  [[asset.source]]\n  provider = "eodhd"\n  symbol = "X-USD.CC"\n  modeled = true\n  [[asset.source]]\n  provider = "binance"\n  symbol = "XUSDT"\n  modeled = true\n',
    "none_modeled": '[[asset]]\nname = "X"\nasset_class = "crypto"\n  [[asset.source]]\n  provider = "eodhd"\n  symbol = "X-USD.CC"\n  [[asset.source]]\n  provider = "binance"\n  symbol = "XUSDT"\n',
    "all_off": '[[asset]]\nname = "X"\nasset_class = "stock"\n  [[asset.source]]\n  provider = "eodhd"\n  symbol = "X.US"\n  enabled = false\n',
    "dupe_name": '[[asset]]\nname = "X"\nasset_class = "stock"\n  [[asset.source]]\n  provider = "eodhd"\n  symbol = "X.US"\n[[asset]]\nname = "X"\nasset_class = "stock"\n  [[asset.source]]\n  provider = "eodhd"\n  symbol = "Y.US"\n',
    "dupe_coord": '[[asset]]\nname = "X"\nasset_class = "stock"\n  [[asset.source]]\n  provider = "eodhd"\n  symbol = "X.US"\n[[asset]]\nname = "Y"\nasset_class = "stock"\n  [[asset.source]]\n  provider = "eodhd"\n  exchange = "eodhd"\n  symbol = "X.US"\n',
    "first_wins": '[[asset]]\nname = "X"\nasset_class = "forex"\ncolour = 1\n',
}


def gen_bad_universes():
    d = os.path.join(FIX, "universes", "bad")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    for name, text in BAD.items():
        with open(os.path.join(d, name + ".toml"), "w", encoding="utf-8") as f:
            f.write(text)


# ---------------------------------------------------------------- more SPLT variants, the mixed set
def gen_more():
    base = os.path.join(HTTP, "splt")
    rows = splt_rows()
    for name, text in (("badsplit", "4:1"), ("zerosplit", "0/1")):
        d = os.path.join(base, name)
        shutil.rmtree(d, ignore_errors=True)
        fx.eod(d, "SPLT.US", rows, start="2024-01-02")
        fx.splits(d, "SPLT.US", [{"date": "2024-01-17", "split": text}])
        fx.divs(d, "SPLT.US", [])
    # many revisions: every tail row re-served with close and adjusted_close moved
    d = os.path.join(base, "many")
    shutil.rmtree(d, ignore_errors=True)
    tail = [d_ for d_ in SPLT_DATES if d_ >= date(2024, 1, 30)]
    served = []
    for d_ in tail:
        r = splt_row(SPLT_DATES.index(d_), d_)
        r["close"] = round(r["close"] + 0.01, 2)
        r["adjusted_close"] = round(r["adjusted_close"] + 0.01, 4)
        served.append(r)
    fx.eod(d, "SPLT.US", served, start="2024-01-30")
    # mixed: SPLT answers 404 on bars, DIVY is healthy (one EODHD collector serves both)
    m = os.path.join(HTTP, "mixed")
    shutil.rmtree(m, ignore_errors=True)
    for f in os.listdir(os.path.join(base, "eod404")):
        shutil.copyfile(os.path.join(base, "eod404", f), os.path.join(m, f)) if os.path.isdir(m) else (os.makedirs(m), shutil.copyfile(os.path.join(base, "eod404", f), os.path.join(m, f)))
    for f in os.listdir(os.path.join(HTTP, "divy", "run1")):
        shutil.copyfile(os.path.join(HTTP, "divy", "run1", f), os.path.join(m, f))
    # both the actions and the bars would fail: the first request decides
    bf = os.path.join(base, "both_fail")
    shutil.rmtree(bf, ignore_errors=True)
    fx.eod(bf, "SPLT.US", {"error": "Ticker Not Found."}, start="2024-01-02", status=404)
    fx.splits(bf, "SPLT.US", {"error": "busy"}, status=503)
    fx.divs(bf, "SPLT.US", [])
    # bar endpoints answering 200 with something that is not a list
    nl = os.path.join(base, "notlist")
    shutil.rmtree(nl, ignore_errors=True)
    fx.eod(nl, "SPLT.US", {"code": 200, "message": "no data"}, start="2024-01-02")
    fx.splits(nl, "SPLT.US", [])
    fx.divs(nl, "SPLT.US", [])
    bnl = os.path.join(HTTP, "binance_notlist")
    shutil.rmtree(bnl, ignore_errors=True)
    fx.klines(bnl, "LIMUSDT", {"code": -1121, "msg": "Invalid symbol."},
              end_ms=fx.ms(date(2024, 6, 30)) + fx.DAY_MS - 1)
    # replay rules: content keys (a renamed file), recursion (a nested file),
    # and manifest.json skipped (it would answer the bars with a 500)
    r = os.path.join(base, "replay")
    shutil.rmtree(r, ignore_errors=True)
    os.makedirs(os.path.join(r, "nested"))
    run1 = os.path.join(base, "run1")
    eod_name = [f for f in os.listdir(run1) if f.startswith("api_eod_")][0]
    spl_name = [f for f in os.listdir(run1) if f.startswith("api_splits_")][0]
    div_name = [f for f in os.listdir(run1) if f.startswith("api_div_")][0]
    shutil.copyfile(os.path.join(run1, eod_name), os.path.join(r, eod_name))
    shutil.copyfile(os.path.join(run1, spl_name), os.path.join(r, "renamed_on_purpose.json"))
    shutil.copyfile(os.path.join(run1, div_name), os.path.join(r, "nested", div_name))
    doc = json.load(open(os.path.join(run1, eod_name)))
    doc["response"] = {"status": 500, "json": {"error": "a manifest is not a fixture"}}
    with open(os.path.join(r, "manifest.json"), "w") as f:
        f.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    gen_splt()
    gen_divy()
    gen_zero()
    gen_pair()
    gen_binance()
    gen_ns()
    gen_res()
    gen_csv()
    gen_bad_universes()
    gen_more()
    print("generated", HTTP)

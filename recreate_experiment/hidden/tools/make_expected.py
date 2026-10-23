"""Record the expected frames the scenarios compare against, by running the
SUBJECT through its adapter (calibration tooling, hidden)."""
import json
import math
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "hidden"))
import adapter_original as a  # noqa: E402

FIX = os.path.join(ROOT, "kit", "features", "fixtures")
OUT = os.path.join(FIX, "expected")


def N(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def dump(frame, name):
    os.makedirs(OUT, exist_ok=True)
    dtypes = {c: str(frame[c].dtype) for c in frame.columns}
    data = []
    for row in frame.itertuples(index=False):
        out = []
        for c, v in zip(frame.columns, row):
            if dtypes[c].startswith("datetime64"):
                out.append(v.isoformat())
            elif dtypes[c] == "int64":
                out.append(int(v))
            elif dtypes[c] == "float64":
                out.append(float(v))
            else:
                out.append(str(v))
        data.append(out)
    doc = {"columns": list(frame.columns), "dtypes": {c: ("text" if d in ("str", "object", "string") else d) for c, d in dtypes.items()}, "data": data}
    with open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8") as f:
        f.write('{"columns": ' + json.dumps(doc["columns"]) + ',\n "dtypes": ' + json.dumps(doc["dtypes"])
                + ',\n "data": [\n')
        f.write(",\n".join("  " + json.dumps(r, allow_nan=True) for r in data))
        f.write("\n ]}\n")


def sync(store, uni, sets, now, **kw):
    u = a.load_universe(os.path.join(FIX, "universes", uni))
    cols = {p: a.make_collector(p, os.path.join(FIX, "http", s)) for p, s in sets.items()}
    res, ok = a.run_sync(u, store, now=N(now), collectors=cols, **kw)
    assert ok, res


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    tmp = tempfile.mkdtemp(dir=os.path.join(ROOT, "hidden", "scratch"))
    s = os.path.join(tmp, "splt")
    sync(s, "splt.toml", {"eodhd": "splt/run1"}, "2024-02-13T12:00:00Z")
    dump(a.stored_frame(s, "eodhd", "SPLT.US"), "splt_run1_stored")
    dump(a.export_frame(s, "eodhd", "SPLT.US"), "splt_run1_export")
    sync(s, "splt.toml", {"eodhd": "splt/run2"}, "2024-02-14T12:00:00Z")
    dump(a.stored_frame(s, "eodhd", "SPLT.US"), "splt_run2_stored")
    d = os.path.join(tmp, "divy")
    sync(d, "divy.toml", {"eodhd": "divy/run1"}, "2024-03-29T01:00:00Z")
    dump(a.stored_frame(d, "eodhd", "DIVY.US"), "divy_stored")
    dump(a.export_frame(d, "eodhd", "DIVY.US"), "divy_export")
    z = os.path.join(tmp, "zero")
    sync(z, "zero.toml", {"eodhd": "zero/run1"}, "2024-02-10T08:00:00Z")
    dump(a.stored_frame(z, "eodhd", "ZERO-USD.CC"), "zero_stored")
    p = os.path.join(tmp, "pair")
    sync(p, "pair.toml", {"eodhd": "pair/at", "binance": "pair/at"}, "2024-01-21T06:00:00Z")
    dump(a.stored_frame(p, "eodhd", "PAIR-USD.CC"), "pair_eodhd_stored")
    dump(a.stored_frame(p, "binance", "PAIRUSDT"), "pair_binance_stored")
    l = os.path.join(tmp, "late")
    sync(l, "splt.toml", {"eodhd": "splt/late1"}, "2024-02-13T12:00:00Z")
    sync(l, "splt.toml", {"eodhd": "splt/late2"}, "2024-02-14T12:00:00Z", force_actions=True)
    dump(a.stored_frame(l, "eodhd", "SPLT.US"), "late_stored")
    y = os.path.join(tmp, "small")
    a.import_csv(y, os.path.join(FIX, "csv", "yahoo_small.csv"), "yahoo", "SMALL", "stock")
    dump(a.stored_frame(y, "yahoo", "SMALL"), "small_stored")
    dump(a.export_frame(y, "yahoo", "SMALL"), "small_export")
    n = os.path.join(tmp, "ns")
    sync(n, "ns.toml", {"eodhd": "ns"}, "2024-05-11T06:00:00Z")
    dump(a.stored_frame(n, "eodhd", "CCSTK-USD.CC"), "ccstk_stored")
    dump(a.stored_frame(n, "eodhd", "WEIRD.XX"), "weird_stored")
    shutil.rmtree(tmp)
    print("expected frames:", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()

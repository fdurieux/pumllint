import json, sys
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
sys.path.insert(0, "/tmp/claude-0/-home-user-pumllint/a27ff026-fb34-5f15-89ad-04bb2be6b2d3/scratchpad/wr-W/out")
import adapter_rc as A
import pandas as pd
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
root = Path(sys.argv[1])
def fixture(d, name, path, params, status, body):
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps({"request": {"method": "GET", "path": path, "params": params}, "response": {"status": status, "json": body}}))
f2 = root/"fx2"
# tail 3 -> start 2024-09-04
rows=[]
for d,px in [(date(2024,9,4),101.75),(date(2024,9,5),102.10),(date(2024,9,6),102.25),(date(2024,9,9),103.0)]:
    rows.append({"date": d.isoformat(), "open": px, "high": px+1, "low": px-1, "close": px, "adjusted_close": px*0.99, "volume": 4000.0})
rows[2]["adjusted_close"] = 102.25*0.99  # unchanged
fixture(f2, "eod", "/api/eod/AAPL.US", {"fmt":"json","order":"a","period":"d","from":"2024-09-04"}, 200, rows)
fixture(f2, "splits", "/api/splits/AAPL.US", {"fmt":"json"}, 200, [{"date":"2024-09-02","split":"4.000000/1.000000"}])
fixture(f2, "div", "/api/div/AAPL.US", {"fmt":"json"}, 200, [])
# BTC eodhd: no fixture -> leg fails
uni = root/"u.toml"
U = A.load_universe(str(uni))
store = root/"store"
now = datetime(2024,9,10,9,0,tzinfo=timezone.utc)
lines=[]
cols = {"eodhd": A.make_collector("eodhd", str(f2)), "binance": A.make_collector("binance", str(f2))}
res, ok = A.run_sync(U, str(store), now=now, collectors=cols, out=lines.append, tail=3)
print("\n".join(lines)); print("ok", ok)
s = A.sync_summary(res, ok); print(json.dumps({k:v for k,v in s.items() if k!="results"}), json.dumps(s["results"][0]["revisions"]))
print(A.stored_frame(str(store), "eodhd", "AAPL.US")[["datetime","close","close_raw","adjusted_close","volume"]].tail(5))
print("calls eodhd:", cols["eodhd"].transport.calls)
# status at now: BTC legs stale (last 09-06, today 09-10 -> 09-07,08,09 missed =3)
doc, code = A.status_json(U, str(store), now=now, spread_threshold=0.0001, spread_alerts=True)
for r in doc["reports"]+doc["pairs"]: print(json.dumps({k:r[k] for k in r if k in ("symbol","a","alerts","warnings","notes","missed_sessions","spread")}))
print("code", code, doc["alerts_total"], doc["warnings_total"])
# inverted: pinned end before tail start
uni2 = root/"u2.toml"
uni2.write_text('''
[[asset]]
name = "AAPL"
asset_class = "stock"
  [[asset.source]]
  provider = "eodhd"
  symbol = "AAPL.US"
  end = 2024-08-30
''')
U2 = A.load_universe(str(uni2))
lines=[]
res, ok = A.run_sync(U2, str(store), now=now, collectors={"eodhd": A.make_collector("eodhd", str(f2))}, out=lines.append, tail=3)
print("\n".join(lines), ok)
lines=[]
A.run_sync(U2, str(store), now=now, dry_run=True, out=lines.append, tail=3); print("\n".join(lines))
for bad in [dict(assets=["ZZZ"]), dict(providers=["yahoo"]), dict(providers=["binance"], assets=["AAPL"])]:
    try: A.select_legs(U, **bad)
    except Exception as e: print(type(e).__name__, e)
try: A.run_sync(U, str(store), tail=0)
except Exception as e: print(type(e).__name__, e)

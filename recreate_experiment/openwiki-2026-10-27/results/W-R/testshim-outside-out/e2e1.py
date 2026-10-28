import json, sys, shutil, os
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
sys.path.insert(0, "/tmp/claude-0/-home-user-pumllint/a27ff026-fb34-5f15-89ad-04bb2be6b2d3/scratchpad/wr-W/out")
import adapter_rc as A
import pandas as pd
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)

root = Path(sys.argv[1]); shutil.rmtree(root, ignore_errors=True); root.mkdir()
def fixture(d, name, path, params, status, body):
    (d).mkdir(parents=True, exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps({"request": {"method": "GET", "path": path, "params": params}, "response": {"status": status, "json": body}}))

# weekdays 2024-08-26 .. 2024-09-06 for AAPL.US with a 4:1 split effective 2024-09-02 (Mon)
days = [date(2024,8,26)+timedelta(days=i) for i in range(12)]
days = [d for d in days if d.weekday()<5]
rows=[]
for i,d in enumerate(days):
    px = 400.0+i if d < date(2024,9,2) else 100.0+i/4
    vol = 1000.0*(4 if d < date(2024,9,2) else 1)  # served split-adjusted volume
    rows.append({"date": d.isoformat(), "open": px, "high": px+1, "low": px-1, "close": px, "adjusted_close": px*0.99 if d>=date(2024,9,2) else px/4*0.99, "volume": 4000.0})
f1 = root/"fx1"
fixture(f1, "eod", "/api/eod/AAPL.US", {"fmt":"json","order":"a","period":"d"}, 200, rows)
fixture(f1, "splits", "/api/splits/AAPL.US", {"fmt":"json"}, 200, [{"date":"2024-09-02","split":"4.000000/1.000000"}])
fixture(f1, "div", "/api/div/AAPL.US", {"fmt":"json"}, 200, [{"date":"2024-08-12","value":0.25,"currency":"USD"}])
# binance: BTCUSDT from 2017-08-01? use custom universe instead
uni = root/"u.toml"
uni.write_text('''
[[asset]]
name = "AAPL"
asset_class = "stock"
  [[asset.source]]
  provider = "eodhd"
  symbol = "AAPL.US"
[[asset]]
name = "BTC"
asset_class = "crypto"
  [[asset.source]]
  provider = "eodhd"
  symbol = "BTC-USD.CC"
  modeled = true
  [[asset.source]]
  provider = "binance"
  symbol = "BTCUSDT"
  start = 2024-09-01
''')
# BTC eodhd: every day 2024-09-01..2024-09-06 ; now = 2024-09-07T12:00Z -> guard 2024-09-06
btc_days=[date(2024,9,1)+timedelta(days=i) for i in range(6)]
fixture(f1, "btc", "/api/eod/BTC-USD.CC", {"fmt":"json","order":"a","period":"d","to":"2024-09-06"}, 200,
        [{"date":d.isoformat(),"open":60000+i,"high":60100+i,"low":59900+i,"close":60000.0+i*10,"adjusted_close":60000.0+i*10,"volume":12345.0} for i,d in enumerate(btc_days)])
def ms(d): return int(datetime(d.year,d.month,d.day,tzinfo=timezone.utc).timestamp())*1000
fixture(f1, "klines", "/api/v3/klines", {"symbol":"BTCUSDT","interval":"1d","limit":"1000","startTime":str(ms(date(2024,9,1))),"endTime":str(ms(date(2024,9,6))+86400000-1)}, 200,
        [[ms(d), "60010.0","60110.0","59910.0", str(60010.0+i*10), "100.5", ms(d)+86399999, "0", 1, "0","0","0"] for i,d in enumerate(btc_days)])

U = A.load_universe(str(uni))
print("legs:", json.dumps(A.select_legs(U), indent=None))
store = root/"store"
now = datetime(2024,9,7,12,0,tzinfo=timezone.utc)
lines=[]
cols = {"eodhd": A.make_collector("eodhd", str(f1)), "binance": A.make_collector("binance", str(f1))}
res, ok = A.run_sync(U, str(store), now=now, collectors=cols, out=lines.append)
print("\n".join(lines)); print("ok", ok)
print(json.dumps(A.sync_summary(res, ok), indent=1)[:600])
print(A.stored_frame(str(store), "eodhd", "AAPL.US")[["datetime","open","close","volume","open_raw","close_raw","volume_raw","adjusted_close","adjustment_factor","cumulative_split_factor","price_basis"]])
print(A.export_frame(str(store), "eodhd", "AAPL.US"))
print(A.export_frame(str(store), "eodhd", "AAPL.US").dtypes.to_dict())
print(json.dumps(A.actions_state(str(store), "AAPL.US")))
doc, code = A.status_json(U, str(store), now=now)
print(code, json.dumps(doc, indent=1))

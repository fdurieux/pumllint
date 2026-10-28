import sys, os, json, datetime as dt
sys.path.insert(0, os.environ["OUT"])
import adapter_rc as A
from jef_data_rc.store import ParquetStore
from jef_data_rc.actions import ActionsStore
open("u.toml","w").write('''
[[asset]]
name = "X"
asset_class = "stock"
[[asset.source]]
provider = "eodhd"
symbol = "X.US"
modeled = true
[[asset.source]]
provider = "binance"
symbol = "XUSDT"
''')
u = A.load_universe("u.toml")
st = ParquetStore("st")
days=[]; d=dt.date(2024,1,1)
while len(days)<80:
    if d.weekday()<5: days.append(d)
    d+=dt.timedelta(1)
bars=[]
for i,d in enumerate(days):
    if 20<=i<=29: continue   # provider-omitted era -> seam gap
    px = 10.0 + (i%3)*0.01
    if i==78: px = 20.0  # jump
    vol = 0.0 if i in (5,6,7) else 100.0
    bars.append({"date":d.isoformat(),"open":px,"high":px,"low":px,"close":px,"volume":vol})
st.ingest(bars, exchange="eodhd", symbol="X.US", asset_type="stock", currency="USD", price_basis="raw", splits=[], volume_basis="split_adjusted")
st.ingest([{"date":b["date"],"open":b["close"]*1.01,"high":1,"low":1,"close":b["close"]*1.01,"volume":5} for b in bars], exchange="binance", symbol="XUSDT", asset_type="stock", currency="USD", price_basis="split_adjusted")
ActionsStore("st").save_splits("X.US", [], now=dt.datetime(2024,4,10,tzinfo=dt.timezone.utc))
print("last", days[-1])
now = dt.datetime(2024,4,30,tzinfo=dt.timezone.utc)
env, code = A.status_json(u, "st", now=now); print(json.dumps(env, indent=1)); print("code", code)
env, code = A.status_json(u, "st", now=now, spread_alerts=True); print(env["pairs"][0]["alerts"], env["alerts_total"], code)

import json, sys, shutil
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
sys.path.insert(0, "/tmp/claude-0/-home-user-pumllint/a27ff026-fb34-5f15-89ad-04bb2be6b2d3/scratchpad/wr-W/out")
import adapter_rc as A
root = Path(sys.argv[1]); shutil.rmtree(root, ignore_errors=True); root.mkdir()
def fx(d, name, path, params, body):
    d.mkdir(parents=True, exist_ok=True)
    (d/f"{name}.json").write_text(json.dumps({"request":[ "GET", path, params], "response":{"status":200,"json":body}}))
days=[d for d in (date(2024,6,3)+timedelta(days=i) for i in range(14)) if d.weekday()<5]
rows=[{"date":d.isoformat(),"open":200.0,"high":201.0,"low":199.0,"close":200.0,"adjusted_close":200.0,"volume":500.0} for d in days]
f1=root/"a"; fx(f1,"eod","/api/eod/X.US",{"fmt":"json","order":"a","period":"d"},rows); fx(f1,"s","/api/splits/X.US",{"fmt":"json"},[]); fx(f1,"d","/api/div/X.US",{"fmt":"json"},[])
(root/"u.toml").write_text('[[asset]]\nname="X"\nasset_class="stock"\n  [[asset.source]]\n  provider="eodhd"\n  symbol="X.US"\n')
U=A.load_universe(str(root/"u.toml")); st=str(root/"store")
r,ok=A.run_sync(U, st, now=datetime(2024,6,15,tzinfo=timezone.utc), collectors={"eodhd":A.make_collector("eodhd",str(f1))})
f2=root/"b"; fx(f2,"eod","/api/eod/X.US",{"fmt":"json","order":"a","period":"d","from":"2024-06-10"},rows[5:]); fx(f2,"s","/api/splits/X.US",{"fmt":"json"},[{"date":"2024-06-12","split":"2/1"}]); fx(f2,"d","/api/div/X.US",{"fmt":"json"},[])
lines=[]; r,ok=A.run_sync(U, st, now=datetime(2024,6,16,tzinfo=timezone.utc), collectors={"eodhd":A.make_collector("eodhd",str(f2))}, out=lines.append, force_actions=True, tail=5)
print("\n".join(lines[:4]))
print(A.stored_frame(st,"eodhd","X.US")[["datetime","close","close_raw","volume","volume_raw","cumulative_split_factor"]].to_string())
doc,code=A.status_json(U, st, now=datetime(2024,6,17,tzinfo=timezone.utc)); print(code, doc["reports"][0]["alerts"])

import json, sys, tempfile
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
from jef_data_rc.collectors.base import *
from jef_data_rc.collectors.binance import BinanceCollector
from jef_data_rc.collectors.eodhd import EODHDCollector, normalize_symbol
from jef_data_rc import sync, universe
from jef_data_rc.store import ParquetStore

class Scripted:
    def __init__(self, seq): self.seq=list(seq); self.calls=[]
    def request(self, m, u, p):
        self.calls.append((m,u,dict(p))); x=self.seq.pop(0)
        if isinstance(x, Exception): raise x
        return x
sleeps=[]
lim = RateLimiter(per_minute=10**9, daily_budget=10**9)
c = EODHDCollector(api_key="SECRET123", transport=Scripted([TransportConnectionError("boom SECRET123"), TransportResponse(503,""), TransportResponse(429,""), TransportResponse(500,""), TransportResponse(502,"")]), rate_limiter=lim, sleep=sleeps.append)
try: c.get_eod("AAPL.US")
except CollectorError as e: print("exhaust:", e, sleeps, lim.daily_count)
c = EODHDCollector(api_key="SECRET123", transport=Scripted([TransportResponse(403,"bad token SECRET123 "+"x"*300)]), rate_limiter=lim, sleep=sleeps.append)
try: c.get_eod("AAPL.US")
except CollectorError as e: print("terminal:", str(e)[:80], "SECRET" in str(e), len(str(e)))
c = EODHDCollector(api_key="SECRET123", transport=Scripted([TransportResponse(200,"{not json")]), rate_limiter=lim)
try: c.get_eod("AAPL.US")
except CollectorError as e: print("json:", e)
# rate limiter
t=[0.0]; waits=[]
def clk(): return t[0]
def slp(s): waits.append(s); t[0]+=s
day=[date(2024,1,1)]
r = RateLimiter(per_minute=2, daily_budget=3, clock=clk, sleep=slp, utc_today=lambda: day[0])
r.acquire(); t[0]=10; r.acquire(); t[0]=20; r.acquire(); print("waits", waits, r.daily_count)
try: r.acquire()
except DailyBudgetExhausted as e: print("budget:", e)
day[0]=date(2024,1,2); r.acquire(); print("reset", r.daily_count)
# binance pagination: 2 full pages (limit 3) then short
def ms(d): return int(datetime(d.year,d.month,d.day,tzinfo=timezone.utc).timestamp())*1000
d0=date(2024,1,1)
def page(start, n): return TransportResponse(200, json.dumps([[ms(start+timedelta(days=i)),"1","2","0.5",str(1+i),"10",0,"0",1,"0","0","0"] for i in range(n)]))
tr = Scripted([page(d0,3), page(d0+timedelta(days=3),3), page(d0+timedelta(days=6),1)])
b = BinanceCollector(transport=tr, rate_limiter=lim, limit=3)
bars = b.get_eod("BTCUSDT", start=d0, end=date(2024,1,10)); print(len(bars), [c[2].get("startTime") for c in tr.calls], tr.calls[0][2])
tr = Scripted([page(d0,3) for _ in range(5)]); b = BinanceCollector(transport=tr, rate_limiter=lim, limit=3)
try: b.paginate(lambda cur: ([1], (cur or 0)+1), None, max_pages=4)
except CollectorError as e: print("cap:", e)
# page-limit diagnostic through run_sync with an injected collector
class Fake:
    VOLUME_BASIS="raw"; page_limit=3
    def get_eod(self, s, start=None, end=None): self.args=(start,end); return [{"date":(d0+timedelta(days=i)).isoformat(),"open":1,"high":2,"low":0.5,"close":1.0+i,"volume":5} for i in range(3)]
U = universe.parse_universe({"asset":[{"name":"BTC","asset_class":"crypto","source":[{"provider":"binance","symbol":"BTCUSDT"}]}]})
tmp = tempfile.mkdtemp(); f=Fake(); lines=[]
res, ok = sync.run_sync(U, store=tmp, binance_collector=f, now=datetime(2024,1,5,tzinfo=timezone.utc), out=lines.append)
print(lines[0]); print("window", f.args)
# recording refusal
class Inner:
    def request(self,m,u,p): return TransportResponse(200, json.dumps({"echo":"tok-XYZ"}))
rec = RecordingTransport(Inner(), tmp+"/fx", secrets=["tok-XYZ"])
try: rec.request("GET","https://h/api/x",{"api_token":"tok-XYZ","a":1})
except CollectorError as e: print("record:", e)
rec = RecordingTransport(Inner(), tmp+"/fx", secrets=["other"]); rec.request("GET","https://h/api/eod/X",{"api_token":"tok-XYZ","a":1})
f = next(Path(tmp+"/fx").glob("*.json")); print(f.name, json.loads(f.read_text())["request"])
rp = ReplayTransport(tmp+"/fx"); print(rp.request("GET","https://other/api/eod/X",{"api_token":"zzz","a":"1"}).json(), rp.calls)
print(normalize_symbol("AAPL"), normalize_symbol("EUR/USD"), normalize_symbol("BTC/USD"), normalize_symbol("TLT.US"))
try: normalize_symbol("FOO/BAR")
except CollectorError as e: print("norm:", e)

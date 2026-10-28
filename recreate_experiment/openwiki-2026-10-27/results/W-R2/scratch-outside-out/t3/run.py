import sys, os, json, datetime as dt
sys.path.insert(0, os.environ["OUT"])
from jef_data_rc.collectors.base import request_identity, request_key, ReplayTransport, RateLimiter, CollectorError, TransportResponse, TransportConnectionError
from jef_data_rc.collectors.binance import BinanceCollector
import adapter_rc as A
DAY=86400000
def ms(d): return (dt.date.fromisoformat(d)-dt.date(1970,1,1)).days*DAY
def kl(d, px): return [ms(d), str(px), str(px+1), str(px-1), str(px), "12.5", ms(d)+DAY-1, "0", 1, "0", "0", "0"]
os.makedirs("bfx", exist_ok=True)
def fx(params, body):
    ident = request_identity("GET", "https://api.binance.com/api/v3/klines", params)
    json.dump({"request": ident, "response": {"status": 200, "json": body}}, open(f"bfx/{abs(hash(json.dumps(ident,sort_keys=True)))}.json","w"))
end_ms = ms("2024-01-07")+DAY-1
fx({"symbol":"BTCUSDT","interval":"1d","limit":3,"startTime":ms("2024-01-01"),"endTime":end_ms}, [kl("2024-01-01",100),kl("2024-01-02",101),kl("2024-01-03",102)])
fx({"symbol":"BTCUSDT","interval":"1d","limit":3,"startTime":ms("2024-01-04"),"endTime":end_ms}, [kl("2024-01-04",103),kl("2024-01-05",104),kl("2024-01-06",105)])
fx({"symbol":"BTCUSDT","interval":"1d","limit":3,"startTime":ms("2024-01-07"),"endTime":end_ms}, [kl("2024-01-07",106)])
c = BinanceCollector(limit=3, transport=ReplayTransport("bfx"), rate_limiter=RateLimiter(sleep=lambda s: None))
bars = c.get_eod("BTCUSDT", "2024-01-01", "2024-01-07")
print(len(bars), bars[0], bars[-1])
print(c.transport.calls)
# universe with eodhd crypto + binance + failure in eodhd
open("u.toml","w").write('''
[defaults]
store = "st"
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
start = 2024-01-01
''')
u = A.load_universe("u.toml")
now = dt.datetime(2024,1,8,3,tzinfo=dt.timezone.utc)
bc = BinanceCollector(limit=3, transport=ReplayTransport("bfx"), rate_limiter=RateLimiter(sleep=lambda s: None))
ec = A.make_collector("eodhd", "nofx")
res, ok = A.run_sync(u, None, now=now, collectors={"eodhd": ec, "binance": bc}, out=print)
print("ok", ok)
print(json.dumps(A.sync_summary(res, ok))[:600])
env, code = A.status_json(u, "st", now=now)
print(json.dumps(env, indent=1)); print(code)
res, ok = A.run_sync(u, None, now=now, dry_run=True, out=print)
# retries
class Scripted:
    def __init__(s, seq): s.seq=list(seq); s.n=0
    def request(s, m, u, p):
        s.n+=1; x=s.seq.pop(0)
        if isinstance(x, Exception): raise x
        return x
    def close(s): pass
sleeps=[]
from jef_data_rc.collectors.eodhd import EODHDCollector
t = Scripted([TransportConnectionError("boom"), TransportResponse(500,"x"), TransportResponse(429,"x"), TransportResponse(200,'[]')])
e = EODHDCollector(api_key="sekret", transport=t, sleep=sleeps.append, rate_limiter=RateLimiter(sleep=lambda s: None))
print(e.get_eod("AAPL.US"), sleeps, e.rate_limiter.daily_count)
t = Scripted([TransportResponse(403,"bad token sekret here")])
e = EODHDCollector(api_key="sekret", transport=t, sleep=sleeps.append)
try: e.get_eod("AAPL.US")
except CollectorError as x: print("err:", x)
t = Scripted([TransportResponse(500,"")]*5)
e = EODHDCollector(api_key="sekret", transport=t, sleep=lambda s: None)
try: e.get_eod("AAPL.US")
except CollectorError as x: print("err:", x)

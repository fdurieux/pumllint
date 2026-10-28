import json, os, datetime as dt, hashlib, sys
sys.path.insert(0, os.environ["OUT"])
from jef_data_rc.collectors.base import request_identity, request_key
def fx(d, method, url, params, status, body):
    ident = request_identity(method, url, params)
    os.makedirs(d, exist_ok=True)
    name = hashlib.sha256(request_key(method,url,params).encode()).hexdigest()[:10]
    json.dump({"request": ident, "response": {"status": status, "json": body}}, open(f"{d}/{name}.json","w"))
days=[]
d=dt.date(2020,8,24)
while d<=dt.date(2020,9,4):
    if d.weekday()<5: days.append(d)
    d+=dt.timedelta(1)
rows=[]
for i,d in enumerate(days):
    pre = d < dt.date(2020,8,31)
    px = 500.0+i if pre else 125.0+i/4
    vol = 1000.0*4 if pre else 1000.0
    rows.append({"date":d.isoformat(),"open":px,"high":px+1,"low":px-1,"close":px,"adjusted_close":px/4 if pre else px,"volume":vol})
B="https://eodhd.com/api"
fx("fx1","GET",B+"/eod/AAPL.US",{"api_token":"k","fmt":"json","order":"a","period":"d"},200,rows)
fx("fx1","GET",B+"/splits/AAPL.US",{"api_token":"k","fmt":"json"},200,[{"date":"2020-08-31","split":"4.000000/1.000000"}])
fx("fx1","GET",B+"/div/AAPL.US",{"api_token":"k","fmt":"json"},200,[{"date":"2020-08-07","value":0.82,"unadjustedValue":0.82,"currency":"USD"}])
rows2=[r.copy() for r in rows if r["date"]>="2020-09-02"]
rows2[1]["close"]+=0.5
rows2.append({"date":"2020-09-08","open":130,"high":131,"low":129,"close":130,"adjusted_close":130,"volume":900})
fx("fx2","GET",B+"/eod/AAPL.US",{"api_token":"k","fmt":"json","order":"a","period":"d","from":"2020-09-02"},200,rows2)
fx("fx2","GET",B+"/splits/AAPL.US",{"api_token":"k","fmt":"json"},200,[{"date":"2020-08-31","split":"4.000000/1.000000"}])
fx("fx2","GET",B+"/div/AAPL.US",{"api_token":"k","fmt":"json"},200,[])

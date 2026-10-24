"""Provider clients with shared retry, quota, recording and replay transports."""
import os,json,time,hashlib
from pathlib import Path
from collections import deque
from datetime import datetime,timezone
from urllib.parse import urlparse
import requests

class CollectorError(RuntimeError):pass
class DailyBudgetExhausted(CollectorError):pass
class TransportConnectionError(RuntimeError):pass

def identity(method,url,params):
 return dict(method=method.upper(),path=urlparse(url).path,params={k:str(v) for k,v in sorted(params.items()) if k!='api_token'})
class HttpTransport:
 def __init__(self,secret=''):self.session=requests.Session();self.secret=secret
 def request(self,method,url,params):
  try:
   r=self.session.request(method,url,params=params,timeout=30);return r.status_code,r.text
  except (requests.ConnectionError,requests.Timeout) as e:
   raise TransportConnectionError(str(e).replace(self.secret,'***') if self.secret else str(e)) from e
 def close(self):self.session.close()
class ReplayTransport:
 def __init__(self,fixture_dir):
  self.fixtures={};self.calls=[]
  for root,dirs,files in os.walk(fixture_dir):
   for name in sorted(files):
    if name.endswith('.json') and name!='manifest.json':
     d=json.loads((Path(root)/name).read_text());self.fixtures[json.dumps(d['request'],sort_keys=True)]=d
 def request(self,method,url,params):
  k=identity(method,url,params);self.calls.append(k);s=json.dumps(k,sort_keys=True)
  if s not in self.fixtures:
   known=sorted(f"  {d['request']['path']} {d['request']['params']}" for d in self.fixtures.values())
   raise CollectorError(f"no recorded fixture for {k['method']} {k['path']} {k['params']}\nknown fixtures:\n"+'\n'.join(known))
  r=self.fixtures[s]['response'];return r['status'],json.dumps(r['json'])
 def close(self):pass
class RecordingTransport:
 def __init__(self,inner,fixture_dir,secrets=()):self.inner=inner;self.root=Path(fixture_dir);self.secrets=secrets;self.written=[]
 def request(self,method,url,params):
  status,text=self.inner.request(method,url,params);key=identity(method,url,params)
  slug=key['path'].strip('/').replace('/','_');digest=hashlib.sha256(json.dumps(key,sort_keys=True).encode()).hexdigest()[:10]
  path=self.root/f'{slug}_{digest}.json'
  serialized=json.dumps(dict(request=key,response=dict(status=status,json=json.loads(text))),indent=1,sort_keys=True)+'\n'
  if any(s and s in serialized for s in self.secrets):raise CollectorError(f'refusing to write fixture: secret material in {path} response/request')
  self.root.mkdir(parents=True,exist_ok=True);path.write_text(serialized);self.written.append(path)
  return status,text
 def close(self):self.inner.close()
class RateLimiter:
 def __init__(self,clock=time.monotonic,sleep=time.sleep,today=lambda:datetime.now(timezone.utc).date()):
  self.clock=clock;self.sleep=sleep;self.today=today;self.window=deque();self.day=None;self.spent=0
 def acquire(self):
  day=self.today()
  if day!=self.day:self.day=day;self.spent=0
  if self.spent>=100000:raise DailyBudgetExhausted(f'daily API budget of 100000 spent ({day}); the per-minute window cannot lend quota across days')
  now=self.clock()
  while self.window and now-self.window[0]>=60:self.window.popleft()
  if len(self.window)>=1000:
   self.sleep(60-(now-self.window[0]));now=self.clock()
   while self.window and now-self.window[0]>=60:self.window.popleft()
  self.window.append(now);self.spent+=1
class BaseCollector:
 def __init__(self,transport=None,secret='',replay=False):self.transport=transport or HttpTransport(secret);self.secret=secret;self.limiter=None if replay else RateLimiter();self.sleep=(lambda _:None) if replay else time.sleep
 def close(self):self.transport.close()
 def redact(self,text):return text.replace(self.secret,'***') if self.secret else text
 def get_json(self,url,params,label):
  for i in range(5):
   if self.limiter:self.limiter.acquire()
   try:status,text=self.transport.request('GET',url,params)
   except TransportConnectionError as e:
    if i==4:raise CollectorError(f'{label}: network failure after 5 attempts: {self.redact(str(e))}') from e
    self.sleep(2.*2**i);continue
   if status==429 or status>=500:
    if i==4:raise CollectorError(f'{label}: HTTP {status} after 5 attempts')
    self.sleep(2.*2**i);continue
   if status!=200:raise CollectorError(f'{label}: HTTP {status}: {self.redact(text)[:200]}')
   try:return json.loads(text)
   except ValueError:raise CollectorError(f'{label}: response is not JSON: {self.redact(text)[:200]}')

def normalize(symbol):
 if '.' in symbol:return symbol
 s=symbol.strip().upper()
 if '/' in s:
  a,b=s.split('/',1);fiat=set('USD EUR GBP JPY CHF AUD NZD CAD SEK NOK DKK PLN CZK HUF TRY ZAR MXN SGD HKD CNY INR BRL KRW RUB'.split())
  if a in fiat and b in fiat:return a+b+'.FOREX'
  if b in 'USD USDT EUR BTC ETH BUSD USDC'.split():return a+'-'+b+'.CC'
  raise CollectorError(f'cannot infer exchange for pair symbol {symbol!r}')
 return s+'.US'
class EODHDCollector(BaseCollector):
 volume_basis='split_adjusted'
 def __init__(self,api_key=None,base_url=None,**kwargs):
  key=api_key or os.environ.get('EODHD_API_KEY')
  if not key:raise ValueError('EODHD API key required: pass api_key= or set EODHD_API_KEY')
  super().__init__(secret=key,**kwargs);self.key=key;self.base=(base_url or 'https://eodhd.com/api').rstrip('/')
 def call(self,kind,symbol,extra=None):
  symbol=normalize(symbol);params=dict(api_token=self.key,fmt='json');params.update(extra or {})
  return self.get_json(self.base+'/'+kind+'/'+symbol,params,kind+' '+symbol)
 def get_eod(self,symbol,start=None,end=None):
  params=dict(period='d',order='a')
  if start:params['from']=str(start)
  if end:params['to']=str(end)
  rows=self.call('eod',symbol,params)
  if not isinstance(rows,list):raise CollectorError(f'eod {normalize(symbol)}: expected a JSON list')
  out={}
  for r in rows:
   if r.get('close') is not None and float(r['close'])>0:out.setdefault(r['date'],r)
  return [out[k] for k in sorted(out)]
 def get_splits(self,symbol):
  out=[]
  for row in self.call('splits',symbol):
   s=row['split']
   try:a,b=map(float,s.split('/'))
   except (ValueError,TypeError):raise ValueError(f'unparseable split string: {s!r}')
   if a==0 or b==0:raise ValueError(f'degenerate split string: {s!r}')
   out.append(dict(date=row['date'],split=s,ratio=a/b))
  return sorted(out,key=lambda e:e['date'])
 def get_dividends(self,symbol):return sorted(self.call('div',symbol),key=lambda e:e.get('date',''))
class BinanceCollector(BaseCollector):
 volume_basis='raw';limit=1000
 def get_eod(self,symbol,start=None,end=None):
  def ms(s):return int(datetime.fromisoformat(str(s)).replace(tzinfo=timezone.utc).timestamp()*1000)
  cursor=ms(start) if start else None;endms=ms(end)+86400000-1 if end else None;out={}
  for page in range(100):
   params=dict(symbol=symbol,interval='1d',limit=self.limit)
   if cursor is not None:params['startTime']=cursor
   if endms is not None:params['endTime']=endms
   rows=self.get_json('https://api.binance.com/api/v3/klines',params,'klines '+symbol)
   if not isinstance(rows,list):raise CollectorError(f'klines {symbol}: expected a JSON list')
   if not rows:break
   for r in rows:
    c=float(r[4]);d=datetime.fromtimestamp(int(r[0])/1000,timezone.utc).date().isoformat()
    if c>0:out.setdefault(d,dict(date=d,open=float(r[1]),high=float(r[2]),low=float(r[3]),close=c,adjusted_close=c,volume=float(r[5])))
   last=int(rows[-1][0]);cursor=last+86400000
   if len(rows)<self.limit or (endms is not None and cursor>endms):break
  else:raise CollectorError('pagination exceeded 100 pages - refusing to truncate silently; raise max_pages if the range is real')
  return [out[k] for k in sorted(out)]
def make_collector(provider,fixture_dir,api_key='test-key-not-real'):
 kwargs=dict(transport=ReplayTransport(fixture_dir),replay=True)
 return EODHDCollector(api_key=api_key,**kwargs) if provider=='eodhd' else BinanceCollector(**kwargs)

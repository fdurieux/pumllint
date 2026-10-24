"""Strict acquisition universe parsing and ordered leg selection."""
from pathlib import Path
from datetime import date
import tomllib

ASSET_TYPE_BY_CLASS={'stock':'stock','crypto':'crypto','bond_etf':'etf'}
PROVIDERS=['eodhd','binance','yahoo-csv']
class UniverseError(ValueError): pass
class SyncError(RuntimeError): pass

def keys(obj,allowed,where):
 extra=sorted(set(obj)-set(allowed))
 if extra: raise UniverseError(f'{where}: unknown key(s) {extra}; allowed: {sorted(allowed)}')
def string(obj,k,where,default=None,required=False):
 if k not in obj and required:raise UniverseError(f"{where}: missing required key '{k}'")
 v=obj.get(k,default)
 if not isinstance(v,str) or not v.strip():raise UniverseError(f'{where}: {k} must be a non-empty string, got {v!r}')
 return v

def boolean(obj,k,where,default):
 v=obj.get(k,default)
 if not isinstance(v,bool):raise UniverseError(f'{where}: {k} must be a boolean, got {v!r}')
 return v

def day(obj,k,where):
 if k not in obj:return None
 v=obj[k]
 try:
  if isinstance(v,date):return v.isoformat()
  if isinstance(v,str):return date.fromisoformat(v).isoformat()
 except ValueError:pass
 raise UniverseError(f'{where}: {k} must be an ISO date (YYYY-MM-DD), got {v!r}')

def load_universe(path=None):
 origin=str(path) if path is not None else 'packaged universe.toml'
 text=(Path(path) if path is not None else Path(__file__).with_name('universe.toml')).read_text()
 try:d=tomllib.loads(text)
 except tomllib.TOMLDecodeError as e:raise UniverseError(f'{origin}: not valid TOML: {e}') from e
 keys(d,['defaults','asset'],origin)
 defaults=d.get('defaults',{})
 if not isinstance(defaults,dict):raise UniverseError(f'{origin}: [defaults] must be a table')
 keys(defaults,['store','currency'],origin+' [defaults]')
 defaults={k:string(defaults,k,'[defaults]',v) for k,v in [('store','data'),('currency','USD')]}
 aa=d.get('asset')
 if not isinstance(aa,list) or not aa:raise UniverseError(f'{origin}: no [[asset]] entries')
 assets=[]
 for n,a in enumerate(aa,1):
  w=f'asset #{n}'
  if not isinstance(a,dict):raise UniverseError(f'{w}: must be a table')
  keys(a,['name','asset_class','currency','threshold','enabled','source'],w)
  name=string(a,'name',w,required=True);w=f'asset {name!r}'
  ac=string(a,'asset_class',w,required=True)
  if ac not in ASSET_TYPE_BY_CLASS:raise UniverseError(f'{w}: unknown asset_class {ac!r}; allowed: {sorted(ASSET_TYPE_BY_CLASS)}')
  th=a.get('threshold',-.05)
  if isinstance(th,bool) or not isinstance(th,(int,float)):raise UniverseError(f'{w}: threshold must be a number (documentation only), got {th!r}')
  currency=string(a,'currency',w,defaults['currency'])
  ss=a.get('source')
  if not isinstance(ss,list) or not ss:raise UniverseError(f'{w}: needs at least one [[asset.source]]')
  enabled=boolean(a,'enabled',w,True);sources=[]
  for j,s in enumerate(ss,1):
   sw=f'{w} source #{j}'
   if not isinstance(s,dict):raise UniverseError(f'{sw}: must be a table')
   keys(s,['provider','symbol','path','exchange','start','end','kind','enabled','modeled','note'],sw)
   provider=string(s,'provider',sw,required=True)
   if provider not in PROVIDERS:raise UniverseError(f'{sw}: unknown provider {provider!r}; allowed: {PROVIDERS}')
   kind=s.get('kind','eod')
   if kind!='eod':raise UniverseError(f"{sw}: kind {kind!r} is not supported - only ['eod']; a non-EOD load is a new data contract, not a config value")
   symbol=string(s,'symbol',sw,required=True)
   if provider=='eodhd' and '.' not in symbol:raise UniverseError(f'{sw}: eodhd symbols must be canonical TICKER.EXCHANGE (e.g. AAPL.US, BTC-USD.CC), got {symbol!r} - bare tickers would blur store coordinates and the crypto/raw basis split')
   modeled=boolean(s,'modeled',sw,False);on=boolean(s,'enabled',sw,True)
   exchange=string(s,'exchange',sw,'yahoo' if provider=='yahoo-csv' else provider)
   note=string(s,'note',sw) if 'note' in s else None
   pathv=string(s,'path',sw,required=True) if provider=='yahoo-csv' else string(s,'path',sw) if 'path' in s else None
   start=day(s,'start',sw);end=day(s,'end',sw)
   if provider=='yahoo-csv' and ('start'in s or 'end'in s):raise UniverseError(f'{sw}: start/end apply to collector sources only; a CSV import is whole-file')
   if provider!='yahoo-csv' and 'path'in s:raise UniverseError(f'{sw}: path applies to yahoo-csv sources only')
   if start and end and start>end:raise UniverseError(f'{sw}: start {start} is after end {end}')
   source=dict(provider=provider,kind=kind,enabled=on,modeled=modeled,exchange=exchange,symbol=symbol,currency=currency)
   if note is not None:source['note']=note
   source.update({'path':pathv} if provider=='yahoo-csv' else {'start':start,'end':end});sources.append(source)
  if any(s['modeled'] and not s['enabled'] for s in sources):raise UniverseError(f'{w}: a modeled source must be enabled')
  m=sum(s['modeled'] and s['enabled'] for s in sources);live=sum(s['enabled'] for s in sources)
  if m>1:raise UniverseError(f'{w}: exactly one enabled source may be modeled = true, got {m}')
  if enabled and live>=2 and not m:raise UniverseError(f"{w}: {live} enabled sources but none marked modeled = true - the binning's feeder must be deterministic (docs/DATA_CONTRACT.md SS7.7)")
  if enabled and not live:raise UniverseError(f'{w}: enabled but has no enabled source - nothing would feed the binning; to pause the asset, set enabled = false on the asset itself')
  assets.append(dict(name=name,asset_class=ac,asset_type=ASSET_TYPE_BY_CLASS[ac],currency=currency,threshold=float(th),enabled=enabled,sources=sources))
 names=[a['name'] for a in assets];dupes=sorted({n for n in names if names.count(n)>1})
 if dupes:raise UniverseError(f'{origin}: duplicate asset name(s) {dupes}')
 coords={}
 for a in assets:
  for s in a['sources']:
   c=(s['exchange'],s['symbol']);owner=coords.get(c)
   if owner and owner!=a['name']:raise UniverseError(f"{origin}: store series {c[0]}/{c[1]} is claimed by both {owner!r} and {a['name']!r} - two assets may never write the same partition")
   coords[c]=a['name']
 return {'defaults':defaults,'assets':assets}

def select_legs(universe,assets=None,providers=None):
 names=sorted(a['name'] for a in universe['assets'])
 for x in assets or []:
  if x not in names:raise SyncError(f'unknown asset {x!r}; universe has {names}')
 for x in providers or []:
  if x not in PROVIDERS:raise SyncError(f'unknown provider {x!r}; allowed: {PROVIDERS}')
 legs=[]
 for a in universe['assets']:
  if not a['enabled'] or (assets and a['name'] not in assets):continue
  for s in a['sources']:
   if not s['enabled'] or (providers and s['provider'] not in providers):continue
   legs.append(dict(asset=a['name'],provider=s['provider'],exchange=s['exchange'],symbol=s['symbol'],path=s.get('path'),asset_type=a['asset_type'],currency=a['currency'],start=s.get('start'),end=s.get('end'),actions=s['provider']=='eodhd' and a['asset_type']!='crypto'))
 if not legs:raise SyncError('selection matched no enabled asset/source legs')
 return legs

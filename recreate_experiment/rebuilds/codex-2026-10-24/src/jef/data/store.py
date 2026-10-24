"""Locked Parquet series writes and pure split arithmetic."""
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone
import json,fcntl,os,time
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

class StoreError(RuntimeError):pass
class AdjustmentRefused(ValueError):pass
COLUMNS=['timestamp','datetime','open','high','low','close','volume','symbol','exchange','asset_type','asset_subtype','adjustment_factor','open_raw','high_raw','low_raw','close_raw','volume_raw','adjusted_close','cumulative_split_factor','currency','price_basis']
TEXT=['symbol','exchange','asset_type','asset_subtype','currency','price_basis']
RAW=['open_raw','high_raw','low_raw','close_raw','volume_raw','adjusted_close']
SEAM=['Date','Open','High','Low','Close','Adj Close','Volume']
SCHEMA=pa.schema([(k,pa.int64() if k=='timestamp' else pa.timestamp('ms',tz='UTC') if k=='datetime' else pa.string() if k in TEXT else pa.float64()) for k in COLUMNS])

def series_path(root,exchange,symbol):return Path(root)/'market_data'/f'exchange={exchange}'/f'symbol={symbol}'
def stored_frame(root,exchange,symbol):
 files=sorted(series_path(root,exchange,symbol).glob('year=*/data.parquet'))
 if not files:return pd.DataFrame(columns=COLUMNS)
 f=pd.concat([pq.ParquetFile(p).read().to_pandas() for p in files],ignore_index=True)
 return f.sort_values('timestamp',kind='stable').drop_duplicates('timestamp').reset_index(drop=True)[COLUMNS]
def latest(root,exchange,symbol):
 files=sorted(series_path(root,exchange,symbol).glob('year=*/data.parquet'))
 return pq.ParquetFile(files[-1]).read().to_pandas()['datetime'].max().date().isoformat() if files else None

def factors(dates,splits):
 out=np.ones(len(dates),dtype='float64')
 for s in splits:
  r=float(s['ratio'])
  if not np.isfinite(r) or r<=0:raise AdjustmentRefused(f"split {s['date']} has degenerate ratio {r!r}")
  out[np.array([d<str(s['date']) for d in dates])]*=r
 return out

def adjust_frame(frame,splits):
 bad=sorted(set(frame['price_basis'])-{'raw'}) if 'price_basis' in frame else []
 if bad:raise AdjustmentRefused(f'price_basis {bad} is already adjusted at the provider - applying split events would double-adjust (docs/DATA_CONTRACT.md §2)')
 missing=[k for k in ['open_raw','high_raw','low_raw','close_raw','volume_raw','datetime'] if k not in frame]
 if missing:raise AdjustmentRefused(f'cannot adjust without immutable raw columns: missing {missing}')
 f=frame.copy();factor=factors(f.datetime.dt.strftime('%Y-%m-%d'),splits)
 for k in ['open','high','low','close']:f[k]=f[k+'_raw'].to_numpy(dtype='float64')/factor
 f['volume']=f.volume_raw.to_numpy(dtype='float64')*factor;f['cumulative_split_factor']=factor
 return f

def bars_frame(bars,exchange,symbol,asset_type,currency,basis,splits=(),volume_basis='raw'):
 if not bars:return pd.DataFrame(columns=COLUMNS)
 b=pd.DataFrame(bars);dt=pd.to_datetime(b.date,utc=True,errors='coerce')
 if dt.isna().any():raise StoreError(f'unparseable dates cannot be stored: {b.loc[dt.isna(),"date"].tolist()[:5]}')
 f=pd.DataFrame(index=b.index);f['timestamp']=dt.astype('datetime64[us, UTC]').astype('int64')//1000000;f['datetime']=dt.astype('datetime64[ms, UTC]')
 for k in ['open','high','low','close','volume']:f[k+'_raw']=b[k].astype('float64')
 f['adjusted_close']=(b['adjusted_close'] if 'adjusted_close'in b else b.close).astype('float64')
 f['adjustment_factor']=f.adjusted_close/f.close_raw
 for k,v in dict(symbol=symbol,exchange=exchange,asset_type=asset_type,asset_subtype='',currency=currency,price_basis=basis).items():f[k]=v
 if basis=='raw':
  if volume_basis not in ['raw','split_adjusted']:raise StoreError(f'unknown volume_basis {volume_basis!r}')
  if volume_basis=='split_adjusted':f['volume_raw']=f.volume_raw.to_numpy()/factors(dt.dt.strftime('%Y-%m-%d'),splits)
  f=adjust_frame(f,splits)
 else:
  for k in ['open','high','low','close','volume']:f[k]=f[k+'_raw']
  f['cumulative_split_factor']=1.
 return f[COLUMNS]

@contextmanager
def locked(root,exchange,symbol):
 path=series_path(root,exchange,symbol);path.mkdir(parents=True,exist_ok=True);lock=path/'.lock'
 fd=os.open(lock,os.O_CREAT|os.O_RDWR,0o644);t=time.monotonic()
 try:
  while True:
   try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);break
   except BlockingIOError:
    if time.monotonic()-t>=300:raise StoreError(f'{exchange}/{symbol}: another writer holds the store lock after 300s ({lock})')
    time.sleep(.5)
  for p in path.glob('year=*/data.parquet.tmp'):p.unlink()
  yield path
 finally:os.close(fd)

def write(path,frame,years=None,prune=False):
 frame=frame.sort_values('timestamp',kind='stable').drop_duplicates('timestamp').reset_index(drop=True)
 present=set()
 for year,g in frame.groupby(frame.datetime.dt.year):
  present.add(int(year))
  if years is not None and int(year) not in years:continue
  p=path/f'year={year}'/'data.parquet';p.parent.mkdir(parents=True,exist_ok=True)
  pq.write_table(pa.Table.from_pandas(g[COLUMNS],schema=SCHEMA,preserve_index=False),str(p)+'.tmp',compression='snappy');os.replace(str(p)+'.tmp',p)
 if prune:
  for p in path.glob('year=*/data.parquet'):
   if int(p.parent.name[5:]) not in present:p.unlink()

def put_bars(root,exchange,symbol,bars,asset_type,currency,basis,splits=(),volume_basis='raw',mode='reconcile'):
 incoming=bars_frame(bars,exchange,symbol,asset_type,currency,basis,splits,volume_basis);revisions=[]
 if not bars and mode!='overwrite':return 0,revisions
 with locked(root,exchange,symbol) as path:
  old=stored_frame(root,exchange,symbol)
  if mode=='overwrite':write(path,incoming,prune=True);return len(bars),revisions
  if old.empty:write(path,incoming);return len(bars),revisions
  if mode=='append':
   f=pd.concat([old,incoming],ignore_index=True).drop_duplicates('timestamp');write(path,f,set(incoming.datetime.dt.year));return len(bars),revisions
  f=old.set_index('timestamp',drop=False);years=set()
  for _,row in incoming.iterrows():
   ts=row.timestamp;replace=ts not in f.index
   if not replace:
    prev=f.loc[ts]
    for k in RAW:
     a,b=prev[k],row[k]
     if not ((pd.isna(a) and pd.isna(b)) or a==b):
      revisions.append(dict(date=row.datetime.date().isoformat(),column=k,stored=float(a),served=float(b)));replace=True
   if replace:f.loc[ts]=row;years.add(row.datetime.year)
  if years:write(path,f.reset_index(drop=True),years)
 return len(bars),revisions

def reapply(root,exchange,symbol,splits):
 with locked(root,exchange,symbol) as path:
  old=stored_frame(root,exchange,symbol)
  if old.empty:raise StoreError(f'nothing stored for {exchange}/{symbol}')
  new=adjust_frame(old,splits)
  if not old.equals(new):write(path,new,prune=True)
 return len(old)

def import_csv(root,csv_path,exchange,symbol,asset_type,currency='USD'):
 f=pd.read_csv(csv_path);missing=[k for k in SEAM if k not in f]
 if missing:raise StoreError(f'{csv_path}: not a 7-column Yahoo CSV, missing {missing}')
 bars=f[SEAM].rename(columns=dict(zip(SEAM,['date','open','high','low','close','adjusted_close','volume']))).to_dict('records')
 put_bars(root,exchange,symbol,bars,asset_type,currency,'split_adjusted',mode='overwrite');return len(f)
def export_frame(root,exchange,symbol):
 f=stored_frame(root,exchange,symbol)
 result=pd.DataFrame({'Date':f.datetime.dt.strftime('%Y-%m-%d')})
 for k,col in zip(['open','high','low','close','adjusted_close','volume'],SEAM[1:]):result[col]=f[k].astype('float64')
 v=result.Volume.to_numpy()
 if len(v) and np.isfinite(v).all() and (np.floor(v)==v).all():result['Volume']=result.Volume.astype('int64')
 return result

def action_path(root,symbol,kind):return Path(root)/'corporate_actions'/kind/(symbol.replace('/','_')+'.json')
def actions_state(root,symbol):
 result={}
 for kind in ['splits','dividends']:
  p=action_path(root,symbol,kind);d=json.loads(p.read_text()) if p.exists() else {};result[kind]=d.get(kind,[])
  if kind=='splits':stamp=d.get('last_updated')
 return dict(splits=result['splits'],dividends=result['dividends'],last_updated=stamp)
def sync_actions(root,symbol,collector):
 splits=collector.get_splits(symbol);divs=collector.get_dividends(symbol)
 for kind,events in [('splits',splits),('dividends',divs)]:
  if kind=='splits':
   events=[dict(date=str(e['date']),split=e.get('split',f"{e['ratio']:g}/1"),ratio=float(e['ratio'])) for e in events]
  p=action_path(root,symbol,kind);p.parent.mkdir(parents=True,exist_ok=True)
  stamp=datetime.now(timezone.utc).replace(tzinfo=None).isoformat()+'Z'
  p.write_text(json.dumps(dict(symbol=symbol,exchange='eodhd',last_updated=stamp,**{kind:events}),indent=2)+'\n')
 return len(splits),len(divs)

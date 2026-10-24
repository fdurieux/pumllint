"""Additional checks derived from arithmetic and operational invariants."""
from pathlib import Path
from types import SimpleNamespace
import json
import numpy as np
import pandas as pd
import pytest
from hypothesis import given, strategies as st, settings
from jef.data import store
from jef.data.collectors import BaseCollector,RateLimiter,DailyBudgetExhausted,TransportConnectionError,CollectorError,RecordingTransport,identity,EODHDCollector
from jef.data import cli
from jef.data.health import sessions

@given(st.floats(min_value=.01,max_value=1e6,allow_nan=False,allow_infinity=False),st.floats(min_value=.1,max_value=20,allow_nan=False,allow_infinity=False))
@settings(max_examples=80)
def test_adjustment_fixed_point_and_no_main_dependency(price,ratio):
 f=pd.DataFrame({'datetime':pd.to_datetime(['2024-01-01'],utc=True),'price_basis':['raw'],**{k+'_raw':[price] for k in ['open','high','low','close','volume']}})
 splits=[dict(date='2024-01-02',ratio=ratio)]
 a=store.adjust_frame(f,splits);b=a.copy()
 for k in ['open','high','low','close','volume']:b[k]=-999.
 pd.testing.assert_frame_equal(a,store.adjust_frame(b,splits),check_exact=True)
 assert a.close.iloc[0]==np.float64(price)/np.float64(ratio)
 assert a.volume.iloc[0]==np.float64(price)*np.float64(ratio)

def test_split_effective_date_and_factor_order():
 d=['2024-01-01','2024-01-02','2024-01-03']
 assert store.factors(d,[dict(date='2024-01-02',ratio=1.5),dict(date='2024-01-03',ratio=7)]).tolist()==[10.5,7.,1.]

class Transport:
 def __init__(self,outcomes):self.outcomes=iter(outcomes);self.calls=[]
 def request(self,*args):
  self.calls.append(args);x=next(self.outcomes)
  if isinstance(x,Exception):raise x
  return x
 def close(self):pass

def test_retry_schedule_and_quota_per_attempt():
 t=Transport([TransportConnectionError('key'),(429,'busy'),(500,'busy'),(503,'busy'),(200,'[]')]);c=BaseCollector(transport=t,secret='key',replay=True);sleeps=[];c.sleep=sleeps.append;acquires=[];c.limiter=SimpleNamespace(acquire=lambda:acquires.append(1))
 assert c.get_json('http://unused',{},'x')==[]
 assert sleeps==[2.,4.,8.,16.] and len(acquires)==5

def test_retry_failure_redacts_token():
 c=BaseCollector(transport=Transport([TransportConnectionError('secret')]*5),secret='secret',replay=True)
 with pytest.raises(CollectorError,match=r'network failure after 5 attempts: \*\*\*'):c.get_json('http://unused',{},'x')

def test_daily_budget_and_rolling_window():
 from datetime import date
 now=[0.];day=[date(2024,1,1)];slept=[]
 def sleep(n):slept.append(n);now[0]+=n
 r=RateLimiter(clock=lambda:now[0],sleep=sleep,today=lambda:day[0])
 for _ in range(1001):r.acquire()
 assert slept==[60.] and len(r.window)==1
 r.spent=100000
 with pytest.raises(DailyBudgetExhausted):r.acquire()
 day[0]=date(2024,1,2);r.acquire();assert r.spent==1

def test_recorder_identity_and_secret_refusal(tmp_path):
 t=RecordingTransport(Transport([(200,'[]')]),tmp_path,secrets=['real-key']);t.request('get','https://host/api/eod/X',{'api_token':'real-key','n':2})
 d=json.loads(t.written[0].read_text());assert d['request']==identity('GET','https://different/api/eod/X',{'n':2})
 t=RecordingTransport(Transport([(200,'"real-key"')]),tmp_path,secrets=['real-key'])
 with pytest.raises(CollectorError,match='secret material'):t.request('GET','https://host/api/x',{})

def test_noop_write_preserves_file_and_crash_temp_cleanup(tmp_path):
 bars=[dict(date='2024-01-01',open=10.,high=11.,low=9.,close=10.,volume=100.)]
 args=(tmp_path,'eodhd','X.US',bars,'stock','USD','raw')
 store.put_bars(*args);p=store.series_path(tmp_path,'eodhd','X.US')/'year=2024/data.parquet';before=p.stat().st_mtime_ns
 assert store.put_bars(*args)==(1,[]);assert p.stat().st_mtime_ns==before
 assert store.reapply(tmp_path,'eodhd','X.US',[])==1;assert p.stat().st_mtime_ns==before
 crash=p.with_name('data.parquet.tmp');crash.write_text('crash');store.put_bars(*args);assert not crash.exists()

def test_load_happy_path_through_replay_transport(tmp_path):
 from datetime import datetime,timezone
 class Fetch:
  volume_basis='split_adjusted'
  def __init__(self):self.requests=[]
  def get_eod(self,symbol,start,end):
   self.requests.append((symbol,start,end));return [dict(date='2024-01-02',open=10.,high=11.,low=9.,close=10.,volume=100.)]
 args=SimpleNamespace(symbol='X',asset_type='stock',store=str(tmp_path),currency='EUR',to=None,**{'from':None});f=Fetch()
 assert cli.load(args,f)==1;assert cli.load(args,f)==1
 assert f.requests==[('X.US',None,None),('X.US','2024-01-03',None)]
 assert len(store.stored_frame(tmp_path,'eodhd','X.US'))==1

def test_lock_contention_times_out_without_corruption(tmp_path,monkeypatch):
 import fcntl
 p=store.series_path(tmp_path,'x','s');p.mkdir(parents=True)
 with (p/'.lock').open('w') as held:
  fcntl.flock(held,fcntl.LOCK_EX|fcntl.LOCK_NB)
  moments=iter([0.,301.]);monkeypatch.setattr(store.time,'monotonic',lambda:next(moments))
  with pytest.raises(store.StoreError,match='another writer holds'): 
   with store.locked(tmp_path,'x','s'):pass
 assert not list(p.glob('year=*/data.parquet'))

def test_invalid_date_writes_nothing(tmp_path):
 bars=[dict(date='not-a-date',open=1.,high=1.,low=1.,close=1.,volume=1.)]
 with pytest.raises(store.StoreError):store.put_bars(tmp_path,'x','s',bars,'stock','USD','raw')
 assert not list(tmp_path.rglob('*'))

def test_session_calendar_strict_endpoints():
 assert sessions('2024-03-01','2024-03-04','stock')==0
 assert sessions('2024-03-01','2024-03-04','crypto')==2

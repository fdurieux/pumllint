"""Read-only source and venue-pair health checks."""
from pathlib import Path
from datetime import datetime,date,timedelta,timezone
from itertools import combinations
import tomllib
import numpy as np
from .universe import select_legs
from . import store

def sessions(a,b,asset_type):
 a=date.fromisoformat(str(a));b=date.fromisoformat(str(b));d=a+timedelta(days=1);n=0
 while d<b:
  n+=asset_type not in ['stock','etf'] or d.weekday()<5;d+=timedelta(days=1)
 return n

def classification(leg,evidence):
 e=evidence.get((leg['exchange'],leg['symbol']));at=leg['asset_type']
 if not e:return 'no_evidence','no vendor classification recorded - run tools/record_classifications.py'
 vt=e['vendor_type'];seen=f", recorded {e['last_verified']}" if e.get('last_verified') else '';mapping={'Common Stock':'stock','ETF':'etf'}
 if vt=='Currency':return 'not_comparable',f"vendor type {vt!r} cannot confirm asset_type {at!r}{seen}: the .CC (crypto) and .FOREX namespaces both serve it, so only the symbol's own namespace separates them and the evidence is not independent"
 if vt not in mapping:return 'unmapped',f"vendor type {vt!r} has no store asset_type counterpart{seen} - no verdict rather than a guess (mapped: ['Common Stock', 'ETF'])"
 if mapping[vt]==at:return 'agree',f'vendor type {vt!r} agrees with declared asset_type {at!r}{seen}'
 return 'disagree',f"declared asset_type {at!r} but the vendor says {vt!r} (-> {mapping[vt]!r}){seen} for {leg['exchange']}/{leg['symbol']} - check the asset_class in universe.toml against docs/EVALUATION_ASSET_CLASSIFICATION.md §5 C2"

def resolution(f,window):
 traded=f[f.volume>0]
 vals=traded.close_raw;vals=vals[vals.notna() & (vals>0)].tail(window)
 if not len(vals):
  vals=traded.close;vals=vals[vals.notna() & (vals>0)].tail(window)
 if len(vals)<60:return None
 v=vals.to_numpy();unique=np.unique(v)
 return dict(sessions=len(v),distinct=len(unique),min_tick=float(np.min(np.diff(unique)/unique[:-1])) if len(unique)>1 else None,flat_share=float(np.mean(v[1:]==v[:-1])))

def status_json(universe,store_path=None,*,assets=None,providers=None,now=None,window=10,jump_threshold=.40,staleness_k=2,resolution_window=500,resolution_k=.20,flat_k=.25,gap_k=5,spread_threshold=.005,spread_alerts=False):
 legs=[l for l in select_legs(universe,assets,providers) if l['provider']!='yahoo-csv'];root=str(store_path or universe['defaults']['store']);today=(now or datetime.now(timezone.utc)).astimezone(timezone.utc).date().isoformat()
 evidence=tomllib.loads(Path(__file__).with_name('classifications.toml').read_text());evidence={(e['exchange'],e['symbol']):e for e in evidence.get('instrument',[])}
 reports=[];frames=[]
 for l in legs:
  r={k:l[k] for k in ['asset','exchange','symbol']};r.update(alerts=[],warnings=[],notes=[])
  if l['provider']=='eodhd':
   verdict,msg=classification(l,evidence);r['declared_class_check']=verdict;r['warnings' if verdict=='disagree' else 'notes'].append('declared class: '+msg)
  f=store.stored_frame(root,l['exchange'],l['symbol']);frames.append(f);reports.append(r)
  if not len(f):r['alerts'].append('never filled - no stored rows (jef-data sync first)');continue
  days=f.datetime.dt.strftime('%Y-%m-%d').tolist();last=store.latest(root,l['exchange'],l['symbol']);missed=sessions(last,today,l['asset_type'])
  r.update(last_session=last,missed_sessions=missed,rows=len(f))
  if missed>=staleness_k:r['alerts'].append(f'stale: {missed} expected session(s) missing since {last} (multi-day holidays can trip this - verify before acting)')
  if last==today:r['notes'].append('today-dated bar stored (pre-close serve? the next tail-refresh heals it)')
  zeros=(f.volume==0).tolist();total=sum(zeros)
  if total:
   note=f'{total} zero-volume row(s), dropped at the seam by pinned policy';best=0;run=0;best_end=0
   for i,z in enumerate(zeros):
    run=run+1 if z else 0
    if run>best:best=run;best_end=i
   if best>1:note+=f' - largest contiguous run {best}, {days[best_end-best+1]}..{days[best_end]}'
   r['notes'].append(note)
  surviving=f[(f.volume>0)&f.close.notna()].datetime.dt.strftime('%Y-%m-%d').tolist();best=(0,None,None)
  for a,b in zip(surviving,surviving[1:]):
   n=sessions(a,b,l['asset_type'])
   if n>best[0]:best=(n,a,b)
  if best[0] and best[0]>=gap_k:r['notes'].append(f"post-seam continuity: {best[0]} expected session(s) absent between {best[1]} and {best[2]} - the seam's output splices across this hole; verify the provider era before modelling (docs/DATA_CONTRACT.md §1)")
  res=resolution(f,resolution_window)
  if res:
   r['resolution']=res;tick=f"{res['min_tick']:.4%}" if res['min_tick'] is not None else 'n/a'
   if res['distinct']/res['sessions']<resolution_k or res['flat_share']>flat_k:r['notes'].append(f"coarse price resolution: {res['distinct']} distinct close(s) in {res['sessions']} traded session(s), min tick {tick}, {res['flat_share']:.1%} flat - the provider's quoting grid, verify before modelling (docs/DATA_CONTRACT.md §7.8)")
  state=store.actions_state(root,l['symbol']) if l['actions'] else {'splits':[],'last_updated':None};splitdays={s['date'] for s in state['splits']}
  for i in range(max(1,len(f)-window),len(f)):
   prev=f.close.iloc[i-1]
   if prev==0:continue
   move=f.close.iloc[i]/prev-1.
   if abs(move)>jump_threshold and days[i] not in splitdays:r['alerts'].append(f'phantom-split-shaped jump {move:+.1%} on {days[i]} with no same-day split event - check corporate actions (docs/DATA_CONTRACT.md §2)')
  if l['actions']:
   stamp=state['last_updated']
   if not stamp:r['alerts'].append('corporate actions stale: never synced - run jef-data sync')
   else:
    stamp=datetime.fromisoformat(stamp.replace('Z','+00:00')).astimezone(timezone.utc).date().isoformat();n=sessions(stamp,today,l['asset_type'])
    if n>=2:r['alerts'].append(f'corporate actions stale: {n} refresh session(s) missed since {stamp} - run jef-data sync')
 pairs=[]
 for asset in dict.fromkeys(l['asset'] for l in legs):
  for i,j in combinations([i for i,l in enumerate(legs) if l['asset']==asset],2):
   a,b=legs[i],legs[j];fa,fb=frames[i],frames[j];al=f"{a['exchange']}/{a['symbol']}";bl=f"{b['exchange']}/{b['symbol']}"
   p=dict(asset=asset,kind='cross_venue',a=al,b=bl,common_session=None,spread=None,threshold=spread_threshold,alerts=[],warnings=[],notes=[]);pairs.append(p)
   if not len(fa) or not len(fb):p['notes'].append(f'{al if not len(fa) else bl} has no stored rows - spread not measured');continue
   def dates(f):return f.tail(window).datetime.dt.strftime('%Y-%m-%d')
   common=sorted(set(dates(fa))&set(dates(fb)))
   if not common:p['notes'].append(f'no common session in the newest {window} - spread not measured (see the staleness check)');continue
   day=common[-1];ca=float(fa.loc[fa.datetime.dt.strftime('%Y-%m-%d')==day,'close'].iloc[-1]);cb=float(fb.loc[fb.datetime.dt.strftime('%Y-%m-%d')==day,'close'].iloc[-1]);mid=(ca+cb)/2
   if mid==0:p['notes'].append(f'zero mid price on {day} - spread not measured');continue
   spread=abs(ca-cb)/mid;p.update(common_session=day,spread=spread);p['notes'].append(f'close spread {spread:.4%} on {day} ({al} {ca:g} vs {bl} {cb:g})')
   if spread>spread_threshold:p['alerts' if spread_alerts else 'warnings'].append(f'cross-venue close spread {spread:.4%} on {day} exceeds {spread_threshold:.4%} ({al} {ca:g} vs {bl} {cb:g}) - feed problem or venue distress; verify before acting, never trade it (docs/EVALUATION_CROSS_EXCHANGE.md)')
 alerts=sum(len(r['alerts']) for r in reports+pairs);warnings=sum(len(r['warnings']) for r in reports+pairs)
 return dict(schema_version=1,store=root,reports=reports,pairs=pairs,alerts_total=alerts,warnings_total=warnings),int(alerts>0)

def render_status(doc):
 lines=[]
 def flag(r):return 'ALERT' if r['alerts'] else 'WARN ' if r['warnings'] else 'ok   '
 def findings(r):
  for k,label in [('alerts','ALERT'),('warnings','WARN '),('notes','note ')]:
   for msg in r[k]:lines.append(f'        {label} {msg}')
 for r in doc['reports']:
  lines.append(f"{flag(r)} {r['asset']:>6} {r['exchange']}/{r['symbol']}: last {r.get('last_session','-')}, {r.get('missed_sessions','-')} missed, {r.get('rows',0)} row(s)")
  if 'resolution'in r:
   x=r['resolution'];tick=f"{x['min_tick']:.4%}" if x['min_tick'] is not None else 'n/a';lines.append(f"        res   {x['distinct']} distinct / {x['sessions']} traded, min tick {tick}, {x['flat_share']:.2%} flat")
  findings(r)
 for p in doc['pairs']:lines.append(f"{flag(p)} {p['asset']:>6} cross-venue {p['a']} vs {p['b']}");findings(p)
 last=f"{len(doc['reports'])} source(s)"
 if doc['pairs']:last+=f", {len(doc['pairs'])} venue pair(s)"
 last+=f", {doc['alerts_total']} alert(s)"
 if doc['warnings_total']:last+=f", {doc['warnings_total']} warning(s)"
 return '\n'.join(lines+[last])

"""Ordered acquisition with failure containment and explicit fetch windows."""
from datetime import datetime,timezone,timedelta
from .universe import select_legs,SyncError
from .collectors import EODHDCollector,BinanceCollector
from . import store

def run_sync(universe,store_path=None,*,assets=None,providers=None,dry_run=False,tail=10,force_actions=False,now=None,collectors=None,out=None,base_url=None):
 if tail<1:raise SyncError(f'tail must be >= 1 session, got {tail}')
 legs=select_legs(universe,assets,providers);root=str(store_path or universe['defaults']['store']);today=(now or datetime.now(timezone.utc)).astimezone(timezone.utc).date();emit=out or (lambda _:None)
 pool=dict(collectors or {});owned=[];results=[]
 if dry_run:emit(f'plan for store {root!r} ({len(legs)} leg(s)):')
 try:
  for leg in legs:
   result=dict(leg);revisions=[]
   try:
    if leg['provider']=='yahoo-csv':
     if dry_run:emit(f"  {leg['asset']:>6} {leg['exchange']}/{leg['symbol']}: import {leg['path']} (whole file, idempotent)");result.update(ok=True,detail='planned');results.append(result);continue
     n=store.import_csv(root,leg['path'],leg['exchange'],leg['symbol'],leg['asset_type'],leg['currency']);detail=f'{n} row(s) imported'
    else:
     existing=store.stored_frame(root,leg['exchange'],leg['symbol']);dates=sorted(set(existing.datetime.dt.strftime('%Y-%m-%d'))) if len(existing) else []
     start=dates[-tail:][0] if dates else leg['start'];end=leg['end']
     if leg['asset_type']=='crypto':end=min(x for x in [end,(today-timedelta(days=1)).isoformat()] if x)
     inverted=bool(dates and end and start>end)
     if dry_run:
      action='sync-actions + load' if leg['actions'] else 'load'
      window=f'reconcile tail of {tail} session(s) from {start}' if dates else f'first fill from {start}' if start else 'first fill, full history'
      if end:window+=f' to {end}'
      if inverted:window+=' - INVERTED: end predates the stored tail, nothing to fetch'
      emit(f"  {leg['asset']:>6} {leg['exchange']}/{leg['symbol']}: {action} ({window})");result.update(ok=True,detail='planned');results.append(result);continue
     provider=leg['provider']
     if provider not in pool:
      c=EODHDCollector(base_url=base_url) if provider=='eodhd' else BinanceCollector();pool[provider]=c;owned.append(c)
     c=pool[provider];detail='';splits=[]
     if leg['actions']:
      state=store.actions_state(root,leg['symbol']);stamp=state['last_updated']
      if force_actions or not stamp or datetime.fromisoformat(stamp.replace('Z','+00:00')).astimezone(timezone.utc).date()<today:
       s,d=store.sync_actions(root,leg['symbol'],c);detail+=f'{s} split(s), {d} dividend(s); '
      else:detail+='actions fresh; '
      splits=store.actions_state(root,leg['symbol'])['splits']
     bars=[] if inverted else c.get_eod(leg['symbol'],start,end)
     if inverted:detail+=f'end {end} predates the stored tail (from {start}); nothing fetched - a pinned window with rows past its end, the fix is the declaration; '
     if not dates and not leg['start'] and len(bars)==getattr(c,'limit',None):detail+=f'first fill hit the provider page limit ({len(bars)} bars, no start declared) - the series is a trailing window, not history; '
     basis='raw' if provider=='eodhd' and leg['asset_type']!='crypto' else 'split_adjusted'
     n,revisions=store.put_bars(root,leg['exchange'],leg['symbol'],bars,leg['asset_type'],leg['currency'],basis,splits,c.volume_basis)
     if basis=='raw' and store.latest(root,leg['exchange'],leg['symbol']):store.reapply(root,leg['exchange'],leg['symbol'],splits)
     detail+=f'{n} bar(s), {len(revisions)} revised cell(s)'
     if bars and bars[-1]['date']==today.isoformat():detail+='; today-dated bar ingested (pre-close fetch?)'
    result.update(ok=True,detail=detail,revisions=revisions)
   except Exception as e:result.update(ok=False,detail=f'{type(e).__name__}: {e}',revisions=[])
   results.append(result)
   emit(f"{'ok      ' if result['ok'] else 'FAILED  '}{leg['asset']} {leg['exchange']}/{leg['symbol']} [{leg['provider']}]: {result['detail']}")
   if result['ok']:
    for r in revisions[:10]:emit(f"        revised {r['date']} {r['column']}: {r['stored']:g} -> {r['served']:g}")
    if len(revisions)>10:emit(f'        ... {len(revisions)-10} more revised cell(s)')
 finally:
  for c in owned:c.close()
 failed=sum(not r['ok'] for r in results)
 if not dry_run:emit(f'{len(results)} leg(s), {failed} failed -> store {root!r}')
 return results,not bool(failed)
def sync_summary(results,ok):
 legs=[{**{k:r[k] for k in ['asset','provider','exchange','symbol','ok','detail']},'revised_cells':len(r.get('revisions',[])),'revisions':r.get('revisions',[])} for r in results]
 return dict(schema_version=1,legs_total=len(legs),legs_failed=sum(not x['ok'] for x in legs),revised_cells_total=sum(x['revised_cells'] for x in legs),ok=ok,legs=legs)

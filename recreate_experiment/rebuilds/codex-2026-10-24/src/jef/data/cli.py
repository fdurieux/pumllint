"""Command-line entry point for market-data acquisition."""
import sys,json
from pathlib import Path
from datetime import date,timedelta
from .parser import parser
from .universe import load_universe,UniverseError,SyncError
from . import store,contract
from .collectors import EODHDCollector,normalize
from .sync import run_sync,sync_summary
from .health import status_json,render_status

class DeclarationRefused(ValueError):pass

def declaration(symbol,asset_type):
 if asset_type is None and not symbol.endswith('.CC'):raise DeclarationRefused(f"{symbol}: asset_type is required (one of ['crypto', 'etf', 'stock']). The ticker carries no instrument-type signal - SPY, TLT, GLD and IBIT are ETFs spelled exactly like equities - so the old 'stock' default was a guess written into the store as a fact, and TLT is in this repo's universe as an explicit override because that guess got it wrong. Only EODHD's .CC crypto namespace is evidence enough to infer from")
 if symbol.endswith('.CC') and asset_type not in [None,'crypto']:raise DeclarationRefused(f"{symbol} is in EODHD's .CC crypto namespace but was declared asset_type={asset_type!r}; that combination cannot be true, and guessing either way decides whether split adjustment runs on pre-adjusted prices (docs/DATA_CONTRACT.md §2)")
 if asset_type not in [None,'crypto','etf','stock']:raise DeclarationRefused(f"unknown asset_type {asset_type!r}; the store vocabulary is ['crypto', 'etf', 'stock'] (derived from the universe's own asset_class map, jef.data.universe.ASSET_TYPE_BY_CLASS)")
 return asset_type or 'crypto'

def load(args,collector):
 symbol=normalize(args.symbol);at=declaration(symbol,args.asset_type);last=store.latest(args.store,'eodhd',symbol)
 start=getattr(args,'from') or ((date.fromisoformat(last)+timedelta(days=1)).isoformat() if last else None)
 bars=collector.get_eod(symbol,start,args.to);basis='split_adjusted' if at=='crypto' else 'raw';splits=store.actions_state(args.store,symbol)['splits'] if basis=='raw' else []
 n,_=store.put_bars(args.store,'eodhd',symbol,bars,at,args.currency,basis,splits,collector.volume_basis,mode='append')
 if basis=='raw' and (bars or last):store.reapply(args.store,'eodhd',symbol,splits)
 return n

def main(argv=None):
 args=parser().parse_args(argv);cmd=args.command
 try:
  if cmd in ['universe','sync','status']:
   u=load_universe(args.universe)
   if cmd=='universe':
    for a in u['assets']:
     print(f"{a['name']} ({a['asset_class']}, {a['currency']}, threshold {a['threshold']})"+(' [disabled]' if not a['enabled'] else ''))
     for s in a['sources']:print(f"  {s['provider']}: {s.get('path',s['symbol'])}"+(' [disabled]' if not s['enabled'] else '')+(' - '+s['note'] if 'note'in s else ''))
    return 0
   if cmd=='sync':
    results,ok=run_sync(u,args.store,assets=args.asset,providers=args.provider,dry_run=args.dry_run,tail=args.tail,force_actions=args.force_actions,base_url=args.base_url,out=print)
    if args.summary_json:Path(args.summary_json).write_text(json.dumps(sync_summary(results,ok),indent=1,sort_keys=True)+'\n')
    return int(not ok)
   doc,rc=status_json(u,args.store,assets=args.asset,providers=args.provider,window=args.window,jump_threshold=args.jump_threshold,staleness_k=args.staleness,resolution_window=args.resolution_window,resolution_k=args.resolution_k,flat_k=args.flat_k,gap_k=args.gap_k,spread_threshold=args.spread_threshold,spread_alerts=args.spread_alerts)
   print(json.dumps(doc,indent=1) if args.json else render_status(doc));return rc
  if cmd=='validate':
   import pandas as pd
   f=pd.read_csv(args.csv);report=contract.validate(f,args.min_rows);print(f'{args.csv}: {len(f)} rows');print(contract.render_validation(report));return int(bool(report[0]))
  if cmd=='import-csv':
   n=store.import_csv(args.store,args.csv,args.exchange,args.symbol,args.asset_type,args.currency);print(f'{args.csv}: {n} row(s) -> {args.store}/market_data/exchange={args.exchange}/symbol={args.symbol}/ (price_basis=split_adjusted)');return 0
  if cmd=='adjust':
   splits=store.actions_state(args.store,args.symbol)['splits'];n=store.reapply(args.store,args.exchange,args.symbol,splits);print(f'{args.exchange}/{args.symbol}: {n} row(s) re-derived from *_raw with {len(splits)} split(s)');return 0
  if cmd=='export':
   f=store.export_frame(args.store,args.exchange,args.symbol);f.to_csv(args.output,index=False);print(f'{args.exchange}/{args.symbol}: {len(f)} row(s) -> {args.output}');report=contract.validate(f);print(contract.render_validation(report));return int(bool(report[0]))
  if cmd=='differential':
   if not args.b_csv and not args.b_symbol:print('differential: pass --b-csv or --b-symbol',file=sys.stderr);return 1
   import pandas as pd
   a=store.export_frame(args.store,args.a_exchange,args.a_symbol);b=pd.read_csv(args.b_csv) if args.b_csv else store.export_frame(args.store,args.b_exchange,args.b_symbol)
   report,ok=contract.differential(a,b,f'{args.a_exchange}/{args.a_symbol}',args.b_csv or f'{args.b_exchange}/{args.b_symbol}',args.tolerance);print(report)
   if args.output:Path(args.output).write_text(report+'\n')
   return int(not ok)
  if cmd in ['load','sync-actions']:
   c=EODHDCollector(base_url=args.base_url)
   try:
    if cmd=='load':n=load(args,c);print(f'{args.symbol}: {n} bar(s) ingested -> {args.store}/market_data/')
    else:s,d=store.sync_actions(args.store,args.symbol,c);print(f'{args.symbol}: {s} split(s), {d} dividend(s) -> {args.store}/corporate_actions/')
   finally:c.close()
   return 0
 except (UniverseError,SyncError,DeclarationRefused) as e:print(f'{cmd}: {e}',file=sys.stderr);return 1

if __name__=='__main__':sys.exit(main())

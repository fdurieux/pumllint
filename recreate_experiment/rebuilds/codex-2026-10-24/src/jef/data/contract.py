"""Validation and relative comparison of exported daily frames."""
import numpy as np
import pandas as pd
from .store import SEAM

def validate(f,min_rows=1115):
 errors=[];notes=[];missing=[k for k in SEAM if k not in f]
 if missing:return [f'missing required columns: {missing}'],[]
 extra=[k for k in f if k not in SEAM]
 if extra:notes.append(f'extra columns {extra} are carried through; NaNs in them will drop rows at load (the transform drops any-NaN rows)')
 nums=f[SEAM[1:]].apply(pd.to_numeric,errors='coerce');bad=[k for k in nums if nums[k].isna().sum()>f[k].isna().sum()]
 if bad:errors.append(f'non-numeric values in {bad}')
 dates=pd.to_datetime(f.Date,errors='coerce')
 if not dates.notna().any():return errors+["no parseable dates in 'Date'"],notes
 n=int(dates.isna().sum())
 if n:notes.append(f'{n} unparseable date(s) - those rows drop at load')
 n=int(dates.dropna().duplicated().sum())
 if n:errors.append(f'{n} duplicate date(s) - forbidden by the contract')
 if not dates.dropna().is_monotonic_increasing:notes.append('dates not sorted ascending - the load transform sorts')
 if not bad:
  negative=[k for k in SEAM[1:-1] if (nums[k]<0).any()]
  if negative:errors.append(f'negative prices in {negative}')
  if (nums.Volume<0).any():errors.append('negative values in Volume')
  n=int((nums.High<nums.Low).sum())
  if n:errors.append(f'{n} row(s) with High < Low')
  n=int((nums.Volume==0).sum())
  if n:notes.append(f'{n} zero-volume row(s) - dropped at load by policy')
  n=int(f[SEAM].isna().any(axis=1).sum())
  if n:notes.append(f'{n} row(s) with NaN - dropped at load')
  clean=int((dates.notna() & (nums.Volume!=0) & ~nums.isna().any(axis=1)).sum())
  if clean<min_rows:notes.append(f'{clean} clean row(s) < recommended minimum {min_rows} (720 warm-up + 395 lags) - the default counter window needs more history (docs/DATA_CONTRACT.md §1)')
 return errors,notes

def render_validation(report):
 errors,notes=report
 return '\n'.join(['ERROR: '+e for e in errors]+['note:  '+n for n in notes]) or 'contract: clean'

def differential(a,b,alabel,blabel,tolerance=.0001):
 a=a.sort_values('Date').set_index('Date');b=b.sort_values('Date').set_index('Date');common=sorted(set(a.index)&set(b.index));unmatched=0;cells=0
 lines=[f'differential: {alabel} vs {blabel} (relative tolerance {tolerance:g})',f'rows: {len(a)} in {alabel}, {len(b)} in {blabel}, {len(common)} dates in common']
 for f,other,label in [(a,b,alabel),(b,a,blabel)]:
  only=sorted(set(f.index)-set(other.index));unmatched+=len(only)
  if only:lines.append(f"only in {label}: {len(only)} date(s): {', '.join(only[:5])}"+(f' (+{len(only)-5} more)' if len(only)>5 else ''))
 for col in SEAM[1:]:
  av=a.loc[common,col].to_numpy(dtype='float64');bv=b.loc[common,col].to_numpy(dtype='float64');den=np.maximum(np.abs(av),np.abs(bv));den[den==0]=1
  rel=np.abs(av-bv)/den;rel[np.isnan(av)&np.isnan(bv)]=0;rel[np.isnan(av)^np.isnan(bv)]=np.inf
  k=int((rel>tolerance).sum());cells+=k
  if not k:lines.append(f'{col}: within tolerance (max {max(rel,default=0):.3%})')
  else:
   i=int(np.argmax(rel));lines.append(f'{col}: {k}/{len(common)} beyond tolerance, worst {rel[i]:.3%} on {common[i]} ({alabel}={av[i]!r}, {blabel}={bv[i]!r})')
 ok=not cells and not unmatched
 lines.append('VERDICT: '+('within tolerance, aligned' if ok else f'{cells} cell(s) beyond tolerance, {unmatched} unmatched date(s) - review before scale-out'))
 return '\n'.join(lines),ok

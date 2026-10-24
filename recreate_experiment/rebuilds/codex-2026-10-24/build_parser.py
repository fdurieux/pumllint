"""Materialize the explicitly specified parser declarations for this build."""
from pathlib import Path
import re
out=Path(__file__).resolve().parent
text=(out.parents[1]/'kit/contracts/cli.md').read_text()
section=text.split('## Parser surface')[1]
description=re.search(r'```text\n(.*?)\n```',section,re.S).group(1)
helps={}
for line in section.split('### Subcommand help strings')[1].split('### Options')[0].splitlines():
 if line.startswith('| `'):
  cells=[s.strip().strip('`') for s in line.strip('|').split('|')];helps[cells[0]]=cells[1]
spec={};command=None
for line in section.split('### Options of each subcommand')[1].splitlines():
 m=re.match(r'#### `([^`]+)`',line)
 if m:command=m[1];spec[command]=[]
 if command and line.startswith('| `'):
  cells=[s.strip().strip('`') for s in line.strip('|').split('|')]
  option,dest,meta,action,typ,default,required,choices=cells[:8];helptext=line.strip('|').split('|',8)[8].strip().strip(chr(96))
  if option=='-h, --help':continue
  kw={}
  arg=dest if option=='(positional)' else option
  if action.startswith('append'):kw['action']='append'
  elif action=='store_true':kw['action']='store_true'
  if typ in ['int','float']:kw['type']=typ
  if default not in ['None','—','False']:
   kw['default']=int(default) if typ=='int' else float(default) if typ=='float' else default
  if required=='yes' and option!='(positional)':kw['required']=True
  if choices!='—':kw['choices']=choices.split(',')
  if option=='--summary-json':kw['metavar']='PATH'
  if helptext!='—':kw['help']=helptext.replace('%','%%')
  spec[command].append((arg,kw))
source='"""Command-line parser declarations."""\nimport argparse\n\nDESCRIPTION='+repr(description)+'\nHELPS='+repr(helps)+'\nOPTIONS='+repr(spec)+'''\n\ndef parser():
 p=argparse.ArgumentParser(prog='jef-data',description=DESCRIPTION)
 sub=p.add_subparsers(dest='command',required=True)
 for command,options in OPTIONS.items():
  s=sub.add_parser(command,help=HELPS[command])
  for arg,kw in options:
   kw=dict(kw)
   if 'type' in kw:kw['type']={'int':int,'float':float}[kw['type']]
   s.add_argument(arg,**kw)
 return p
'''
(out/'src/jef/data/parser.py').write_text(source)

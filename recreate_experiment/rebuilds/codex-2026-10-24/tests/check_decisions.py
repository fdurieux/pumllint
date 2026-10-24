"""Finite-domain decision-table checks, independent of the excluded harness."""
from pathlib import Path
import itertools,json,re,xml.etree.ElementTree as ET
out=Path(__file__).resolve().parents[1];root=out.parents[1]/'kit/contracts/dmn'
ns={'d':'https://www.omg.org/spec/DMN/20191111/MODEL/'}
def text(e,path):
 x=e.find(path,ns);return x.text if x is not None else None

def matches(expr,value):
 if expr=='-':return True
 if expr.startswith('not('):return not matches(expr[4:-1],value)
 for op in ['>=','<=','>','<']:
  if expr.startswith(op):
   n=float(expr[len(op):]);return {'>=':value>=n,'<=':value<=n,'>':value>n,'<':value<n}[op]
 return value==json.loads(expr)
results=[]
for p in sorted(root.glob('*.dmn')):
 for d in ET.parse(p).getroot().findall('d:decision',ns):
  table=d.find('d:decisionTable',ns);domains=[];inputs=table.findall('d:input',ns);rules=table.findall('d:rule',ns)
  for i in inputs:
   typ=i.find('d:inputExpression',ns).attrib['typeRef'];v=text(i,'d:inputValues/d:text')
   domains.append([False,True] if typ=='boolean' else [0,1,2,3,100000] if typ=='integer' else json.loads('['+v+']'))
  points=0
  for values in itertools.product(*domains):
   hit=[r for r in rules if all(matches(text(e,'d:text'),v) for e,v in zip(r.findall('d:inputEntry',ns),values))]
   assert len(hit)==1,(p.name,d.attrib['name'],values,[r.attrib['id'] for r in hit]);points+=1
  results.append(dict(file=p.name,decision=d.attrib['name'],rules=len(rules),sampled_points=points,result='unique on sampled declared domain'))
print(json.dumps({'method':'Enumerate all declared finite values; representative nonnegative integers at and around thresholds. Not full FEEL validation or excluded harness equivalence.','decisions':results,'rules_total':sum(x['rules'] for x in results),'limitation':'actions_gate future-stamp domain omission remains F-005.'},indent=2))

"""Build an auditable inventory; preserve initial assessments on subsequent runs."""
from pathlib import Path
import json, hashlib, re, xml.etree.ElementTree as ET
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
BASE='88f656a39f47fe92a31e887e26888775658aa19b'
FINDINGS=[
 ('F-001','minor','inconsistency','kit/README.md','Requirements count says 162; requirements.json actually has 163.','Use the actual ID inventory, not the stale prose count.'),
 ('F-002','major','missing','handover/DONE.md','Checks 4 and 5 require harness tools outside the permitted input set.','Do not consult them. Derive independent checks; do not claim those exact gates ran.'),
 ('F-003','major','missing','kit/contracts/chain.md','events.sh and dashboard.sh are called given externals, but neither is supplied in kit or handover; conftest copies existing files instead of supplying stubs.','Keep production externals absent; run additional chain tests with explicitly labelled, independently written test doubles.'),
 ('F-004','minor','identifier_collision','kit/contracts/refusals.md','X-10 names both absent differential and parser errors.','Identify findings by requirement ID and condition as well as refusal ID.'),
 ('F-005','moderate','incomplete_domain','kit/contracts/dmn/actions_gate.dmn','Stamp domain includes none/before_today/today but omits future stamps; JDL-091 and real-clock injection allow future stamps.','Follow JDL-091: stamps on or after today are fresh. Treat DMN completeness as conditional on its restricted domain.'),
 ('F-006','minor','inconsistency','kit/CHANGES.md','Closing-round section says three additions but lists more; JDL-163 and the wave-2 changes are absent.','Use pinned files rather than changelog as the complete inventory.'),
 ('F-007','moderate','missing','kit/contracts/universe.toml','Packaged universe CSV paths refer to experiments files outside permitted inputs.','Ship the bytes as required; default full sync needs those external snapshots. Offline dry-run remains possible.'),
 ('F-008','minor','inconsistency','kit/uml/data_model.puml','Transport request returns TransportResponse in the model, while prose and adapter describe (status, text).','Implement tuple transport per the explicit collector contract.'),
]
DIMS=['semantic_correctness','completeness','consistency','clarity','verifiability','implementation_value']
def build():
 target=OUT/'input-quality.json'
 old=json.loads(target.read_text()) if target.exists() else None
 if old:return old
 arts=[]
 for area in ['kit','handover']:
  for p in sorted((ROOT/area).rglob('*')):
   if not p.is_file():continue
   rel=p.relative_to(ROOT).as_posix();text=p.read_text(); ids=sorted(set(re.findall(r'JDL-\d{3}',text)))
   derivative=area=='handover' and (p.name in ['REQUIREMENTS.md','TRACE.md','DECISIONS.md'] or p.suffix=='.svg')
   kind='generated view' if derivative else 'fixture' if 'fixtures' in p.parts else 'decision model' if p.suffix=='.dmn' else 'diagram' if p.suffix=='.puml' else 'acceptance oracle' if p.suffix=='.feature' else 'support code' if p.suffix=='.py' else 'contract/configuration'
   fs=[f[0] for f in FINDINGS if f[3]==rel]
   scores={d:{'score':None,'confidence':'low','rationale':'Unassessed until used; no inference from presence alone.'} for d in DIMS}
   for d in ['completeness','consistency','clarity','verifiability']:
    scores[d]={'score':3 if fs else 4,'confidence':'low','rationale':('Initial inspection found '+', '.join(fs)+'.' if fs else 'Initial structural/read-through assessment; scoped sufficiency needs implementation evidence.')}
   if kind=='fixture':
    for d in DIMS:scores[d]={'score':None,'confidence':'low','rationale':'Full file consumed and structurally inspected; individual semantic quality not established before execution.'}
   arts.append({'id':f'A-{len(arts)+1:03d}','path':'recreate_experiment/'+rel,'kind':kind,'baseline_commit':BASE,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scope':p.stem,'read_status':'structurally parsed' if kind=='fixture' or derivative else 'read; detailed reassessment during use','use_status':'pending','source_relationship':'Derived from kit; shared facts must not be counted twice' if derivative else None,'requirement_ids':ids,'baseline_scores':scores,'final_scores':None,'findings':fs,'contribution_events':[],'history':[]})
 return {'schema_version':'1.0','baseline_commit':BASE,'run_metadata':{'model':'gpt-6.1-sol-wm','reasoning_effort':'unverified','independence':'Only allowed inputs present; repository metadata inspected; no prior code or outcomes read.'},'artefacts':arts,'findings':[{'id':i,'severity':sev,'classification':k,'path':'recreate_experiment/'+p,'observation':s,'resolution':r,'status':'recorded','evidence':p} for i,sev,k,p,s,r in FINDINGS],'set_assessment':{'baseline':'163 requirements; 221 files; externals and optional verification tools missing. Overall semantic correctness unverified.','final':None},'validation_runs':[]}
if __name__=='__main__':
 d=build();(OUT/'input-quality.json').write_text(json.dumps(d,indent=2)+'\n')
 lines=['# Input quality assessment','','Status: baseline recorded before implementation. Scores are ordinal, provisional, and evidence-limited. Semantic correctness and implementation value are not yet scored.','','## Findings','']
 for f in d['findings']:lines += [f"### {f['id']} — {f['classification']} ({f['severity']})",'',f"Source: `{f['path']}`",'',f['observation'],'',f"Resolution: {f['resolution']}",'']
 lines += ['## Per-file baseline','','Every file has a separate machine-readable record, hash, scores and uncertainty in `input-quality.json`. Generated views add navigation/comprehension evidence, not independent behavioural coverage.','','| Artefact | Kind | Findings | C / consistency / clarity / V |','|---|---|---|---|']
 for a in d['artefacts']:
  scores=' / '.join(str(a['baseline_scores'][k]['score']) for k in ['completeness','consistency','clarity','verifiability'])
  lines.append(f"| {a['path']} | {a['kind']} | {', '.join(a['findings']) or 'None identified yet'} | {scores} |")
 (OUT/'INPUT-QUALITY.md').write_text('\n'.join(lines)+'\n')

"""Join the preserved baseline assessment to implementation and validation evidence."""
from pathlib import Path
import json,re,hashlib
out=Path(__file__).resolve().parent;kit=out.parents[1]/'kit';p=out/'input-quality.json';d=json.loads(p.read_text())
extra=[
 ('F-009','moderate','test_harness_limitation','kit/features/steps/conftest.py','The chain call logger writes arguments without escaping embedded newlines, then splits records by line. Valid multiline python -c arguments generate false call-list failures.','Use single-line escaped Python code arguments in daily.sh; leave supplied test code unchanged.'),
 ('F-010','minor','incorrect_example','kit/contracts/cli.md','General JSON rules say non-ASCII is escaped, but display an unchanged section sign as the example. Python default JSON and the actual JSON examples use escaped Unicode.','Follow Python json defaults and the precise output contracts.'),
]
for i,sev,c,path,obs,res in extra:
 if not any(f['id']==i for f in d['findings']):d['findings'].append(dict(id=i,severity=sev,classification=c,path='recreate_experiment/'+path,observation=obs,resolution=res,status='recorded',evidence=path))
# Requirement-to-scenario links are static declarations, not code-coverage claims.
scenarios=[]
for f in sorted((kit/'features').glob('*.feature')):
 tags=[]
 for n,line in enumerate(f.read_text().splitlines(),1):
  t=line.strip()
  if t.startswith('@'):tags+=re.findall(r'JDL-\d{3}',t)
  if re.match(r'Scenario(?: Outline)?:',t):
   scenarios.append(dict(feature=f.name,line=n,name=t.split(':',1)[1].strip(),requirements=sorted(set(tags))));tags=[]
def modules(n):
 if n<=22:return ['universe.py']
 if n<=39:return ['collectors.py']
 if n<=75:return ['store.py']
 if n<=83:return ['contract.py']
 if n<=106:return ['sync.py']
 if n<=132:return ['health.py']
 if n<=145:return ['cli.py','parser.py']
 if n<=158:return ['deploy/daily.sh']
 return ['cli.py','parser.py','store.py']
requirements=json.loads((kit/'requirements.json').read_text());trace=[]
for r in requirements:
 trace.append(dict(requirement=r['id'],kind=r['kind'],implementation=[x if '/' in x else 'src/jef/data/'+x for x in modules(int(r['id'][4:]))],scenarios=[x for x in scenarios if r['id'] in x['requirements']],qualification='Static trace plus successful supplied scenarios using test doubles for chain externals; not line/branch coverage or proof of full semantic correctness.'))
(out/'requirement-trace.json').write_text(json.dumps(trace,indent=2)+'\n')
# Specific comments supplement the score anchors and category-level limits.
notes={
 'README.md':'Reading order and deliverables are directly usable; baseline instructions distinguish kit authority from navigation.',
 'requirements.json':'163 unique IDs supplied numerical constants and branch conditions; static trace links each ID to implementation and tagged scenarios.',
 'adjustment.md':'Strict-before effective dates and explicit float operation order resolved implementation choices; independent fixed-point/effective-date checks support local arithmetic semantics.',
 'store.md':'The 21-column schema, write modes and lock discipline directly determined store.py; no-op, lock and invalid-date checks extend supplied examples.',
 'seam_frame.md':'Volume dtype and unchanged-row rules prevented rounding/filtering at export; the suite compared the seam frames exactly.',
 'collectors.md':'Specified one retry policy for both live and replay traffic; independent tests exercised retries and rate limits without provider calls.',
 'fixtures.md':'Request identity and replay ordering made offline collector validation possible; recorder secret checks were independently exercised.',
 'cli.md':'Parser tables enabled a standalone parser with no runtime kit dependency; exact help and refusal scenarios exposed one generator spacing defect, corrected.',
 'cli_help.md':'Verbatim oracle detected a spacing defect in generated status help; it contributes exact output validation rather than an independent behavioural source.',
 'chain.md':'Detailed stage arguments and error propagation enabled daily.sh; missing externals limit production integration and required test-only substitutes.',
 'universe.toml.md':'Explicit validation order and exact refusals enabled deterministic parsing; invalid-universe scenarios check first-error behaviour.',
 'classifications.toml.md':'Mapping separates agreement from evidence independence. Only the packaged valid input is currently needed; arbitrary invalid-file validation is not exposed.',
 'classifications.toml':'Packaged evidence shipped byte-identically. Historical vendor provenance was not independently reverified because external lookup is excluded.',
 'universe.toml':'Shipped byte-identically; its listing and nine-leg dry-run pass. Referenced external snapshot files are not supplied.',
 'HARNESS_INTERFACE.md':'The adapter signatures allowed clock injection and replay without any copied prior implementation; adapter contains imports only.',
 'leg.md':'Exact leg keys and ownership of clocks prevented clock injection from changing actions-file stamps.',
 'refusals.md':'Exact messages and wrapped/contained/traceback distinctions contributed direct CLI decisions; reused X-10 identifier weakens traceability.',
 'DECISIONS.md':'Readable DMN view served as a branch checklist. It shares source information with DMN and is not separately counted as semantic coverage.',
 'REQUIREMENTS.md':'Navigable generated requirement view; primary JSON remains authoritative. No independent information gain is claimed.',
 'TRACE.md':'Generated joins aided navigation. Independent requirement-trace.json was generated from the supplied tags; no prior experiment evidence was used.',
 'DONE.md':'Separates gate from optional checks and documents uncovered live paths; some required supporting files are excluded/missing, so its full gate is not claimed.',
 'KNOWN-QUIRKS.md':'Prevented changing timestamp seconds, actions clock and absent-series tracebacks that would have violated the intended recreation.',
 'AGENTS.md':'Established independence and allowed inputs before coding. Its no-network instruction is applied to behavioural research, with administrative transport and pinned dependency retrieval recorded.',
 'ARCHITECTURE.md':'Provided module and operation sequencing orientation. Behavioural decisions were checked against detailed contracts.',
 'CHANGES.md':'Useful revision orientation, but does not comprehensively enumerate the latest wave-2 additions.',
 'build.py':'Read as a generated-view provenance aid; not executed because it depends on pumllint outside the allowed recreation input/environment.',
 'pumllint.toml':'Configures optional diagram linting only; not used to implement runtime behaviour or claim diagram quality gates.',
 'conftest.py':'Adapter-driven numerical comparisons, log assertions and stubbed commands provided concrete checks; chain externals are not actually supplied and multiline argument logging is lossy.',
 'test_features.py':'Collected all 257 supplied acceptance cases unchanged.',
 'pins.md':'Exact runtime pins installed successfully; CPython 3.12.14 used for specified traceback/help compatibility. Python 3.11 was not tested.',
}
primary_used={'adjustment.md','store.md','seam_frame.md','collectors.md','fixtures.md','cli.md','cli_help.md','chain.md','universe.toml.md','classifications.toml.md','HARNESS_INTERFACE.md','leg.md','refusals.md','requirements.json','pins.md','universe.toml','classifications.toml','KNOWN-QUIRKS.md','AGENTS.md','DECISIONS.md','ARCHITECTURE.md'}
for a in d['artefacts']:
 path=Path(a['path']);name=path.name;txt=path.read_text();raw=path.read_bytes()
 a['git_blob_sha1']=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
 a['findings']=sorted(set(a['findings']+[f['id'] for f in d['findings'] if f['path']==a['path']]))
 issues=[f for f in d['findings'] if f['id'] in a['findings']]
 a['implementation_links']=sorted(set(y for r in trace if r['requirement'] in a['requirement_ids'] for y in r['implementation']))
 a['scenario_links']=[f"{s['feature']}:{s['line']}" for s in scenarios if set(s['requirements']) & set(a['requirement_ids'])]
 structural=a['kind'] in ['fixture','generated view']
 a['comment']=notes.get(name, 'Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source.' if a['kind']=='fixture' else 'Decision model: branch partitions were inspected and checked over the declared finite domains; completeness beyond those domains is not established.' if a['kind']=='decision model' else 'Diagram: used for structural orientation with primary contracts; no independent semantic truth or causal contribution is inferred.' if a['kind']=='diagram' else 'Executable scenarios provide observable assertions for the tagged requirements; passing them does not establish complete behavioural coverage.' if a['kind']=='acceptance oracle' else 'Supporting input inspected; contribution beyond navigation is not established.')
 final={}
 for dim in ['semantic_correctness','completeness','consistency','clarity','verifiability','implementation_value']:
  score=None;confidence='low';reason='No independent evidence sufficient to score this dimension.'
  if dim=='semantic_correctness':
   if name=='adjustment.md':score=4;confidence='medium';reason='Worked arithmetic and effective-date/fixed-point properties checked independently. Not a proof over all floating-point inputs.'
   elif a['kind']=='decision model':score=3 if a['findings'] else 4;confidence='medium';reason='Unique matches on enumerated declared finite domains and sampled nonnegative integer thresholds; real-world domain completeness not proved.'
   else:reason='Agreement with this kit and acceptance examples is observed; independent domain truth is unverified.'
  elif dim=='implementation_value':
   if name in primary_used:score=5 if name in ['adjustment.md','store.md','cli.md','HARNESS_INTERFACE.md','KNOWN-QUIRKS.md'] else 4;confidence='medium';reason=a['comment']
   elif a['kind']=='acceptance oracle' or name in ['conftest.py','test_features.py']:score=4;confidence='medium';reason='Used unchanged for acceptance assertions; chain results depend on labelled substitute externals.'
   elif a['kind']=='decision model':score=3;confidence='medium';reason='Used as branch checklist via the rendered table and independently checked for domain partitioning; information overlaps prose.'
   else:reason='Individual marginal contribution was not instrumented; grouped corpus/structural use does not establish a per-file effect.'
  else:
   if a['kind']=='fixture':
    if dim=='verifiability':score=4;confidence='medium';reason='Structurally parsed, pinned by hash, and supplied corpus/behaviour assertions ran; does not independently validate every expected cell.'
    else:reason='Individual fixture scope and completeness cannot be inferred solely from successful suite execution.'
   elif a['kind']=='generated view':
    if dim in ['clarity','verifiability']:score=3;confidence='low';reason='Derived view inspected structurally; SVGs were not visually reviewed and full regeneration was not executed.'
   else:
    score=4;confidence='medium';reason=a['comment']
    if issues:
     score=2 if dim=='completeness' and any(f['severity']=='major' for f in issues) else 3
     reason='Recorded issues '+', '.join(a['findings'])+' qualify scoped sufficiency: '+a['comment']
  final[dim]=dict(score=score,confidence=confidence,rationale=reason)
 a['final_scores']=final;a['use_status']='primary implementation/validation input' if name in primary_used or a['kind']=='acceptance oracle' else 'corpus/structural/navigation input; individual effect unmeasured'
 a['contribution_events']=[dict(classification='decision guidance' if name in primary_used else 'validation' if a['kind']=='acceptance oracle' else 'navigation/corpus support',observation=a['comment'],evidence=a['implementation_links'] or ['validation/final-with-test-doubles.txt'],limitation='Observed role in one build; no controlled ablation or causal magnitude measured.')]
 a['history'].append(dict(phase='post implementation',reason='Added implementation evidence and known gaps; preserved original baseline scores.'))
for f in d['findings']:f['score_impact']='Affected artefact completeness/consistency/clarity remains below 4; resolution is an implementation choice, not a repair to the supplied input.'
d['set_assessment']['final']={'files':len(d['artefacts']),'requirements':len(requirements),'tagged_scenarios':len(scenarios),'acceptance_cases':257,'non_chain_cases':246,'chain_cases':11,'semantic_correctness':{'score':None,'reason':'Independent domain truth not established; local arithmetic invariants passed.'},'completeness':{'score':3,'reason':'Enough to recreate data behaviour; missing external scripts prevent the exact complete integration gate.'},'consistency':{'score':3,'reason':'Recorded identifiers, counts, model domain and transport-shape mismatches require interpretation.'},'clarity':{'score':4,'reason':'Detailed contracts provide numerical order, exact messages and validation order.'},'verifiability':{'score':4,'reason':'257 reproducible cases, recorded traffic and exact frames; live paths and external integration remain qualified.'},'limitations':['No prior implementation, hidden tests or experiment outcomes consulted.','No live provider or real AWS integration was run.','Missing original externals were never reconstructed as production files.','Excluded optional harness gates were not executed.','No SVG visual QA, full handover regeneration, code-coverage instrumentation, or controlled contribution ablation.','Per-file unknowns remain null; no composite average score.']}
d['validation_runs']=[{'file':'validation/acceptance-initial.txt','result':'244 passed / 13 failed; diagnostic only, before local transport newline and parser-generation corrections; 11 failures were missing externals.'},{'file':'validation/final-with-test-doubles.txt','result':'268 passed: 257 supplied acceptance cases using test-only shell externals plus 11 independent checks.'},{'file':'validation/decisions.json','result':'Independent finite-domain uniqueness check; not the excluded harness checker.'},{'file':'validation/final-required-externals.txt','result':'246 passed, 11 failed at setup because required external scripts are absent; zero skipped. The exact gate is not satisfied.'}]
p.write_text(json.dumps(d,indent=2)+'\n')
lines=['# Input quality and contribution assessment','','Input commit: `'+d['baseline_commit']+'`. Every baseline score is preserved in `input-quality.json`. Final scores use 0–5 ordinal anchors; `—` means unverified/unassessed, not zero. No aggregate average is reported.','','## Set assessment','','The 221 supplied files contain 163 requirements, 130 tagged scenarios, and 257 collected cases. The independently recreated data behaviour passed all 246 non-chain cases. All 257 cases passed with explicitly substituted test-only shell externals; 11 independent checks also passed. The exact full integration gate remains blocked by the absent original externals.','','| Dimension | Score | Reason |','|---|---|---|']
for dim,v in d['set_assessment']['final'].items():
 if isinstance(v,dict) and 'score'in v:lines.append(f"| {dim} | {v['score'] if v['score'] is not None else '—'} | {v['reason']} |")
lines+=['','## Findings and resolutions','']
for f in d['findings']:lines += [f"### {f['id']} — {f['classification']} ({f['severity']})",'',f"Source: `{f['path']}`",'',f['observation'],'','Recorded resolution: '+f['resolution'],'',f['score_impact'],'']
lines+=['## Per-artefact final review','','Columns: S semantic correctness; C completeness; A consistency/agreement; L clarity; V verifiability; U implementation usefulness. Confidence and dimension-specific evidence are in JSON. Each row is scoped to its file, not an estimate of causal quality improvement.','','| Artefact | S / C / A / L / V / U | Comment and observed contribution |','|---|---|---|']
for a in d['artefacts']:
 scores=' / '.join('—' if x['score'] is None else str(x['score']) for x in a['final_scores'].values())
 lines.append(f"| `{a['path']}` | {scores} | {a['comment']}"+(' Findings: '+', '.join(a['findings']) if a['findings'] else '')+' |')
lines+=['','## Evidence and limits','','`requirement-trace.json` links all declared IDs to implementation files and scenario declarations. These are static trace links, not measured line or branch coverage. Tests can share assumptions with contracts and synthetic fixtures. Individual fixture and generated-view contributions were not causally isolated; unsupported scores remain unassigned.','']
for x in d['set_assessment']['final']['limitations']:lines.append('- '+x)
(out/'INPUT-QUALITY.md').write_text('\n'.join(lines)+'\n')
print(len(d['artefacts']),'artefacts;',len(scenarios),'scenarios;',len(trace),'requirements;',sum(bool(x['scenarios']) for x in trace),'with tags')

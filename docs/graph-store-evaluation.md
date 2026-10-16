# Running pumllint on a graph store (Neo4j) — three readings, evaluated

*Dated evaluation, 2026-10-16, written against `15a517b` (v0.33.0 plus
docs, after #168). The question as posed, in two turns: would it make
sense to plan for pumllint as a semantic validation tool on top of a
semantic layer for corporate knowledge (customer-journey documentation,
BPMN process documentation, UML-based artefacts); and, sharpened, "run
pumllint on a graph network, such as a Neo4j".*

**Verdict up front: no to pumllint inside the store, a shape on record
for the store feeding pumllint, and nothing to build for pumllint feeding
the store. The question has three readings, and only the second is on
no record. (1) *Rules executed over the store* is the 2026-08-26
settlement's N1 and N3, confirmed at the primary by #168, and the rule
census below adds one fact: the 31 of 52 rules that keep a meaning over a
property graph are exactly the ones the store's own constraint and SHACL
tooling already expresses, and the other 21 check things a store cannot
hold. (2) *Store → in-memory model → engine* works today, measured: a
`Diagram` built from store-shaped rows runs through `Engine.lint_diagram`
and `scoring.score` unchanged. It also skips the step aris2puml exists
for. An unclosed or unstructured branch becomes invisible rather than
refused, findings anchor to invented lines, remediation speaks PlantUML
to someone who never wrote it, and the syntax gate can never run. So if
it is ever built, it is a converter that emits `.puml`, in its own
repository and under aris2puml's iron rules, never an adapter inside
pumllint. (3) *Findings loaded into the store* needs no pumllint code. An
imported score or trace report is evidence only once Arc E's
run-provenance candidate ships, whose trigger already names "a
consumer — an evidence store, a knowledge graph — ingesting them";
imported lint findings are not evidence even then, and how they could
be is open. No checkbox is added, no trigger fires, and the priorities
do not move.**

*Bounds: every repository claim was executed at `15a517b`, and §7 lists
the commands. No Neo4j server is available in this environment, so every
Cypher fragment below is illustrative and unexecuted, and no verdict
rests on one. Licences were read at the source: the `neo4j` Python driver
6.4.1 on PyPI (`Apache-2.0 AND Python-2.0`), the Neo4j server repository's
`LICENSE.txt` (GPL-3.0, Community Edition), and neosemantics' `pom.xml`
(Apache-2.0). None of them is load-bearing: the zero-dependency agreement
closes the product path whatever the licence. The rule census in §2 is a
classification by judgment, listed per rule so it can be re-graded.*

*Corrected 2026-10-16: §4's last paragraph twice, by #170 and #171;
the verdict's clause (3), the §1 table's row (3) and §6 item 2 once, by
#171. The ROADMAP's decision log, under the 2026-10-12 knowledge-graph
entry, lists why. These edits add no claim about pumllint's code, which
still rests on `15a517b` and §7; what they say of the Arc E item rests
on that item as corrected on 2026-10-16.*

## 0. Why this ran, and what it is not

This is the sixth record in the thread, and it is short because five
records already carry most of it:

- the knowledge-graph note (2026-08-26): N1–N5 and the four re-litigation
  triggers;
- Linked.Archi (2026-08-27): the seam, and SHACL's binary conformance;
- BPMN (2026-08-27): no, on four grounds;
- the EA ontology stack (2026-09-14): Loop C, and the generated-`.puml`
  hazard;
- the research synthesis (2026-10-12, #168): N3 read at w3.org, an
  Archi→Neo4j article already graded, and Gap 1 and Gap 2.

What is new is the second reading: no record looks at running pumllint's
engine on a model that never was a file. This note is not a Neo4j
evaluation. It is a note on where the product's boundary sits when the
source of truth is a graph.

## 1. Three readings of "run pumllint on Neo4j"

| Reading | Direction | Verdict |
|---|---|---|
| (1) The rules run inside the store, as Cypher or SHACL | pumllint → store, as engine | **No.** Settled (N1, N3). §2 |
| (2) A store-built model runs through pumllint's engine | store → pumllint | **Feasible; recorded shape, adopter-gated, outside pumllint.** §3 |
| (3) pumllint's reports are imported into the store | pumllint → store, as data | **No pumllint build; score and trace reports are evidence only behind Arc E, lint findings not even then.** §4 |

## 2. Reading 1 — the rules inside the store

Settled, and not re-derived here. N1 refuses a graph store on the product
path (scale: 950 elements across the 174-diagram wild corpus, against the
10⁵–10⁶ where a store pays; and the zero-dependency agreement). N3 refuses
OWL/SHACL as the rule engine: a closed-world boolean over a tolerant
projection cannot grade, and it reports every absence it constrains,
including what the projection never read. #168 §3 quotes SHACL §3.6.1.1
and §2.1.4 at the source.

**What the census adds.** Each of the 52 catalog rules was asked one
question: does the defect it reports still exist when the model is a
property graph (typed nodes, typed edges, properties) with no source
text and no diagram as a unit?

| Class | Count | Rules | What a store does with it |
|---|---|---|---|
| **Cannot occur in a store**: an authoring defect of the text | 8 | SEQ001, SEQ003, SEQ004, SEQ010, SEQ101, SEQ108, ACT004, GEN003 | Nothing. A node is never "undeclared", a block is never "unclosed", and there is no skinparam. |
| **Needs the diagram as a unit, or its order and fragment tree** | 13 | GEN001, GEN002, GEN005, GEN008, GEN009, GEN010, SEQ007, SEQ008, SEQ009, SEQ011, SEQ104, SEQ105, SEQ107 | Only if the store models the view itself, with diagram nodes, message order and fragments, and is then a PlantUML model kept in a database. |
| **Transfers as a constraint** | 31 | Topology (9): CLS004, STA001, STA002, UC001, UC003, SEQ002, SEQ006, ACT001, ACT002. Label or property (17): ACT003, ACT005, ACT006, CLS001, CLS002, CLS003, CLS005, GEN004, GEN006, GEN007, SEQ005, SEQ102, SEQ103, SEQ106, SEQ109, STA003, UC002. Cross-node agreement (5): XD001–XD005 | Native constraints, a Cypher query or a SHACL shape via neosemantics. For example, CLS004 is `MATCH p=(c:Class)-[:EXTENDS*]->(c) RETURN c` and UC001 is `MATCH (n:Actor) WHERE NOT (n)--() RETURN n` (illustrative, unexecuted). |

The 31 that transfer are the ones the store's tooling already expresses,
so porting them builds a weaker neosemantics. The 21 that do not transfer
are where the catalog earns its keep: the defects a person writing a file
makes. XD changes meaning on the way in. A store with one node per entity
has already decided identity, so an XD conflict becomes a merge decision
taken before validation, which is the "never merge on similar names"
warning #168 §2 records. The graded verdict (levels, gap report, ratchet)
has no counterpart either way: `sh:conforms` is a boolean.

## 3. Reading 2 — the store feeding the engine

**It works today, measured.** `Engine.lint_diagram(diagram: Diagram)`
(`pumllint/engine.py`) takes an in-memory model, and
`scoring.score(violations, diagram, syntax_ok=…)` scores it. Probe P2
(§7) builds an activity `Diagram` from six rows standing in for
`MATCH (p:Process {id:'P-1'})-[:HAS_STEP]->(s) RETURN s ORDER BY s.seq`:
start, a noun-named action, a decision, an action, an else-branch, and an
action with no stop node. Output at `15a517b`:

```
--- anchor=seq: 3 finding(s)
neo4j://process/P-1:3: [ACT003/minor] Decision '(In stock?)' has an unlabelled 'then' branch — write "then (yes)"
neo4j://process/P-1:5: [ACT003/minor] Unlabelled 'else' branch — write "else (no)"
neo4j://process/P-1:6: [ACT002/major] Activity flow never terminates with 'stop' or 'end' (unterminated flow)
score syntax_ok=True: Level 3 (Disciplined) 77.5/100, elements=6
score syntax_ok=False: Level 1 (Sketchy) 77.5/100, elements=6
--- anchor=none: 3 finding(s)
neo4j://process/P-1:0: [ACT002/major] Activity flow never terminates with 'stop' or 'end' (unterminated flow)
neo4j://process/P-1:0: [ACT003/minor] Decision '(In stock?)' has an unlabelled 'then' branch — write "then (yes)"
neo4j://process/P-1:0: [ACT003/minor] Unlabelled 'else' branch — write "else (no)"
```

Four things the probe shows, each a reason the shape is wrong inside
pumllint:

1. **The structuring step is skipped, silently.** The rows hold a
   decision and a branch with no join. Where the branches meet is not in
   the data, and the engine accepts the flat list. ACT004 cannot fire:
   it reads `diagram.blocks`, which only the parser fills
   (`pumllint/rules/activity/structure.py`, `UnterminatedConstruct.check`).
   An adapter must therefore either invent the nesting, which is invented
   structure, or refuse. Refusing with the node named is aris2puml's
   structuring pass, the whole reason that repository exists, and an EPC
   is the same problem with different node names.
2. **Anchors are invented.** `Violation.file_path` and `line` are
   whatever the builder supplies. Anchored on a `seq` property, "line 3"
   is a store property posing as a line. Unanchored, every finding lands
   on `:0`, and the sort order changes (ACT002 moves first). Everything
   keyed on `(file, line)` loses its referent: the baseline, the language
   server, the sonar export, inline suppressions (which have no carrier
   at all), and the lint schema's own description of `file`, "Source path
   as given to the CLI".
3. **Remediation speaks the notation.** `write "then (yes)"` is PlantUML
   syntax, addressed to someone who never wrote a line of it. Every
   rule's message assumes the reader can edit the file.
4. **The syntax gate can never run.** DIM-SYN is PlantUML's verdict on
   the source, and there is none. The probe shows that the gate decides:
   the same findings score Level 3 when the gate is assumed passed and
   Level 1 when it fails (C2). The disclosure already exists, since the
   score report's `syntaxGateRan: false` (#147) and the text reporter's
   "Syntax gate: not run" carry it, but an adapter would carry it on
   every run, permanently. This is the same family as the 2026-09-14
   hazard, a verdict on content the tool did not read, reached by a third
   route.

**The shape that survives** is the one aris2puml already proves: a
converter that reads the store and **emits `.puml`**, in its own
repository, under the same iron rules. It makes the content checkable and
never makes it pass; it refuses what does not reduce to nested
single-entry, single-exit blocks, with the node named; it preserves
defects rather than repairing them; it records what it dropped in a
sidecar; and its mapping table moves with pumllint's
`docs/business-processes.md` §2. Emitting the file gives back everything
the in-memory route loses: the parser fills `blocks`, lines are real, the
syntax gate runs, remediation addresses the file the converter wrote, and
the artefact is reviewable. Element identity goes back to the store the
way #168's Gap 2 argues it for ARIS: a line → ids map in the converter's
sidecar, not a pumllint field.

*Recorded, not queued. No pumllint checkbox: the build would live outside
this repository, as aris2puml does. Trigger: an adopter whose authored
process or interaction content (steps, actors, messages, written by
people) lives in a graph store, asking for it to be gated. An enterprise
knowledge graph assembled from other tools' exports does not fire it:
that is Loop C, and the gate belongs on the exports' sources.*

## 4. Reading 3 — pumllint's reports in the store

No pumllint code. The `-f json` shapes are the interface, pinned by
`pumllint/schemas/`. The lint report is a bare array of
`{ruleId, severity, message, file, line}`
(`lint.schema.json`, `additionalProperties: false`), and the score and
trace reports carry levels, gap items and coverage. A consumer maps them
on its side, for example (illustrative, unexecuted):

```cypher
// lint.json loaded as $findings
UNWIND $findings AS f
MERGE (a:Artefact {path: f.file})
CREATE (a)-[:HAS_FINDING]->(:Finding {rule: f.ruleId, severity: f.severity,
                                      line: f.line, message: f.message})
```

No Cypher or RDF reporter is warranted. A reporter is a contract
(`-f` values and their shapes), it would have one hypothetical consumer,
and the mapping is a dozen lines on the consumer's side.

**Correction to the chat answer that prompted this note:** "zero build"
was right for pumllint's code and wrong as a claim about value. Imported
this way, a finding names its input by path only. It cannot say which
pumllint version, which configuration or which content produced it
(#168 Gap 1). And when the artefact was generated from a model held
elsewhere, it cannot reach that model's element except by a name join
(Gap 2). A graph of findings is therefore a dashboard, not an evidence
record, until Arc E's *Run provenance in the score and trace reports*
ships — and, for lint findings like the ones imported above, not even
then. Arc E covers the score and trace reports only, and a separate score
or trace invocation cannot lend lint findings provenance. Nothing
recorded gives them any; that is an open question for Arc E's build (the
2026-10-12 record's *Corrected* and *Corrected again* 2026-10-16 notes).
That item's trigger already names this consumer: "a consumer — an
evidence store, a knowledge graph — ingesting them". A question about
one is not that consumer, so the trigger does not fire. The pointer
added to the item makes this reading its concrete shape, which the item
only half serves: score and trace reports, within the limits it names,
and not the lint findings imported above.

## 5. The corporate-semantic-layer framing

The first turn named three artefact families. Each already has a verdict:

- **BPMN process documentation:** no, on four grounds (2026-08-27).
  PlantUML has no BPMN diagram type; `bpmnlint` exists and is this
  product's architectural twin; a BPMN file is the implementation, so
  nothing upstream needs gating; and the one remaining fit, BPMN as a
  codegen carrier, measured badly at W3.
- **UML-based artefacts:** already the product, for the PlantUML subset
  it parses (sequence, activity, class, state, use case). Component and
  deployment are the standing Arc C candidate, census-gated.
- **Customer-journey documentation:** no artefact. PlantUML has no
  journey diagram type, and this repository has never parsed one. A
  journey drawn as an activity diagram is an activity diagram and is
  checked as one. A journey notation would be a metamodel invented here,
  which no gate in either repository permits.

A semantic layer that unifies these is Loop C (2026-09-14). The seam is
unchanged: pumllint runs in the producer repository, on the file a person
wrote, before anything grounds it in an ontology or loads it into a store.

## 6. Decision, recorded shapes, triggers

**Decision: nothing queued, no checkbox, priorities unchanged.** The
critical path stays aris2puml A1b → A4. Open checkboxes stay at 17, all
gated.

**Never build** (each already on record; restated here in this question's
vocabulary):

- pumllint's rules executed in, or ported to, a graph store (N1, N3; §2);
- an in-memory store→`Diagram` adapter inside pumllint (§3: it skips
  structuring, invents anchors and runs ungated);
- a Cypher or RDF reporter (§4: the JSON schemas are the interface).

**Recorded, not queued:**

1. **A store→`.puml` converter**, aris2puml-shaped, in its own
   repository. Trigger: §3.
2. **The findings-import mapping**, a consumer-side recipe and not
   product. Imported score and trace reports can become evidence
   through Arc E's run-provenance item, within the limits it names,
   and its trigger already covers a knowledge-graph consumer; the lint
   findings the recipe imports do not become evidence, even then (§4).

**Annotated in place, as pointers:** the Arc E *Run provenance* item (its
knowledge-graph consumer, given a concrete shape), and the knowledge-graph
settlement's re-litigation line (touched, not fired).

**Re-litigate on** the knowledge-graph settlement's four triggers,
unchanged; none fires. The first, a model set beyond one in-memory batch,
is the one a Neo4j-resident corpus would most plausibly fire, and no such
corpus is named.

## 7. Reproduction

```bash
# at 15a517b
python - <<'EOF'                                   # 52 rules, by applies_to/dimension
import tomllib; c = tomllib.load(open("pumllint/rules/catalog.toml", "rb"))
rules = {k: v for k, v in c.items() if isinstance(v, dict) and "severity" in v}
print(len(rules)); [print(k, v["name"], v["applies_to"]) for k, v in sorted(rules.items())]
EOF
grep -n "def check" -A3 pumllint/rules/activity/structure.py   # ACT004 reads diagram.blocks
python -c "import json; print(json.load(open('pumllint/schemas/lint.schema.json'))['\$defs']['violation']['required'])"
```

Probe P2, run as `PYTHONPATH=. python p2_store_model.py` from the
checkout:

```python
from pumllint.engine import Engine
from pumllint.model import ActivityNode, Diagram, Directive
from pumllint.scoring import score

ROWS = [  # MATCH (p:Process {id:'P-1'})-[:HAS_STEP]->(s) RETURN s ORDER BY s.seq
    {"seq": 1, "kind": "start", "label": ""},
    {"seq": 2, "kind": "action", "label": "Customer order"},
    {"seq": 3, "kind": "decision", "label": "In stock?", "branch_label": None},
    {"seq": 4, "kind": "action", "label": "Ship goods"},
    {"seq": 5, "kind": "branch", "label": "", "branch_label": None},
    {"seq": 6, "kind": "action", "label": "Notify customer"},
]

def build(rows, *, anchor):
    d = Diagram(file_path="neo4j://process/P-1", name="P-1", start_line=1,
                end_line=None, diagram_type="activity")
    d.directives.append(Directive(kind="title", value="Order to cash", line=1))
    for r in rows:
        d.activity_nodes.append(ActivityNode(kind=r["kind"], label=r["label"],
            line=r["seq"] if anchor == "seq" else 0, branch_label=r.get("branch_label")))
    return d

engine = Engine({})
for anchor in ("seq", "none"):
    d = build(ROWS, anchor=anchor)
    vs = engine.lint_diagram(d)
    print(f"--- anchor={anchor}: {len(vs)} finding(s)")
    for v in vs:
        print(f"{v.file_path}:{v.line}: [{v.rule_id}/{v.severity.value}] {v.message}")
    for ok in (True, False):
        r = score(vs, d, syntax_ok=ok)
        print(f"score syntax_ok={ok}: Level {r.level} ({r.level_name}) "
              f"{r.composite:.1f}/100, elements={r.element_count}")
```

The noun-named action draws no finding because ACT006 is dormant until a
verb list or pattern is configured. That is the same on the file path, so
it is not a property of this route.

## Related reading

- [A knowledge graph for pumllint, evaluated](knowledge-graph-evaluation.md):
  N1–N5, the four triggers.
- [Knowledge graphs for architecture and process artefacts — a research synthesis, evaluated](kg-research-synthesis-evaluation.md):
  N3 at the primary, Gap 1 and Gap 2, the Archi→Neo4j article.
- [Linked.Archi and pumllint](linked-archi-evaluation.md): the seam, and
  SHACL's binary conformance.
- [The BPMN ecosystem, evaluated](bpmn-ecosystem-evaluation.md): the four
  grounds.
- [The ontology/graph EA stack, evaluated](ea-ontology-stack-evaluation.md):
  Loop C, and the generated-`.puml` hazard.
- [Linting business processes](business-processes.md) §2: the mapping
  table a store→`.puml` converter would implement.
- aris2puml's README and CLAUDE.md: the iron rules a converter of this
  shape inherits.

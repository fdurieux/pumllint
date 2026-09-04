# Graph checks over diagrams — sense, nonsense, fit, gap, SWOT

*Dated evaluation, 2026-09-04, written against `2b2a805` (v0.30.0). An
externally-prompted analysis under the house discipline, and the second
in the policy-as-code thread. The question as posed: evaluate the sense
and nonsense of extending pumllint's validation with **graph checks of
diagrams** — "checkov?" — with the [policy-as-code
note](policy-as-code-ecosystem-evaluation.md) as the reference; grade
sense, nonsense and SWOT.*

**Verdict up front: three different proposals hide in the question and
they get three different answers. (1) checkov as an engine or
dependency — no, unchanged from the thirtieth note, and now with the
dependency measured: it needs two third-party graph libraries. (2)
checkov's graph-check *vocabulary* as a rule-authoring format — no, and
this note finally sizes the candidate the Semgrep and policy-as-code
notes left unsized: read from its solver source, checkov's only
multi-node primitive is **undirected, one-hop adjacency**, so a
checkov-shaped format reaches at most 31 of 51 rules and exactly three
of the fourteen the knowledge-graph note counted as graph algorithms —
the degree tests. It cannot say *cycle*, *reachable*, *before* or *same
name, different kind*. (3) New graph-shaped **rules** over the model
pumllint already has — reachability on state machines, sinks, orphan
classifiers, dependency cycles, split interactions, actor-reachability
— are decidable, stdlib-only and invent no semantics, **and a prototype
of all six reports nothing over 184 diagrams and 1,473 elements that a shipped
rule does not already report.** The only firings are pile-ons: every
state a traversal would flag sits in a diagram STA001 already fails at
blocker. Recorded as candidates with their measured zero and one design
constraint attached; nothing queued.**

**And the finding that reframes the ask: the artefact class where graph
checks pay — component, deployment and C4 diagrams, the ones that *are*
architecture graphs — is the class pumllint does not parse.** Measured:
a hand-written component diagram is typed `sequence`, draws four false
`SEQ001` criticals and five false `SEQ009`s, and scores Level 3; a
deployment diagram scores Level 4 as a sequence diagram. Graph checks
there are a parser first and a rule pack second, and that parser is the
census-gated Arc C item whose trigger last read **0 of 39**. On the five
types pumllint does parse, the graph checks are either shipped (fourteen
rules) or measured-zero (this note).

**Four measurements carry this note, all reproducible from §12.**

**(1) checkov's connection solver is one hop and direction-blind.**
`BaseConnectionSolver.is_associated_edge` accepts an edge in either
direction; `ConnectionExistsSolver` walks the edge list once and passes
a vertex on the first adjacent vertex of the other type, following at
most one further edge through a module `output`. Operators: `exists`,
`not_exists`, `one_exists`. No path, reachability or cycle primitive
exists anywhere under `checks_infra/solvers/`.

**(2) The catalogue, classified.** Six tiers by what a rule is evaluated
against: node-local 25, aggregate 7, adjacency 6, traversal 3, ordering
5, cross-batch group-by 5. A checkov-shaped format covers the first and
third tiers — **31 of 51 at most** — and none of the other twenty.

**(3) Six candidate graph rules, prototyped, zero net findings.** Over
the repository's 87 diagrams and the 97-unit calibration corpus: state
reachability from `[*]` adds **0** states beyond STA002 on any diagram
with an initial transition, and **5** on two mutation units that have
none — where STA001 already fires; sinks **0**; orphan classifiers
**0** across 19 class diagrams; split interactions **0** across 91
sequence diagrams; use cases unreachable from every actor **0** beyond
UC001.

**(4) The graph-shaped artefacts are mistyped today.** §5.

*Bounds. Every pumllint claim was executed at `2b2a805` with the
neutral config of §12 (GEN006/GEN007 off). **checkov 3.3.16 was
downloaded from PyPI as a wheel and read; it was not executed here** —
the thirtieth note ran it, and nothing below contradicts what that run
showed. Every checkov claim is a quotation from its source, cited by
file. **OPA/Rego, Cypher/GQL and every other reachability-capable
query language were not run**, and §3's sizing is explicitly about
checkov's vocabulary, not about declarative formats in general. The
prototype in §4 is a scratch script, quoted in §12, not a rule. No
GitHub repository was read.*

## 0. What "graph checks" names — three proposals and two asides

The question is short and the noun is overloaded. Pinning it is most of
the analysis, because each reading has its own settled record and its
own verdict.

| # | Reading | What it would add | Settled where |
|---|---|---|---|
| **A** | **checkov as engine or dependency** | a second scanner, or a `checkov`-style runner, over `.puml` | Thirtieth note (2026-08-29): no; zero functional overlap, IaC artefact |
| **B** | **checkov's YAML vocabulary as a rule format** | `cond_type: connection` policies over pumllint's parsed graph — the Spectral note's F2, re-scoped by the thirtieth note to three tiers and left unsized | Spectral / Semgrep / policy-as-code notes: recorded, demand-gated, **unsized** |
| **C** | **new graph-shaped rules over the existing model** | reachability, sinks, orphans, connectivity, direction — written in Python like the 51 that exist | TLA+/Alloy note (2026-08-30): F3/F4 recorded for state diagrams, not queued; nothing for the other types |
| *aside 1* | graph checks on **component / deployment / C4** diagrams | orphan components, layering, package cycles — the checks people usually mean | C4 pack evaluation (2026-07-27): parser first, census-gated |
| *aside 2* | **policy-shaped** connection checks — "every X must connect to a Y", "no actor talks to a database" | checkov's actual strength | Obligation/flow settlement (2026-07-30): ARC001–003 against a declared table, adopter-gated |

A is not re-litigated: §2 adds one measured fact to it. B is where this
note does new work (§2, §3). C is where it measures (§4). The asides
are where the honest answer to the question actually lives (§5, §6).

## 1. What already ships, and where each stop is drawn

The knowledge-graph note established that the parsed model *is* a
labelled property graph and that fourteen rules are already graph
queries over it. What that note did not do — because its question was
about infrastructure — is record **where each of those rules stops**,
which is exactly what a "more graph checks" proposal needs to know.

| Rule | Graph operation shipped | Where it stops, and why |
|---|---|---|
| STA002 | in-degree zero, self-loops excluded | no traversal — *"a cycle disconnected from `[*]` is not reported"*, documented in code and RULES.md; three arguments recorded in the TLA+ note §3 |
| UC001 | degree zero | *"Membership, not reachability"* — a use case linked only to another use case is linked |
| SEQ002 | declared minus edge endpoints | degree, per lifeline |
| UC003 | one-hop actor neighbourhood, then edge direction against it | direction is judged only when exactly one endpoint is actor-connected — no verdict otherwise |
| CLS004 | DFS cycle search | generalization/realization edges only; dependency and association cycles are not examined |
| SEQ009 / SEQ104 / SEQ108 | ordered reverse-edge existence, call/reply pairing, per-lifeline stack | line order, not graph structure; path-insensitive across `alt` branches (the recorded SEQ202 remainder) |
| SEQ107 | edge-inside-block containment | fragment spans, not adjacency |
| XD001–005 | cross-batch group-by on entity name | **nodes, never edges** — the cross-diagram note's headline |

Two stops are structural rather than chosen, and matter for §4:

- **Activity diagrams have no edges in the model.** `ActivityNode` is a
  flat list of nodes — `start`, `stop`, `action`, `decision`, `branch`,
  `swimlane` — with no successor relation. ACT001/ACT002 test for the
  *existence* of terminals, not for flow. There is no graph to check on
  activity diagrams without a parser change, and the BPMN note's
  `no-disconnected` analogue cannot be built there today.
- **Component, deployment and C4 diagrams have no parser.** §5.

## 2. checkov's graph vocabulary, read from source

The thirtieth note executed one checkov connection policy and found it
discriminated correctly; it inferred *"given a resolved graph, a
declarative format can ask relational questions of it"* and left open
*"whether a graph-query format can or cannot express the ordering tier"*.
This section answers the checkov half of that from the code, which the
wheel makes available without running anything.

**What the graph is.** For Terraform, vertices are blocks (resources,
variables, modules, outputs…) and an edge is created for every
attribute value that references another block by name
(`terraform/graph_builder/local_graph.py`, `_build_edges_for_vertex` →
`get_referenced_vertices_in_value` → `_create_edge_from_reference`).
An `Edge` carries `origin`, `dest` and a `label` (the attribute key).
Directed in storage. The store is a `networkx.DiGraph` or a
`rustworkx.PyDiGraph`; **`Requires-Dist: networkx<2.7` and
`rustworkx<1.0.0,>=0.13.0`** are two of the 52 `Requires-Dist` lines in
the wheel's metadata. That is the measured fact added to reading A: the engine
whose graph checks the thirtieth note admired cannot compute them
without two compiled graph libraries, and the zero-dependency working
agreement is not negotiable on the product path.

**What a policy can say.** `checks_parser.py` maps `cond_type` onto five
solver families, which is the entire vocabulary:

| `cond_type` | Solver | Evaluates |
|---|---|---|
| `attribute` | `attribute_solvers/` (~40 operators: `equals`, `regex_match`, `exists`, `within`, `length_*`, `is_true`…) | **one vertex's own attributes** against a literal |
| `resource` | `resource_solvers/` (`exists`, `not_exists`) | whether **any vertex of a type** is present |
| `connection` | `connections_solvers/` (`exists`, `not_exists`, `one_exists`) | **adjacency** between two vertex-type sets |
| `filter` | `filter_solvers/` | narrows the vertex set a check runs over |
| `and` / `or` / `not` | `complex_solvers/`, `complex_connection_solver.py` | boolean composition of the above |

**What `connection` actually computes**, from
`connections_solvers/base_connection_solver.py` and
`connection_exists_solver.py`:

```python
def is_associated_edge(self, origin_type, destination_type):
    return (origin_type in self.resource_types and destination_type in self.connected_resources_types) or (
        origin_type in self.connected_resources_types and destination_type in self.resource_types
    )
```

```python
for u, v in edge_dfs(graph_connector):
    origin_attributes = graph_connector.nodes(data=True)[u]
    ...
    destination_attributes = graph_connector.nodes(data=True)[v]
    if destination_attributes in opposite_vertices:
        self.populate_checks_results(...)      # one hop: pass
        continue
    if destination_block_type == BlockType.OUTPUT:
        ...                                    # exactly one more hop, through a module output
```

Three properties follow, and each one is a rule class it cannot reach:

1. **Direction-blind.** `is_associated_edge` is symmetric, and the edge
   walk passes a vertex whichever end it sits on. STA002's *in*-degree,
   UC003's *include points from base to included*, SEQ009's *reply
   opposite to the call* are all direction questions.
2. **One hop.** A vertex passes on the first adjacent vertex of the
   opposite type; the only second hop is the module-`output`
   indirection. No path length, no closure. CLS004 (a cycle) and a
   traversal STA002 (reachable from `[*]`) need closure.
3. **No order.** Vertices carry attributes and edges carry a label;
   nothing carries a position. SEQ003/SEQ104/SEQ108's stacks and
   pairings are questions about *before* and *after*.

A `grep` over `checks_infra/solvers/` for `reachab`, `transitiv`,
`shortest`, `has_path`, `all_paths`, `bfs`, `dfs` matches nothing but
`edge_dfs` — imported, given a fallback, and used above as an edge
*iterator*. The vocabulary is
attribute predicates plus undirected adjacency, composed with boolean
operators. That is a precise and useful thing to know, because the
thirtieth note's correction — *SEQ001's exact shape, in data* — is
true, and §3 shows how little of the catalogue shares that shape.

## 3. The catalogue, classified — F2 sized

The Semgrep note asked for *"a per-rule classification of the
catalogue"* and *"deliberately does not guess at the number"*; the
policy-as-code note re-scoped it to three tiers and *"deliberately does
not guess the split"*. Having read all 51 `check()` bodies, here is the
split, against the criterion both notes named — **what the rule is
evaluated against** — refined to six tiers because three do not
separate the cases that matter.

| Tier | Evaluated against | Rules | n | In checkov's vocabulary? |
|---|---|---|---|---|
| **T1 node-local** | one node's or one edge's own fields; or the existence of a node of a kind | GEN001 GEN002 GEN003 GEN004 GEN006 GEN007 · SEQ004† SEQ005 SEQ006‡ SEQ007 · SEQ102 SEQ103 SEQ105 SEQ106 · ACT001 ACT002 ACT003 ACT004† ACT005 ACT006 · CLS001 CLS002 CLS003 · STA003 · UC002 | **25** | `attribute` / `resource` — **yes**, given one graph per diagram |
| **T2 aggregate** | a count, ratio or depth over a collection | GEN005 GEN008 GEN009 SEQ008 SEQ011 CLS005 STA001 | **7** | **no** — `length_*` measures one attribute's list, never a vertex set; *exactly one* (STA001) has no operator |
| **T3 adjacency** | degree, or one-hop existence | SEQ001 SEQ002 SEQ010 SEQ101 STA002 UC001 | **6** | `connection` — **yes**, with STA002 losing its direction and its self-loop exclusion |
| **T4 traversal / structure** | closure, direction against a neighbourhood, containment spans | CLS004 UC003 SEQ107 | **3** | **no** — §2 properties 1–2 |
| **T5 ordering** | line-ordered stacks and pairings | SEQ003 SEQ009 SEQ104 SEQ108 SEQ109 | **5** | **no** — §2 property 3 |
| **T6 cross-batch group-by** | same key across diagrams, values compared | XD001 XD002 XD003 XD004 XD005 | **5** | **no** — an attribute solver compares to a literal, not to another vertex |

*† SEQ004 and ACT004 are node-local only because the parser has already
paired each block with its `end_line`; the question underneath is
ordering. ‡ SEQ006 compares two fields of one edge (`source == target`);
checkov's attribute operators compare a field to a literal, so it is T1
in shape and still not expressible as the vocabulary stands. SEQ001,
SEQ010 and SEQ101 are T3 in the thirtieth note's framing — a use vertex
connected to a declaration vertex; in pumllint's model the parser has
already folded that into `Participant.declared`, which makes them
node-local there. Inside the format's reach on either reading.*

**The sizing.** A checkov-shaped format reaches **T1 + T3 = 31 of 51 at
most** (30 with SEQ006 excluded), and **none of the other 20**. Set
against the knowledge-graph note's fourteen "graph algorithm" rules —
CLS004, STA002, UC001, UC003, SEQ002, SEQ009, SEQ104, SEQ108, SEQ107 and
XD001–005 — it reaches **three**: the degree tests STA002, UC001 and
SEQ002. The nine intra-diagram graph rules split 3 / 3 / 3 across
adjacency, traversal and ordering, and the format stops after the first
group.

**What this does to F2.** The policy-as-code note's open bucket —
*"evidence that a graph-query format can or cannot express the ordering
tier"* — is closed **for checkov's format**: it cannot, and it cannot
express the traversal tier either, which that note had placed on the
expressible side under "relational". The honest three-tier statement
becomes: *lexical and node-local, expressible anywhere; adjacency,
expressible over a resolved graph; traversal, ordering and cross-batch,
not expressible in the one graph-query format this series has run.*
Whether a reachability-capable format would do better is a different
question this note did not run — OPA documents a `graph.reachable`
built-in and Cypher has variable-length paths, both read, neither
executed, neither load-bearing.

**Why this matters more than the number.** The thirty rules a
checkov-shaped format could carry are the *least* distinctive part of
the catalogue: naming patterns, empty labels, budgets aside, and the
declaration-versus-use family. The twenty it cannot carry are the
budgets, every traversal and ordering rule, and the whole XD pack.
Adopting the vocabulary would mean adopting a ceiling on precisely the
checks the question asks for more of.

## 4. Candidate graph rules over the existing model — prototyped

Reading C. Each candidate below is decidable from declared edges alone,
invents no semantics (the TLA+ note's §4 distinction, which this note
adopts), is a few stdlib lines, and extends a shipped rule past a stop
§1 recorded. The prototype (§12) computes each one beside the shipped
rule it extends and counts only what is **new**.

| Candidate | Extends | Shape | Repo (87 diagrams) | Corpus (97 units) |
|---|---|---|---|---|
| **G1** state unreachable from `[*]` (traversal) | STA002 (in-degree) | T4 | 3 state diagrams; **0 new** | 11 state diagrams; **5 new** — all on the 2 units with no initial transition |
| **G2** state with no path to `[*]` (sink) | — (TLA+ F4) | T4 | 2 diagrams with a final; **0** | 11 with a final; **0** |
| **G3** declared classifier with no relation (orphan) | UC001's shape, class pack | T3 | 4 class diagrams; **0** | 15; **0** |
| **G3′** cycle over `..>` dependency edges | CLS004 (generalization only) | T4 | **0** | **0** |
| **G4** interaction split into ≥2 components | SEQ002 (degree) | T4 | 43 sequence diagrams; **0** | 48; **0** |
| **G5** use case unreachable from every actor | UC001 (degree) | T4 | 2; **0 new** | 8; **0 new** |
| **G6** lifeline unreachable from every actor | — | T4 | **0** | **0** |

**Read.** Across 184 diagrams and 1,473 elements — every `.puml` this
repository authored plus its own mutation ladders — no candidate finds a
defect a shipped rule does not already name. The five G1 firings are the
instructive case:

```
door_lock_state_good__S-drop_initial.puml:1: [STA001/blocker] State machine has no top-level '[*] -->' initial transition
```

Remove the initial transition and *every* state is unreachable from
`[*]`; a traversal rule would add three `major` findings to a diagram
STA001 already fails at `blocker`, and on the L5 ladder rung two more
beside the STA002 that already fires on `Alarmed`. **A reachability rule
must be silent when STA001 fires** — otherwise the ladder's monotonicity
holds and the density arithmetic still moves the score for one defect
counted four times. That is a design constraint the TLA+ note's three
arguments did not include, and it is the one concrete thing this
measurement adds to F3.

**Two honesty notes.** The corpora are the wrong instrument for finding
these defects and the right one for finding pile-ons: every repository
diagram was written to be clean and every corpus unit is a *single*
mutation of one, so an island or a split interaction is not a shape the
mutation operators produce. The J-F foreign corpus — where the one
edge-shaped defect on record was found (a `..>` pointing the wrong way,
Level 5, 100/100) — is not on disk, and the wild census kept metadata
only. So the zero is *"nothing in any corpus this repository holds"*,
the same scoping the SEQ104 flip measurement was given, and not
*"nothing in the wild"*. And the zero is also the reason the golden
contract could not guard these rules if they shipped: they would join
SEQ102/104/107/109 in firing on no calibration unit.

## 5. The artefact class where graph checks pay is the one not parsed

"Graph checks of diagrams", said by an architect, usually means the
architecture diagram: components and their dependencies, deployment
nodes and their links, C4 containers and `Rel()`s. Orphan components,
layering violations, package cycles, an external system nobody calls —
the C4 review checklist and Structurizr's inspections (orphaned
elements, empty views) are the published oracle for that class, as the
C4 pack evaluation recorded.

pumllint parses none of it. `Diagram.diagram_type` is one of
`sequence | usecase | activity | class | state | unknown`; `model.py` has
no component, node or package type. Measured at `2b2a805` with the §12
neutral config on two hand-written diagrams:

| Input | Typed as | Findings | Level |
|---|---|---|---|
| component diagram — 2 packages, 5 `[components]` + a database, 5 directed arrows, 1 orphan `[Reporting]` | **`sequence`** | **4× SEQ001 critical** (the `[alias]` declarations are invisible, so every arrow endpoint is "undeclared"), **5× SEQ009** (every `-->` reads as a reply with no call), 1× GEN004 | **Level 3 (Disciplined), 78.5** |
| deployment diagram — nested `node`s, a `cloud`, 2 arrows | **`sequence`** | 2× SEQ009 | **Level 4 (Precise), 92** |

Eleven of twelve findings are false in component semantics (the
twelfth, GEN004 on `odb`, is at least a naming finding); the one
planted defect — `[Reporting]`, declared and connected to nothing, the
orphan a graph check exists to catch — is invisible, because the
declaration line is never modelled. This is the C4 pack note's sample C
in raw-component form and another instance of the type-fallback class
the ArchiMate entry carries; it is recorded here as an instance, not a
new candidate.

**Consequence for the question.** On this class, graph checks are a
**parser** — element declarations, `package`/`node` containment, the
arrow family — before they are rules, and that parser is Arc C's
"component and deployment first" item, whose demand instrument is the
census and whose last reading was **0 of 39** on working-project
material. When it fires, the rule pack comes with a published oracle
(the C4 checklist) and the graph checks in it are T3/T4 shapes over a
new model type, in Python, like CLS004. Nothing about checkov is needed
for that, and nothing about it is possible before it.

## 6. Policy-shaped connection checks — the oracle question

checkov's real product is not the graph engine; it is **7,973 shipped
policies**, and they ship because their oracle is external and
published — CIS benchmarks, vendor hardening guides, cloud provider
documentation. *"An instance must be attached to a security group"* is
a rule someone else wrote down, and checkov's job is to evaluate it.

The diagram analogue of that policy — *"every `<<external>>` call needs a
failure branch"*, *"no actor talks to a database directly"*, *"the UI
layer may call the service layer and nothing else"* — has **no CIS**.
Nobody publishes which connections are wrong in a PlantUML sequence
diagram, because the answer is the adopter's architecture. This
repository already reached that conclusion from the other direction on
2026-07-30: the participant-pair sweep was rejected *"regardless of
implementation effort"* for lack of an oracle, and the kept form is a
**declared table** — `[obligations]` (SEQ110–113) and `[architecture]`
layers (ARC001–003) — adopter-gated because the first rows have to come
from someone who owns a modelling standard. SEQ107 is the one
policy-shaped check that ships, and it ships because its oracle is a
*lexicon* (failure vocabulary) rather than a topology.

So the checkov comparison lands where the thirtieth note left it, with
one sentence added: **policy-as-code scales on external oracles, and
for diagrams the oracle is per-adopter by construction**, which is why
ARC001–003 are config-gated and always will be. A "graph policy pack"
with defaults would be manufacturing the convention it claims to check.

## 7. Sense — five true things

**S1. The model is already a graph and fourteen rules already traverse
it** (knowledge-graph note §2; §1 here). Every proposal to "add graph
checks" starts from a substrate that exists and is queried in 3 ms.

**S2. The candidate rules are honest.** They read declared edges, invent
no semantics, and are stdlib-linear — the TLA+ note's category-error
scoping holds for all six (§4). Cheapness is real; it is just not
demand.

**S3. The thirtieth note's correction stands and is now bounded.**
*"Given a resolved graph, a declarative format can ask relational
questions of it"* is true for adjacency and false, in checkov's
vocabulary, for everything past it (§2, §3). Saying where it stops is
better than either the Semgrep note's "lexical only" or an unbounded
"relational".

**S4. The F2 measurement finally exists** (§3) — the per-rule
classification two notes asked for and declined to guess.

**S5. The question points at the right artefact class** (§5). Component
and deployment diagrams are graphs first, and the question is right
that checking them as graphs is what a linter should do. The gap is
upstream of any rule.

## 8. Nonsense — six moves to refuse

**N1. checkov as a dependency, plugin host or runner.** Two graph
libraries among 52 dependencies against a zero-dependency promise; an
IaC artefact with zero functional overlap; a framework whose graph
builders are one-per-IaC-language and would need a `.puml` builder
written from scratch — which is this project's parser, inside someone
else's tool (the Semgrep note's N2, again).

**N2. checkov's YAML shape as the rule format.** §3: it caps the
catalogue at the degree tier and drops twenty rules including every
traversal, every ordering rule and the whole XD pack. Refused on merit
before demand is even consulted — and demand is still absent, unchanged
across four notes.

**N3. "Add G1–G6 because they are cheap."** §4: zero net findings on
every diagram this repository holds, one pile-on hazard found. The TLA+
note's N3 — *cheapness is not demand* — with a measurement attached.

**N4. Inferring missing edges from graph structure.** *"A calls B, B
calls C, nothing calls C directly"* is the participant-pair sweep with a
query language, refused 2026-07-30 regardless of effort and again in the
knowledge-graph note's N4. A graph makes the unanswerable question one
line long.

**N5. A default-on "graph policy" pack.** §6: no oracle, so it would
manufacture the convention. The declared-table form exists, is specced,
and waits for its first rows.

**N6. Reading §5's mistyping as a reason to build the component parser
now.** The motivation reproduces at HEAD, as it did in July; the demand
reading is 0 of 39 and the record is explicit that *"real motivation,
measured-zero demand"* is a park, not a go.

## 9. Fit — graded

| Fit | Verdict |
|---|---|
| **F1** — checkov as engine / dependency / runner | **No.** N1; thirtieth note unchanged; dependency now measured. |
| **F2** — checkov-shaped declarative graph rules (the Spectral F2, third re-scoping) | **No as a format; the candidate is now sized.** ≤31/51, three of fourteen graph rules. Stays recorded on its unchanged adopter trigger — an adopter asking to author project-local rules — but the answer to *that* adopter is a T1 lexicon format, not a graph one. |
| **F3** — G1 traversal STA002, G2 sink (the TLA+ note's F3/F4) | **Recorded, not queued, measured-zero; one constraint added** — gate on STA001. Triggers unchanged. |
| **F4** — G3 orphan classifier, G3′ dependency cycle | **Recorded, not queued, measured-zero.** New to the record as candidates; the class pack has no degree rule and this is its natural one, when a class corpus shows an orphan that survived a gate. |
| **F5** — G4 split interaction, G5/G6 actor-reachability | **Recorded, not queued, measured-zero, and weakest.** A split interaction is a readability smell with no evidence; actor-reachability has no oracle when no actor is drawn. |
| **F6** — graph checks on component / deployment / C4 diagrams | **Parser first; Arc C, census-gated, unchanged.** §5 supplies the raw-component probe the C4 pack note's sample C implied. |
| **F7** — policy-shaped connection checks with defaults | **No.** N5; the declared-table form (ARC001–003, SEQ110–113) is the kept reading and is unchanged. |
| **F8** — activity-diagram flow checks | **Blocked on the model.** No edge relation in `ActivityNode`; a parser change before any rule, and no trigger on record. |

### Fit against declared constraints

| Declared constraint | Where the readings land |
|---|---|
| **Zero runtime dependencies** | F1 fails outright (networkx + rustworkx). F3–F5 pass trivially — stdlib traversals. |
| **Deterministic product path** | Passes for every reading; traversal order is a report-ordering surface, already handled by the engine's sort. |
| **Golden score contract** | F3–F5 would ship with zero calibration firings (§4) — the same blindness recorded for SEQ102/104/107/109, and a reason to require fixtures before any of them lands. |
| **Demand-driven / Arc E bar** | Nothing here has an adopter. F2's constituency is unchanged across four notes; F3's trigger is an adopter reporting an island or a sink. |
| **Claim language** | Unaffected. |

## 10. SWOT

Scope: *extending pumllint's validation with graph checks, in any of the
three readings.*

**Strengths (internal, favourable)**

- The substrate is a graph, documented as one, queried by fourteen rules
  in single-digit milliseconds; adding a traversal is a `check()` of a
  dozen lines with no new machinery.
- The declared-graph argument (TLA+ note §4) holds for every candidate:
  edges are what the author wrote, so no verdict rests on imposed
  semantics.
- The catalogue is now classified by evaluation tier (§3) — the
  measurement two notes asked for — so the next declarative-format
  proposal can be sized in a minute instead of a note.
- The stops are documented where they fall (STA002, UC001, XD) — the
  disclosure discipline the series keeps finding elsewhere and rarely
  finds in the tools it compares against.

**Weaknesses (internal, unfavourable)**

- **Activity diagrams have no edges** in the model; the one diagram type
  whose whole point is flow cannot be flow-checked without parser work.
- **Component, deployment and C4 diagrams have no parser** and are
  mistyped as sequence diagrams today, with false criticals (§5).
- A model-level finding (an island, a split) has no report shape: every
  `Violation` is a line in a file, and the schemas are pinned with
  `additionalProperties: false`.
- The corpora cannot exercise any of G1–G6, so a shipped version would be
  golden-blind from day one.

**Opportunities (external, favourable)**

- None external — no adopter has asked for any reading.
- Internal: if the C4/component census ever fires, the graph checks come
  with an externally authored oracle (C4 checklist, Structurizr
  inspections) and land as ordinary rules on a new model type — the one
  place "graph checks" and "published convention" coincide.
- Internal: the F2 sizing turns a recurring proposal into a lookup.

**Threats (external, unfavourable)**

- **The no-oracle temptation** (N4), which a graph vocabulary makes
  cheaper to fall into — the knowledge-graph note's most likely threat,
  restated for rules rather than stores.
- **Pile-on scoring** (§4): a traversal rule without a STA001 gate
  counts one defect four times through the density formula.
- **A vocabulary ceiling**: a format adopted from IaC would freeze the
  catalogue at the degree tier (N2).
- **Dependency creep by analogy**: "checkov does it with networkx" is
  exactly the sentence the zero-dependency agreement exists to refuse.

## 11. Decision, recorded candidates, triggers

**Decision: no checkov — as engine, dependency, runner or rule format;
no graph store or graph library; no new graph rule queued. The
policy-as-code note's verdict is unchanged and its open F2 bucket is
closed for checkov's vocabulary. Nothing in the plan changes.**

**Never build:**

- A checkov dependency, plugin, runner or `.puml` graph builder (N1).
- A rule-authoring format whose multi-node vocabulary is one-hop
  adjacency (N2) — it would cap the catalogue below what ships.
- Missing-edge inference (N4), already twice refused.
- A default-on connection-policy pack (N5).
- Any graph-derived metric in the score without a wave under charter §10
  discipline (knowledge-graph note, N5).

**Recorded, not queued:**

1. **F2 sized** (§3): six tiers, 25/7/6/3/5/5; a checkov-shaped format
   reaches ≤31 of 51 and three of the fourteen graph rules. The Semgrep
   and policy-as-code entries should be read with this attached; the
   policy note's "ordering tier" bucket is answered for checkov and left
   open for reachability-capable formats that were not run.
2. **G1 gate constraint** (§4): any traversal rule on state diagrams is
   silent when STA001 fires. Attaches to the TLA+ note's F3.
3. **G3 / G3′** — orphan classifier and dependency-edge cycle on class
   diagrams: new candidates, measured-zero, same trigger class as F3.
4. **G4 / G5 / G6** — split interaction and actor-reachability: recorded
   so they are not re-derived; weakest of the set (F5).
5. **The raw-component probe** (§5) as an instance of the type-fallback
   class — attaches to the ArchiMate candidate and the C4 pack note's
   sample C; not a new candidate.
6. **"No CIS for diagrams"** (§6): the sentence to cite when a
   policy-as-code analogy is next proposed — external oracles are why
   checkov ships 7,973 defaults and why ARC001–003 cannot ship any.

**Re-litigate on:**

- An adopter reporting an island, a sink, an orphan classifier or a
  split interaction that pumllint passed — the same trigger the TLA+
  note wrote, now covering G3–G6 too.
- The component/C4 census trigger firing — graph checks on that class
  arrive with the parser, not before it.
- A reachability-capable declarative format (Rego's `graph.reachable`,
  Cypher) run here against the T4/T5 rules — the only thing that would
  reopen the format half of F2 above the adjacency tier.
- An adopter with a modelling standard supplying the first
  `[architecture]` rows — ARC001–003's trigger, unchanged since
  2026-07-30.

## 12. Reproduction

All pumllint probes run from the repository root at `2b2a805`, with
`PYTHONPATH=$PWD` and:

```toml
# neutral.toml — switch off the repo's own convention-gated rules
[rules]
GEN006 = false
GEN007 = false
```

| Probe | What it establishes | Command |
|---|---|---|
| M1 | checkov's connection solver is symmetric and one-hop | `pip download checkov==3.3.16 --no-deps`; unzip; read `checkov/common/checks_infra/solvers/connections_solvers/{base_connection_solver,connection_exists_solver}.py`; `grep -rniE 'reachab\|transitiv\|shortest\|has_path\|all_paths\|bfs\|dfs' checkov/common/checks_infra/solvers` → nothing but `edge_dfs` |
| M1′ | the dependency | `grep -E '^Requires-Dist: (networkx\|rustworkx)' checkov-3.3.16.dist-info/METADATA` |
| M2 | the catalogue split | read `pumllint/rules/**/*.py` against §3's tier definitions; the table is the record |
| M3 | G1–G6 over repo + corpus | `python tools/gen_corpus.py /tmp/corpus`, then the probe below |
| M4 | the two G1 units are STA001 failures | `pumllint -c neutral.toml /tmp/corpus/mutations/door_lock_state_good__S-drop_initial.puml /tmp/corpus/mutations/door_lock_state_good__L5.puml` → `STA001/blocker` on both |
| M5 | component and deployment diagrams typed `sequence` | `pumllint -c neutral.toml probe/`; `pumllint score -c neutral.toml probe/` on the two diagrams described in §5 |

The M3 probe, condensed to the three candidates that carry the argument
(the full script also computes G2, G3′, G5 and G6 the same way):

```python
import collections, glob
from pumllint.parser import parse_file

def reach(start, adj):
    seen = set(start); stack = list(start)
    while stack:
        n = stack.pop()
        for m in adj.get(n, ()):
            if m not in seen:
                seen.add(m); stack.append(m)
    return seen

for f in sorted(glob.glob("**/*.puml", recursive=True)):
    for d in parse_file(f):
        if d.diagram_type == "state":                       # G1 vs STA002
            adj = collections.defaultdict(set)
            for t in d.transitions:
                adj[t.source].add(t.target)
                if t.container and t.source == "[*]":       # a composite's inner [*]
                    adj[t.container].add(t.target)
            targeted = {t.target for t in d.transitions if t.source != t.target}
            indeg0 = {s for s in d.states if s not in targeted}
            island = set(d.states) - reach(["[*]"], adj) - indeg0
            if island: print(f, "G1 beyond STA002:", sorted(island))
        elif d.diagram_type == "class":                     # G3
            deg = collections.Counter()
            for r in d.class_relations:
                deg[r.left] += 1; deg[r.right] += 1
            orphans = [n for n, c in d.classes.items() if c.declared and not deg[n]]
            if orphans: print(f, "G3 orphan classifier:", orphans)
        elif d.diagram_type == "sequence":                  # G4
            und = collections.defaultdict(set); nodes = set()
            for m in d.messages:
                if m.source and m.target:
                    und[m.source].add(m.target); und[m.target].add(m.source)
                    nodes |= {m.source, m.target}
            comps, seen = 0, set()
            for n in nodes:
                if n not in seen:
                    comps += 1; seen |= reach([n], und)
            if comps > 1: print(f, "G4 split interaction:", comps)
```

Output at `2b2a805` over the repository's 72 files (87 diagrams, 552
elements) and the 97 corpus units (921 elements): two G1 lines, one for
each of the two units named in §4, and nothing else.

Suites, unchanged by this note (documentation only):

```
python tests/run_tests.py   →  606/606 passed
python -m pytest            →  728 passed
```

## Related reading

- [The policy-as-code ecosystem, evaluated](policy-as-code-ecosystem-evaluation.md)
  — the note this one returns to; its correction stands and its open
  "ordering tier" bucket is answered here for checkov's vocabulary.
- [Semgrep and rules-as-data, evaluated](semgrep-rules-as-data-evaluation.md)
  — where the per-rule classification was asked for; §3 is that
  classification.
- [The TLA+ / Alloy ecosystem, evaluated](tlaplus-alloy-ecosystem-evaluation.md)
  — F3/F4 and the declared-graph distinction §4 adopts; the STA001 gate
  constraint attaches there.
- [A knowledge graph for pumllint, evaluated](knowledge-graph-evaluation.md)
  — the "fourteen rules are already graph algorithms" count §3 splits
  by tier, and the no-oracle threat §8 restates.
- [Cross-diagram relationships in pumllint, evaluated](cross-diagram-relationships-evaluation.md)
  — nodes-never-edges, the one graph check with a foreign-corpus defect
  behind it, already recorded in Arc C and untouched here.
- [Would a C4-PlantUML rule pack fit?](c4-pack-evaluation.md) — the
  parser-first argument §5 rests on, and the published oracle a
  component-class graph pack would have.
- [ROADMAP.md](../ROADMAP.md) — the obligation/flow settlement
  (ARC001–003, the declared-table form §6 defers to), the Arc C
  component/deployment item, and the working agreements.

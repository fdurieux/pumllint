# The EA ontology stack in the SDLC: a value-stream assessment

*Audience: IT management, enterprise-architecture leads, transformation
and governance owners. No familiarity with semantic-web technology is
assumed — every technical term is introduced in plain language as it
first appears. Structure mirrors its companion,
[pumllint in the SDLC](value-in-the-sdlc.md): a two-page executive
brief, then the full assessment, then a practice-domain-level mapping as
an appendix. **What is assessed here is not this repository's tooling.**
It is an enterprise-architecture approach set out in an adopter's own
nine-slide deck — enterprise models lifted into a knowledge graph,
architecture principles expressed as machine-checkable rules, and the
result queried, reasoned over and offered to domain experts through a
language model. The deck's fit against this project's two roadmaps was
settled separately in
[The ontology/graph EA stack, evaluated](ea-ontology-stack-evaluation.md);
that note answers "does either tool belong in these flows" (no). **This
one answers a different and larger question: where in a delivery value
stream does the approach itself pay, and what would have to be true for
it to pay there.***

**How to read the claims.** The tag vocabulary is the companion
document's, in decreasing order of strength:

- **[measured]** — backed by a controlled experiment or a census over a
  real population, with the population named.
- **[mechanism]** — a concrete causal chain exists, but it has not been
  measured inside an organisation.
- **[hypothesis]** — plausible and worth testing; treat as unproven.

**One warning about the tags that does not apply to the companion
document, and it is the most important sentence on this page.** In the
companion, the strongest claims are [measured] *of the thing being
assessed* — over 500 runs of the tool under test. **Here, no claim is
[measured] of this architecture, because this architecture has not been
run.** Where [measured] appears below, it labels a measurement of a
*comparable* pipeline — a model-transformation census, or an experiment
about language models reading architecture artefacts — and each one says
explicitly what transfers and what does not. Treat a transferred
measurement as a well-grounded prior, never as a result about your
estate. Producing results about your estate is what
[the pilot](#pilot-getting-your-own-numbers-in-the-right-order) is for,
and its first phase exists precisely to replace these priors.

---

## Executive brief

**What this is about.** Large organisations describe themselves in
models: which business capabilities exist, which processes realise them,
which applications support those processes, which servers and networks
those applications run on. **ArchiMate** is the standard notation for
that description, and the models usually live in a modelling tool such as
Archi. Today those models are read by people. The approach assessed here
converts them into a form machines can reason over — a **knowledge
graph**: a database that stores facts as linked statements ("this
application *supports* that process") rather than as rows in tables, so
that a question like "what breaks if this server goes away" can be
answered by following links rather than by asking an expert. On top of
the graph sit two further layers: an **ontology**, which defines what the
concepts mean and how they may legally connect, and **constraint rules**
(the standard for these is called SHACL), which check that the stored
facts obey both the notation's own metamodel and the organisation's
architecture principles. The output is an automated validation report.
Domain experts then converse with the whole thing through a language
model in their own vocabulary.

**Why the approach is serious.** Three things distinguish it from the
usual "let's build an architecture repository" proposal.

1. **The rules it would enforce are already written down.** ArchiMate's
   specification contains a table stating, for every ordered pair of
   element types, which relationships are permitted — **over 3 800
   element-relationship-element rules**, plus twenty derivation rules
   that say when a relationship may be inferred from others. These are
   not house opinions to be invented and defended; they are a published
   standard, and a public formalisation of them into machine-checkable
   shapes already exists. [measured — the count is from a published
   formalisation of ArchiMate 3.2, not from this estate]
2. **It targets checks that no document-level tool can perform.** Whether
   a *view* uses only the elements its *viewpoint* permits, whether an
   application realises a capability that no-one owns, whether a change
   to one node reaches a regulated process three hops away — none of
   these is decidable from any single diagram. They are properties of the
   estate, and only an estate-level store can see them. [mechanism]
3. **Its strongest use case is genuinely strong.** Multi-hop impact and
   root-cause analysis over a dependency graph is the one capability in
   the deck that nothing else in a normal delivery toolchain provides.
   [mechanism]

**Where the value lands**, mapped to the four aspects of the
[SAFe Continuous Delivery Pipeline](https://framework.scaledagile.com/continuous-delivery-pipeline):

| Aspect | The EA stack's role | Strength |
|---|---|---|
| **Continuous Exploration** | Its home. Architecture principles and notation legality become mechanical checks instead of review rounds; one vocabulary across domains; derivation makes the consequences of a design decision computable | Direct [mechanism] |
| **Continuous Integration** | **Nothing, as drawn.** No slide places a check in a pipeline, and the deliverable is named *Validation Report* — a report, not a gate. This is the approach's largest gap and its cheapest fix | **Absent** |
| **Continuous Deployment** | Where a graph beats a document. Impact analysis before a change, root-cause traversal during an incident, and conformance of what runs to what was declared | Direct at incident response, supporting elsewhere [mechanism] / [hypothesis] |
| **Release on Demand** | Standing, queryable evidence that the architecture of record is legal and principle-conformant — worth more in a regulated setting than anywhere else | Supporting [mechanism] |

**The shape of that table is the finding.** Value concentrates at the two
ends of the pipeline — where intent is formed, and where consequences are
felt — with a hole in the middle, at the exact point where an
organisation's existing automation already runs on every change. The hole
is not inherent to the approach. It is an artefact of the deck stopping
at *report*.

**The one risk that outranks every other.** Every step in this
architecture is a transformation, and **every transformation silently
drops what it cannot represent**. If three-fifths of the estate arrives
in the graph, then a validation report saying "no violations" means "no
violations among the three-fifths that arrived" — and nothing in the
nine slides measures, publishes or even names that fraction. A closely
comparable pipeline was censused over two public model collections and
converted **74.0 %** and **46.0 %** of them; restricted to models
substantial enough to be worth checking, the first figure falls to
**46.2 %**. Those are different notations and a different transformation,
so they are a *prior*, not a prediction — but the mechanism is
notation-independent, and it means the first number this programme should
produce is not how many principles it can check. It is **what fraction of
the estate arrives, and what was dropped**. [measured, on a comparable
pipeline — see [the coverage denominator](#the-risk-that-outranks-the-others-the-coverage-denominator)]

**Cost, stated plainly.** This is not a free tool that switches on in a
build file. It is a system: a triple store or graph database to operate,
an ontology to author and keep current as the ArchiMate standard moves
(the standard moved in April 2026, cutting its element set from 61 types
to 40 — a re-formalisation, not a patch), principles to formalise,
constraint shapes to write and maintain, an import pipeline to keep
faithful, and — if the language-model layer is in scope — model
consumption to fund and govern. The skills are specialised and thin in
most organisations. None of that argues against it; it argues for sizing
it honestly and for staging it so that each stage earns the next.

**The ask.** Approve a four-phase pilot whose **first phase validates
nothing**. Phase 0 imports one domain's models and publishes the coverage
figure and the dropped-element list — the denominator under every later
claim. Phase 1 takes a *single* principle end to end and measures how
many of your principles are decidable from the model at all. Only then do
phases 2 and 3 add a gate and a use case. The order is deliberate:
starting with principles produces a number nobody can interpret; starting
with coverage produces the number that tells you whether the rest is
worth building. See
[the pilot](#pilot-getting-your-own-numbers-in-the-right-order).

---

## The full assessment

### Method, and two conditionals to test first

Three choices frame this assessment, and they are the companion
document's.

**The unit of analysis is the development value stream** — the flow of
work from idea to released value — rather than a component list. For each
stage the question is: what architecture-related waste occurs here today
(rework, waiting, defects, stale inventory), what would this approach
change, through which mechanism, moving which flow metric?

**The structure is SAFe's Continuous Delivery Pipeline.** Its four
*aspects* — Continuous Exploration, Continuous Integration, Continuous
Deployment, Release on Demand — are the closest thing SAFe has to SDLC
phases. The sixteen activities inside them are the *practice domains*
assessed by the SAFe DevOps Health Radar; the
[appendix](#appendix-the-sixteen-practice-domains) maps every one,
including those where the approach has nothing to offer.

**Claims stay inside the evidence**, per the tag vocabulary above and the
warning attached to it.

And two conditionals, both of which a pilot can settle cheaply:

**Conditional 1 — the estate is complete and current enough that
conclusions drawn from the graph are conclusions about the enterprise.**
This is the coverage question, and it is treated at length
[below](#the-risk-that-outranks-the-others-the-coverage-denominator). An
architecture repository that describes two-thirds of the landscape is a
perfectly good repository and a dangerous oracle, and the difference
between the two is entirely whether the missing third is *stated*.

**Conditional 2 — enough architecture principles are decidable from the
model alone.** A principle such as *"every application component has a
named owner"* is decidable: the fact is either in the model or it is not.
A principle such as *"applications are bought before they are built"* or
*"solutions favour the strategic platform"* is not decidable from a
structural model at all — deciding it needs procurement records,
exception registers, or judgment. Nobody knows the ratio in your
principle catalogue until someone classifies it, and **that
classification is a week of one architect's time and the single
highest-value thing to do before committing to this architecture.** If
the answer is that eight of forty principles are mechanically decidable,
the approach is still worth building — but it is worth building for
*those eight plus impact analysis*, which is a very different business
case from *automated architecture governance*. [hypothesis]

### Continuous Exploration — where intent is formed, and the approach's home

*CE is the aspect in which needs become prioritised solution intent; its
practice domains are Hypothesize, Collaborate & Research, Architect and
Synthesize. Enterprise models are the Architect activity's principal
written output.*

The waste, today: architecture principles are enforced by review. A
design goes to a board, a human reads it against a principle catalogue,
and a judgment comes back days later — inconsistently, because different
reviewers weigh differently and because nobody can hold forty principles
and a thousand-element landscape in their head at once. Meanwhile the
notation's own legality rules are enforced by whichever modelling tool
the author happened to use, and the models that arrive by import or from
a supplier are enforced by nothing at all.

What changes:

- **Notation legality becomes mechanical and total.** The 3 800-odd
  permitted-relationship rules are enforced uniformly over the whole
  estate rather than per-tool at authoring time. The gain is not in the
  well-tooled centre — a modeller using a mature tool is already
  prevented from drawing an illegal relationship — but at the **edges**:
  imported models, supplier deliverables, migrated repositories, and
  anything hand-assembled. [mechanism]
- **Decidable principles become checks instead of review rounds.** For
  the subset that conditional 2 identifies, a violation is found in
  seconds, uniformly, and at the moment the model changes rather than at
  the next board. Review time is freed for the principles that genuinely
  need judgment — which is the better use of a board and the harder
  argument to make without a tool like this. [mechanism]
- **One vocabulary across domains, which is the quiet structural win.**
  The deck shows five expert personas — banking-architecture, solution
  architecture, security, service management, DevOps — each with its own
  terminology. An ontology is, before anything else, an agreement about
  what words mean and which concepts are the same concept. Aligning
  a banking reference model's service domains with the architecture
  model's application components is the kind of work that pays for a
  decade and is nearly impossible to justify on its own; an ontology
  programme is a legitimate vehicle for it. [mechanism]
- **Derivation makes consequences computable.** ArchiMate defines
  rules for when a relationship may be inferred from a chain of others.
  Applied mechanically, "which business processes does this server
  ultimately support" stops being an analyst exercise and becomes a
  query. This is the capability that most distinguishes the approach
  from any document-level tooling. [mechanism]

**The honest qualifier on this aspect**, and it will disappoint whoever
sponsors the programme: none of the above says anything about whether the
architecture is *good*. Legality, principle conformance and derivation
are all properties of the *description*. A landscape can be fully legal,
fully principle-conformant and a poor design. The deck's own diagram
concedes this, and says so more precisely than most vendors would: its
knowledge pyramid brackets the layers as *Know What*, *Know How* and
*Know Why*, and everything the validation report produces sits in the
first two. [mechanism]

### Continuous Integration — the gap, and the cheapest fix in this document

*CI's practice domains are Develop, Build, Test End-to-End and Stage.
This is the aspect where an organisation's existing automation runs on
every change — and **not one of the nine slides places anything here**.*

Two fairness notes before the finding. The deck does say *automated
validation* and *architecture governance automation*, and both are
accurate descriptions of what it builds — but **automation is not a
gate**: a check that runs by itself and a check that a change must pass
are different instruments with different effects on behaviour. And if a
pipeline step already exists and simply did not reach the slides, this
section is satisfied already and its recommendation is moot — which is
worth one question to the team rather than an assumption either way.

Taking the deck at face value, the approach as drawn produces a
**Validation Report**. A report is read
by whoever chooses to read it. Every organisation that has tried to run
architecture governance on circulated reports has learned the same
lesson: reports inform the diligent and are invisible to everyone else,
and a finding that blocks nothing is a finding that ages.

The fix is small and does not require rethinking anything:

- **Give the validation run an exit code and put it in a pipeline.** Any
  constraint validator can return non-zero when it finds a violation.
  That single change converts the report from a circulated document into
  a step that a change has to pass — the same move that source-code
  quality tooling made two decades ago and that nothing about
  architecture makes inapplicable. [mechanism]
- **Then solve the brownfield problem, which is why gates like this
  usually fail.** Constraint validation as standardly implemented is
  **binary**: a model set either conforms or it does not. Point a binary
  gate at a real estate on day one and it fails on thousands of
  pre-existing violations, so it is switched to advisory, and advisory is
  where it stays. The countermeasure is worth borrowing wherever it comes
  from: **record today's violations as an accepted baseline and fail only
  on new ones**. Adoption then costs no clean-up project and the estate
  can only improve. This is a property the approach does not have as
  drawn, and it is the difference between a gate that survives contact
  with an organisation and one that does not. [mechanism]
- **Report progress as a graded position, not a yes/no.** A binary
  validator cannot say "this domain is close" or "three violations from
  compliant", so it cannot motivate anyone. A count, a trend and a
  per-domain breakdown cost nothing beyond the query already being run,
  and they are what a management audience can act on. [mechanism]

If only one recommendation from this document is adopted, it should be
this aspect's, because it is the one that decides whether the rest of the
architecture changes behaviour or merely describes it.

### Continuous Deployment — where a graph genuinely beats a document

*CD's practice domains are Deploy, Verify, Monitor and Respond. The
companion document's assessment of a diagram linter refuses to claim
anything here. A knowledge graph is a different proposition, and this is
the aspect where the extra machinery earns its cost.*

- **Impact analysis before a change. [mechanism]** "What does this
  decommissioning touch" is a graph traversal — and traversal over stored
  relationships is exactly what the storage layer is for. Done by hand it
  is an analyst-days task per significant change, done imperfectly,
  repeated for every change. This is the clearest return in the deck and
  the easiest to measure in a pilot.
- **Root-cause traversal during an incident. [mechanism]** The deck lists
  root-cause analysis as a use case, and during an incident the question
  is the inverse traversal: from a failing component to the business
  services affected, and to what else shares the dependency. Its value
  depends on a property nothing in the slides guarantees — that the graph
  is current at the moment of the incident. An architecture repository
  refreshed quarterly answers incident questions about last quarter.
  [hypothesis, and the pilot should test the refresh interval, not the
  query]
- **Conformance of what runs to what was declared. [hypothesis]** The
  deck names this as gap analysis between a *declarative* and a *running*
  digital twin. It is a genuine and valuable question, and it is also
  the most expensive thing on the slides: it needs a trustworthy
  observed-state feed — discovery tooling, a CMDB that is actually
  accurate, or process-mining event logs — and the quality of that feed,
  not the graph, is what decides whether the answer is meaningful. Size
  this one separately and late.
- **Deploy: no claim.** Nothing here participates in deploying software.

### Release on Demand — governance, and the strongest case in a regulated setting

*RoD's practice domains are Release, Stabilize, Measure and Learn.*

- **Architecture evidence becomes a standing property rather than a
  pre-audit scramble. [mechanism]** In a regulated organisation, the
  ability to answer "show me that your architecture of record is complete
  and conforms to your stated principles, and show me the check that
  proves it" is worth real money in audit effort — and a queryable,
  continuously validated graph is a better answer than a folder of
  approved documents. This is the single most fundable claim in the deck
  for a bank, and it is the one to lead the business case with.
- **Architecture health becomes measurable. [mechanism, with a warning]**
  Violation counts, conformance by domain and trend over time add a
  number to the Measure activity that most organisations lack. The
  warning is twofold and both halves matter. First, **a metric over an
  incomplete graph measures the import, not the estate** — a conformance
  percentage that rises because coverage fell is the failure mode to
  design against, and publishing coverage beside every conformance figure
  is the containment. Second, **any architecture metric that becomes a
  managed target stops measuring anything**: the cheapest way to clear a
  violation is to change the model, and a model changed to clear a
  violation is a model that no longer describes the enterprise. Report
  conformance beside coverage and beside change volume, never alone.
- **Derived findings are a ready-made architecture backlog. [mechanism]**
  Violations enumerate themselves, with the offending element named —
  which is prioritisation already done, in the same way a gap report is.

### The risk that outranks the others: the coverage denominator

This section is the one whose recommendation costs a week and changes the
whole programme's credibility, so it is set out in full.

**The mechanism.** The architecture has at least three transformations in
series: modelling tool → interchange file → ontology instance data →
inferred graph. Each is a *projection*: it carries what it can represent
and drops what it cannot. Drops are rarely errors; they are usually
correct decisions by the transformation author about constructs with no
target representation. The problem is not that they happen. **The problem
is that a dropped element and an element that was never modelled are
indistinguishable downstream.** A constraint that says "every application
component must have an owner" finds no violation for a component that
never arrived — so incompleteness reads, in the report, exactly like
compliance. This is not a hypothetical failure mode of validation over
imported data; it is the standard one.

**The prior, and its limits.** A pipeline of comparable shape — a
structured business-process notation transformed into a checkable target,
then validated — was censused over two public model collections:

| | Models | Arrived in the checkable form |
|---|---|---|
| A vendor reference model collection | 604 | **74.0 %** |
| An academic model collection | 4 332 | **46.0 %** |
| The same vendor collection, restricted to models substantial enough to be worth checking (≥ 5 activities and ≥ 1 branch point) | 160 | **46.2 %** |
| The same, requiring that nothing was approximated in translation | 160 | **20.6 %** |

[measured — public corpora, a different notation and a different
transformation. **What transfers** is the shape: a headline coverage
figure well under 100 %, and a *substantially* lower figure once trivial
models are excluded and once faithfulness rather than mere arrival is
required. **What does not transfer** is any specific percentage: ArchiMate
into RDF is a structurally easier transformation than process control-flow
into a block-structured target, and should do better. How much better is
exactly what Phase 0 measures.]

The third row is the one to dwell on. **The headline figure was carried
by trivial models** — the median converted model had two activities — so
reading it as coverage of the things worth checking was off by roughly a
factor of three. Any coverage number this programme publishes should be
reported the same way: overall, and restricted to the models that carry
enough content to be worth validating.

**The recommendation, in one sentence.** Make the import produce a
**fidelity account** alongside the data — per source model, what arrived,
what was dropped, what was approximated, and what was refused outright —
publish the resulting coverage percentage beside every validation
result, and treat that percentage as the denominator of every claim the
programme makes. It costs a counter in the transformation and a column in
a report, and without it the validation report's central number cannot
be interpreted at all. [mechanism]

### The language-model layer, assessed separately

The deck's platform slide places domain-expert personas in conversation
with a language model over the knowledge base, promising *trustable
conversation in their own terminology*. Three observations, kept apart
from the rest because the evidence here is of a different kind.

**1. The direction of dependency is one-way, and it is the right way
round.** A language model reading a governed, validated graph is a
*consumer* of architecture quality. Nothing about the conversation makes
the underlying facts more true; the conversation's trustworthiness is a
property of the pipeline beneath it. That is a compliment to the
architecture — the graph is placed where it belongs, underneath — but it
also means **the conversational layer cannot be the pilot's first
deliverable**, because it will appear to work regardless of the data's
quality, which is precisely why it makes a poor test.

**2. Letting the model write back into the graph is a different
proposition, and the measured evidence is discouraging.** In controlled
experiments in this repository's evidence base, when a language model was
asked to *repair* under-specified architecture artefacts by supplying the
missing content, executed correctness of the result fell by about **6
percentage points** against leaving the artefacts alone (−5.9 pp
pooled), and by **53 points** on one artefact, from one invented rule. The
same repair loop, changed only to *ask the artefact's owner* rather than
guess, recovered almost all of it — a gap of about **27 percentage
points**. The design rule that follows is specific and cheap to adopt:
**structure to the machine, content to the people who own the intent.**
Let the model propose, normalise, translate and retrieve; never let it
supply a fact the estate did not contain. [measured — on architecture
diagrams and generated code, not on an RDF graph; what transfers is the
failure mode of invention under-specification, which is
representation-independent]

**3. Judge it by execution, not by impression.** The same evidence base
found that model-as-judge assessments of quality correlated only weakly
with what happened when the work was actually run — and not at all across
vendors — while two judges agreed comfortably with each other. **Two
judges agreeing is reliability, not validity.** If the programme evaluates
its conversational layer, evaluate it on tasks with checkable answers —
"which services does this node support", verified against the graph —
not on whether the answers read well. [measured]

### Costs, frictions, and how they are contained

The cost side here is substantial and should be presented as such; a
business case that hides it will be found out at the first budget review.

- **Standing operational cost.** A store to run, an import pipeline to
  keep working, and a reasoner whose behaviour at estate scale has to be
  managed. Unlike a file-level checker, this does not switch on in a
  build file and it does not stay switched on for free.
- **Ontology maintenance, and standard drift.** The formalisation has to
  track the notation. **ArchiMate 4 was published in April 2026 and cut
  the element set from 61 types to 40**, merging the per-layer behavioural
  elements and removing six others. The most complete public
  formalisation available today targets 3.2. Whichever edition the
  programme picks, a future edition will impose this cost again — so
  budget the re-formalisation as a recurring line, and pick the edition
  deliberately rather than inheriting it from whichever artefact was
  found first. [measured — published release, characterised from The Open
  Group's own release material]
- **Staleness that still looks authoritative.** The dominant documented
  failure mode of knowledge-graph programmes is not that the graph is
  wrong on day one but that it silently stops being current while
  continuing to answer questions with full confidence. The containment is
  a freshness indicator carried with every answer — the date of the
  import the answer rests on — and it is far cheaper to design in now
  than to retrofit after the first wrong answer in an incident.
- **Principle formalisation effort, and the rewriting trap.** Turning
  prose principles into constraint rules is careful work, and it has a
  specific hazard: when a principle turns out to be undecidable, the
  temptation is to *redefine the principle* into something checkable. The
  organisation then governs what it can measure instead of what it meant.
  Conditional 2's classification exists to make that trade explicit
  rather than accidental.
- **Neutrality asserted rather than designed.** The deck states three
  neutrality properties — vendor-neutral format, notation-edition
  compliance, and language-model independence — and names a specific
  product beside each. That is not an objection to any of the three
  choices; it is an observation that a property claimed without a
  mechanism tends not to survive the second year. If neutrality is
  load-bearing for the business case, each of the three needs an
  explicit preservation mechanism — an export format, an edition policy,
  an abstraction boundary — and those are design work, not
  procurement decisions.
- **Skills concentration.** Ontology engineering, constraint authoring
  and graph operations are specialised, and in most organisations sit
  with very few people. The single-expert dependency is a programme risk
  in its own right and is worth naming in the risk register on day one.

### Pilot: getting your own numbers, in the right order

Every [mechanism] above is a hypothesis about *your* estate. The
sequencing below is the assessment's main practical recommendation, and
its first phase deliberately validates nothing.

| Phase | What happens | What you learn | Rough size |
|---|---|---|---|
| **0 — Coverage** | Import one domain's models end to end. Produce no validation at all. Publish: how many source models went in, how many arrived, what was dropped or approximated and why, and the same figures restricted to models substantial enough to matter | **The denominator.** Whether the graph can represent your estate, and what it systematically loses. Every later number is uninterpretable without this one | Days |
| **1 — Decidability** | Classify the principle catalogue into *decidable from the model*, *decidable with one extra data source*, and *needs judgment*. Then take **one** decidable principle all the way to a constraint rule and run it over Phase 0's data. Manually classify a sample of its findings into true, false and undecidable | What fraction of governance this approach can actually automate — and the false-positive rate, which decides whether anyone will ever trust the gate | 1–2 weeks |
| **2 — A gate that survives** | Wire the validation run into a pipeline step with an exit code. Advisory first. Then record today's violations as a baseline and fail only on new ones | Whether a check changes behaviour, and what it costs in friction to find out | A sprint |
| **3 — One use case, measured before and after** | Pick impact analysis. Take the next significant change, have an analyst scope it the current way and the graph answer it independently, and compare both against what the change actually touched | Whether the graph is faster, and — more important — whether it is *complete*, which the Phase 0 number predicts | A quarter |
| **Ongoing** | KPIs | Import coverage % (overall and substantial-only); dropped-element count; share of principles mechanically decidable; violations per domain and trend; false-positive rate on sampled findings; graph freshness at time of query | — |

Two notes on the sequencing. **Phase 1 before phase 2** because a gate
built on a rule with a high false-positive rate is worse than no gate:
it teaches an organisation to route around architecture governance, and
that lesson outlives the tool. **Phase 3 last** because it is the phase
that produces the business case, and a business case built before the
coverage figure exists will be rebuilt.

And one note on what the pilot is not. None of these phases requires the
language-model layer, the running digital twin, or the observed-state
feed. Those are later increments with their own cases; including them in
a first pilot converts a four-week question into a multi-year programme
before anyone knows whether the denominator supports it.

---

## Appendix: the sixteen practice domains

The [SAFe DevOps Health Radar](https://framework.scaledagile.com/continuous-delivery-pipeline)
assesses the pipeline at the resolution of its sixteen activities — four
per aspect. Legend, as in the companion document:

- **●** direct — the approach executes here, or its findings act here
- **◐** supporting — its outputs are used in this activity
- **○** inherited — value arrives only because the graph was kept
  trustworthy upstream
- **—** no claim

| Aspect | Practice domain | Claim | Basis |
|---|---|---|---|
| Continuous Exploration | Hypothesize | ◐ | Landscape queries can inform which options are worth exploring — real but weak, and not what the architecture is for [hypothesis] |
| | Collaborate & Research | ● | One vocabulary across banking, security, service-management and delivery domains; the ontology *is* the agreement about what concepts mean [mechanism] |
| | Architect | ● | The core action point: notation legality over the whole estate, decidable principles checked mechanically, derived relationships computed rather than analysed [mechanism] |
| | Synthesize | ● | Derivation rules turn "what does this decision imply" into a query rather than an exercise [mechanism] |
| Continuous Integration | Develop | — | No authoring-time surface; the modelling tool already governs the author, and this stack sees the model only after export |
| | Build | — | **No claim as drawn, and this is the gap.** A validation run with an exit code would make it ● at very low cost; see [the CI section](#continuous-integration--the-gap-and-the-cheapest-fix-in-this-document) |
| | Test End-to-End | — | No claim |
| | Stage | — | No claim |
| Continuous Deployment | Deploy | — | No claim |
| | Verify | ◐ | Declared-versus-running gap analysis is conformance at architecture scope — gated on an observed-state feed the slides do not size [hypothesis] |
| | Monitor | ◐ | Operational data joined to the architecture graph makes monitoring interpretable in business terms [hypothesis] |
| | Respond | ● | Multi-hop root-cause and blast-radius traversal during an incident — the capability nothing else in the toolchain provides, conditional on graph freshness [mechanism] |
| Release on Demand | Release | ◐ | Standing, queryable evidence that the architecture of record is legal and principle-conformant; the strongest regulated-setting claim [mechanism] |
| | Stabilize | ○ | Post-incident problem-solving over a trustworthy landscape — inherited from Respond [hypothesis] |
| | Measure | ◐ | Conformance and violation trend add architecture health to what is measured — publish coverage beside it, always [mechanism] |
| | Learn | ◐ | Violations enumerate themselves into an architecture backlog with the offending element named [mechanism] |

**Read the distribution, not the marks.** Four direct claims, seven
supporting or inherited, five with no claim at all — and the five with no
claim are *contiguous*: the whole of Continuous Integration, plus Deploy
immediately after it. That is the assessment in one picture: an instrument that is
strong where architecture is decided and where its consequences are felt,
and absent from the aspect that touches every change an organisation
makes. An approach that scored well everywhere would deserve less trust,
not more; concentration plus stated limits is what a real instrument
looks like.

**The two distributions, side by side.** The same sixteen domains, this
approach's marks beside those the companion document records for a
commit-time checker of individual models — reproduced from its appendix,
not re-derived here:

| Aspect | Practice domain | EA ontology stack | Commit-time checker |
|---|---|---|---|
| Continuous Exploration | Hypothesize | ◐ | — |
| | Collaborate & Research | ● | ◐ |
| | Architect | ● | ● |
| | Synthesize | ● | ◐ |
| Continuous Integration | Develop | — | ● |
| | Build | — | ● |
| | Test End-to-End | — | ○ |
| | Stage | — | — |
| Continuous Deployment | Deploy | — | — |
| | Verify | ◐ | — |
| | Monitor | ◐ | — |
| | Respond | ● | ○ |
| Release on Demand | Release | ◐ | ○ |
| | Stabilize | ○ | ○ |
| | Measure | ◐ | ◐ |
| | Learn | ◐ | ◐ |

Only one domain carries a direct mark in both columns — **Architect** —
and even there the two act on different objects: one on the estate, one
on the document in front of the author. Everywhere else the columns are
close to complementary, and the two blocks of dashes sit in different
places.

**The complementarity, stated once and without a sales pitch.** The
companion document assesses a commit-time checker whose distribution is
the mirror image: strong in Continuous Exploration and Continuous
Integration, absent from Continuous Deployment. The two approaches are
not alternatives and neither is a cheaper version of the other — they
check different objects, at different times, for different people, and
the failure each catches is invisible to the other. An organisation that
builds only the estate-level layer will find that nothing stops a poor
model from being committed in the first place; one that builds only the
commit-time layer will find that nothing tells it what the estate as a
whole implies. Which to build first is a straightforward question of
where the current pain is, and it does not need this document to answer
it.

---

*Method and structure follow [pumllint in the SDLC](value-in-the-sdlc.md),
including its claim-tag discipline and its practice-domain appendix. The
roadmap-fit question for this repository's own tooling — settled
separately, and answered "neither belongs in these flows" — is in
[The ontology/graph EA stack, evaluated](ea-ontology-stack-evaluation.md),
which also carries the sources for every external figure quoted here.*

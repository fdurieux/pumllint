# The UML ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-27, written against `08efeda` (v0.29.0). The
question as posed: investigate the UML ecosystem, then assess the
boundaries, overlap, fit, gap, sense and nonsense of the different fits
against pumllint's roadmap and ecosystem. Fifth and last in a series
(Linked.Archi, C4, ArchiMate, BPMN, this).*

**Verdict up front: UML is the ecosystem this project's artefact belongs
to by name and not by substance, and the evaluation's yield is therefore
inward-facing. There is no fit to grade outward — no pack to build, no
tool to integrate with, no niche to occupy. What there is instead is a
measurement of how far pumllint actually sits from the standard whose
notation it lints, and the answer is: much further than the name
suggests, deliberately, and with one exception that is worth fixing.**

**Three layers, one shared. UML defines a metamodel — 242 metaclasses,
449 metaclass-owned invariants, 425 of them with OCL bodies, and Clause 2
makes validating them a conformance requirement. PlantUML borrows UML's
*notation* and implements none of that: its 607-page Language Reference
Guide contains zero occurrences of "metamodel", "semantic",
"well-formed", "OCL" or "XMI", and one of "conform" — about arrowhead
shape. pumllint builds its own typed model behind that notation. Only the
notation is common to all three, which is why "UML linter" would be the
wrong name for this tool and the repository has never used it.**

**The claim language survives contact with the standard, which is the
first thing a UML-literate reader would doubt. Audited exhaustively: 59
bare-"UML" tokens repo-wide against 553 "pumllint" and 295 "PlantUML";
only three sit in product-facing surfaces and all three are the same
claim (CLS004's "invalid UML"); a regex for any of
lint/check/validate/verify/enforce/conform within 25 characters of a bare
"UML" returns **nothing** repo-wide; no OMG, ISO 19505 or "UML 2.5.1"
reference appears in README, RULES, SCORING, EVIDENCE, `action.yml` or
the package source; and exactly one of 42 rule rationales appeals to UML.
Nothing to correct.**

**And the catalog is 86.3% not-UML. Classified rule by rule against the
spec's invariants: 7 of 51 rules are UML well-formedness in disguise, and
only **3** of those correspond to an actual OCL invariant (CLS004, STA001
in half, UC003). The other 44 are modelling hygiene and convention (27),
ambiguity and prose quality (11), and readability budgets (6) — things
the UML specification has no opinion on whatsoever. A UML-conformance
checker would duplicate three rules out of fifty-one.**

**Two findings are actionable, and both are about this project rather
than the ecosystem. The first is the type-fallback defect class in its
worst form yet: of the nine UML diagram types PlantUML renders and
pumllint does not parse, some fail honestly (component and deployment in
bracketed style, timing — the `[...]` and `@`-timecode tokens break the
endpoint pattern, so nothing parses and cap C6 holds at Level 1) while
the rest do not. A two-line styled component link,
`api -[#red]-> ledger : postEntry`, reaches **Level 4 (Precise), score
100.0, zero findings** on a file the tool understood nothing about. The
second is a concrete, cheap rule candidate the critic surfaced and this
note verified: pumllint enforces one UML invariant
(`Pseudostate::initial_vertex` ≈ STA001, a blocker, exit 1) and is
completely silent on another that is equally expressible and needs **zero
parser work** — a Class specializing an Interface or an Enumeration
scores Level 4 (Precise) with no structural finding at all.**

*Bounds. Every pumllint claim was executed at `08efeda` with default
config on files outside the repo (verified: GEN006/GEN007 stay dormant).
The external research was produced by a fan-out of five research agents,
each followed by an adversarial verifier instructed to refute rather than
confirm, plus three repository probes and a completeness critic —
fourteen agents, 677 tool calls. **All five verifiers returned "refuted"**,
and every correction they forced is carried below rather than the
original wording. Per this session's repository scope **no GitHub
repository was read**, which cost real coverage: Modelio's audit catalog,
the SysML v2 pilot implementation and the MIWG interchange test cases all
live there. Several vendor sites were unreachable — sparxsystems.com
returns 403 behind a Cloudflare interstitial and its validation PDF has no
extractable text, modelio.org 503s, ibm.com/docs 403s — so every Sparx,
Modelio and IBM claim is second-hand and is marked where it matters. The
650 OCL bodies were bracket-balance scanned, not parsed; no OCL parser was
available.*

## 0. Why this ran, and what it is not

There is no prior UML settled question. UML appears in the ROADMAP only
incidentally — inside the Linked.Archi entry's `uml:Lifeline` finding, and
in the phrase "C4/ArchiMate/UML diagrams describe something a human or
agent then implements". So this is a first look, like ArchiMate.

But it is a different *kind* of first look, and the difference is the
reason to write it. The previous four asked whether to reach into a
neighbouring ecosystem. This one asks what the relationship is to the
standard whose notation the tool already lints — which is a question about
this project, not about a market. Accordingly §7 grades fewer outward fits
and §8 carries more measurement.

One claim needed checking before anything else, because a UML-literate
reader arrives suspicious of it. The prose-pipeline settlement (2026-07-29)
adopted the finding that "the metamodel-conformance gate is the real prize
and is already shipped (lint/score + codegen profile)". In UML and MDA,
"metamodel conformance" means conformance to the OMG metamodel. It does
not mean that here, and the same document says so explicitly: the repo
"already hand-builds what the MDE stack would provide — parsers
(line-oriented recognizers), **the metamodel (typed dataclasses)**,
conformance (rules), and M2T (reporters)". The metamodel is
`pumllint/model.py`. Accurate as written; worth restating because the
misreading is available.

Nothing here is queued. §10 records the candidates.

## 1. The standard

### 1.1 What UML actually specifies

Current formal version **2.5.1**, OMG document `formal/2017-12-05`, dated
December 2017 — approaching nine years old. `omg.org/spec/UML/2.6/` returns
404; a UML 2.6 Revision Task Force exists and is accumulating issues
(hundreds; OMG's own tracker views disagree on the count, 629 vs 824 vs 826
on the same day, and which is authoritative could not be determined), but
has published nothing.

Measured directly on the normative `UML.xmi` (fetched from omg.org, 1,901,856
bytes, `sha256 e8166c91f5…`, re-downloaded and re-parsed independently by the
verifier with matching hash):

| | Count |
|---|---|
| Metaclasses | 242 (49 abstract) |
| `uml:Constraint` elements | 674 |
| …with an OCL-language body | 650 |
| Metaclass-owned invariants | 449 (425 OCL, 24 natural-language only) |
| Metaclasses carrying ≥1 invariant | 156 of 242 (**86 carry none**) |

Clause 7.4.3.1 states verbatim: *"The ownedRule Constraints for a Namespace
represent well-formedness rules for the constrained elements… These
constraints are evaluated when determining if the constrained elements are
well-formed."* Clause 2 makes it a conformance requirement: a conforming
tool *"must also provide a way to validate the well-formedness of models
that corresponds to the constraints defined in the UML metamodel."*

Two further facts shape everything below.

**Constraint density tracks execution semantics, not architecture.** Actions
155, Activities 50, Interactions 49, StateMachines 47 — against Deployments
4, SimpleClassifiers 5, CommonBehavior 7, UseCases 8. The `StandardProfile.xmi`
(33 stereotypes) carries **zero** constraints. UML's formal rigour is
concentrated where UML is an execution language, and is thin exactly where it
is used for architecture documentation.

**Compliance levels were abolished.** UML 2.5 states: *"The compliance levels
L0, L1, L2, and L3 have been eliminated, because they were not found to be
useful in practice. A tool either complies with the whole of UML or it does
not… in which case the vendor should declare which subset it implements."*
"Should", not "shall", with no register and no test. A grep for
"testing suite|test suite|certif" over the whole 796-page document returns
three hits, all in front-matter boilerplate.

### 1.2 How UML's legality differs from ArchiMate's — corrected

The ArchiMate evaluation (2026-08-27) called that ecosystem's Appendix B a
**legality metamodel**: a total enumerated matrix over (source, relationship,
target). The obvious move is to say UML is the same thing, larger. The
adversarial pass refuted that, and then refuted the refutation's overreach.
The corrected picture:

- **UML has no consolidated relationship-legality matrix.** True.
- **But it does constrain relationship legality — through static end typing
  in the metamodel, not through a table.** Of the 25 metaclasses that are or
  specialize `Relationship`, **17 have ends typed narrower** than
  Element/NamedElement/PackageableElement — `Include` UseCase→UseCase,
  `Generalization` Classifier→Classifier, `Deployment`
  DeployedArtifact→DeploymentTarget, `InterfaceRealization`
  BehavioredClassifier→Interface, `PackageMerge` Package→Package. Only
  `Dependency` and its subtypes `Abstraction`, `Realization` and `Usage`
  have genuinely unrestricted `NamedElement` ends — so the normative
  metamodel does permit a Dependency between any two named elements, and
  that is the narrow true statement.
- **The nearest thing to an ArchiMate table row is
  `InformationFlow::sources_and_targets_kind`**, which explicitly enumerates
  thirteen permitted metaclasses at each end. One rule, not a matrix.

So the difference is real but it is a difference of *form*: UML enforces
legality mostly by typing the metamodel, ArchiMate by enumerating a matrix.
Both make most illegal connections unrepresentable in a conforming tool.
(The ArchiMate note's line that its tables are "enforced at authoring time by
every conforming tool" is **characterized, not verified** — that evaluation's
own bounds say no ArchiMate tool was executed. It is not repeated here as
established.)

**On the formal layer's own health**, one claim needs narrowing. OMG issue
OCL25-217 is open and states *"The new OCL for UML 2.5.1 seems not to have been
checked by any tool"*, and both defects it names reproduce in the file fetched
from omg.org (`OpaqueExpression::only_in_or_return_parameters` contains an
unescaped reserved word; `Lifeline::interaction_uses_share_lifeline` ends with
an `implies` whose right side is a Bag, not a Boolean). Ninety-two issues are
open against 2.5.1 specifically, including "UML.xmi is not well-formed" and
"Duplicated xmi:id values in UML.xmi". But a balance scan found **0 of 650**
OCL bodies with unbalanced delimiters, which is evidence *for* partial
validity. "Two named defects reproduce and the OCL has never been
machine-checked" is supported; "the formal layer is invalid" is not.

## 2. Three layers, one shared

```
  UML 2.5.1          metamodel: 242 metaclasses, 449 invariants, 425 OCL
      │              conformance requires validating them (Clause 2)
      │  notation borrowed, metamodel NOT implemented
      ▼
  PlantUML           renders UML-inspired notation. Reference Guide (607 pp):
      │              metamodel 0 · semantic 0 · well-formed 0 · OCL 0 · XMI 0
      │              conform 1 (arrowhead shape). XMI: "Work is in progress."
      │  parsed by a tolerant line recognizer into its own typed model
      ▼
  pumllint           model.py: Diagram / Participant / Message / ClassEntity…
                     51 rules over that model. 3 of them restate a UML invariant.
```

PlantUML states its own position plainly. Its FAQ, retrieved 2026-08-27:
*"it does not restrict the creation of inconsistent diagrams — such as mutual
inheritance between two classes. Consequently, it functions more as a drawing
tool rather than a modeling tool."* The historic FAQ said the same in
different words — *"So it's more a drawing tool than a modeling tool"* —
verbatim in archive snapshots from 2016, 2019 and 2022.

That is not merely a disclaimer; it was **executed**. Against the official
server (`x-powered-by: PlantUML Version 1.2026.8beta1`) and independently
against `plantuml-1.2026.7.jar` from Maven Central, every one of these renders
successfully and `--check-syntax` exits 0:

| Construct | UML constraint violated |
|---|---|
| mutual inheritance between two classes | `Classifier::no_cycles_in_generalization` (§9.9.4.8) |
| three-way generalization cycle | same |
| self-generalization | same |
| two transitions out of the initial pseudostate | `Pseudostate::initial_vertex` (§14.5.6) |
| actor—actor association | `Actor::associations` (§18.2.1.4) |

Three named normative constraints, violated, rendered, and passed by
PlantUML's own syntax gate. That is the empirical form of "borrows the
notation, implements none of the metamodel", and it is the founding premise of
this project measured rather than asserted.

*(Doc-hygiene note: `README.md:6-8` attributes the "drawing tool rather than a
modeling tool" characterisation to PlantUML "by its own admission" with **no
URL**. The attribution is correct — verified verbatim above — but uncited in
the project's founding sentence. Recorded in §10.)*

## 3. Overlap — 3 rules out of 51

Every rule classified against UML's invariants:

| Class | Count | Share |
|---|---|---|
| **A** — a UML well-formedness constraint in disguise | **7** | 13.7% |
| **B** — modelling hygiene / convention (a well-formed UML model can violate it) | 27 | 52.9% |
| **C** — ambiguity / prose quality (about what a label *says*) | 11 | 21.6% |
| **D** — readability budget (thresholds, no truth value) | 6 | 11.8% |

And the A-class halves again. Only **three** correspond to an actual OCL
invariant:

- **CLS004** (inheritance cycle) — `not self.allParents()->includes(self)`.
  The one unambiguous A. Its rationale names UML explicitly, and it is the
  single UML appeal in the entire catalog.
- **STA001** (single initial state) — UML's `Region` invariant is *at most
  one* initial Pseudostate; pumllint requires *exactly* one. Half the rule is
  the invariant; the other half is stricter than UML, since a Region with zero
  initial vertices is legal UML.
- **UC003** (include/extend direction) — `Include` and `Extend` have
  UseCase-typed ends, so a reversed or actor-terminated relationship is a
  *type error*, unrepresentable in the metamodel. Though pumllint cannot read
  direction structurally and reconstructs it heuristically, staying silent
  when the evidence is ambiguous.

The other four A-rules (SEQ003, SEQ004, SEQ108, ACT004) are **not** OCL
invariants and could not be: they describe defects **unrepresentable in UML's
abstract syntax**. An unclosed `alt` has no metamodel counterpart — a
`CombinedFragment` either contains an `InteractionOperand` or it does not;
containment is structural. An `activate` without `deactivate` is an
`ExecutionSpecification` missing its mandatory `finish` — you cannot build the
object. These are **concrete-syntax repairs**: pumllint re-establishing, at the
text level, structure the metamodel gets for free.

That is the whole overlap. A UML-conformance checker pointed at pumllint's
catalog would duplicate three rules and have nothing to say about the other
forty-eight — because 86.3% of the catalog is about matters on which the UML
specification is silent by design.

## 4. Boundaries

1. **Notation vs metamodel.** Shared: the notation. Not shared: everything
   that makes UML a modelling language. §2.
2. **Abstract vs concrete syntax.** Four of pumllint's seven UML-ish rules
   exist *only* because the artefact is text — they repair at the character
   level what a metamodel enforces structurally. That work is invisible to
   UML and indispensable to PlantUML.
3. **Execution semantics vs architecture documentation.** UML's formal rigour
   is concentrated on Actions/Activities/Interactions/StateMachines and thin
   on Deployments and UseCases (§1.1). pumllint's users are on the thin side.
4. **Discovered vs not.** `.xmi`, `.uml` and `.ecore` are outside
   `PUML_EXTENSIONS`; the "nothing was checked" warning holds.

## 5. Sense — four true things

**S1. The claim language is accurate, and that is a finding rather than an
absence.** Five ecosystems in, this is the first evaluation whose main
repo-side risk was overclaim rather than coverage — and the audit came back
clean on every axis, including runtime output. `--help` says "Semantic linter
for PlantUML diagrams"; `--list-rules` renders CLS004 without the word UML;
the HTML report and badge say only "pumllint maturity report".

**S2. PlantUML's own FAQ is a better citation than the UML spec for this
project's founding premise.** It names *exactly* the defect CLS004 detects —
"inconsistent diagrams — such as mutual inheritance between two classes" — so
the rule can be justified without any appeal to UML at all. That is a
strictly better warrant: it is the tool's author conceding the gap the linter
fills.

**S3. The catalog's 86.3% non-UML share is the positioning, stated
numerically.** Every prior evaluation argued the differentiation
qualitatively. Here it is countable: the ambiguity dimension (11 rules) and
the readability budgets (6) have no metamodel counterpart *in principle* — no
constraint language can make "TBD" illegal — and the 27 hygiene rules are
things a perfectly well-formed UML model can violate freely.

**S4. Six ecosystems, still no grader — and this one nearly broke the
streak.** SDMetrics is the closest architectural analogue to pumllint found in
any of the six: design-rule checking plus OO metrics over XMI from any UML
tool, rules and metrics in a user-extensible XML config, a CLI for
"automated analysis runs", HTML/XML reports — commercially since ~2002. Its
226-page manual contains **no quality model, index, score, rating or maturity
concept at all**; output is per-element metric tables plus rule violations
ranked by a severity attribute. The academic literature says the same from the
inside: *"Current Computer-Aided Software Engineering (CASE) tools do not give
any hints to improve models, except some layout algorithms and syntax."* The
streak holds at six, by the narrowest margin yet.

## 6. Nonsense — five moves to refuse

**N1. Implementing UML's OCL invariants as rules. Refused.** It is the
well-formedness-as-a-type anti-goal (2026-08-02) at scale, against a 449-rule
denominator of which the vast majority is unexpressible in PlantUML anyway —
UML's constraints concentrate on Actions and Activities metaclasses that
PlantUML's notation cannot address. The three that *are* expressible and
relevant, this catalog already has (§3), plus the one it is missing (§8.2).

**N2. Reading XMI. Refused on identity, as with `.archimate` and `.bpmn`.**
A second artefact class is a second product. Note the door is shut from the
other side too: PlantUML's own FAQ says of XMI, *"Work is in progress."*

**N3. Renaming or repositioning toward "UML linter". Refused, and this is the
one that would actively damage the product.** 86.3% of the catalog is not UML,
three rules of fifty-one restate an invariant, and the tool cannot read UML's
interchange format. The current name is precise; a UML-flavoured one would be
an overclaim the audit in §8.1 shows the repository has scrupulously avoided
for its whole life.

**N4. Treating UML's age as an opportunity.** UML 2.5.1 is nine years old with
hundreds of open issues and no successor — but the successor energy went
elsewhere: OMG adopted **SysML v2.0 and KerML 1.0** in July 2025, built on
KerML rather than as a UML profile, *with a textual notation and a published
BNF*. That is OMG shipping a textual modelling language **with** formal
semantics. Whatever that implies, it is not a gap for a PlantUML linter.
(Characterized — the pilot implementation lives on GitHub, outside scope.)

**N5. Reading the AI layer as an opening.** Four independent PlantUML MCP
servers expose a syntax check; executed against PlantUML 1.2026.7,
`check_syntax` returns `{"valid":true,"warnings":[]}` for a typo'd alias that
silently invents a phantom lifeline, an association to a never-declared class,
orphan components, an unclosed group and a malformed stereotype. It returns
`valid:false` only for garbage tokens, a missing `@enduml`, and an empty
diagram. Tempting — until the verifier probed the tool the researcher had not
called: `explain_diagram` returns **structured per-line semantic facts**, from
which an agent could derive the phantom-lifeline defect itself. So the surface
is not a bare parse gate; it is syntax **plus inspection**, with no judgment
layer between them. What is missing is not the raw material for semantic
checking — it is any shipped rule, severity or verdict on top of it. That is a
narrower and more honest reading than "nothing above parseability", and it is
not an invitation to build.

## 7. Fit — graded

### F1 — a UML-conformance mode or rule pack. **No.** N1 and §3.

### F2 — XMI input. **No, on identity.** N2.

### F3 — repositioning toward UML. **No, and harmful.** N3.

### F4 — closing the one real invariant asymmetry. **Yes in principle; recorded, not queued.** §8.2.

The only outward-looking finding that turns into inward work. pumllint already
enforces `Pseudostate::initial_vertex` (STA001, blocker) and is silent on
`Classifier::specialize_type`, which is equally expressible in PlantUML,
equally relevant, and needs **zero parser work**. It is a rule, not a
programme.

### F5 — the honest/dishonest split across the nine uncovered UML types. **The type-fallback candidate, fifth instance.** §8.3.

Unchanged in substance from the ArchiMate entry's candidate 1; strengthened in
evidence, and this note supplies the mechanism at line-of-source precision.

### Fit against declared constraints

| Declared constraint | Where the UML fits land |
|---|---|
| **Zero runtime dependencies** | **Passes** for F4 (a rule over the existing model). Not reached for F1–F3. |
| **Deterministic product path, no LLM** | **Passes.** |
| **Golden score contract** | **Material for both F4 and F5** — each changes verdicts and needs a deliberate re-freeze. |
| **Demand-driven / Arc E bar** | F1–F3 fail on merit. F4 and F5 are **maintainer self-demand with measured defects behind them** — the WS3a / link-integrity label. |
| **Claim language is settled** | **Audited clean** (§8.1); one uncited attribution recorded. |

## 8. Gap — measured

### 8.1 The claim audit — clean

59 bare-"UML" tokens repo-wide (against 553 "pumllint", 509 "@startuml", 295
"PlantUML"). Only **three** occur in product-facing surfaces, and all three are
one claim:

```
README.md:267                     "…invalid UML that PlantUML happily renders."
RULES.md:1545                     "…semantically invalid UML and uncompilable…"
pumllint/rules/class_/structure.py:105   (same sentence, as CLS004's docstring)
```

Three decisive negatives:

1. **Zero verb+UML claims.** A regex for
   `(lint|check|validat|verif|enforc|conform|comply|against)` within 25
   characters of a bare "UML" returns nothing repo-wide.
2. **Zero appeals to the spec as normative authority.** No OMG, no ISO 19505,
   no "UML 2.5.1" in README, RULES, SCORING, EVIDENCE, `action.yml` or the
   package source. The only such references live in
   `docs/linked-archi-evaluation.md`, describing a third party's ontology and
   explicitly contrasting it ("**Not commensurable.**").
3. **Zero UML claims reach users at runtime.** `--help`, `--list-rules`,
   `catalog.toml`, the HTML reporter and the badge are all UML-free; the
   scope-guard warning is explicitly PlantUML-block-scoped.

Of 42 `**Rationale:**` blocks in RULES.md, exactly one appeals to UML.

### 8.2 The one invariant asymmetry — verified at HEAD

`Classifier::specialize_type` resolves through `maySpecializeType`, whose
default OCL body is `self.oclIsKindOf(c.oclType())` — so a Class may specialize
neither an Interface nor an Enumeration. Executed:

```
$ python3 -m pumllint spec.puml          # Payable <|-- Invoice ; Currency <|-- Invoice
spec.puml:1: [GEN001/minor] Diagram has no title
✖ 1 issue(s): 1 minor                                                  (exit 0)
  type='class'    level=4 (Precise)      score=99.0   elements=5

$ python3 -m pumllint uc.puml            # UC1 <|-- Customer  (Actor specializes UseCase)
uc.puml:1: [GEN001/minor] Diagram has no title
✖ 1 issue(s): 1 minor                                                  (exit 0)
  type='usecase'  level=3 (Disciplined)  score=97.5   elements=2

$ python3 -m pumllint init2.puml         # [*] --> Idle ; [*] --> Running
init2.puml:3: [STA001/blocker] Duplicate initial transition '[*] --> Running' …
✖ 3 issue(s): 1 blocker, 2 minor                                       (exit 1)
  type='state'    level=2 (Structured)   score=74.0   elements=5
```

One UML invariant enforced as a **blocker**; another, equally expressible,
drawing **no structural finding at all** — the only complaint is a missing
title. And the fix is small: `pumllint/model.py:258` already stores
`kind: str  # class | abstract | interface | enum | "implicit"` on the
classifier, and the relation carries its own `kind`. A `CLS006
type-mismatched-generalization` needs **no parser change**.

Two honesty notes. It is a *scoring* change and takes its own decision and
golden re-freeze. And the rule should be justified the way CLS004 is —
against what the target language will not compile, and against PlantUML's own
admission — not by appeal to the OMG spec, which would break the claim-language
discipline §8.1 just verified.

### 8.3 Nine uncovered UML types, split honest and dishonest

pumllint parses **5 of UML 2.5.1's 14 diagram types** — verified from source,
not inferred: `pumllint/parser/` holds exactly four modules, and
`model.py:363` documents the closed set `sequence | usecase | activity | class
| state | unknown`. No rule or parser mentions object, component, composite
structure, package, deployment, profile, communication, interaction overview
or timing.

All nine uncovered types render under PlantUML 1.2026.7 (`-checkonly` rc=0).
They split:

**Honest — Level 1, 0 elements, cap C6 holds:** component and deployment in
bracketed style (`[Web UI] --> [Order Service]`), and timing in all three
idiomatic forms. The `[...]` brackets and the `@`-suffixed timecode break the
`_IDENT = (?:"[^"]+"|[\w.]+)` endpoint pattern in `RE_MESSAGE`, so nothing
parses at all.

**Dishonest — Level 4 "Precise", frequently 100.0 with zero findings:**
object, package, composite structure, communication, component in alias style,
deployment without brackets, object with `map`, and timing the moment one
ordinary arrow is added.

The mechanism, at line precision: `A --> B` yields 2 implicit participants + 1
message = `elementCount` 3, which is exactly `l4_min_elements`
(`scoring.py:88`), so the `element_count < l4_min_elements` branch does not
fire and the level reaches 4. **Arrow shape decides the margin**: dashed and
dotted forms (`-->`, `..>`, `--`, `..`) set `is_return_arrow=True`
(`sequence.py:472`) → SEQ009 in DIM-SEM (weight 0.20) → Level 4; a solid `->`
trips SEQ005 in DIM-AMB (weight 0.25) instead → DIM-AMB 66.67 < the 70.0 L4
gate → Level 3. Either way, never the honest Level 1.

The sharpest case needs two lines. `api -[#red]-> ledger : postEntry` — the
label kills SEQ005, and `-[...]->` is solid so SEQ009 does not fire —
reaches **Level 4 (Precise), score 100.0, zero findings**. And
`--min-level` inverts: a timing diagram with one arrow passes
`score --min-level 4` (exit 0) while the same diagram *minus* that arrow fails
`--min-level 3` (exit 1).

Worse than dishonest in one case: a deployment diagram using
`database "orders" as ordersdb` — idiomatic, and `database` is in
`PARTICIPANT_KEYWORDS` — types the file `sequence` and reports **critical**
findings, failing CI at exit 1 on a diagram nothing understood.

This is the fifth instance of the class recorded in the ArchiMate entry
(C4 raw arrows; component + one `database`; native ArchiMate; BPMN sprites;
now nine UML types). The candidate is unchanged. What this note adds is the
exact threshold arithmetic and the arrow-shape dependency.

### 8.4 What was not measured

No UML tool was executed. The proportion of UML's 449 invariants that are
(a) expressible in PlantUML and (b) checked here is **not** computed — this
note has the denominator and three data points, not a table. That is the
analogue of the C4 note's "40% mechanizable" figure and it is missing;
producing it would be the honest way to claim the overlap is exactly 3.
Sparx EA, Modelio and IBM claims are all second-hand (unreachable sites).
SDMetrics' aggregate-score status rests on a 226-page manual with no such
concept, which is strong but is not the vendor denying it.

## 9. SWOT

Scope: *pumllint's position relative to UML*.

**Strengths (internal, favourable)**

- Claim language audited clean on every axis, including runtime output —
  the discipline held for the tool's whole life without a settled question
  telling it to.
- The differentiation is now countable: 44 of 51 rules address matters UML
  has no opinion on.
- PlantUML's own FAQ warrants the founding premise better than the UML spec
  would, and names CLS004's exact defect.
- Six ecosystems, no grader.

**Weaknesses (internal, unfavourable)**

- Nine of 14 UML diagram types unparsed, and most of them score dishonestly
  (§8.3) — the worst instance of the class yet measured.
- One UML invariant enforced, a comparable one silent, for no principled
  reason (§8.2).
- The founding sentence's PlantUML attribution is uncited.
- No numerator for the expressible-invariants figure (§8.4).

**Opportunities (external, favourable)**

- Only F4, and it is a single rule.

**Threats (external, unfavourable)**

- **The dishonest-verdict surface is widest here.** Nine diagram types, most
  of them scoring Precise on files the tool did not read. Unlike the previous
  four evaluations, this is not a market judgment — it is a wrong claim the
  product makes today, in more forms than anywhere else.
- **SysML v2 / KerML.** A textual modelling language *with* formal semantics,
  adopted by OMG in 2025, is the one development that speaks directly to the
  premise that text notations need an external semantic gate. It does not
  threaten the PlantUML niche, but it is the thing to watch.

## 10. Decision, recorded candidates, triggers

**Decision: no UML support of any kind — no conformance mode, no rule pack
from the spec, no XMI reader, and no repositioning. Two candidates recorded,
both inward-facing, neither queued.**

**Never build:**

- UML OCL invariants as a rule pack (N1) — the anti-goal at scale, over a
  denominator mostly unexpressible in PlantUML.
- An XMI or `.uml` reader (N2) — a second artefact class, refused on identity.
- Any repositioning toward "UML linter" or UML-conformance claims (N3) —
  86.3% of the catalog is not UML, and §8.1 shows the repository has avoided
  this for its whole life.

**Recorded, not queued:**

1. **`CLS006 type-mismatched-generalization`** — a Class specializing an
   Interface or an Enumeration, and an Actor specializing a UseCase, draw no
   structural finding today while the comparable `Pseudostate::initial_vertex`
   violation is a blocker (§8.2, verified at `08efeda`). `model.py` already
   carries the classifier `kind` and the relation `kind`, so **no parser work**.
   Must be justified as CLS004 is — uncompilable in the target language, plus
   PlantUML's own admission — **not** by appeal to the OMG spec, which would
   break the claim-language discipline. Scoring change: own decision, own
   golden re-freeze. Maintainer self-demand.
2. **The type-fallback defect class, fifth instance** (§8.3). No new candidate
   — the ArchiMate entry's candidate 1 covers it. Recorded here for the
   mechanism at line precision (`scoring.py:88`, `sequence.py:472`), the
   arrow-shape dependency, the two-line Level-4/100.0 case, and the
   `--min-level` inversion; and because nine diagram types make this the
   widest surface the class has.
3. **Cite the PlantUML attribution** — `README.md:6-8` says "by its own
   admission" with no URL. The current FAQ wording differs from the historic
   one and both are verbatim-quotable (§2). Documentation candidate.
4. **The expressible-invariants numerator** (§8.4) — the analogue of the C4
   note's 40%-mechanizable table. Would convert "3 of 51 overlap" from a
   classification into a measurement. Lab work, no behaviour change.

**Re-litigate on:**

- An adopter feeding pumllint output to a real UML toolchain — which would
  make XMI's absence a concrete blocker rather than a scope decision, and
  which PlantUML's "work is in progress" makes currently impossible anyway.
- SysML v2 / KerML acquiring a PlantUML-renderable textual form with users —
  the one ecosystem movement that touches the premise (N4).
- Evidence that a UML tool has begun producing a graded verdict, which would
  end the six-ecosystem streak and require the positioning claim to narrow.

## Related reading

- [The ArchiMate ecosystem, evaluated](archimate-ecosystem-evaluation.md) —
  candidate 1 there is the type-fallback class this note supplies a fifth
  instance and the exact mechanism for; its legality-metamodel framing is
  corrected in §1.2.
- [The BPMN ecosystem, evaluated](bpmn-ecosystem-evaluation.md) — the
  convergence argument this note's §3 is the mirror image of: `bpmnlint`
  independently reached pumllint's rules, while UML's spec shares only three.
- [The C4 model ecosystem, re-examined](c4-ecosystem-evaluation.md) — its
  "40% mechanizable" table is the model for the missing measurement in §8.4.
- [Linked.Archi and pumllint, evaluated](linked-archi-evaluation.md) — its
  UML 2.5.1 ontology mapping, and the `uml:Lifeline` flattening that is this
  repository's only other contact with the standard.
- [Model verification beyond linting](model-verification-evaluation.md) — the
  well-formedness-as-a-type anti-goal N1 rests on.
- [Prose→model→prose pipeline: fit evaluation](prose-pipeline-evaluation.md) —
  the "metamodel (typed dataclasses)" line that settles §0's question.

# Would the prose → model → prose requirements pipeline fit?

*Dated fit evaluation, 2026-07-29. An externally authored reassessment of a
prose → DSL → prose requirements-validation pipeline (itself a reversal of an
earlier external report that had judged the round-trip idea "nonsense")
was verified element-by-element against this repository, following the
precedent of the [C4 pack evaluation](c4-pack-evaluation.md). Verdict up
front: **sense — with corrections.** The reassessment's central conditional
holds and is satisfiable here *by construction*; two of its recommendations
do not survive contact with this repo's working agreements and are
corrected below. The resulting plan is recorded as
[ROADMAP.md](../ROADMAP.md) Arcs G–J (specified, gated); the decision
record lives in ROADMAP § Settled questions. Repo-internal claims were
verified against the working tree at v0.24.0; the probes in the appendix
were measured on 2026-07-29. The reassessment's external literature and
licensing claims are consistent with its own cited sources and with prior
research passes here; its self-flagged unverified items (exact arXiv IDs
for two papers, the Unisys SBVR implementation) are carried forward as
unverified, not re-litigated.*

## Why this evaluation ran

The ROADMAP already contains a parked adjacent-verifier item —
*spec/acceptance-criteria linting*: "the architecture transfers (text
artifact → parser → rules → score) but grammar, corpus, and calibration
start from zero" (§ Settled questions, 2026-07-26). The reassessment
attacks a different decomposition of the same territory: instead of
linting free prose (grammar from zero), close a **prose ↔ model loop
around the artifact class this tool already parses** — prose requirements
are cast into a typed model by an LLM under a human gate, the model is
gated deterministically, and a deterministic back-translation renders the
model as controlled prose for review. If that decomposition is sound, most
of the pipeline's deterministic legs land on existing machinery rather
than on a from-zero grammar. That is worth a recorded verdict either way.

## What the reassessment claims (compressed, so this note stands alone)

1. **The round trip is defensible iff the back leg is deterministic**
   model-to-text (verbalization, in the Attempto/ORM tradition), never a
   second LLM call. One stochastic leg, not two → divergence attributes
   cleanly to the forward leg. Done with an LLM on the back leg, the
   original "nonsense" verdict stands in full.
2. **The real prize is the metamodel, not the round trip**: forcing prose
   through typed elements, cardinalities and constraints mechanically
   surfaces missing actors, unbound references, orphan entities —
   defects prose-to-prose comparison cannot catch. The round trip is a
   review UI; a prose-similarity *score* must not be built.
3. **k-way divergence becomes tractable on models**: generate k models
   from the same prose, diff them element-wise; where the prose is
   ambiguous, the k models diverge *at the ambiguous element*. Nearly
   intractable for free-form code, a solved problem for typed models.
4. **LLM legs stay gated and secondary**: LLM ambiguity detection runs
   ~50% precision in its cited study; LLM-as-judge stays out of the
   primary correctness path; a human gate before promoting LLM-proposed
   structure is mandatory.
5. **Design-history lessons**: EARS succeeded (five lightweight
   human-readable patterns, industrial adoption) where SBVR Structured
   English failed (no formal grammar, no tooling — a style guide, not a
   language); ACE's verbalizer is the existence proof for lossless
   deterministic model↔prose, and also the caveat — it drops its most
   complex constructs, so verbalization completeness is capped by the
   verbalizer's coverage.
6. **Licensing**: a CLI linter is *run, not linked*, so GPL is essentially
   frictionless for the run-in-CI adopter, including in a regulated-bank
   audit culture; AGPL is a non-starter the moment a network service or
   MCP wrapper exists; the Eclipse MDE stack (EMF, Xtext, Epsilon,
   EMF Compare) is EPL and **EPL is GPL-incompatible**, ruling that stack
   out and (per the reassessment) ruling in the Python MDE stack
   (textX/pyecore/Lark/ANTLR); license *rug-pulls* (SonarQube → SSALv1
   2024-11-29; Semgrep restriction 2024-12-13 → Opengrep fork) destroy
   more adoption than copyleft ever does, so a credible non-relicensing
   commitment matters more than the specific license.

## Verified against this repository

**"pumllint is architecturally already a metamodel-conformance checker" —
TRUE, and specifically.** The reassessment's strongest fit claim checks
out in the code: the parser produces a typed semantic model
(`pumllint/model.py` — `Diagram`, `Participant`, `Message`, typed per
diagram family), and rules are conformance checks over it, including
exactly the checks the reassessment names as the metamodel's mechanical
yield: undeclared/implicit entities (SEQ001/SEQ101, `declared=False` on
the model), unbound references (C4 note's undeclared-alias pattern),
orphan entities (UC001, SEQ002, STA002), call/reply completeness
(`pair_calls_and_replies`), activation-stack well-formedness
(`walk_activation_stack`), cross-diagram identity (XD001–005's entity
symbol table with majority attribution). The pipeline's
"metamodel-conformance gate" for generated models is therefore not a
build item — it is `pumllint lint`/`score` with the codegen profile, as
shipped.

**The codegen gate as terminal gate — TRUE with measured backing.** The
reassessment calls SEQ101–109 the crown jewel and keeps it as the
pipeline's terminal gate. The evidence base here is stronger than the
reassessment needed: the below-Level-2 cliff is execution-oracle-robust
(21.9 pp pooled executed pass-rate, three generators, two vendors —
EVIDENCE.md), and this repo *independently measured* the reassessment's
LLM-as-judge caution: judged fidelity tracks executed correctness at
r ≈ 0.25 within-vendor and r ≈ 0.002 across the vendor boundary (X3,
XV1). The two lines of evidence were produced independently and agree.

**The back leg can be deterministic here by construction.** In this
repo's terms the back leg is `parse → verbalize`: both are ordinary
deterministic code paths, and the house already holds a determinism
contract for rendered output (the HTML report is byte-identical across
runs — no scripts, no timestamps). A verbalizer inherits that contract.
The reassessment's crux conditional — *back leg deterministic, or the
nonsense verdict returns* — is therefore satisfiable without ceremony.
What pumllint must never do is route the back leg through an LLM; that
lands in the working agreements via the boundary rule below.

**The k-way diff has a live foothold.** XD001–005 already build an
entity symbol table across a batch and attribute minority declarations
against a majority reference (`rules/common/consistency.py`). Probe B
(appendix) diffs two parsed sequence diagrams of the same scenario with
the existing parser and stdlib only: participants match 3/3 by identity,
declaration drift is localized per element (`OrderDB` database →
implicit; `OrderService` stereotype lost), and the message-set diff
surfaces the divergent labels verbatim. Element-localized divergence —
the reassessment's "most rigorous component" — is reachable from shipped
machinery. (Label-exact matching is deliberately the crudest matcher;
a real meter needs similarity matching per (source, target) pair. The
*identity* layer, which is what localization stands on, already works.)

**The traceability matrix has a foothold and a genuine gap.** GEN007
(requirement-link, `rules/common/governance.py`) already detects
requirement/ADR references in name/title/header/footer/caption/notes,
dormant until the project supplies its reference `pattern` — the
diagram → requirement direction, as a per-diagram boolean. What does not
exist is the **matrix**: given a requirements inventory, which
requirement IDs are realized by which diagrams, and which are covered by
none (and which diagrams reference nothing). Deterministic, no LLM
anywhere, and the reassessment's "empty niche, ship first" claim
survives inspection: nothing in the tool aggregates coverage today.

## Corrections — where the reassessment does not survive this repo

**1. "textX/pyecore is licence-necessary" — overstated; corrected to
stdlib-first.** The EPL trap is real and now binding (this repo
relicensed MIT → GPL-3.0-or-later at v0.24.0, the reassessment's own
"GPLv3 if copyleft is a value commitment" fork): EMF, Xtext, Epsilon and
EMF Compare are off-limits in product *and* lab code — an EPL+GPL
combined work is not distributable, and everything in this repo ships in
one GPL sdist. But the remedy does not follow. What license law requires
is *avoiding EPL*; the stdlib satisfies that as thoroughly as textX
does, and the working agreement here is explicit: product code runs on
the stdlib only. This repo already hand-builds what the MDE stack would
provide — parsers (line-oriented recognizers), the metamodel (typed
dataclasses), conformance (rules), and M2T (reporters). The Python MDE
stack is recorded as the *fallback for lab tooling* (`tools/` may take
optional extras per the auto-improvement settlement) if a purpose-built
requirements DSL ever outgrows hand-written parsing — not as a product
dependency, and not as a necessity.

**2. The back leg's substrate is a projection, and honesty about that is
a build requirement, not a footnote.** The parser deliberately
recognizes a governance-relevant subset and skips unknown lines, never
fatally and currently *without tracking* (`parser/sequence.py`). A
verbalizer renders the parsed model, so anything the parser skipped is
silently absent from the prose — the exact failure class the
reassessment flags for ACE ("expect the same class of loss, which caps
the round trip's completeness"), arriving here through the parser rather
than the verbalizer. Measured (Probe A): on the in-dialect bundled
corpus the projection is semantically complete — 167/188 content lines
modelled, and all 21 misses are comment lines or class-body closing
braces whose content is modelled elsewhere; zero semantic statements
dropped. On a foreign corpus that number is an open question, and the
pilot census already measures exactly it ("files yielding nothing",
big-file/few-element suspects). Consequence for the build: the verbalizer
ships **with an unmodelled-content disclosure** (a per-run count of
skipped non-comment source lines, surfaced in the output the way
suppressed findings are surfaced in scores — never silently), which
requires small additive parser/model support first.

**3. The pipeline's phases are not all product.** The reassessment's
phased recommendation reads as if the whole loop ships in the tool. It
must not: the forward leg (prose → model, an LLM under a human gate) and
the k-fold generation that feeds the divergence meter are **recipe and
lab territory** — docs/agents.md and `tools/` — exactly as the existing
evidence harnesses are. The product stays a deterministic verifier; the
LLM legs stay outside the primary path (the stance this repo already
holds and has now twice measured). This boundary is what keeps the
zero-dependency promise, the determinism contracts, and the run-not-
linked GPL posture all intact at once.

## Component verdicts (reassessment → verified against this repo)

| Component (reassessment's) | Its verdict | After verification here |
|---|---|---|
| 1. Deterministic bidirectional traceability matrix | Sense; ship first | **Confirmed** — genuine gap, GEN007 foothold, no LLM anywhere. Arc G. |
| 2. LLM-assisted classification/rewrite, human-gated | Sense, gated | **Confirmed, but out of product** — recipe (docs/agents.md) + gates already shipped. Not an arc. |
| 3. Generate a model from prose (metamodel conformance) | Sense — the big upgrade | **Confirmed and already built** — lint/score + codegen profile are the conformance gate. No build. |
| 4. Back-translate model → prose | Sense *iff* deterministic | **Confirmed with the projection caveat** — parse+verbalize is deterministic by construction; unmodelled-content disclosure mandatory. Arc H. |
| 5. Manual comparison → automated diff + residue | Partially replaceable | **Confirmed** — XD machinery generalizes; element-localized divergence measured feasible (Probe B). Arc I. |
| Prose-similarity round-trip *score* | Do not build | **Adopted verbatim** — recorded in the never-build list. |
| LLM back leg / free-form-code intermediate / AGPL / EPL stack | Do not build/choose | **Adopted verbatim** — see Settled questions. |

## Licensing — what changes after verification

Nothing to decide, something to record. The license choice the
reassessment argues for was already made (GPL-3.0-or-later, v0.24.0,
2026-07-27) and its run-not-linked analysis matches how this tool is
consumed (CLI in CI, composite Action, pre-commit; the opt-in PlantUML
syntax gate invokes a separate process — arm's length, not linking).
Three of its constraints are adopted as standing decisions: **never
AGPL** for any future service or MCP wrapper derived from this codebase;
**EPL dependencies are off-limits** repo-wide (product and lab — one GPL
sdist); Apache-2.0 dependencies remain compatible if the optional-extras
door is ever used. Its fourth recommendation — a **credible
non-relicensing commitment** ("will never move to source-available"),
the rug-pull lesson — is a maintainer's public promise, recorded in the
ROADMAP as a recommended act for the owner, not silently made by this
evaluation.

## Do arcs fit this initiative?

Yes — and the reassessment's own phase numbering is the argument. Arcs
here have never been a schedule; they are parallel trust-building
threads, each carrying its own completion bar (committed vs
wait-for-pull), which is the device that kept demand-driven work from
bleeding into committed work for two years of this ROADMAP. The
reassessment's phases map onto that device cleanly — Phase 1 → Arc G
(traceability), Phase 2.5 → Arc H (verbalizer), Phase 3 → Arc I
(divergence meter), Phase 4 → Arc J (evidence, Arc D's methodology
reapplied) — with one structural gain the phase numbering obscures:
**Phase 2 does not become an arc at all**, because its substance is
either already shipped (the conformance gate) or deliberately outside
the product (the LLM leg, gated by recipe). A chronological phase list
implies everything ships in the tool; arcs plus the boundary rule state
exactly which legs live in the product, the lab, and the recipe. That
distinction is load-bearing for this pipeline in a way it never had to
be for the original linter — the original arcs organized *when* trust
was built; these also organize *where determinism ends*.

## Decision and triggers

**Specified and gated — recorded as ROADMAP Arcs G–J; no build starts
from this note alone.** The demand instrument is unchanged: the pilot
(docs/pilot-charter.md) and its census. Per-arc triggers are recorded in
the ROADMAP; the never-build list and the license posture live in
§ Settled questions. Re-litigate this evaluation's corrections only on
new evidence: a foreign-corpus census materially below Probe A's
projection completeness would raise the disclosure requirement from
"ship with Arc H" to "blocking precondition"; a concrete adopter whose
requirements DSL cannot be hand-parsed would reopen the textX fallback
as a lab dependency.

## Appendix — probes (measured 2026-07-29, v0.24.0 working tree)

**Probe A — projection coverage.** For each bundled example, parse with
`pumllint.parser.sequence.parse_source`, collect every line number
carried by any model object (declared participants, messages,
activations, block delimiters and branches, directives, use-case links,
activity nodes, classifiers and members, relations, states, transitions,
suppressions), and compare against non-blank content lines (excluding
`@startuml`/`@enduml`). Result: **167/188 content lines modelled (89%)**
across 14 files; the 21 unmodelled lines are 16 comment lines (the
examples' deliberate-mess annotations) and 5 class-body closing braces —
**no semantic statement is skipped in-dialect**. The number that bounds
this claim on real corpora is the census's dialect-coverage report, not
this probe.

**Probe B — element-level diff dry run.** Parse
`examples/order_payment_codegen_good.puml` and `..._bad.puml` (two
renderings of the same scenario), match participants by name, compare
declarations and message sets — existing parser + stdlib only, no new
code in the package:

```text
participants: 3/3 matched by identity (OrderService, PaymentGateway, OrderDB)
declaration drift on 'OrderDB':      good=(database, –)        bad=(implicit, –)
declaration drift on 'OrderService': good=(participant, service) bad=(participant, –)
messages: good 7, bad 3, shared 0 — divergent labels verbatim, e.g.
  good: OrderService -> OrderDB : 'findOrderById(orderId)'
  bad : OrderService -> OrderDB : 'store the result ... etc'
```

Divergence lands *at named elements*, which is the property the k-way
meter needs. The probe script is not committed; the method is fully
described above and reproducible in a few dozen lines.

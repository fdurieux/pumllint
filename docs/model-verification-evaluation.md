# Model verification beyond linting — three formal ambitions, evaluated

*Dated evaluation, 2026-08-02, written against `b326484`
(post-v0.26.0). An externally authored note proposed a horizon "beyond
linting into verifying the models themselves" — three formal ambitions
(proving sequence interactions deadlock-free / every message matched by
a return; proving the rule set internally consistent; encoding
well-formedness as a type so ill-formed models are unconstructible) —
then named model checkers (TLA+, Alloy) or a rules DSL as the "honest
alternatives," and closed with a concrete recommendation: a proper
grammar (Lark or ANTLR) for the .puml subset, rules as pluggable
visitors, and the glossary/terminology check as one rule among many.
Verdict up front: **inverted, with one keeper. The note's closing
recommendation describes, in two of its three parts, the architecture
this repository already ships; the third part (a Lark/ANTLR grammar)
re-litigates a settled question and would regress recorded
requirements. Its "ambitions beyond linting" are, in order: a category
error for the artifact class (deadlock-freedom), a property the
calibration corpus already witnesses constructively — and in a
stronger form (rule-set consistency), and an architectural inversion
that would destroy the product (well-formedness as a type). The one
genuinely new, buildable item hiding in the text is a
glossary/approved-term rule — small, precedented, and adopter-gated
like its siblings.** Bounds: repo-internal claims were verified against
the working tree; formal-methods literature is characterized from
general knowledge and kept non-load-bearing — no primary was fetched in
this pass, and no verdict below rests on one.*

## Why this evaluation ran

This is the fourth externally authored analysis verified under the
house discipline (after the prose-pipeline reassessment and spec-stack
recommendation, 2026-07-29, and the capability-horizon mapping,
2026-08-01). Unlike the previous three it proposes *builds* — and
builds of a specific temperament: formal-methods machinery (provers,
model checkers, type-level encodings, a generated-parser grammar). The
records already hold the instruments this proposal must be triaged
against — the obligation/flow settlement's oracle discipline, the
zero-dependency working agreement, the recorded Lark/textX fallback
shelf, and the clean-probe golden contract — so the evaluation's job
is to run that triage once, record it, and prevent re-derivation.

## What the note says (compressed, so this note stands alone)

1. **Ambition 1 — interaction semantics.** Formalize the semantics of
   a sequence diagram and *prove* that a set of interactions is
   deadlock-free, or that every message has a matching return.
2. **Ambition 2 — rule-set consistency.** Prove no two rules exist
   that can never be simultaneously satisfied.
3. **Ambition 3 — well-formedness as a type.** Encode process-model
   well-formedness (à la ARIS conventions checking) as a type, so an
   ill-formed model is literally unconstructible.
4. **Alternatives.** The "honest alternatives" are model checkers
   (TLA+, Alloy) or a rules DSL — "both far cheaper to reach," Alloy
   in particular "built for exactly 'find me a counterexample to this
   structural constraint.'"
5. **Recommendation.** Staying in Python: a proper grammar (Lark or
   ANTLR) for the .puml subset, rules as pluggable visitors, the
   glossary/terminology check as one rule among many.

## Ambition 1 — the bundle conflates a shipped lint check with an unoracled proof

The two examples sit at opposite ends of the cost spectrum, and the
note presents them as one workload.

**"Every message has a matching return" is not verification — it is
linting, and it ships today, four ways.** SEQ003 (unbalanced
activation), SEQ009 (unpaired return), SEQ104 (codegen-missing-return)
and SEQ108 (activation lifecycle as a well-formed per-lifeline stack)
are exactly this check at four strictness tiers, over the
`pair_calls_and_replies` and activation-stack helpers in
`pumllint/model.py`. The genuinely *semantic* remainder — is the call
answered on **every execution path** through the alt tree, not merely
somewhere later in the text — is already specced as SEQ202 (WS3b) in
the obligation/flow settlement (ROADMAP, 2026-07-30), together with
the recorded verification that shipped SEQ104 is path-insensitive (a
reply in a mutually exclusive sibling branch satisfies linear pairing
while no execution path is answered). That remainder is **decidable
with a fragment-tree walk** — no prover, no model checker — and it is
measurement-gated, not theory-gated: prototype branch-aware pairing,
count SEQ104 verdict flips on a real corpus, then decide.

**"Deadlock-free" is a category error for this artifact class.** A
PlantUML sequence diagram denotes a scenario — one trace, or a finite
tree of traces via alt/opt/loop/par. Deadlock is a property of a
*system* of communicating processes under a concurrency semantics:
blocking or non-blocking sends, FIFO buffers or bags, bounded or not.
The diagram specifies none of that, because PlantUML has no execution
semantics at all — the README's own opening premise ("a drawing tool
rather than a modeling tool") is the reason this linter exists. To
prove deadlock-freedom one must first *impose* the semantics the
author never wrote — synchronous rendezvous versus asynchronous
buffered delivery changes the answer — and then the checker is
verifying its own invention. That is precisely the no-oracle shape the
obligation/flow settlement rejected in the participant-pair sweep
("the complement of a diagram is not a set of omissions … rejected
regardless of implementation effort"). The formal-methods field
confirms both halves at once: interaction-diagram verification is a
real literature (Message Sequence Chart realizability and race
analysis, Alur–Etessami–Yannakakis and successors), and its central
lesson is that the interesting properties range from polynomial to
undecidable *depending entirely on which communication semantics is
imposed* — the choice PlantUML leaves undefined. (Characterization,
non-load-bearing; the verdict stands on the oracle argument alone.)
If semantic-trace work is ever pulled, the decidable member of that
family — visual order contradicting causal order — would land as a
rule over the existing fragment tree, inside the shipped
architecture. Nothing about it needs a prover.

**"Verifying the models themselves" needs a referent, and the honest
referents are cross-artifact.** A single diagram contains no second
source of truth to verify against. Where a second artifact claims the
same facts, this repo already checks or has specced the check:
`pumllint trace` (diagram ↔ requirements inventory — shipped,
v0.25.0), the XD pack (diagram ↔ diagram entity identity — shipped),
the sequence↔contract cross-check (message signatures ↔
OpenAPI/AsyncAPI operations — recorded 2026-07-29, trigger-gated),
and the declared-policy packs (diagram ↔ obligations/architecture
tables — specced 2026-07-30, adopter-gated). And for the property
that actually motivates "verification" here — do these models support
faithful downstream implementation — the repo holds something
stronger than a proof over invented semantics: a **measurement**
(Arc D: executed-fidelity cliff 21.9 pp pooled, three generators, two
vendors, oracle-robust). Proving theorems about a semantics nobody
authored is a weaker epistemic position than measuring outcomes of
the artifact as actually consumed.

## Ambition 2 — the corpus already witnesses the stronger property

"No two rules that can never be simultaneously satisfied" is
**pairwise** consistency — the weak form. Pairwise consistency does
not compose: a rule set can be pairwise-satisfiable and jointly
unsatisfiable. The property worth having is **joint** satisfiability —
one diagram satisfying *all* default rules at once — and the
calibration corpus proves it the constructive way: the clean probes
(`tools/gen_corpus.py` — `tiny_clean`, `small_clean`, `large_clean`,
plus per-type probes `class_clean`, `state_clean`, `usecase_clean`)
are exhibited witnesses, per diagram type, enforced on every run by
the golden-score contract. A satisfiability proof by exhibited model
*is* a proof — the same deliverable Alloy would produce (an instance),
with zero parallel formalization to maintain.

That last clause is the real cost the note's Alloy suggestion hides.
Encoding 40+ rules in relational logic means writing and maintaining a
**second implementation** of every rule's semantics; the moment the
Alloy model and the Python drift, the consistency "proof" silently
stops being about the shipped linter — formalization drift is the same
bug class the exercise was meant to catch, now unfalsifiable from
inside Alloy. Where inconsistency can actually enter this system is
**user configuration** (a project can configure GEN004 patterns and
per-kind overrides that contradict each other), which no upfront proof
over the shipped rules can cover, and which the config path already
handles as a config error, not a crash. For *surprising interactions*
short of contradiction, the shipped instrument is the corpus-firing
report (`tools/corpus_firing.py`) — where every rule fires, and where
it never does; it is the analysis that exposed the zero-firing codegen
rules. If adversarial instance-finding is ever wanted, the
ethos-compatible form is property-based generation of `Diagram` models
(Hypothesis) in `tools/` behind the optional-extras door — the same
shelf the settled questions already assign to Lark/textX — not a
product-path Alloy model.

## Ambition 3 — unconstructibility is the anti-goal of a linter

Encoding well-formedness so that "an ill-formed model is literally
unconstructible" is architecturally inverted for this product,
independent of cost. **The linter's input is the ill-formed model;
its entire output is a graded diagnosis of ill-formedness** —
severities, maturity levels 1–5, prescriptive gap reports, ratchet
baselines whose whole purpose is holding *brownfield* (ill-formed)
model sets, and `pumllint fix`, which must represent the broken model
in order to repair it. Make ill-formedness unrepresentable and every
finding collapses into a parse rejection at the first defect — which
is PlantUML's own `-checkonly` behavior, i.e., exactly the gap this
tool was built to fill. "Parse, don't validate" is the right pattern
*downstream* of a gate — a generator may legitimately demand a
validated model constructible only from a passing lint — never *in*
the gate. (Mechanically it is also out of reach in the declared
stack: the invariants that matter — balanced activation stacks,
per-path call answering, acyclic generalization — are relational and
ordering properties over the whole model, beyond what Python's type
system expresses; the "types" would decay into runtime smart
constructors, which are the existing rules renamed, minus their
diagnostics.)

The note itself steers away from this option, but for the wrong
reason — cost ("far cheaper to reach" alternatives). The correct
reason is that for a linter it is product-destroying at any cost,
including zero.

The ARIS reference corroborates the architecture it argues against:
ARIS conventions checking (its semantic-check machinery) is itself a
**rules engine over a parsed repository** — the industry's own
instance of this exact problem chose pluggable rules over a model,
not types and not a prover. The honest ARIS-parity path in this repo
is the declared-policy direction already specced: obligations
(SEQ110–113) and architecture conformance (ARC001–003), decidable
against tables an organisation declares, adopter-gated.

## The alternatives claim — TLA+ mismatched, Alloy's "prove" overstated, the DSL already instantiated where honest

- **TLA+** checks temporal properties of specified state machines.
  Neither named problem fits: rule-set consistency is not temporal,
  and a sequence diagram supplies no state machine — using TLA+ first
  requires authoring the missing semantics, the very cost the
  "cheaper" framing was meant to avoid.
- **Alloy** fits the *shape* (relational instance/counterexample
  finding) but the note's verb slips: Alloy is bounded model finding —
  "no counterexample within scope *k*," never a proof — while the
  ambitions are phrased as *proving*. Its real cost here is the
  parallel formalization (Ambition 2 above). The narrow honest use is
  exploratory: sketching a *new* rule's interaction space before
  implementation, as lab tooling, off the product path.
- **A rules DSL** — this repo consciously holds the two-layer version
  of that idea already: declarative metadata in `catalog.toml` plus
  imperative `check()` in Python, and above it the RULES.md Gherkin
  blocks as an *executable specification* layer (extract_features +
  pytest-bdd + sync guard). That is a rules DSL exactly where it pays
  (specification and acceptance) and none where it doesn't
  (implementation). The parked EARS-shaped-DSL settlement (2026-07-29)
  already records the design lesson the note gestures at: lightweight
  and hand-parseable first, or it fails like SBVR.

## The recommendation — two thirds shipped, one third a regression

**"Rules as pluggable visitors" — shipped.** Auto-discovered
`@register` rule classes over a shared parsed `Diagram` model;
adding a rule = one class + one catalog entry; profiles, config,
suppressions and reporters uniform across packs
(`pumllint/rules/__init__.py`). Nothing to adopt.

**"Glossary/terminology as one rule among many" — shipped in spirit;
one small genuine gap.** Terminology governance is already a family
of rules among many: GEN004 (naming patterns, per-kind), ACT006/UC002
(verb-first with configurable verb whitelists), GEN006/GEN007
(convention-gated tag patterns, dormant until configured), XD001–005
(cross-diagram entity identity). What does *not* exist is the ARIS
sense of a glossary: **a curated approved-term list as the naming
oracle** — "declared element names must resolve against the project's
term inventory," the `pumllint trace` inventory pattern applied to
names instead of requirement IDs. That is the note's one keeper: a
single dormant-by-default rule taking a term-list file (text/json/yaml,
the trace inventory loader's shape), checking declared names across
entity kinds, with the same unknown-reference instinct SEQ001 and
`trace` already embody. It slots into the existing chassis as exactly
"one rule among many" — a GEN-pack addition, not an architecture.
Recorded as a candidate, not queued; trigger below.

**"A proper grammar (Lark or ANTLR)" — the one concretely wrong call
for this codebase, on grounds already in the records:**

1. **PlantUML has no grammar to be "proper" about.** The language is
   defined by its Java implementation — which itself parses
   line-by-line with per-command regexes — and evolves continuously.
   The shipped line-oriented recognizer mirrors the reference
   implementation's own architecture; a context-free grammar would be
   a *less* faithful model of the language, not a more rigorous one.
2. **For a linter, tolerance is a requirement, not a shortcut.** A
   strict grammar turns every valid-but-unmodeled construct on a
   foreign corpus into a parse failure; approximating today's
   "unknown lines are skipped, never fatal" behavior in a generated
   parser means hand-building error recovery — expert-level work to
   buy back a property the current design gets by construction. The
   known cost of tolerance — silent projection gaps — already has a
   cheaper recorded fix: Arc H's unmodelled-content disclosure
   (count and locate skipped lines), a precondition on the books.
3. **Zero-dependency is a working agreement, and this exact question
   is settled.** The prose-pipeline evaluation (2026-07-29) records
   textX/pyecore/Lark as a *lab-tooling fallback* behind the
   optional-extras door, explicitly not product path. The note
   re-litigates without new evidence.
4. **What a grammar would buy is the feature set nobody has pulled.**
   Column-precise spans and a CST for richer autofix are LSP-territory
   wants; Arc E's LSP item is itself strictly wait-for-pull. A grammar
   is a dependency of an unpulled feature, not an upgrade to the
   shipped product. *[2026-09-03: the LSP was pulled and built
   2026-08-31, so this premise is gone. The conclusion survives on a
   different ground: the shipped server extracts precise sub-ranges from
   the existing parser's named groups, so span-tracking in the recognizer
   proved sufficient — exactly the "evaluate first" step the closing
   bullet prescribes. Column-precise spans are now a shipped limitation
   (`lsp.py` widens to end-of-line where a violation carries no column),
   not a hypothetical want.]*
5. **Parser fidelity is defect-class work, and the guards exist.** The
   v0.26.0 fixes (half-arrow direction, legend bodies, delay arrows)
   were found, fixed and frozen under the corpus + golden contract. A
   grammar rewrite resets that hardening and puts 42 rules and the
   score contract at migration risk for zero behavioral gain.

## Corrections

1. **"Every message has a matching return" is not an example of
   heavyweight formalization.** It is shipped linting (SEQ003/009/104/
   108); the genuinely semantic remainder (branch-aware pairing,
   SEQ202) is specced, decidable without a prover, and
   measurement-gated since 2026-07-30.
2. **"Deadlock-free" is not a property of this artifact.** A PlantUML
   sequence diagram carries no concurrency semantics; the proof
   requires imposing one, which is the no-oracle failure shape the
   obligation/flow settlement rejected regardless of effort.
3. **"Proving … internally consistent" names the weak property and
   the wrong instrument.** Pairwise consistency does not compose;
   joint satisfiability is the property worth having, and the corpus's
   clean probes witness it constructively under continuous golden
   enforcement — with no second formalization to drift.
4. **"Ill-formed model literally unconstructible" is the anti-goal.**
   Representable ill-formedness is the product (findings, levels,
   ratchet, fix). The note discards this option on cost; the correct
   ground is that it is product-destroying at any cost.
5. **"Both far cheaper to reach" is true only against the proof
   ambitions.** Against what exists it is backwards: for every goal
   the note names, this repo holds a cheaper shipped or specced
   instrument (clean probes, corpus-firing reports, fragment-tree
   rules, declared-policy tables, cross-artifact tracing).
6. **Alloy does not "prove."** Bounded instance finding within scope
   *k* is evidence, not proof — a material slippage in a note whose
   ambitions are all phrased as proving.
7. **The Lark/ANTLR recommendation re-litigates a settled question**
   (prose-pipeline evaluation, 2026-07-29; ROADMAP settled questions)
   without new evidence, and independently conflicts with two recorded
   requirements: the zero-dependency promise and parse tolerance.

## Where the note is right

The temperament is sound and matches the records: skepticism toward
prover-grade machinery for this artifact class, preference for cheap
structural checking, rules as plugins, terminology governance as
ordinary rules rather than a special subsystem. Its instinct that the
ARIS-conventions thread belongs *inside* the rule architecture — not
beside it — is exactly the shipped design, and its instinct that
counterexample-finding beats theorem-proving for structural
constraints is the same instinct behind the corpus's mutation ladders
and clean probes. The note's error is not direction but inventory: it
recommends building what is built, and formalizing what is either
already decided decidable or undecidable-by-missing-oracle.

## Decision and triggers

**Recorded; one candidate noted; nothing queued; nothing in the plan
changes.**

- **Glossary/approved-term rule** (the keeper): build when an adopter
  or the pilot's conventions workshop supplies an actual term
  inventory — the same trigger class as `trace` adoption and the
  obligation tables. Dormant-by-default (GEN006/GEN007 pattern);
  inventory loader shape shared with `trace`. Until a real term list
  exists, building it would manufacture a convention, not check one.
- **Semantic-trace work** (races, per-path properties): only on pull,
  and then as fragment-tree rules per the obligation/flow settlement
  (WS3a/WS3b) — never as a prover or model checker.
- **Formal tools as lab exploration** (Alloy sketches, Hypothesis
  generation of `Diagram` instances): welcome in `tools/` behind the
  optional-extras door, same shelf as Lark/textX; never product path,
  never a gate.
- **Grammar question**: closed here; reopen only if a concrete LSP
  adopter makes column-precise spans load-bearing, and then evaluate
  span-tracking in the existing recognizer before any parser
  generator. *[Reopen condition fired 2026-08-31; the ordered second
  clause was executed and returned "sufficient". Still closed, for that
  reason — see §4's annotation above.]*

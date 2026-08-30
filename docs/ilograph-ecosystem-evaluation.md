# The Ilograph ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-27, written against `7043819` (v0.29.0). The
question as posed: investigate the Ilograph ecosystem, then assess the
boundaries, overlap, fit, gap, sense and nonsense of the different fits
against pumllint's roadmap and ecosystem. Ninth in a series
(Linked.Archi, C4, ArchiMate, BPMN, UML, Mermaid, D2, Structurizr DSL,
this).*

**Verdict up front: no, on the cleanest grounds in the series — and the
evaluation's yield is not about Ilograph at all. Three refusals, each
sufficient. (1) Ilograph is not a diagram notation. It is a *model plus
perspectives* format for an interactive viewer: `resources` (a tree),
`perspectives` (relation or sequence), `contexts` and `imports`. The
"diagram" is a navigation experience, not a static picture, so pumllint's
founding assumption — a file contains a diagram, of a type, with elements
one can reason about — does not hold. (2) It is the **first fully
commercial, fully closed ecosystem** in the series: Free / Pro / Team /
Team+ SaaS tiers plus a paid Desktop app, with no open-source component
at all. Every predecessor had an open core to read, extend or depend on.
(3) It is YAML — and this repository's own W3 wave measured structured
YAML as the **worst** codegen carrier of five (−30.3 pp pooled, −66.7 pp
flow-sensitive, with the strong generator producing non-compiling code in
3 of 3 runs).**

> **GROUNDS (2) AND (3) CORRECTED 2026-08-30 by
> [the Ilograph re-examination](ilograph-ecosystem-reexamined.md), which
> ran the vendor's own validator.** **Ground (2) is FALSE**: Ilograph is
> not fully closed. The vendor publishes `validate-ilograph` on npm under
> the **verbatim MIT grant**, authored "Ilograph LLC", released
> **2025-12-03 — nine months before this note**. The *product* remains
> commercial (pricing re-verified 2026-08-30), but "no open-source
> component at all" is wrong. **Ground (3) is MIS-LOCATED**: the trigger
> is the line shape **`- key: value`**, not YAML. A plain **Markdown**
> bullet list of `- Owner: Alice` is typed `sequence` and scores **Level
> 4 (Precise), 99.22/100, exit 0**; the same bullets without colons score
> `unknown`/Level 1/0 elements. **Cite this note's refusal as ONE
> sufficient ground — (1), not a diagram notation — which is untouched
> and now verified by execution.**

**The finding is the third one, generalized past its occasion. Wrapping
an Ilograph model in `@startuml…@enduml` — the migration mistake — is
typed `sequence` and scored **Level 4 (Precise), 99.62/100, with one
cosmetic finding and exit 0**. The mechanism, verified in the parse:
**the YAML list dash `-` is read as a PlantUML arrow**, the YAML *key*
becomes the target participant, and the YAML *value* becomes the message
label. `- id: Checkout UI` becomes a message to a participant named `id`
labelled `Checkout UI`. The four "participants" recovered were `id`,
`name`, `from` and `to` — YAML keys, not entities.**

**And it gets worse with size, which is the part that matters. Measured
across four model sizes, the composite **rises monotonically** as the
volume of unrecognized YAML grows:**

> **"MONOTONICALLY" CORRECTED 2026-08-30.** Re-measured on a **real
> vendor-authored** file (`lib/aws.ilograph`, shipped with the
> validator — 8175 lines), the composite rises **98.44 → 99.99** across
> 3 → 1438 resources but **dips once** (25 → 40: 99.76 → 99.73). *Rises
> with volume* is the finding; *monotonically* was an artefact of the
> uniform synthetic sample. The real-content ceiling is **99.99,
> displayed as `100.0/100`**, from a file that yields **one participant,
> named `name`**, and 1438 messages.

| resources | level | score | elements | findings | exit |
|---|---|---|---|---|---|
| 3 | 4 | 99.44 | 9 | 1 | 0 |
| 10 | 4 | 99.78 | 23 | 1 | 0 |
| 25 | 4 | 99.81 | 53 | 2 | 0 |
| 40 | 4 | **99.82** | 83 | 3 | 0 |

**A bigger foreign file scores better. That is the sixth instance of the
type-fallback class and by a distance the most severe: not merely a wrong
verdict, but a verdict that improves as the tool understands less. And it
is not an Ilograph property — it is a **YAML** property, and YAML is
simultaneously the carrier this lab ranked last, the serialization
Structurizr uses for its Ilograph export, and one of the most common file
shapes in any repository.**

> **NOT A YAML PROPERTY — corrected 2026-08-30.** It is a property of the
> line shape **`- key: value`**. JSON, TOML and Markdown-without-colons
> all land at `unknown`/Level 1/**0 elements** — the honest outcome. But
> **Markdown bullets that contain a colon reproduce the hazard in full**.
> The correction *widens* the risk: `- Owner: Alice` is ordinary
> Markdown, far commoner in a repository than `.ilograph`. **Any fix for
> the type-fallback class must be validated against the line shape, not
> against a file format.**

*Bounds. Every pumllint claim was executed at `7043819` with default
config on files outside the repo (verified: GEN006/GEN007 stay dormant).
**No Ilograph tool was executed** — it is closed commercial software and
was not licensed or installed, so nothing here reports what its editor
accepts or rejects. **[This was DEBT, not a limitation — corrected
2026-08-30: the vendor's validator was on public npm the whole time, and
one `npm install` retired this bound and the reconstruction bound below.
The editor itself is still unrun.]** The sample model is **reconstructed** from the
published spec's property list, not exported from Ilograph; the spec page
fetched documents `resources`/`perspectives`/`contexts`/`imports` and
their properties **but does not state the serialization format** — that
it is YAML is taken from Structurizr's exporter documentation ("Ilograph
(as YAML)") and is characterized, not verified against Ilograph's own
docs. **[RESOLVED 2026-08-30: verified from a vendor-authored
`.ilograph` file shipped inside `validate-ilograph`. It is YAML.]** Per this session's repository scope **no GitHub repository was
read**, so the unofficial MCP server's actual validation behaviour is
uninspected. **[STILL UNVERIFIED as of 2026-08-30, and now the only claim
in this note resting on description alone.]** Adoption is not measured.*

## 0. Why this ran, and what it is not

Ilograph entered this repository yesterday as a line item: one of the six
formats `structurizr-cli export` writes. That is the whole prior record —
no settled question, no evaluation. So this is a first look, and the
shortest-justified "no" of the nine.

It is worth writing anyway for one reason, and the reason is not
Ilograph. Probing a YAML-shaped artefact surfaced a failure mode that
eight previous evaluations missed because all eight probed *diagram*
notations. §8 is about YAML; Ilograph is how it was found.

Nothing here is queued.

## 1. The ecosystem

### 1.1 What Ilograph is

Ilograph is an **interactive** diagramming tool — web, desktop and a
Confluence Cloud plugin — whose model is declared once and viewed through
multiple lenses. Its spec defines four top-level properties:

- **`resources`** — "an array of resources (the resource tree)". Each has
  a required `name` and optional `subtitle`, `description`, `children`,
  `icon`, `instanceOf`, `abstract`, `layout`, `id`, and styling.
- **`perspectives`** — either **relation** perspectives (`from` / `to` /
  `via`, with `label`, `arrowDirection`, `secondary`) or **sequence**
  perspectives (a `sequence` object with `start` and `steps`, where steps
  use `to`, `toAndBack`, `toAsync`, `restartAt` or `subSequence`).
- **`contexts`** — alternate framings of the same resource tree.
- **`imports`** — composition across files.

The shape is model-plus-views, and it is *deliberately* not a picture
format: resources are declared once, and each perspective is a different
traversal of the same tree, explored interactively rather than rendered
flat. The `instanceOf` / `abstract` pair even gives it a light type
system for repeated resources.

**Sequence perspectives are the one construct that maps** to a pumllint
pack — and even there the mapping is loose: Ilograph's steps carry
`toAsync` and `subSequence`, but there is no activation/deactivation
concept, which is where four of pumllint's eleven base sequence rules
live. **[VERIFIED BY EXECUTION 2026-08-30 — the vendor validator
recognises `start`, `steps`, `toAndBack`, `toAsync`, `restartAt`,
`subSequence` and no `activate`/`deactivate` of any kind.]**

### 1.2 Governance — the first closed ecosystem in the series

| Tier | Price | Notable |
|---|---|---|
| Free | $0 | unlimited public and private diagrams, 14 days history |
| Pro | ~$18–22/mo | custom icons, unlimited history, private sharing |
| Team | ~$25–30/editor/mo | collaboration, unlimited viewers |
| Team+ | custom | SAML 2.0 SSO, **API access** |
| Desktop | ~$11–15/mo | offline, local files, "behind firewalls" |

> **CORRECTED 2026-08-30 — the two paragraphs below are false.**
> `validate-ilograph@0.0.1` is **MIT-licensed**, authored "Ilograph LLC".
> So there **is** source to check a recognizer against (`index.js`,
> shipped, though minified), and the licence-posture question **does**
> have an answer: **MIT, GPL-3.0-compatible**. See
> [the re-examination §2](ilograph-ecosystem-reexamined.md).

No open-source component was found. That is a first: Structurizr DSL is
Apache-2.0, D2 is MPL-2.0, Mermaid, bpmnlint, Archi, Papyrus and LikeC4
are all open, and even the commercial tools in the UML note (SDMetrics,
Sparx, BiZZdesign) sit inside ecosystems with open cores. Ilograph has
none.

The consequence for this project is concrete rather than ideological: a
closed format's grammar is whatever the vendor ships next, there is no
source to check a recognizer against, and the licence posture question
("could we depend on it?") has no answer to give.

### 1.3 Validation and the AI layer

> **CORRECTED 2026-08-30.** The distinction this section missed: Ilograph
> **documents** no validation — literally true, the validator appears
> nowhere in its docs — but the vendor **has published** one,
> `validate-ilograph`, on **2025-12-03**. Everything below that infers
> from the documentation gap to a vendor gap is wrong.

Ilograph documents **no** validation, linting or semantic checking of its
own — the spec is a property-by-property reference with types and
required/optional flags, and no error-reporting behaviour is described.

The only validation tooling found is an **unofficial, community-built
MCP server** offering "real-time validation with detailed error analysis
and suggestions" alongside documentation access and diagram-creation
guidance. Its own description states it is "not affiliated with or
endorsed by Ilograph LLC".

So the pattern differs from every predecessor: Mermaid's niche is
occupied by third parties, D2's is claimed by upstream, BPMN's is
occupied by a mature incumbent — Ilograph's validation story is a
community MCP server for a closed product whose vendor has published no
validator. **[FALSE — the vendor published one on 2025-12-03.]**

**On the no-grader streak:** nothing here grades either, but this is a
weaker data point than its eight predecessors and should be counted as
one. Ilograph ships no validator of its own, so "it does not grade" is
close to vacuous; the unofficial MCP server validates without grading,
which is the only real observation available. The streak holds at nine
with that caveat attached.

> **CAVEAT WITHDRAWN 2026-08-30 — and withdrawing it makes entry nine
> one of the STRONGEST in the streak, not the weakest.** Ilograph ships a
> competent validator (~40 diagnostic templates: duplicate sibling ids,
> dangling references, circular imports, context cycles, unrecognized
> properties) with **three severities** and **zero** occurrences of
> `score`/`grade`/`maturity`/`rating`/`percent`/`quality` in its source.
> Its `--level 0/1/2` is a **severity filter, not a grade**. So the
> observation is the substantive one — a capable validator that **chose**
> not to grade — rather than the vacuous one. **Cite entry nine without
> this caveat.**

## 2. The relationship

```
   Structurizr DSL ──► export ──► Ilograph YAML ──► Ilograph (closed, interactive)
                       │
                       └────────► .puml ──► pumllint
```

Ilograph sits at the end of a branch of the producer chain documented
yesterday — a sibling output of the same exporter, going somewhere
pumllint cannot follow and has no reason to. The two tools share a
supplier and nothing else.

## 3. Overlap

| Concern | pumllint | Ilograph | Reading |
|---|---|---|---|
| Sequence structure | 11 base + 9 codegen rules | sequence perspectives (`start`, `steps`, `toAsync`, `subSequence`) | **Partial**: no activation concept, so SEQ003/SEQ108 and their codegen kin have no counterpart |
| Element identity / reuse | XD001–005 across a batch | `id`, `instanceOf`, `abstract` in the resource tree | Ilograph solves this *in the model*, by construction |
| Relation labelling | SEQ005, STA003, CLS003 | `label` on relations and steps, optional | No checker either side |
| Naming conventions | GEN004, CLS001, ACT005 | `name` required; restricted characters force an explicit `id` | A format constraint, not a quality rule |
| Ambiguity / prose quality | DIM-AMB, codegen lexicons | none | Unoccupied |
| Level / gap report / ratchet | the scoring model | none | Unoccupied (see §1.3 caveat) |

The middle rows repeat a pattern the series has now seen four times: what
pumllint checks as *hygiene*, a model-based tool makes *unrepresentable*
or *required by the schema*. Ilograph's `id`/`instanceOf` handling is the
identity discipline the XD pack enforces, achieved by having a model
instead of a picture.

## 4. Boundaries

1. **Model+perspectives vs diagram.** The unit pumllint reasons about —
   one diagram, one type, one rendered form — is not a unit Ilograph has.
   A perspective is a traversal, not a picture.
2. **Closed vs open.** No source, no grammar guarantee, no dependency
   available. §1.2.
3. **YAML vs a diagram notation.** Which is where §8's finding lives, and
   where W3's carrier evidence bites.
4. **Discovery.** `.ilograph` is outside `PUML_EXTENSIONS` and the scope
   guard reports it honestly (§8.1) — right up until someone wraps the
   content in `@startuml`.

## 5. Sense — four true things

**S1. The refusal is the cleanest in the series and needs no market
judgment.** Not a notation, not open, and made of the carrier this lab
ranked last. Three independent grounds, none of which an adopter could
change.

**S2. The YAML hazard is real, general, and was invisible to eight prior
evaluations.** Every previous probe wrapped a *diagram* language in
`@startuml`. This one wrapped a data format, and the parse degrades
differently: not "some lines were dropped" but "structural punctuation
was read as semantics". The `-` of a YAML list is a PlantUML arrow.

**S3. The scaling result is the sharpest single number the series has
produced.** 99.44 → 99.82 as unrecognized content grows. Every other
instance of the type-fallback class produced *a* wrong verdict; this one
produces a wrong verdict that gets more confident the less it
understands. That inverts the honesty property cap C6 exists to protect.

**S4. Ilograph's identity handling is a small argument for the XD pack's
premise, from an unexpected direction.** `id`, `instanceOf` and `abstract`
exist because a resource referenced from many perspectives must be *one*
resource. That is XD001–005's thesis — one entity, one identity — solved
structurally by a tool that has a model. **[MECHANISM CORRECTED
2026-08-30: it is not solved structurally. It is *linted* — the vendor's
validator reports "Duplicate name or id … used for two or more sibling
resources" — and the vendor's own shipped model fails that check 8 times.
The conclusion survives and is strengthened: identity needs a checker,
exactly as the XD pack assumes.]** pumllint enforces it by
inspection because PlantUML does not.

## 6. Nonsense — five moves to refuse

**N1. An Ilograph reader or pack. Refused three times over.** §1.1
(not a notation), §1.2 (closed), §8 (YAML). No adopter changes any of the
three.

**N2. A YAML front-end of any kind. Refused, and this is the one worth
stating plainly.** **[The refusal stands; its framing is corrected
2026-08-30 — the hazard is the line shape `- key: value`, which Markdown
also produces, so "YAML" was never the right unit to refuse. See the
re-examination §5.4.]** §8 makes YAML input look tempting — "we clearly need
to handle it better". The opposite follows: pumllint has no business
reading YAML at all, and W3 measured why (structured YAML last of five
carriers; the only non-compiles in the single-shot programme). The fix
for §8 is to stop scoring what was not recognized, not to start
recognizing more.

**N3. Building against a closed format. Refused on availability, not
principle.** There is no source to validate a recognizer against and no
guarantee the grammar is stable between releases. Even if everything else
were favourable, this alone would make the pack unmaintainable.

**N4. Reading the unofficial MCP server as an opening. Refused.** A
community-built, explicitly unendorsed validator for a closed product is
evidence that *someone* wanted validation — not that a second one is
wanted, nor that the vendor would tolerate it.

**N5. Treating the Structurizr export link as a pipeline. Refused.**
Structurizr writes Ilograph YAML and `.puml` as *alternative* outputs.
Nobody's `.puml` becomes Ilograph or vice versa; the two branches never
meet, and §2's diagram is a shared supplier, not a chain.

## 7. Fit — graded

### F1 — an Ilograph reader or rule pack. **No.** N1, N3.

### F2 — YAML input generally. **No, and the temptation runs the wrong way.** N2.

### F3 — the YAML-wrapping hazard. **The one real finding, and it belongs to the type-fallback candidate.** §8.2–8.3.

Sixth instance, most severe, and it adds a property none of the previous
five had: **the score rises with unrecognized volume.** Any fix for the
class must be checked against a YAML-shaped file, not only a
foreign-diagram-shaped one — the two degrade differently, and a fix tuned
to the latter would leave this untouched.

### F4 — the no-grader streak. **Holds at nine, with a caveat that weakens it.** §1.3.

Recorded honestly: Ilograph ships no validator, so its non-grading is
close to vacuous. This is the first entry in the streak that should not
be cited without its caveat.

> **CAVEAT WITHDRAWN 2026-08-30.** Ilograph ships a validator; it does
> not grade, by choice. Entry nine is now one of the *strongest* in the
> streak. See §1.3's annotation and
> [the re-examination §3](ilograph-ecosystem-reexamined.md).

### Fit against declared constraints

| Declared constraint | Where the Ilograph fits land |
|---|---|
| **Zero runtime dependencies** | Not reached — F1 fails on the artefact and the licence before any dependency question. |
| **Deterministic product path, no LLM** | Not reached. |
| **Golden score contract** | Material only for F3, which inherits the existing candidate's re-freeze requirement. |
| **Demand-driven / Arc E bar** | F1 fails on **merit** three ways; demand is not the operative gate. |
| **Licence posture** (GPL-3.0-or-later) | ~~**No answer available** — Ilograph is closed commercial software with no open component.~~ **CORRECTED 2026-08-30: the answer is MIT** (`validate-ilograph`), which is GPL-3.0-compatible. Not a blocker — and not proposed as a dependency either. |
| **Claim language is settled** | Unaffected; nothing here proposes a claim. |

## 8. Gap — measured

*Reconstructed sample; see Bounds.*

### 8.1 The extension boundary is honest

```
$ python3 -m pumllint .                      # a directory of .ilograph files
warning: no PlantUML files found in . (looked for .puml, .plantuml, .iuml, .wsd) — nothing was checked
✔ No issues found.                                                    (exit 0)

$ python3 -m pumllint arch.ilograph
warning: 1 file(s) contained no @startuml block and were not checked: arch.ilograph
✔ No issues found.                                                    (exit 0)
```

Both forms of the "nothing was checked" contract, unchanged for the ninth
time.

### 8.2 YAML wrapped in `@startuml` — the mechanism

```
$ python3 -m pumllint wrapped.puml
wrapped.puml:1: [GEN001/minor] Diagram has no title
✖ 1 issue(s): 1 minor                                                 (exit 0)
  type='sequence'  level=4 (Precise)  score=99.62  elements=13
```

The parse shows exactly what happened:

```
participants: {'id': implicit, 'name': implicit, 'from': implicit, 'to': implicit}
messages: 9
  {'source': None, 'target': 'id',   'label': 'Checkout UI',  'line': 3,  'arrow': '-'}
  {'source': None, 'target': 'name', 'label': 'Requests',     'line': 11, 'arrow': '-'}
  {'source': None, 'target': 'from', 'label': 'Checkout UI',  'line': 13, 'arrow': '-'}
  {'source': None, 'target': 'to',   'label': 'OrderService', 'line': 23, 'arrow': '-'}
  …
```

**The YAML list dash is read as a PlantUML arrow.** `- id: Checkout UI`
parses as a message with `arrow: '-'`, target `id` (the YAML key) and
label `Checkout UI` (the YAML value). Nine list items became nine
messages; four distinct keys became four participants. Not one of the
recovered "participants" is an entity in the model — they are the
vocabulary of the file format.

This differs in kind from the five previous instances. Those dropped
lines they could not read and mis-typed on the ones they could. This one
reads *structural punctuation as semantics*, which is why it produces so
much apparent content from a file it understands not at all.

### 8.3 The severity: score rises with unrecognized volume

Same shape, four sizes (`n` resources plus `n−1` relations):

| resources | level | score | elements | findings | exit |
|---|---|---|---|---|---|
| 3 | 4 (Precise) | 99.44 | 9 | 1 | 0 |
| 10 | 4 (Precise) | 99.78 | 23 | 1 | 0 |
| 25 | 4 (Precise) | 99.81 | 53 | 2 | 0 |
| 40 | 4 (Precise) | **99.82** | 83 | 3 | 0 |

Level 4 throughout, exit 0 throughout. The extra findings at 53 and 83
elements are density budgets (GEN009/SEQ011) firing at `minor`, which
moves the composite by fractions and the level not at all.

**The composite improves as the file gets more foreign.** More YAML means
more "messages" with labels, so DIM-AMB and DIM-CMP have more clean
material and the density penalties are too small to matter. Cap C6 exists
to stop a diagram with nothing modelled from claiming a level; nothing
stops a diagram with nothing *understood* from claiming a good score.

### 8.4 What was not measured

No Ilograph tool was run — the sample is reconstructed from the spec's
property list, and its fidelity to a real `.ilograph` file (especially
one emitted by `structurizr-cli export -f ilograph`) is unverified. The
YAML finding was measured on this reconstruction only; it would hold for
any YAML with list items, but no other YAML dialect was tested. Whether
the same mechanism affects JSON, TOML or Markdown wrapped in `@startuml`
is unmeasured and is the obvious next probe if the candidate is ever
picked up.

> **PROBE EXECUTED 2026-08-30, and the answer inverts the expectation.**
> Same model, four carriers: YAML `sequence`/L4/99.8/82 elements; **JSON,
> TOML and Markdown all `unknown`/L1/95.0/0 elements** — the honest
> outcome, so cap C6 works for three of the four. **But Markdown passed
> only because its bullets had no colons.** With colons
> (`- Owner: Alice`) Markdown is typed `sequence` at **Level 4, 99.22,
> exit 0**. The trigger is the line shape `- key: value`, not the file
> format. The reconstruction-fidelity bound is resolved too: a **real
> vendor-authored** `.ilograph` file now exists to test against, and on
> it the composite reaches **99.99**.

## 9. SWOT

Scope: *pumllint's position relative to Ilograph*.

**Strengths (internal, favourable)**

- The extension boundary held honestly for the ninth consecutive
  ecosystem (§8.1).
- Ilograph's `id`/`instanceOf` design independently corroborates the XD
  pack's one-entity-one-identity thesis (§5/S4).

**Weaknesses (internal, unfavourable)**

- The most severe type-fallback instance yet, and the first where the
  verdict *improves* with foreign content (§8.3).
- The class's six instances now degrade in two distinct ways —
  dropped-lines and punctuation-as-semantics — and the existing candidate
  was written against the first.

**Opportunities (external, favourable)**

- None. Third consecutive evaluation with an empty opportunity column,
  and the first where all three refusal grounds are structural rather
  than competitive.

**Threats (external, unfavourable)**

- **The YAML hazard is not confined to Ilograph.** YAML is everywhere;
  `@startuml` is one careless copy-paste away; and the failure is silent,
  confident and improves with size. Of everything measured across nine
  evaluations, this is the one most likely to produce a passing gate on
  content nobody checked.

## 10. Decision, recorded candidates, triggers

**Decision: no Ilograph support of any kind. Three structural refusals,
no demand gate involved. One candidate, and it amends an existing item
rather than adding one.**

**Never build:**

- An Ilograph reader or rule pack (N1, N3) — not a diagram notation,
  fully closed commercial software with no open component, and YAML.
- **A YAML front-end of any kind** (N2) — §8 makes this look needed and
  it is the opposite: the fix is to stop scoring the unrecognized, not to
  recognize more. W3 measured structured YAML last of five carriers.
- Anything premised on the Structurizr→Ilograph export being a pipeline
  into pumllint (N5) — the branches never meet.

**Recorded, not queued:**

1. **Amend the type-fallback candidate again, for a second degradation
   mode.** The ArchiMate entry's candidate 1 (typing confidence, cap C6),
   as amended by the D2 entry (a rule option can silence the last
   objection), was written against foreign *diagram* syntax, which the
   parser drops. YAML degrades differently: **the list dash is read as an
   arrow and keys become participants**, so the parser manufactures
   content rather than losing it — and the composite **rises with
   volume** (99.44 → 99.82 across 3→40 resources). Any fix must be
   validated against a YAML-shaped file as well as a
   foreign-diagram-shaped one. Maintainer self-demand; scoring change;
   inherits the existing candidate's decision and golden re-freeze.
2. ~~**The next probe, if that candidate is picked up**: JSON, TOML and
   Markdown wrapped in `@startuml`. §8.4 — unmeasured, and the mechanism
   suggests they may behave differently again.~~ **DONE 2026-08-30 — they
   do not trigger it; Markdown *with colons* does. The trigger is
   `- key: value`.**
3. ~~**The no-grader streak's first caveated entry** (§1.3) — Ilograph
   ships no validator, so its non-grading is near-vacuous. Cite the
   streak at nine only with this attached.~~ **WITHDRAWN 2026-08-30 — the
   vendor ships a validator that chooses not to grade. Cite entry nine
   without a caveat.**

**Re-litigate on:**

- Nothing that an adopter can bring. All three grounds are structural;
  the only events that would change them are Ilograph open-sourcing a
  core, or shipping a text notation with diagram semantics — neither
  plausible, both recorded so the answer is not re-derived.
- The YAML candidate is not gated on demand at all: it awaits a decision
  on the type-fallback class, which is already recorded as maintainer
  self-demand.

## Related reading

- [The Ilograph ecosystem, re-examined](ilograph-ecosystem-reexamined.md)
  — **runs the vendor's validator this note said did not exist**, and
  corrects grounds (2) and (3), the monotonicity claim, the S4 mechanism
  and the licence-posture answer. Read it alongside this note.
- [The Structurizr DSL ecosystem, re-examined](structurizr-dsl-ecosystem-evaluation.md)
  — where Ilograph first appears, as one of six export targets; §2's
  shared-supplier relationship.
- [The ArchiMate ecosystem, evaluated](archimate-ecosystem-evaluation.md)
  — candidate 1 for the type-fallback class, which §10 amends a second
  time.
- [The D2 ecosystem, evaluated](d2-ecosystem-evaluation.md) — the first
  amendment (a rule option as a silencing mechanism), and the previous
  holder of "quietest wrong verdict".
- [The measured minimum sufficient stack](minimum-sufficient-stack.md) —
  W3's carrier table, where structured YAML places last of five.
- [ROADMAP.md](../ROADMAP.md) — the Arc E bar and the licence posture
  §7 could not answer for a closed product.

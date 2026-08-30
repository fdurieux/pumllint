# The Mermaid ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-27, written against `f806dce` (v0.29.0). The
question as posed: investigate the Mermaid ecosystem, then assess the
boundaries, overlap, fit, gap, sense and nonsense of the different fits
against pumllint's roadmap and ecosystem. Sixth in a series
(Linked.Archi, C4, ArchiMate, BPMN, UML, this).*

**Verdict up front: no sibling stack — and for the first time in this
series the reason is not that the fit is wrong but that someone else
built it, for the notation that already won the niche, while this
project's own measurement says that notation is the weaker carrier.
Mermaid is not an adjacent ecosystem. It is the direct substitute: it
competes for the same slot, in the same repositories, for the same
artefact. That makes this the sharpest of the six evaluations and the one
with the least comfortable finding.**

**Four grounds. (1) *The sibling stack exists.* `@mermaid-lint/cli`
(0.53.1, last published two weeks before this note) is a near-complete
architectural mirror of pumllint: a config file the repo owns, per-rule
severities `off`/`warn`/`error`, inline suppression comments,
`--format json` for CI, an `--fix` autofix, and a GitHub Action posting
inline PR annotations. `@probelabs/maid` (0.0.29, ISC) is a second one.
Their semantic rules are pumllint's rules under other names — `sequenceDiagram`
activations without matching deactivations is **SEQ003**/**SEQ108**,
self-looping edges is **SEQ006**, empty labels is **SEQ005**, duplicate
node IDs is the **XD** identity family. And `mermaid-lint` lints **fenced
diagrams inside Markdown**, which is precisely the capability the
2026-07-26 demand scan declined to build for PlantUML. (2) *Mermaid owns
the niche that scan measured.* It already found Mermaid dominating the
same spec directories 76× and 437×; Mermaid has rendered natively in
GitHub since February 2022 and in GitLab, Notion, Obsidian and VS Code
since, and is characterized as the only format that renders inline in a
README with no build step. (3) *This project's own evidence says the
carrier is worse.* W3 measured Mermaid sequence at **−9.1 pp pooled and
−20.0 pp flow-sensitive** against the PlantUML baseline, with carrier
equivalence refuted. Building for Mermaid would mean building for the
carrier this lab measured as losing, on the axis where its evidence
lives. (4) *Seventh ecosystem, still no grader.* `mermaid-lint` reports
pass/fail per diagram with file, line and message, and produces **no
aggregate score or grade**.**

> *Confirmed by execution 2026-08-30, for **both** linters — and
> **candidate 2's re-check is discharged**: the rule set is unchanged at
> 0.53.1 and has **not** grown into a graded verdict, so the streak
> stands. Execution also showed `duplicate-ids` is the **only**
> error-severity semantic rule, which **sharpens** §3's XD mapping —
> `mermaid-lint` rates identity above everything else it checks.*

**The uncomfortable part is not any of those; it is that the category
claim and the carrier evidence now point in opposite directions.**
pumllint's positioning, settled 2026-07-26, is "deterministic verifiers
for AI-read/AI-written artifacts". Mermaid is where AI-authored diagrams
actually land — by default, at volume, in Markdown. And `mermaid-lint`'s
stated motivation is this project's own thesis, in someone else's words:
*"In agentic engineering workflows — where AI agents are reading your
docs, parsing your architecture diagrams, and generating code alongside
you — your Markdown files are live context. A broken diagram doesn't just
fail a human reader; it injects a parse error into a context window."*
An independent tool reached the category thesis, the rule concepts and
the autofix, in the competing notation, and got to the AI-authored volume
first. The honest reading is that **the category is validated and the
niche is contested** — and that the two facts belong in the record
together, because either alone misleads.**

*Bounds. Every pumllint claim was executed at `f806dce` with default
config on files outside the repo (verified: GEN006/GEN007 stay dormant).
External claims were read on 2026-08-27 from vendor documentation, the npm
registry and web-search summaries, with URLs given. **No Mermaid tool was
executed** — neither linter was installed or run, so the rule mapping in
§3 is read from published rule descriptions, not from paired runs against
equivalent diagrams. Per this session's repository scope **no GitHub
repository was read**, which is a real cost here: both linters, Mermaid
itself and the `mermaider` MCP server are GitHub-hosted, so maintenance
status, star counts, issue activity and actual rule implementations are
all uninspected. `probelabs.com/maid` returned HTTP 403; Maid's details
come from its npm metadata only. `@mermaid-lint/cli`'s npm record shows
**no licence field**, which is unverified rather than absent. Adoption
claims ("LLMs emit Mermaid by default", "the only format that renders
inline") are characterized from secondary sources, not measured.*

## 0. Why this ran, and what it is not

Mermaid carries more prior evidence in this repository than any other
ecosystem in the series — and unlike C4's, it is spread across three
unrelated records:

- **The embedded-PlantUML demand scan (2026-07-26)** measured Mermaid
  dominating the spec-driven directories 76× (`.kiro/`) and 437×
  (spec-kit `plan.md`), and recorded: *"Mermaid support would be a
  sibling stack (parser, corpus, calibration, golden) under the same
  Arc E bar — recorded, not queued."*
- **W3 (the carrier wave)** measured Mermaid sequence as a codegen
  carrier at −9.1 pp pooled / −20.0 pp flow-sensitive, third of five.
- **W3b** found Mermaid's stored-frame deficit did not reproduce beyond
  the equivalence bar, and left a **carrier-deficit reproduction wave**
  recorded, not queued — explicitly *"queue only if a decision comes to
  hang on those two carriers' standing W3 numbers, which today none
  does."*
- **The C4 evaluation (2026-08-27, S4)** qualified the sibling-stack cost
  estimate: Mermaid's C4 plugin is syntax-compatible with C4-PlantUML, so
  a C4 recognizer would largely transfer.

So this is not a first look and not a re-derivation. It asks the question
those four leave open: **the sibling stack was costed and parked — has
anything changed the costing?** Something has, and not in the direction
the parking assumed. §10 records it.

Nothing here is queued.

## 1. The ecosystem

### 1.1 What Mermaid is, and how much of it there is

Mermaid is *"a JavaScript based diagramming and charting tool that renders
Markdown-inspired text definitions to create and modify diagrams
dynamically"*, created by Knut Sveidqvist. Its surface is large and
growing: roughly sixteen standard diagram types — flowchart, sequence,
class, state, ER, Gantt, git graph, user journey, swimlanes, pie,
quadrant, requirement, C4, mindmap, timeline, ZenUML — plus about fifteen
marked experimental or beta (Sankey, XY chart, block, packet, Kanban,
architecture, radar, event modeling, treemap, Venn, Ishikawa, Wardley,
Cynefin, TreeView; **C4 itself is flagged ⚠️**).

Two facts about that surface matter here.

**It is not a superset of what pumllint parses.** Mermaid has sequence,
class and state — three of pumllint's five — and has **no use-case
diagram at all**; its flowchart is not an activity diagram in the UML
sense. So a Mermaid pack would not be "the same rules against a second
syntax": two of five packs would have no target, and a large majority of
Mermaid's own types (Gantt, pie, git graph, mindmap, radar, Wardley…)
have no pumllint counterpart and no obvious modelling-hygiene rules.

**Mermaid itself ships no semantic validation.** Its documentation
describes no built-in validation, linting or semantic checking beyond
parse-error detection — and `mmdc`, the official CLI, is characterized as
unreliable even at that, sometimes exiting successfully and rendering a
diagram with broken syntax. That gap is exactly what the third-party
linters exist to fill.

### 1.2 The linter layer — the entry that decides this evaluation

| | `@mermaid-lint/cli` | `@probelabs/maid` | pumllint |
|---|---|---|---|
| Version / age | 0.53.1, created 2026-06-16, published 2026-08-13 | 0.0.29, created 2025-09-30, published 2026-03-18 | 0.29.0 |
| Licence | **none stated on npm** | ISC | GPL-3.0-or-later |
| Config file | `mermaid-lint.config.js` / `.mermaidlintrc` / `package.json` | — | `pumllint.toml` |
| Severities | `off` / `warn` / `error` | — | 5 levels + `--fail-on` |
| Suppression | ~~`%% mermaid-lint-disable <rule>`~~ **CORRECTED — see below** | — | suppression comments |
| Machine output | `--format json` | "clear diagnostics" | `-f json`, schema-pinned |
| Autofix | `--fix` | "fixing them instantly" | `pumllint fix` |
| CI | GitHub Action, inline PR annotations | CLI for CI/agents | Action + pre-commit hooks |
| **Markdown fences** | **yes** — `"docs/**/*.md"` | yes | **no** |
| **Aggregate verdict** | **none** | none found | levels, gaps, ratchet, badge |

> **CORRECTED 2026-08-30 by [the Mermaid re-examination](mermaid-ecosystem-reexamined.md),
> which installed and ran both linters.** The suppression row was read from
> documentation and is wrong in practice: `%% mermaid-lint-disable <rule>`
> is **rejected** — the rule still fires *and* a `suppression-malformed`
> warning is added. The working form needs `-next-line` **and a reason**:
> `%% mermaid-lint-disable-next-line no-self-loop: intentional retry edge`.
> **`mermaid-lint` requires a justification at the suppression site.**
> Everything else in this table held under execution, and `maid`'s `—`
> cells understate it (it has `--format json`, `--fix[=all]`, a coded rule
> taxonomy and a `render` subcommand). The rule inventory below was read
> correctly: **all eight rules fire, with matching names.**

`mermaid-lint`'s architecture is a two-tier parse — a Rust WASM parser
with the official `mermaid.parse()` API as authoritative fallback — and
its **semantic** rules, distinguished in its own documentation from
syntax checking, are: legacy `graph` keyword, flowcharts lacking a
direction, duplicate or self-looping edges, empty labels,
`sequenceDiagram` activations without matching deactivations, duplicate
class methods, and duplicate node IDs. Its stated purpose for the
distinction is that semantic rules catch diagrams that parse but *"still
mislead"* — which is, word for word, this project's founding
distinction between syntax and semantics.

There is also a Mermaid MCP server for syntax checking and a published
Claude Code skill for Mermaid validation and repair, so the agent surface
is served too.

### 1.3 Adoption — the part that is not close

GitHub added native Mermaid rendering in **February 2022**; any Markdown
file with a `mermaid` code block renders on view. It renders natively in
GitLab, Notion, Obsidian and VS Code. It is characterized as the only
diagram format that renders inline in a GitHub README with no build step,
and as the format *"most LLMs output when asked for a diagram in
markdown"*.

This repository measured the local form of that a year ago without
drawing the conclusion: the demand scan found embedded PlantUML-in-markdown
at 8,068 files against 131,008 standalone `.puml` — and Mermaid
outnumbering PlantUML 76× and 437× in the two spec-driven directories it
sampled. The scan's verdict was "the demand isn't there" *for embedded
PlantUML*. It was not a finding that the embedded niche is small; it was a
finding that PlantUML does not own it.

## 2. The relationship: substitute, not neighbour

Every prior evaluation in this series examined a layer *around* the
artefact — a graph the diagram feeds (Linked.Archi), a method it
expresses (C4), a model it renders (ArchiMate), a runtime it is not
(BPMN), a standard it borrows notation from (UML). Mermaid is none of
those.

```
   the same job, two notations
   ────────────────────────────────────────────────────────
   .puml  ──►  PlantUML renderer   ──►  picture        ← pumllint gates here
   .mmd / ```mermaid fence  ──►  mermaid.js  ──►  picture   ← mermaid-lint gates here
```

Same artefact class, same repositories, same authors, same purpose,
increasingly the same machine authors. The two notations are competing
for one slot, and the gating tools are competing behind them.

That changes what "fit" means. There is no seam to sit on and no
complementarity to claim. The only questions are whether to build for the
other notation, and what to say about the fact that its linter got to the
AI-authored volume first.

## 3. Overlap

### 3.1 Rules — close enough to be uncomfortable

| `mermaid-lint` semantic rule | pumllint | Shared principle |
|---|---|---|
| `sequenceDiagram` activations without matching deactivations | **SEQ003** unbalanced-activation, **SEQ108** codegen-activation-lifecycle | an opened lifeline must close |
| duplicate or self-looping edges | **SEQ006** no-self-message | an edge to itself carries no interaction |
| empty labels | **SEQ005**, **STA003**, **CLS003** unlabelled-* | a meaning-bearing element must say something |
| duplicate node IDs | **XD003** name-case-collision, **SEQ001** identity | one entity, one identity |
| duplicate class methods | *(no analogue; nearest is **CLS005** max-members)* | — |
| flowcharts lacking a direction | *(no analogue — flowchart is not a pumllint type)* | — |
| legacy `graph` keyword | *(no analogue — deprecation lint)* | — |
| — | **DIM-AMB** and the codegen lexicons (SEQ103/105/106/109) | **nothing in `mermaid-lint`** |
| — | levels, gap report, ratchet, badge | **nothing in `mermaid-lint`** |

Four one-to-one correspondences of principle, arrived at independently.
This is the second time in the series (after `bpmnlint`) that a linter
built for another notation converged on this catalog's concepts — and
this time the notation is the direct competitor, which makes it a
sharper signal about the rules and a worse one about the market.

The last two rows are the whole surviving difference. `mermaid-lint` has
"empty labels" — presence. It has nothing about what a label *says*: no
vagueness lexicon, no elision markers, no signature-shape requirement, no
guard evaluability. And it produces no verdict above the finding list.

### 3.2 Types — the pack would not transfer cleanly

| pumllint pack | Mermaid counterpart |
|---|---|
| sequence (11 base + 9 codegen) | `sequenceDiagram` — direct |
| class (5) | `classDiagram` — direct |
| state (3) | `stateDiagram-v2` — direct |
| **use case (3)** | **none** |
| **activity (6)** | flowchart — related, not equivalent (no UML activity semantics) |

Three of five transfer. And Mermaid's own large surface — Gantt, pie, git
graph, mindmap, journey, and fifteen experimental types — is mostly
outside any modelling-hygiene rule set, this one included.

## 4. Boundaries

1. **Substitute, not layer.** §2. There is no complementarity available
   to claim, and claiming one would be false.
2. **Fence-bound vs file-bound.** Mermaid's native home is a fenced block
   inside Markdown; pumllint's discovery is file-extension-based
   (`PUML_EXTENSIONS`), and the embedded-extraction capability was
   demand-tested and declined in 2026-07-26. `mermaid-lint` ships it.
3. **Presence vs content.** The surviving rule-level difference (§3.1):
   both linters check that a label exists; only one checks what it says.
4. **Finding list vs graded verdict.** Seventh ecosystem, unchanged.

## 5. Sense — four true things

**S1. The rule catalog is validated a second time, by the hardest
possible witness.** `bpmnlint` converging was striking because the
notation was distant. `mermaid-lint` converging is more informative
because the notation is a substitute: two teams solving the *same*
problem for competing syntaxes independently reached activation pairing,
self-edge detection, label presence and identity uniqueness. That is
about as strong as external design validation gets.

**S2. The category thesis is corroborated by a competitor's own
motivation.** `mermaid-lint`'s "your Markdown files are live context…
injects a parse error into a context window" is the tooling-landscape
settlement's positioning, written by someone who has never read it. The
category is real and someone else is betting on it too.

**S3. The demand scan's finding needs restating, not revising.** It
concluded that embedded PlantUML has no demand. Correct — and the
stronger reading, available then and drawn now, is that *the embedded
niche is large and PlantUML does not own it*. Those are different
sentences with different consequences, and only the first is in the
record.

**S4. The grading gap survives its most contested test.** Seven
ecosystems, seven validators — Structurizr, LikeC4, SHACL, Archi,
`bpmnlint`, SDMetrics, `mermaid-lint` — and not one produces a level, a
gap report, a ratchet or an aggregate. In a notation with two competing
linters and enormous volume, nobody has built the layer this project's
whole scoring model occupies.

## 6. Nonsense — five moves to refuse

**N1. A Mermaid pack "because the rules already exist". Refused.** Three
of five packs transfer (§3.2), the parser/corpus/calibration/golden cost
is a full sibling stack as costed in 2026-07-26, and the destination
niche has two incumbents, one of which ships the Markdown-fence
capability this project separately declined. The rule overlap makes the
build *look* cheap and does nothing to make it cheap.

**N2. Reading the convergence as market validation. Refused, and this is
the specific trap of this evaluation.** `mermaid-lint` agreeing with the
catalog validates the *design*. It is evidence *against* the build, not
for it — an occupied niche with an independently-derived equivalent
product is the BPMN lesson, one notation closer to home.

**N3. Building for Mermaid on the codegen axis. Refused on this project's
own measurement.** W3 put Mermaid at −9.1 pp pooled / −20.0 pp
flow-sensitive against PlantUML. Whatever else is true, extending the
codegen profile to the carrier this lab measured as weaker, in order to
serve generation quality, is incoherent. (W3b's non-reproduction of the
stored-frame deficit is noted and does not rescue it: the pooled
ordering held, and the recorded reproduction wave is explicitly gated on
a decision hanging on those numbers.)

**N4. Repositioning around "diagram linting" generically. Refused.** The
claim-language discipline audited clean against UML yesterday; the same
discipline applies here. This tool lints PlantUML. Saying "diagrams"
where the artefact is `.puml` would be the first overclaim in the
project's history, and it would be immediately falsifiable by anyone
pointing at a `.mmd` file.

**N5. Treating Mermaid's C4 compatibility as a wedge. Refused — and
weaker than when it was recorded.** The C4 note's S4 observed that a C4
macro recognizer would largely transfer to Mermaid's C4 plugin. Still
true, still gated behind a C4 pack that is itself gated on census pull —
and Mermaid's C4 is flagged **⚠️ experimental** in its own documentation,
which is a poor foundation for a transfer argument.

## 7. Fit — graded

### F1 — a Mermaid sibling stack. **No. The 2026-07-26 parking now has a stronger reason than cost.**

N1–N3. The costing that parked it assumed an unserved niche; the niche
has two linters, one of them a near-mirror of this product with an
autofix, a GitHub Action and Markdown-fence support. Recorded as a
firmer no, not merely an unqueued one.

### F2 — Markdown-fence extraction for PlantUML. **Unchanged: demand-tested and failed (2026-07-26).**

Noted only because `mermaid-lint` shipping it for Mermaid is the clearest
possible confirmation of the scan's own diagnosis: the capability is
worth building *for the notation that owns the niche*, and PlantUML does
not.

### F3 — Mermaid as a `pumllint fix` output target, or a converter. **No.**

Out of scope by construction (a second notation with its own semantics),
and it would put this project in the business of translating into the
carrier its own evidence ranks lower.

### F4 — the grading layer as the differentiator. **The one thing that survives, and it is positioning, not a build.**

§5/S4. Seven ecosystems, no grader. What this evaluation adds is that the
gap persists even where two linters compete — so it is not an artefact of
thin markets.

### F5 — restating the demand-scan finding. **Recorded, not queued. Documentation only.**

§5/S3. One sentence, and it makes an existing record say what its own
numbers support.

### Fit against declared constraints

| Declared constraint | Where the Mermaid fits land |
|---|---|
| **Zero runtime dependencies** | Not reached — F1 fails before a dependency question (a Mermaid parser would be hand-written anyway, as PlantUML's is). |
| **Deterministic product path, no LLM** | Not reached. |
| **Golden score contract** | Not reached; F1 would require a full second calibration and golden set. |
| **Demand-driven / Arc E bar** | F1 **fails on an occupied niche**, which is the BPMN ground, not the C4 ground. F5 is documentation. |
| **Claim language is settled** | **N4 is a live risk** — the temptation to say "diagrams" rather than "PlantUML" is strongest here. |

## 8. Gap — measured

### 8.1 The boundary is honest, in all three forms

```
$ python3 -m pumllint .                      # a dir of .mmd and .md
warning: no PlantUML files found in . (looked for .puml, .plantuml, .iuml, .wsd) — nothing was checked
✔ No issues found.                                                    (exit 0)

$ python3 -m pumllint seq.mmd
warning: 1 file(s) contained no @startuml block and were not checked: seq.mmd
✔ No issues found.                                                    (exit 0)

$ python3 -m pumllint pasted.puml            # Mermaid source, .puml extension, no @startuml
warning: 1 file(s) contained no @startuml block and were not checked: pasted.puml
✔ No issues found.                                                    (exit 0)
```

Three ways a Mermaid diagram can arrive, three warnings, no exit-code
movement, no implied coverage. The scope guard holds even against a
plausible user error (Mermaid saved with a `.puml` extension).

### 8.2 The one case that is not honest — and one finding in it is right

Mermaid source *wrapped* in `@startuml…@enduml` — the mistake a user
migrating between notations would actually make:

```
wrapped.puml:1: [GEN001/minor]   Diagram has no title
wrapped.puml:3: [SEQ002/minor]   Participant 'Checkout' is declared but never used
wrapped.puml:4: [SEQ002/minor]   Participant 'OrderService' is declared but never used
wrapped.puml:5: [SEQ001/critical] Participant 'UI' is used but never declared
wrapped.puml:5: [SEQ001/critical] Participant 'OS' is used but never declared
wrapped.puml:6: [SEQ003/major]   Lifeline 'OS' is activated here but never deactivated
wrapped.puml:7: [SEQ009/minor]   Return 'orderId' from 'OS' to 'UI' pairs with no preceding call
✖ 7 issue(s): 2 critical, 1 major, 4 minor                            (exit 1)
  type='sequence'  level=3 (Disciplined)  score=69.17  elements=6
```

Five of the seven are artefacts of a syntax collision: Mermaid's
`participant UI as Checkout UI` binds the alias the opposite way from
PlantUML's, so the parser reads "Checkout" as the declared name, SEQ002
fires on participants that do not exist and SEQ001 fires on the ones that
do. SEQ009 likewise misreads `-->>`.

**But SEQ003 is correct.** `activate OS` genuinely has no matching
deactivation, and that is exactly the defect `mermaid-lint` names as
*"`sequenceDiagram` activations without matching deactivations"*. One
rule of seven is right, for the right reason, in the other notation — a
small confirmation of §3.1 obtained by accident.

Recorded as an observation rather than a candidate: unlike the
type-fallback class, this needs a user to actively wrap foreign syntax in
PlantUML delimiters, and the honest forms in §8.1 cover every way the file
would normally arrive.

### 8.3 What was not measured

Neither Mermaid linter was executed — no paired run against equivalent
diagrams, so §3.1's mapping is read from published rule descriptions. No
count exists of how many of `mermaid-lint`'s rules would fire on a corpus,
nor of how its findings compare to pumllint's on the same model expressed
twice. The adoption claims are characterized from secondary sources; this
note measures no Mermaid-vs-PlantUML prevalence itself, and the one
prevalence figure it cites is the repository's own 2026-07-26 scan.

## 9. SWOT

Scope: *pumllint's position relative to Mermaid*.

**Strengths (internal, favourable)**

- Rule design validated a second time, by a substitute-notation competitor.
- A measured carrier advantage on the codegen axis (W3), which is the axis
  this project's evidence is built on.
- The grading layer unoccupied across seven ecosystems, including this one
  where two linters compete.
- Honest scope guard in all three arrival forms (§8.1).

**Weaknesses (internal, unfavourable)**

- No reach into the niche where AI-authored diagrams actually land.
- The Markdown-fence capability, declined in 2026-07-26, is now a
  demonstrated product feature elsewhere.
- Three of five packs would transfer; the sibling-stack cost stands.

**Opportunities (external, favourable)**

- Only F4 and F5 — positioning and one corrected sentence. This is the
  first evaluation in the series whose opportunity column is honestly
  almost empty.

**Threats (external, unfavourable)**

- **The category is contested by a faster-moving equivalent.**
  `mermaid-lint` went from first publish to 0.53.1 in under ten weeks, in
  the notation with the volume. Nothing obliges it to stay
  findings-only — the grading layer is unoccupied, not unreachable.
- **Carrier drift.** If LLM-emitted Mermaid keeps growing and models get
  better at it, W3's ordering is a measurement of one occasion, and the
  recorded carrier-deficit reproduction wave exists precisely because the
  numbers proved unstable once already.
- **The naming temptation** (N4): this is where "diagram linter" would be
  most convenient and least true.

## 10. Decision, recorded candidates, triggers

**Decision: no Mermaid support, and the 2026-07-26 sibling-stack parking
is upgraded from *unqueued on cost* to *refused on an occupied niche*.
Two documentation candidates recorded, nothing queued.**

**Never build:**

- A Mermaid parser/rule pack (N1–N3) — three of five packs transfer, a
  full sibling stack of parser/corpus/calibration/golden is required, two
  incumbents hold the niche, and this project's own W3 measurement ranks
  the carrier below its current one.
- A PlantUML↔Mermaid converter or Mermaid `fix` output (F3).
- Any repositioning from "PlantUML linter" to "diagram linter" (N4) —
  the claim-language discipline audited clean yesterday and this is where
  it would break first.

**Recorded, not queued:**

1. **Restate the demand-scan finding** — the 2026-07-26 record concludes
   embedded PlantUML has no demand, which is right; its own numbers also
   support the stronger and more useful sentence that *the embedded niche
   is large and PlantUML does not own it*. `mermaid-lint` shipping
   Markdown-fence linting for Mermaid is the confirmation. Documentation
   candidate; no behaviour change.
2. **The convergence record (§3.1)** — second instance after `bpmnlint`,
   and the more informative one because the notation is a substitute.
   Worth citing when the catalog's design is questioned; worth re-checking
   if `mermaid-lint`'s rule set grows, **especially if it grows upward
   into a graded verdict**, which is the one change that would end the
   seven-ecosystem streak from the closest possible range.
3. **The wrapped-Mermaid observation (§8.2)** — recorded as an
   observation, not a candidate: it needs a user to wrap foreign syntax
   in `@startuml`, and every normal arrival form warns honestly.

**Re-litigate on:**

- **`mermaid-lint` or Maid shipping a level, score or maturity verdict** —
  the single event that would contest the differentiator directly, from
  the notation with the volume.
- A concrete adopter with PlantUML *and* Mermaid in one repository asking
  for one gate over both — the only shape in which a Mermaid recognizer
  serves an existing user rather than a new market.
- A carrier wave reversing W3's ordering (the recorded carrier-deficit
  reproduction wave, still gated on a decision hanging on those numbers).
- Mermaid's C4 leaving experimental status *and* the C4 pack's own census
  trigger firing — the compound condition under which S4's transfer
  argument becomes live.

## Related reading

- [Demand scan: PlantUML in markdown specs](demand-scan-embedded-plantuml.md)
  — the 2026-07-26 record this note restates rather than revises, and the
  origin of the sibling-stack parking.
- [The measured minimum sufficient stack](minimum-sufficient-stack.md) —
  W3's carrier table, the source of the −9.1 pp / −20.0 pp figures.
- [The BPMN ecosystem, evaluated](bpmn-ecosystem-evaluation.md) — the
  first convergence finding (`bpmnlint`), and the occupied-niche ground
  N1 reuses one notation closer to home.
- [The C4 model ecosystem, re-examined](c4-ecosystem-evaluation.md) — S4's
  Mermaid-C4 recognizer note, qualified in N5.
- [The UML ecosystem, evaluated](uml-ecosystem-evaluation.md) — the
  claim-language audit N4 is protecting.
- [ROADMAP.md](../ROADMAP.md) — the Arc E bar, the Mermaid sibling-stack
  record, and W3b's carrier-deficit reproduction wave.

# The BPMN ecosystem, evaluated — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-27, written against `eee24ac` (v0.29.0). The
question as posed: investigate the BPMN ecosystem, then assess the
boundaries, overlap, fit, gap, sense and nonsense of the different fits
against pumllint's roadmap and ecosystem. Fourth in a series
(Linked.Archi, C4, ArchiMate, this).*

**Verdict up front: no, on four independent grounds, any one of which
would be sufficient — and this is nonetheless the most *useful* of the
four evaluations, because what it returns is not a market judgment but
the strongest external validation this project's rule catalog has ever
received.**

**The four grounds. (1) *No artefact.* PlantUML has no BPMN diagram type
with BPMN semantics — the standard library carries BPMN icons and
sprites, and native support has been an open request for years. `.bpmn`
is OMG XML, never discovered, and correctly warned about. (2) *No gap.*
`bpmnlint` already exists and is architecturally the same product as this
one: configurable rules, three named presets, `off`/`warn`/`error`
severities, a plugin system, a CLI reporting `✖ 6 problems (6 errors, 0
warnings)`, and live feedback inside the modeler. Twenty-odd built-in
rules. (3) *No generation step to gate.* This is the structural one.
C4, ArchiMate and UML diagrams describe something a human or an agent
then implements; a BPMN file **is** the implementation — deployed to
Zeebe or Flowable and validated by the engine at deploy time. The thesis
`docs/agents.md` rests on — gate the spec before the agent generates from
it — has nothing to gate here. (4) *Measured evidence against the one
remaining fit.* BPMN XML as a codegen carrier was proposed by the
2026-08-11 external review; W3 had already measured the nearest analog,
structured YAML at fixed information, at **−30.3 pp pooled and −66.7 pp
flow-sensitive** against the PlantUML baseline, with the strong generator
producing non-compiling code in 3 of 3 runs — the only non-compiles of
the entire single-shot W1–W4 programme. This repository's own comparison
note already called that "a warning shot for feeding raw enterprise
machine formats (BPMN XML et al.) to generators".**

**What makes it worth writing anyway is §3. `bpmnlint` was built by
people who have never heard of this project, for a different notation, on
a different runtime, and it converged on the same architecture *and the
same rules*. Its `start-event-required`, `end-event-required` and
`conditional-flows` are ACT001, ACT002 and ACT003 — and measured here, a
PlantUML activity diagram carrying exactly those three defects returns
exactly those four findings. Its `no-implicit-start` / `no-implicit-end`
/ `no-implicit-split` family is SEQ001 / SEQ010 / SEQ101's principle
under another name: relying on the tool's implicit behaviour is an
ambiguity hazard, so declare it. Convergent design from an independent
implementation is worth more than any review, because nobody was trying
to agree.**

> **CORRECTED 2026-08-29 by [the BPMN re-examination](bpmn-ecosystem-reexamined.md),
> which executed the paired run this note deferred (§8.4).** Two of the
> three named correspondences hold; **`conditional-flows` is NOT ACT003.**
> It is guarded on the node *already* being conditional-forking, so a
> gateway with **zero** conditions is clean under `bpmnlint:recommended`.
> **It enforces consistency; ACT003 enforces completeness.** The honest
> restatement is **subsumption, not equivalence** — everything
> `conditional-flows` catches ACT003 would also catch, and not the
> converse. The convergence argument survives and is narrower than
> written here.

> **Criterion refined 2026-08-27 (TOGAF) and re-verified 2026-08-29:**
> the claim is that **nothing grades a *description***. Under that
> criterion BPMN is not a counterexample — `bpmnlint` grades nothing at
> all — so the paragraph stands, but the *ordinal* is a period figure:
> the count has since passed six, and the observation is now cited
> **two-sided** (an unoccupied slot beside a mature peer can mean the
> maturity model is the differentiator, or that nobody wanted a number).

**And it is the fifth ecosystem in a row with no grader. `bpmnlint`
reports raw problem counts with severity breakdowns and stops there — no
level, no dimension weighting, no gap report, no ratchet, no aggregate of
any kind. Five independently built validators across five ecosystems and
five technology stacks, and the maturity model still has no competitor.**

*Bounds. Every pumllint claim was executed at `eee24ac` with default
config on files outside the repo (verified: GEN006/GEN007 stay dormant).
External claims were read on 2026-08-27 from package registries, vendor
documentation and web-search summaries, with URLs given. **No BPMN tool
was executed**, and per this session's repository scope **no GitHub
repository was read** — `bpmnlint`'s rule inventory was read from its
published package on unpkg, not from source, and the PlantUML BPMN
situation is characterized from forum and issue *titles* surfaced by
search rather than from their contents, so "long-standing open request"
is a characterization and not a verified status. W3's figures are quoted
from this repository's own frozen records.*

## 0. Why this ran, and what it is not

Unlike ArchiMate, BPMN is not new here. It appears in the record twice,
and both entries matter:

- **As a codegen carrier.** The 2026-08-11 external review recommended
  adding "BPMN 2.x XML and DMN/FEEL to the carrier experiment". The
  evaluation graded that lineup **hypothesis**, noting "No wave touched
  BPMN/DMN/AsyncAPI" and that the nearest analog measured worst.
- **As a spec-graph node.** The same review's platform items — "BPMN/DMN
  carriers, cross-spec verifier, context compiler, coverage metric,
  domain benchmark" — are recorded as staying "with the adopter
  programme — not this repository's scope".

So this note is not a first look and not a re-litigation. It asks the one
question those entries left open: *the platform items were scoped out on
ownership grounds; do they also fail on merit, and what does the ecosystem
itself look like?* The answer to the first is yes, on four grounds. The
answer to the second turned out to be the reason to write it down.

Nothing here is queued. §10 records what would have to become true.

## 1. The ecosystem

### 1.1 The standard, and what kind of artefact it produces

BPMN 2.0 (OMG; 2.0.2 is the current maintenance revision) differs from
every notation evaluated this week in one decisive respect: **it defines
an execution semantics and a serialization that engines run.** A `.bpmn`
file is XML with a defined interchange format, and the layer above it —
Camunda 8 / Zeebe, Flowable, Activiti, jBPM — deploys and executes it,
with vendor extensions carried in their own namespaces (`zeebe:`,
`flowable:`).

That single fact drives §2 and most of §7.

### 1.2 The tool layers

| Layer | Examples | Validation it ships |
|---|---|---|
| **Linter** | **`bpmnlint`** (+ `dmnlint`) | ~25 configurable rules, three presets, `off`/`warn`/`error`, plugin API, CLI |
| **Modeler** | `bpmn-js`, Camunda Desktop/Web Modeler | `bpmnlint` embedded via `bpmn-js-bpmnlint` — live feedback while modelling |
| **Engine** | Camunda 8/Zeebe, Flowable | Model validation **before deployment**; executable-semantics errors are deploy failures |
| **AI layer** | BPMN Copilot, Processes MCP Server, Desktop Modeler MCP plugin, third-party BPMN MCP servers | Generation and orchestration; validation inherited from the modeler/engine |
| **Semantic** | Linked.Archi (`bpmn-shapes`, `bpmn-infra-shapes`) | Post-hoc SHACL conformance of derived RDF |

**`bpmnlint`** is the entry that changes this evaluation. Read against
`pumllint --list-rules`, the resemblance is not thematic, it is
structural:

| Concern | `bpmnlint` | pumllint |
|---|---|---|
| Rule configuration | `.bpmnlintrc`, `extends` + `rules` blocks | `pumllint.toml`, profiles + per-rule options |
| Named presets | `bpmnlint:all`, `:recommended`, `:correctness` | default profile, `codegen` profile |
| Severities | `off` / `warn` / `error` | `info` / `minor` / `major` / `critical` / `blocker`, `--fail-on` |
| Extensibility | `bpmnlint-plugin-{NAME}` | `@register` + `catalog.toml` |
| Editor integration | `bpmn-js-bpmnlint`, live in the modeler | none (LSP is Arc E, wait-for-pull) |
| Terminal summary | `✖ 6 problems (6 errors, 0 warnings)` | `✖ 6 issue(s): 2 major, 4 minor` |
| **Aggregate verdict** | **none** | levels, dimensions, gap report, ratchet, badge |

Its published package carries 27 rule files, two of which (`global.js`,
`helper.js`) are infrastructure — so on the order of 25 rules against
this project's 51, for a notation with one diagram type against this
project's five.

> **CORRECTED 2026-08-29 (same version, so this was a miscount, not
> drift): 28 files = 27 rules + one helper.** `global.js` is **a shipped
> rule**, present in both `all` and `recommended` — and it is the single
> richest correspondence in the catalogue, checking *has a name* + *is
> referenced at least once* + *is unique per type per name*, i.e. the
> label-required family, the orphan family and the XD family in one rule.
> **This note filed its best piece of evidence under "infrastructure" and
> dropped it from the table built to argue the catalogues converge.**


### 1.3 The AI layer — the most developed of the four ecosystems, and pointing the other way

Camunda's 2026 material describes three distinct MCP directions: a **BPMN
Copilot** that generates process diagrams from a description in Web
Modeler; a **Processes MCP Server** that exposes *deployed processes as
MCP tools an agent can call*; and a **Desktop Modeler MCP plugin** letting
Claude Code and similar assistants create and manipulate BPMN models
directly. Third-party BPMN MCP servers emit BPMN 2.0 artefacts openable
in Camunda, Signavio, Visio and Lucidchart.

One line of ecosystem commentary describes the resulting practice as *AI
generating BPMN files directly in the repository, reviewed and versioned
like code* — which is precisely the artefact class this project exists
for: machine-authored specification entering a repo under review. It is
already gated, by `bpmnlint`, in the modeler and in CI.

But the more interesting half is the **Processes MCP Server**, because it
inverts the relationship every other ecosystem has with agents. Camunda's
own framing is that BPMN matters *more* in the age of AI as the
deterministic scaffold that orchestrates agents — the process model calls
the agent, not the other way round. That completes a pattern the previous
three evaluations were building:

| Ecosystem | Agent strategy |
|---|---|
| LikeC4 | a skill teaches the DSL — **prevention by instruction** |
| Structurizr | MCP exposes validation and inspection — **verification** (the `agents.md` shape) |
| ArchiMate | MCP servers enforce the metamodel in the authoring API — **prevention by construction** |
| **BPMN** | **the model orchestrates the agent** — **containment** |

Only Structurizr's is this project's shape. BPMN's is a fourth thing
entirely, and it is the one position from which a diagram linter is least
relevant: when the model is the control flow that *calls* the model,
"is this spec good enough to generate from?" is not a question anyone in
that architecture is asking.

## 2. The structural fact: executed, not implemented

Everything in §7 follows from this, so it is worth stating alone.

```
C4 / ArchiMate / UML          BPMN
────────────────────          ────────────────────────────────
diagram  ──►  human or        .bpmn  ──►  engine  ──►  running
              agent                        (Zeebe,      process
                ↓                          Flowable)
             code                            ↑
                                       deploy-time validation
       ↑
  a gate here has                the artefact IS the program;
  something to gate              there is no downstream
                                 implementation step
```

pumllint's measured claim is about the first column: maturity of a
specification correlates with the executed correctness of code generated
from it (EVIDENCE.md; r ≈ 0.49, a sharp cliff below Level 2). That claim
is *about a generation step*. BPMN has none. A defective BPMN file does
not produce bad generated code — it produces a deploy failure, a stuck
token, or a wrong path at runtime, and those are caught by the engine and
by process tests, not by a spec gate.

This is not a small distinction, and it is not one an adopter can
dissolve. It is why the BPMN answer is a firmer no than the ArchiMate
one, which at least concerned a describing artefact.

## 3. Overlap — the convergence, which is the point

Read `bpmnlint`'s inventory against this project's catalog:

| `bpmnlint` rule | pumllint analogue | Shared principle |
|---|---|---|
| `start-event-required` | **ACT001** missing-start | a flow must declare its entry |
| `end-event-required` | **ACT002** missing-stop | a flow must declare its termination |
| ~~`conditional-flows`~~ | ~~**ACT003** unlabelled-decision-branch, **SEQ007** unlabelled-block-condition~~ | **ROW CORRECTED — see the abstract's note. Measured: subsumption, not equivalence.** |
| `label-required` | **SEQ005**, **STA003**, **CLS003** unlabelled-* | an element that carries meaning must be named |
| `no-disconnected` | **UC001** orphan, **SEQ002** unused-participant, **STA002** unreachable-state | a declared element that connects to nothing is a defect |
| `no-implicit-start` / `no-implicit-end` / `no-implicit-split` | **SEQ001** undeclared-participant, **SEQ010** explicit-participant-order, **SEQ101** codegen-implicit-participant | **relying on the tool's implicit behaviour is an ambiguity hazard — declare it** |
| `no-duplicate-sequence-flows` | **XD** family (identity/duplication across a batch) | the same thing said twice is a defect |
| `superfluous-gateway`, `superfluous-termination` | **SEQ006** no-self-message, **GEN008** note-density | structure that adds no information should go |
| `no-complex-gateway`, `no-inclusive-gateway` | **SEQ008** fragment-nesting-depth, **GEN005/GEN009** budgets | comprehension budgets on constructs that defeat readers |
| `no-overlapping-elements`, `no-bpmndi` | **none** | *layout* concerns — pumllint lints source, not rendering |
| — | **DIM-AMB** and the codegen lexicons | **none in `bpmnlint`** — vague labels are unaddressed |
| — | levels, gap report, ratchet, badge | **none in `bpmnlint`** |

Three readings, in increasing order of importance.

**The core is shared, and neither project copied the other.** Six rows
are genuine one-to-one correspondences of principle. The `no-implicit-*`
row is the striking one: two teams, two notations, two runtimes,
independently concluding that a modelling tool's convenience feature —
auto-creating what you did not declare — is the thing a linter must
report. That is exactly SEQ001's rationale and SEQ101's escalation to
`blocker` in the codegen profile.

**The divergences are explained by the artefact, not by taste.**
`bpmnlint` has layout rules because BPMN files carry diagram-interchange
geometry and a modeler renders them; pumllint has none because PlantUML
lays out for you. pumllint has an ambiguity dimension because its
artefact is prose-bearing and feeds a generator; `bpmnlint` has none
because a BPMN task label is documentation for humans while the execution
semantics live in the attributes.

> **CORRECTED 2026-08-29, and this is the one that matters.** The clause
> after the semicolon is **true of `bpmnlint` core and false of the BPMN
> ecosystem — and it was false six weeks before this note was written.**
> `bpmnlint-plugin-camunda-compat` has shipped `agent-tool-documentation`,
> `agent-tool-output-key` and `agent-fromai-contract` since 2.56.0
> (**2026-07-15**); their stated rationale is that *an LLM reads the text
> and an underspecified label degrades what it does*. **That is DIM-AMB's
> argument, verbatim, in BPMN.** The boundary claim was scoped to a
> *package* and stated about an *ecosystem*. It also narrows ground (3)
> below: a consumption step **did** appear in BPMN — and the ecosystem
> grew this project's dimension to gate it, which **reinforces** the
> refusal rather than weakening it.


**The last two rows are the whole product boundary.** What pumllint has
that `bpmnlint` does not is exactly what §2 says BPMN does not need
(ambiguity, because there is no generation step) and what five ecosystems
running have now failed to build (grading).

Measured, so this is not a reading of names. The same order process as a
PlantUML activity diagram, carrying the three defects `bpmnlint`'s
foundational rules exist for:

```
$ python3 -m pumllint order_defective.puml
order_defective.puml:4: [ACT001/major] Activity flow has no 'start' node — entry point is implicit
order_defective.puml:5: [ACT003/minor] Decision '(Order valid?)' has an unlabelled 'then' branch — write "then (yes)"
order_defective.puml:7: [ACT003/minor] Unlabelled 'else' branch — write "else (no)"
order_defective.puml:8: [ACT002/major] Activity flow never terminates with 'stop' or 'end' (unterminated flow)
✖ 4 issue(s): 2 major, 2 minor                                        (exit 1)
```

The well-formed version scores **Level 4 (Precise) — 100/100**, gapped
only on the codegen profile. Whatever else this evaluation concludes, the
ACT pack is doing on PlantUML activity diagrams what the BPMN ecosystem's
own linter does on BPMN, and arrived there independently.

## 4. Boundaries

1. **Executed vs implemented.** §2. The one boundary that cannot be
   negotiated.
2. **XML vs text-with-layout.** `.bpmn` is an interchange format with
   geometry; `.puml` is a source rendered by a layout engine. Different
   artefact classes with different defect sets, as §3's divergences show.
3. **Occupied vs unoccupied.** BPMN's linting niche is filled by a mature,
   embedded, plugin-extensible tool. This is the first ecosystem in the
   series where that is true.
4. **Discovered vs not.** `.bpmn` is outside `PUML_EXTENSIONS`; the
   warning says so and the exit code does not move.

## 5. Sense — four true things

**S1. `bpmnlint` is the best available evidence that this project's
architecture is right.** Not its market, its *design*. Independent
convergence on configurable rules, named presets, graded severities, a
plugin surface and a terminal summary — plus six rules whose principles
match one-to-one — is a stronger signal than any of the five external
reviews on file, because there was no interaction to bias it.

**S2. The gap `bpmnlint` leaves is exactly the one this project fills,
and it does not apply to BPMN.** No ambiguity dimension, no aggregate
verdict. The first is absent because BPMN needs none (§2); the second is
absent for the fifth ecosystem running, and that one is not
notation-specific.

**S3. The repository already measured the strongest form of the "add BPMN
as a carrier" proposal, and it failed.** W3's structured-YAML arm —
−30.3 pp pooled, −66.7 pp flow-sensitive, 3/3 non-compiles from the
strong generator, the only non-compiles in the single-shot programme — is
the nearest measured analog to feeding enterprise machine formats to a
generator. That is not proof about BPMN XML specifically, and the record
is careful to call the lineup hypothesis; but it is evidence pointing one
way, and it was gathered before anyone asked this question.

**S4. The agent-strategy quadruple is now complete, and BPMN supplies its
most distant corner.** Prevention by instruction, verification,
prevention by construction, containment. Only the second is this
project's shape. Knowing which of the four an ecosystem has chosen
predicts the fit better than anything else these four evaluations
measured — and it is a cheaper question to ask than a full evaluation.

## 6. Nonsense — four moves to refuse

**N1. A BPMN rule pack, in any form. Refused four times over.** §2 (no
generation step), §1.2 (`bpmnlint` occupies the niche), §1.1 (`.bpmn` is
XML, a second artefact class — the identity objection recorded against
`.archimate` yesterday applies identically), and PlantUML's lack of a
BPMN modelled form. There is no version of this that survives.

**N2. Adding BPMN XML as a carrier arm without a wave. Refused on charter
discipline.** The proposal exists in the record and is graded hypothesis.
Any carrier claim needs a pre-registered wave under charter §10 — and W3b
already showed how badly carrier intuitions travel, with carrier-native
frames *hurting* by 10.6–18.2 pp pooled. Adding an arm because a reviewer
suggested it is how a lineup becomes a prior.

**N3. Reading `bpmnlint`'s convergence as a market signal. Refused.** It
validates the design and says nothing about demand for a PlantUML linter.
The C4 note recorded the general form of this error (a competitor's
adoption is not one's own pull); here the temptation is subtler because
the convergence is genuinely flattering.

**N4. "BPMN is popular, therefore adjacent." Refused.** BPMN's popularity
is in a runtime layer this tool does not touch, gated by a linter that
already exists, in an artefact class this project has already declined to
add. Popularity is the weakest form of the adjacency argument and BPMN is
where it would be most tempting.

## 7. Fit — the candidate fits, graded

### F1 — a BPMN rule pack over `.bpmn`. **No, and not wait-for-pull.** N1.

Second consecutive ecosystem to fail on grounds an adopter cannot flip.
Recorded plainly so it is not re-derived from BPMN's market size.

### F2 — a BPMN-over-PlantUML pack. **No — there is nothing to parse.**

PlantUML's BPMN support is icons and sprites, not a modelled form with
BPMN semantics; native support appears to be a long-standing open request
(characterized, not verified — see Bounds). A pack would have to invent
the notation it checks, which is convention-manufacturing in its purest
form. Measured incidentally: a sprite-based BPMN-ish file
(`rectangle` + `-->`) is typed `sequence` at Level 4 — the §8.2 defect
class again, in a fourth notation.

### F3 — BPMN XML as a codegen carrier arm. **Recorded, hypothesis, unchanged.** N2 and S3.

The record already grades it. This note adds only that the ecosystem's own
direction (§1.3) makes it less interesting than when it was proposed:
Camunda's architecture calls agents from the process, so "generate code
from BPMN" is not a workflow the ecosystem is building toward.

### F4 — a cross-spec verifier spanning BPMN, DMN, OpenAPI and diagrams. **Adopter programme, unchanged.**

The 2026-08-11 settlement stands verbatim. Noted here only because
someone reading a BPMN evaluation will think of it.

### F5 — the ACT pack as "BPMN-lite" for teams who do not want BPMN. **Recorded, not queued — and it is a positioning note, not a build.**

The one genuinely interesting residue. §3 shows the ACT pack already
implements `bpmnlint`'s foundational rules for PlantUML activity
diagrams. There exist teams who sketch processes in PlantUML precisely
because they do not want a BPMN toolchain, and for them the ACT pack is
already the linter they would otherwise not have. That is **claim
language, not a feature** — and it would need care, because the
comparison invites the false inference that pumllint checks BPMN. Any use
of it must say "activity diagrams, not BPMN" in the same breath.
It also inherits the DIM-AMB coverage residual recorded 2026-08-26:
activity diagrams carry **no** ambiguity rule, so a vague process scores
a vacuous 100 on a 0.25-weight dimension. Positioning the ACT pack as a
process linter without fixing that would be overclaiming.

### Fit against declared constraints

| Declared constraint | Where the BPMN fits land |
|---|---|
| **Zero runtime dependencies** | Not reached — no candidate survives to a dependency question. |
| **Deterministic product path, no LLM** | Not reached. |
| **Golden score contract** | Only F5 touches scores, and only if the DIM-AMB residual is fixed first. |
| **Demand-driven / Arc E bar** | F1 and F2 **fail on merit, not demand** — an adopter does not flip either. F3/F4 are recorded elsewhere and unchanged. |
| **Claim language is settled** | **F5 needs new claim language before any use**, and it is the risky kind. |

## 8. Gap — measured

### 8.1 The boundary behaves honestly

```
$ python3 -m pumllint order.bpmn
warning: 1 file(s) contained no @startuml block and were not checked: order.bpmn
✔ No issues found.                                                    (exit 0)

$ python3 -m pumllint .
warning: no PlantUML files found in . (looked for .puml, .plantuml, .iuml, .wsd) — nothing was checked
✔ No issues found.                                                    (exit 0)
```

Both forms of the "nothing was checked" contract, on the ecosystem's
native artefact. No coverage is implied that does not exist.

### 8.2 A fourth instance of the honesty-cap defect class

A BPMN-ish sketch drawn with stdlib sprites — `rectangle` declarations
plus plain arrows:

```
  type='sequence'  level=4 (Precise)  score=91.0  elements=5
```

Same mechanism the ArchiMate note characterized yesterday: no recognized
type marker, undecorated arrows, endpoints materialize as implicit
lifelines, cap C6 escaped. `rectangle` is not a type marker; `-->` is
enough.

That makes **four notations** now — C4 (macros + raw arrows), component
diagrams (one `database` keyword), native ArchiMate (one undecorated
arrow), and BPMN-by-sprites (`rectangle` + arrows) — against one standing
candidate. Nothing about the candidate changes; the instance count does,
and it was already past the bar.

### 8.3 What the ACT pack does with the same process

§3's measurement. Four findings on the three-defect version, exit 1;
Level 4 / 100 on the clean one. Recorded here because it is the only
positive measurement in this note and because F5 depends on it.

### 8.4 What was *not* measured, and cannot be from here

No BPMN tool was executed. In particular this note does not compare
`bpmnlint`'s findings against pumllint's on equivalent processes — the
convergence in §3 is read from rule names, documented rationales and this
project's own catalog, not from paired runs. A paired run would be the
honest way to claim the mapping is exact, and it would need a Node
toolchain and a corpus of matched BPMN/PlantUML pairs that does not
exist. The mapping is offered as a reading, and §3's measured half covers
only the pumllint side.

## 9. SWOT

Scope: *pumllint's position relative to the BPMN ecosystem*.

**Strengths (internal, favourable)**

- Independent architectural validation from a shipping tool in a
  neighbouring notation (§3) — the strongest design evidence on file.
- The ACT pack already covers the process-flow rules that ecosystem's own
  linter considers foundational.
- Grading unoccupied for the fifth ecosystem running.
- Honest silence on `.bpmn` (§8.1).

**Weaknesses (internal, unfavourable)**

- Nothing reaches BPMN's artefact, by construction.
- The ACT pack's DIM-AMB coverage hole (no ambiguity rule for activity
  diagrams) undercuts the one positioning claim BPMN suggests.
- A fourth instance of the type-fallback defect class, still unfixed.

**Opportunities (external, favourable)**

- Only F5, and it is claim language rather than a build — with a
  correctness precondition attached.

**Threats (external, unfavourable)**

- **Over-claiming adjacency.** "pumllint does process linting" is one
  careless sentence away from "pumllint checks BPMN", which is false.
  This is the first ecosystem where the positioning risk exceeds the
  build risk.
- **The containment pattern.** If the industry direction is processes
  orchestrating agents rather than specs feeding generators, the gate
  thesis has less surface than the Arc D evidence assumes. That is the
  capability-horizon watch item (2026-08-01) arriving by a different
  road, and it is worth noting that it arrives as an *architectural*
  trend, not a capability one.

## 10. Decision, recorded candidates, triggers

**Decision: no BPMN support of any kind, and no carrier arm. The prior
records stand unchanged. One positioning candidate is recorded with a
correctness precondition.**

**Never build:**

- A BPMN rule pack, over `.bpmn` or over PlantUML — no generation step to
  gate, an occupied niche, a second artefact class, and no BPMN modelled
  form in PlantUML to parse (N1, F1, F2).
- A BPMN XML carrier arm added without a pre-registered wave under
  charter §10 (N2).

**Recorded, not queued:**

1. **The ACT-pack positioning note (F5)** — the ACT pack already
   implements what `bpmnlint` treats as foundational, for teams who
   sketch processes in PlantUML rather than adopt a BPMN toolchain.
   **Claim language, not a feature, and gated on a correctness
   precondition**: the DIM-AMB coverage residual (activity diagrams carry
   no ambiguity rule, so a vague process scores a vacuous 100 on a
   0.25-weight dimension) must be addressed before this is said in
   public, or the claim overstates. Any wording must say "activity
   diagrams, not BPMN" in the same breath.
2. **The convergence record itself (§3)** — worth citing when the rule
   catalog's design is questioned, and worth re-checking if `bpmnlint`'s
   rule set changes materially. It is the only external validation on
   file that nobody solicited.
3. **A fourth instance of the type-fallback defect class (§8.2)** —
   no new candidate; the ArchiMate entry's candidate 1 already covers it,
   and this is recorded so the instance count is not re-derived.

**Re-litigate on:**

- PlantUML gaining a BPMN diagram type with actual BPMN semantics — which
  would create an artefact where today there is none, and is the only
  thing that reopens F2.
- A measured wave establishing that a machine interchange format
  outperforms a diagram carrier for the model→code hop — which would
  overturn S3 and reopen F3. W3's result points the other way, and W3b
  showed carrier intuitions travel badly.
- An adopter running PlantUML activity diagrams as their process
  documentation of record and asking for process-flow rules beyond
  ACT001–006 — which is the F5 constituency showing up, and would also
  make the DIM-AMB residual urgent rather than recorded.

## Related reading

- [The ArchiMate ecosystem, evaluated](archimate-ecosystem-evaluation.md)
  — the previous note; its type-fallback defect class gains a fourth
  instance here, and its agent-strategy triple becomes a quadruple.
- [The BPMN ecosystem, re-examined](bpmn-ecosystem-reexamined.md) — the
  twenty-second note, which executed §8.4's deferred paired run and
  **corrected three claims here**, one of them central. Read it with this
  one.
- [The C4 model ecosystem, re-examined](c4-ecosystem-evaluation.md) — the
  "a competitor's adoption is not your pull" record N3 reuses.
- [Linked.Archi and pumllint, evaluated](linked-archi-evaluation.md) — its
  BPMN SHACL profiles are the semantic layer in §1.2's table.
- [The measured minimum sufficient stack](minimum-sufficient-stack.md) —
  §3's carrier table, the source of S3's figures.
- [The two-stage external project review, evaluated](external-review-evaluation.md)
  — where the BPMN/DMN carrier and spec-graph proposals are graded, and
  the scope boundary §0 starts from.
- [A knowledge graph for pumllint, evaluated](knowledge-graph-evaluation.md)
  — the DIM-AMB coverage residual F5 is gated on.

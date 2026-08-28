# The Structurizr DSL ecosystem, re-examined — boundaries, overlap, fit, gap, sense, nonsense

*Dated evaluation, 2026-08-27, written against `2bac87e` (v0.29.0). The
question as posed: investigate the Structurizr DSL ecosystem, then assess
the boundaries, overlap, fit, gap, sense and nonsense of the different
fits against pumllint's roadmap and ecosystem. Eighth in a series
(Linked.Archi, C4, ArchiMate, BPMN, UML, Mermaid, D2, this).*

**Verdict up front: no — the twice-settled decision stands, and the
re-examination changes its *reason* rather than its answer. Structurizr
DSL has been out of scope since 2026-07-27 ("a different language with
its own toolchain, and adding it would double the surface area") and was
reaffirmed on 2026-08-27 ("nonsense; stronger than in July"). Both
records treated Structurizr as something pumllint might *support*. That
framing is wrong, and correcting it is this note's main contribution:
Structurizr is not a candidate for support, it is a **producer of the
artefact pumllint already gates.** `structurizr-cli export` emits
PlantUML in two dialects — `plantuml/structurizr` and
`plantuml/c4plantuml` — plus Mermaid, D2, DOT, Ilograph and
WebSequenceDiagrams. The relationship is producer→consumer, which none of
the seven predecessors had.**

**Measured on all three export shapes, and the third is the finding.
(1) The C4-PlantUML export lands on cap C6 — `unknown`, 0 elements,
**Level 1 (Sketchy) 98.75** — exactly as the C4 evaluation predicted for
pure-macro C4, an honest silence and a clean cross-check of that note.
(2) The static-view export is typed `sequence` and scored **Level 3
(Disciplined) 85.0**, its only findings three GEN003 inline-skinparam
warnings — true, and about styling the exporter generates and the user
cannot remove. (3) The dynamic-view export with
`plantuml.sequenceDiagram=true` is a *genuine* PlantUML sequence diagram:
typed correctly, parsed correctly, **Level 4 (Precise) 93.57**, and its
three findings are GEN004 naming violations on participants named `1`,
`2` and `3` — because the exporter emits numeric identifiers and GEN004
tests the identifier, not the display name (verified: identifier `'1'`,
display_name `'Single-Page App'`).**

**So: **every Structurizr sequence export trips GEN004 on every
participant, systematically.** And that is the sharpest form the
generated-artefact problem has taken across the series. The ArchiMate
note argued that linting a generated rendering produces findings that
cannot be durably acted on. Here the argument is stronger, because
nothing fails: the type is right, the parse is right, the findings are
*true* — and their only correct fix is upstream in the DSL, where
Structurizr's own inspections already run. A true finding with no
actionable owner is worse than a false one, because it survives review.**

*Bounds. Every pumllint claim was executed at `2bac87e` with default
config on files outside the repo (verified: GEN006/GEN007 stay dormant).
**The three export samples are reconstructed**, not captured from a real
`structurizr-cli` run — the CLI was not installed, and the documentation
pages fetched describe the exporters' properties and output shape but
print no verbatim sample. They are built from the documented constructs
(`@startuml(id=…)`, `skinparam` blocks, `rectangle … <<tag>> as N`,
styled arrows; `!include <C4/…>` with `Person`/`Container`/`Rel`;
numeric participant identifiers) and each renders, but the exact
byte-level output of a real export is unverified — so §8's *mechanisms*
are measured and its *fidelity to real exporter output* is characterized.
Per this session's repository scope **no GitHub repository was read**, so
the exporter source, the DSL grammar and community tooling are
uninspected. Adoption is not measured here.*

## 0. Why this ran, and what it is not

Structurizr is the most-covered ecosystem in this series without ever
having been its subject. It appears in two settled records:

- **2026-07-27 (C4 pack evaluation):** *"Structurizr does check
  completeness — on its own workspaces… Structurizr DSL is out of scope
  for any pack built from this note: it is a different language with its
  own toolchain, and adding it would double the surface area."*
- **2026-08-27 (C4 re-examination):** *"F2 — supporting Structurizr DSL
  or LikeC4. **Nonsense; stronger than in July.**"* — plus correction C3,
  recording that Structurizr ships an MCP server providing DSL
  validation, parsing and inspection to agents.

Both are correct and neither is revisited. What neither examined is the
**export surface**: Structurizr's ability to emit PlantUML, and therefore
its standing as a source of the files pumllint reads. That is this note's
subject, and it is the reason the answer stays "no" while the argument
changes.

One count correction before anything else. Structurizr was the **first**
validator counted in the no-grader streak (C4 note: *"three C4-capable
validators… not one of them grades"*). This note re-examines a member of
that streak; it does not extend it. **The count stays at eight
ecosystems, not nine** — re-confirming Structurizr's non-grading is a
check, not a new data point.

Nothing here is queued.

## 1. The ecosystem

### 1.1 The DSL, the tooling, and two corrections

Structurizr DSL is **Apache-2.0**, created and maintained by Simon Brown,
with a free open-source core (DSL, CLI, Lite) and a paid hosted platform.
Community tooling includes a VS Code extension and a **C4 DSL Language
Server** for LSP-compatible editors.

The CLI's documented command set is `push`, `pull`, `lock`, `unlock`,
`export`, `merge`, `list`, **`validate`** and **`inspect`**.

Two facts follow from that list, both **additions to the record rather
than corrections of it** — the C4 notes are silent on how inspections are
executed, not wrong about it:

- **`inspect` is a documented CLI verb.** Inspections are runnable from
  the command line, not only in the workspace UI or through the MCP
  server. The C4 re-examination listed the 26 inspections without stating
  how they run; this fills that gap and contradicts nothing in it.
- **`validate` and `inspect` are separate commands**, which matters for
  the syntax/semantics distinction this project turns on: `validate`
  checks *"a JSON or DSL workspace for correctness"*, `inspect` runs the
  named inspections. Structurizr therefore ships both halves from one
  CLI — something no other ecosystem in this series does.

### 1.2 The export surface — the part nobody had examined

`structurizr-cli export` writes to PlantUML (two exporters), Mermaid,
WebSequenceDiagrams, DOT, Ilograph and D2, and custom exporters can be
added via `WorkspaceExporter`/`DiagramExporter` on the classpath.

| Exporter | What it emits | Relevant properties |
|---|---|---|
| `plantuml/structurizr` (StructurizrPlantUMLExporter) | PlantUML built from Structurizr's own tags and styles — shapes (rectangle, component, cylinder, folder, hexagon, pipe…), `skinparam` blocks, styled relationships | `plantuml.title`, `plantuml.includes`, **`plantuml.sequenceDiagram`**, `plantuml.animation`, `plantuml.shadow` |
| `plantuml/c4plantuml` (C4PlantUMLExporter) | C4-PlantUML macros, `!include` of the stdlib by default | the same four, plus `c4plantuml.tags`, `.legend`, `.stereotypes`, `.elementProperties`, `.relationshipProperties`, `.stdlib`, `.sprite`, `.shadow` |

`plantuml.sequenceDiagram` is the property that matters most here: set
`true`, a dynamic view exports as *"a UML sequence diagram"*; left
`false` (default), it exports as a collaboration diagram. That is
Structurizr deliberately producing the one artefact form pumllint's
largest and best-evidenced pack — 11 base plus 9 codegen sequence
rules — was built for.

### 1.3 Where it sits in the series

Structurizr has now appeared in four notes under four different
relationships, which is worth stating plainly because each implies a
different answer:

| Note | Structurizr's role |
|---|---|
| C4 pack evaluation (2026-07-27) | the incumbent that bounds the claim ("no tool checks *hand-written* C4-PlantUML") |
| C4 re-examination (2026-08-27) | the AI-axis mover (MCP server with validation + inspection) |
| BPMN / UML / Mermaid / D2 notes | the first member of the no-grader streak |
| **this note** | **the producer of `.puml` that pumllint reads** |

## 2. The relationship: producer → consumer

```
   Structurizr DSL  ──►  validate      (syntax/correctness)
        │                inspect       (~26 named inspections)   ← the model is gated here
        │
        └──►  export ──►  .puml  ──►  pumllint                   ← and again here, on the output
                          .mmd
                          .d2
```

Every previous evaluation asked whether to reach *into* another
ecosystem. This one describes a pipe that already exists and runs in one
direction: Structurizr's model is authored and gated upstream, then
rendered into a file pumllint will happily read.

That produces the question this note actually answers: **what should a
gate do with an artefact that is machine-generated from an already-gated
model?** §8 measures the answer, and §5 states it.

## 3. Overlap

| Concern | pumllint | Structurizr | Reading |
|---|---|---|---|
| Element description / technology completeness | — (no analogue; the C4 pack is unbuilt) | `model.*.description`, `model.*.technology` inspections | **Structurizr's, upstream, on the model** |
| Orphan / disconnected elements | UC001, SEQ002, STA002 | `model.element.disconnected` | Same principle, but Structurizr checks the model and pumllint the rendering |
| Relationship description | SEQ005 unlabelled-message | `model.relationship.description` | Same, split by artefact |
| Naming conventions | GEN004, CLS001, ACT005, UC002 | none — the DSL has identifiers, and the exporter *chooses* them | **§8.3: this is where the overlap goes wrong** |
| Styling discipline | GEN003 inline-skinparam | styles are the DSL's job, emitted by the exporter | **§8.2: true finding, no owner** |
| Ambiguity / prose quality | DIM-AMB, codegen lexicons | none | Unoccupied, and unreachable from a rendering |
| Level / gap report / ratchet | the scoring model | none (re-confirmed) | Unoccupied |

The pattern in the middle four rows is the whole evaluation: where the
two tools check the same concern, Structurizr checks it **on the model,
before export**, and pumllint checks it **on the rendering, after** — at
which point the only party who can act is the exporter.

## 4. Boundaries

1. **Model vs rendering, with the gate already upstream.** ArchiMate's
   version of this boundary was "the `.puml` is a picture of a model held
   elsewhere". Structurizr's is sharper: the model is not merely held
   elsewhere, it is *already inspected* elsewhere, by a tool with ~26
   rules and a CLI verb.
2. **Author's choices vs exporter's choices.** A finding about a
   generated file is only actionable if it concerns something the author
   controls. Participant identifiers and skinparam blocks are not. §8.
3. **Two languages, one direction.** DSL → PlantUML is supported and
   documented; there is no path back. Nothing pumllint reports can reach
   the DSL.
4. **Discovery.** `.dsl` is outside `PUML_EXTENSIONS` — measured honest in
   the C4 note (`warning: no PlantUML files found`), unchanged.

## 5. Sense — four true things

**S1. The producer relationship is real and was missed twice.** Two
settled records treated Structurizr as a support candidate. It is a
supplier. That reframing costs nothing and prevents a whole class of
future confusion, because "should we support Structurizr?" and "what do
we do with Structurizr's output?" have different answers and only the
second is a live question.

**S2. The C4 evaluation's measurement predicts the C4 export exactly.**
That note measured a pure-macro C4 container diagram at Level 1 via the
zero-element cap. The C4PlantUML export lands in the same place —
`unknown`, 0 elements, Level 1, 98.75 — from a different producer. A
dated measurement predicting an unmeasured case correctly is the cheapest
kind of validation and worth recording as one.

**S3. The sequence export is the one place the two tools genuinely
meet — and it is where the problem is clearest.** `plantuml.sequenceDiagram=true`
produces exactly what the SEQ pack was built for; pumllint types it,
parses it and scores it correctly at Level 4. And every finding it
produces is about the exporter. That is not a failure of coverage; it is
coverage arriving at the wrong artefact.

**S4. Structurizr is the only tool in the series shipping both halves
from one CLI.** `validate` for correctness, `inspect` for the named rule
set. Every other ecosystem splits these across tools, or ships only one.
It still does not grade — re-confirmed, and the streak's count is
unchanged at eight because Structurizr was already its first member.

## 6. Nonsense — five moves to refuse

**N1. Supporting the Structurizr DSL. Refused, unchanged, and now for a
better reason.** The 2026-07-27 ground (a second language, doubled
surface area) stands. The stronger ground is §2: Structurizr already
gates its own model with `validate` and `inspect`, so a second checker
for its DSL would duplicate a shipped feature of the tool that owns the
language.

**N2. A "Structurizr export" recognizer or profile. Refused.** Tempting
after §8 — teach pumllint to recognize `@startuml(id=…)` and suppress
GEN003/GEN004 on generated files. It is the wrong fix twice over: it
special-cases one producer among many (the same file shapes arrive from
hand-authoring), and it would encode a third party's output format as a
contract this project must track. The configurable route already exists
(§8.4).

**N3. Reading the export surface as a distribution channel. Refused.**
"Structurizr users produce `.puml`, therefore they are prospective
pumllint users" does not follow: what they produce is generated output
whose defects belong to a model they gate upstream. Volume of artefacts
is not demand for a gate on them — the demand-scan lesson, in a new
costume.

**N4. Treating the systematic GEN004 firing as a rule defect. Refused.**
GEN004 does exactly what its catalog row says: the identifier `1` does
not match the configured pattern. The finding is true. What is absent is
an actor who can act on it. That is a fact about the artefact, not a bug
in the rule, and no change to GEN004 is proposed.

**N5. Any claim that pumllint "checks Structurizr models". Refused.** It
checks a rendering of one, after the fact, and can see nothing the DSL
did not choose to emit. The claim-language discipline audited clean
against UML and holds here.

## 7. Fit — graded

### F1 — supporting the Structurizr DSL. **No, unchanged.** N1.

### F2 — a Structurizr-export recognizer/profile. **No.** N2.

### F3 — documenting what pumllint does with Structurizr output. **The one candidate; documentation only.**

A user piping `structurizr-cli export -f plantuml` into pumllint gets one
of three behaviours (§8) and no warning about which. Two of the three are
misleading in ways they will not diagnose: Level 3 on a mistyped static
view, and Level 4 with three systematic naming findings on a correctly
parsed sequence view. A short note — *what to expect when your `.puml` is
generated, and which config knobs neutralise it* — is honest, cheap and
needs no behaviour change. **Recorded, not queued**: it is documentation
for a user this project has not yet observed.

### F4 — the generated-artefact principle, generalized. **Recorded; it is now a pattern, not an anecdote.**

ArchiMate (jArchi/MCP exports), and now Structurizr (`export`), both
produce `.puml` from a gated upstream model. The ArchiMate note refused a
pack partly on this ground. This note supplies the second instance and
the sharper form: the problem is not that findings are wrong, it is that
they are **true and unownable**. Worth stating once as a principle so the
third instance does not need re-deriving.

### Fit against declared constraints

| Declared constraint | Where the Structurizr fits land |
|---|---|
| **Zero runtime dependencies** | Not reached — F1/F2 fail before a dependency question. |
| **Deterministic product path, no LLM** | Not reached. |
| **Golden score contract** | Not reached; F3 is documentation. |
| **Demand-driven / Arc E bar** | F1 fails on **merit** (duplicating a shipped feature of the language's owner). F3 is documentation awaiting an observed user. |
| **Licence posture** | **Passes** — Structurizr DSL is Apache-2.0; nothing here proposes depending on it. Recorded because it was checked. |
| **Claim language is settled** | N5 holds; no correction needed. |

## 8. Gap — measured

*Reconstructed export samples; see Bounds.*

### 8.1 C4-PlantUML export — honest, and a clean cross-check

```
$ python3 -m pumllint structurizr-c4.puml
structurizr-c4.puml:1: [GEN002/info] @startuml has no name
✖ 1 issue(s): 1 info                                                  (exit 0)
  type='unknown'  level=1 (Sketchy)  score=98.75  elements=0
```

Cap C6 holds; the report says there is no modelled content. Identical in
shape to the C4 evaluation's sample A, from a different producer.

### 8.2 Static-view export — mistyped, and the findings are unownable

```
$ python3 -m pumllint structurizr-static.puml
structurizr-static.puml:4:  [GEN003/minor] Inline 'skinparam {' — move styling to the shared theme include
structurizr-static.puml:12: [GEN003/minor] Inline 'skinparam rectangle<<1>> {' — …
structurizr-static.puml:17: [GEN003/minor] Inline 'skinparam rectangle<<2>> {' — …
✖ 3 issue(s): 3 minor                                                 (exit 0)
  type='sequence'  level=3 (Disciplined)  score=85.0  elements=3
```

The `rectangle … as 1` declarations are not read; the styled dotted arrow
is read as a message; two endpoints plus one message make 3 elements, so
cap C6 is escaped — the type-fallback class, sixth notation. And GEN003's
advice — *"move styling to the shared theme include"* — is addressed to
an author who did not write the styling and cannot remove it: the
exporter emits it on every run.

### 8.3 Sequence export — right type, right parse, and still unownable

```
$ python3 -m pumllint structurizr-seq.puml
structurizr-seq.puml:3: [GEN004/minor] Participant name '1' does not match pattern '^[A-Z][A-Za-z0-9]*…'
structurizr-seq.puml:4: [GEN004/minor] Participant name '2' does not match pattern …
structurizr-seq.puml:5: [GEN004/minor] Participant name '3' does not match pattern …
✖ 3 issue(s): 3 minor                                                 (exit 0)
  type='sequence'  level=4 (Precise)  score=93.57  elements=7
```

Everything works. The file is a real PlantUML sequence diagram, typed
correctly, parsed correctly, scored Level 4. And the parse shows why the
findings cannot be acted on:

```
identifier='1'  display_name='Single-Page App'
identifier='2'  display_name='API Application'
identifier='3'  display_name='Database'
```

GEN004 tests the **identifier**; the exporter emits numeric identifiers
and puts the real name in the display slot. So **every Structurizr
sequence export trips GEN004 on every participant**, deterministically,
forever. The rule is right, the finding is true, and the only fix is in
someone else's exporter.

This is the series' clearest statement of the generated-artefact problem.
The ArchiMate note reached it by showing findings would be *overwritten*;
this reaches it by showing findings that are *correct and unownable* even
when nothing malfunctions.

### 8.4 The mitigation that already exists

GEN004 takes a `pattern` option (and `per_kind`). A Structurizr shop
piping exports through pumllint can set a permissive pattern, or disable
GEN004, in `pumllint.toml`. GEN003 likewise takes `allowed` prefixes.
Nothing needs building — which is precisely why F3 is documentation
rather than a feature.

### 8.5 What was not measured

`structurizr-cli` was not installed: the samples are reconstructed from
documented output shape, so byte-level fidelity to a real export is
unverified. `structurizr-cli validate` and `inspect` were not executed,
so nothing here reports what they actually accept or emit. The
collaboration-diagram form of a dynamic view (`plantuml.sequenceDiagram`
left at its `false` default) was not measured at all, and is the more
common case. No adoption figure is offered.

## 9. SWOT

Scope: *pumllint's position relative to the Structurizr DSL ecosystem*.

**Strengths (internal, favourable)**

- A dated prediction confirmed: the C4 note's Level-1 measurement holds
  for a producer it never examined (§8.1).
- The one genuine meeting point — exported sequence diagrams — is the
  pack with the most rules and the best evidence behind it.
- Existing config options already neutralise both systematic findings
  (§8.4), so the problem has a user-side answer today.

**Weaknesses (internal, unfavourable)**

- Two of three export shapes produce misleading or unownable output, and
  nothing warns the user which they are looking at.
- GEN004 fires on 100% of participants in every sequence export — the
  most systematic false-signal pattern measured anywhere in the series.
- The type-fallback class gains a sixth notation.

**Opportunities (external, favourable)**

- Only F3, and it is a documentation note awaiting an observed user.

**Threats (external, unfavourable)**

- **Unownable findings are worse than wrong ones.** A false positive gets
  diagnosed and dismissed; a true finding with no available fix gets
  argued about, then the gate gets disabled. If any Structurizr shop pipes
  exports through pumllint today, this is what they meet.
- **Producer drift.** Nothing obliges Structurizr's exporters to keep
  their current output shape, and this project has no reason to track it —
  which is itself the argument against N2.

## 10. Decision, corrections, triggers

**Decision: no — the twice-settled decision stands. Its reason is
corrected from "a second language we would have to support" to
"a producer of our own input, whose model is already gated upstream".
One documentation candidate; nothing queued.**

**Added to the record** (neither is a correction — the C4 notes are silent
on both points, not wrong about them):

- **`inspect` is a documented Structurizr CLI verb**, alongside
  `validate`. The C4 re-examination listed the inspections without
  stating how they run. Structurizr is the only ecosystem in the series
  shipping syntax validation *and* a named rule set from one CLI.
- **The ecosystem count stays at eight, not nine.** Structurizr was the
  first validator counted in the no-grader streak, so re-confirming it is
  a check rather than a new data point. This is a guard on *this* note's
  framing, not a fix to an earlier one.

**Never build:**

- Structurizr DSL support (N1) — duplicating `validate`/`inspect`, shipped
  by the language's owner.
- A Structurizr-export recognizer or profile (N2) — special-casing one
  producer, and encoding a third party's output format as a contract.
- Any claim that pumllint checks Structurizr models (N5).

**Recorded, not queued:**

1. **A short note on generated `.puml`** (F3) — what to expect from each
   of the three export shapes, and that GEN004's `pattern` and GEN003's
   `allowed` already neutralise the systematic findings. Documentation
   only; awaiting an observed user.
2. **The generated-artefact principle** (F4) — second instance after
   ArchiMate, and the sharper form: the hazard is not that findings are
   wrong but that they are **true and unownable**. Stated once so a third
   instance does not re-derive it.
3. **Type-fallback class, sixth notation** (§8.2) — no new candidate; the
   ArchiMate entry's candidate 1, as amended by the D2 entry, covers it.

**Re-litigate on:**

- An adopter piping `structurizr-cli export` output into pumllint and
  reporting friction — which would turn F3 from a documentation candidate
  into a written page, and is the only trigger here that a user can fire.
- Structurizr's inspections gaining an aggregate verdict — the standing
  streak trigger, unchanged.
- A `plantuml.sequenceDiagram` default flip, or evidence that exported
  sequence diagrams are a common input — which would make §8.3's
  systematic finding a common experience rather than a latent one.

## Related reading

- [Would a C4-PlantUML rule pack fit?](c4-pack-evaluation.md) — where
  Structurizr DSL was first ruled out of scope, and whose Level-1
  measurement §8.1 confirms from a new producer.
- [The C4 model ecosystem, re-examined](c4-ecosystem-evaluation.md) — the
  reaffirmation this note corrects in two places (CLI `inspect`; the
  ecosystem count).
- [The ArchiMate ecosystem, evaluated](archimate-ecosystem-evaluation.md)
  — the first generated-artefact instance, and candidate 1 for the
  type-fallback class.
- [The D2 ecosystem, evaluated](d2-ecosystem-evaluation.md) — the
  amendment to that candidate, and the other export target Structurizr
  writes.
- [Demand scan: PlantUML in markdown specs](demand-scan-embedded-plantuml.md)
  — the "volume of artefacts is not demand" lesson N3 reuses.

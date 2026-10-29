# The ARIS ONE Standard semantic check and pumllint, compared

*Dated evaluation, 2026-10-29, written against `b205cd7` (v0.34.0). The
question as posed: compare the semantic checks in ARIS — specifically the
ONE Standard – Foundation accelerator's check, "Model and Convention
Validation (ONE Standard)" — with those pumllint covers, then draw an
opportunity canvas and a SWOT. Verdict up front: **the two rule sets are
complementary with almost no overlap. All 35 ONE Standard rules test the
repository — attributes, hierarchy, group placement, name identity,
assignment cardinality, occurrence policy, library echo, document linking
— and not one of them tests the flow inside a process model. Everything
pumllint is strongest at (structural well-formedness, labelling, naming
regexes, size limits, scoring, trace, CI) has no counterpart in the check,
and one ONE Standard convention the check leaves unenforced (verb–noun task
names) is ACT006. Nothing is queued; two small rule shapes with a published
precedent are recorded, and one converter gap is handed to aris2puml.**
Bounds and method in §8; the 35 rules are reproduced verbatim in the
appendix, so the comparison can be re-read without the source page.*

## 1. Why this evaluation ran

[docs/business-processes.md](business-processes.md) maps EPC conventions
onto the activity pack and says, twice, that ARIS's own semantic checks
are the tool for the models of record. It never says what those checks
are. This note fixes that: the accelerator's check is the first ARIS rule
set this repository has read rule by rule, and the reading corrects an
assumption the guide carries — that "ARIS semantic checks" cover
event–function alternation and connector pairing. The *stock* ARIS
profiles do; the ONE Standard accelerator's check does not, and an adopter
who installs the accelerator and runs the check it asks for gets no flow
checking at all.

## 2. What the ONE Standard check contains

The ONE Standard – Foundation accelerator (initial release 2026-01-01,
current 1.SR5, 2026-08) ships six assets: a method filter (13 model types,
15 object types, read-only since 1.SR4), a conventions database, a project
template database with its group tree, the semantic check (v1.3.0), the
BPMN Link Modeler (superseded by ARIS 10.2026.04 standard functionality),
and content-type configurations. The check is a single profile that
modellers are required to run before a model is released, and its page
lists exactly 35 rule codes. Severities are Error, Warning and Note. Rule
families, with the architecture each applies to (PM/PO: Process Landscape
L1–L3; EM/EO: End-to-End scenarios L1–L2; LM/LO: library models; BM: BPMN
L4–L5; GM/GO/DO: all):

| Family | Codes | Rule |
|---|---|---|
| Level identification | PM0, EM0 | Infer the model's level from the symbols used and the superior object; Note or Error |
| Required model attributes | PM1, EM1, LM1, BM8 | Description, Person Responsible, Level attribute; validated in every language the administrator configured |
| Required object attributes | PO1, EO1, LO1 | Per-function attributes maintained |
| Superior object | PM5, EM5, LM5 | Exactly one superior object, one level up, occurring in this model; a Level 1 model has none |
| Group placement | PM6, EM6, LM6, PO7, EO7a, EO7b, LO7 | The model, and the definition of each occurred object, sit in the group the template prescribes |
| Name identity | PM9, BM5; PM10, EM10, BM6 | Model name = group name; model name = superior function name (Warnings) |
| Assignment cardinality | PO6, EO6 | Exactly one assignment, of the prescribed model type |
| Occurrence policy | PO9, EO9 | How many occurrence copies a symbol may have, per level |
| Library echo | PO8.a, PO8.b, EO8.a, EO8.b | A document or metric attached to a function must also occur in the Document or Metric library model (Warnings) |
| Required relationship | PO10 | A landscape object must be connected to its sibling Process Category / Area / Process objects |
| Document linking | GM1, GO1, DO1 | Documents attach to functions only via satellite modelling; the document object carries exactly one of the two link attributes |

Three readings of that table.

- **No flow rule.** The BPMN rows (BM5, BM6, BM8) are name identity and
  attributes. There is no rule for a start or end event, gateway pairing,
  lane typing, sequence-flow labels or event naming. Flow checking in ARIS
  comes from the stock BPMN semantic-check profile, a separate product
  feature the accelerator neither bundles nor references.
- **Every rule needs the repository.** Groups, assignments, occurrence
  copies, superior objects and library models are properties of the ARIS
  database, not of any one diagram. A text file has none of them.
- **The check enforces a subset of its own conventions.** The guideline
  pages state rules with no code behind them: exactly one white-box pool
  per L4 model; user and manual tasks only in a role lane, service tasks
  only in a system lane; abstract tasks named verb–noun ("Review Invoice",
  "Create Order"); `is predecessor of` ordering on E2E Level 2; no
  occurrence copies of functions across one level; E2E L1 objects with no
  occurrence copies at all. Of these, verb–noun naming is ACT006 and
  one-pool-per-model is the activity pack's one-diagram-per-pool mapping.

## 3. The comparison, family by family

| ONE Standard family | pumllint counterpart | Verdict |
|---|---|---|
| Level identification | Diagram-type detection from syntax | Analogue in kind only. pumllint has no levels; its "level" is the diagram type, and the maturity level is a different axis |
| Required model attributes | GEN001 title, GEN002 `@startuml` name, GEN006 owner tag, GEN007 requirement link | **Partial.** GEN006 is Person Responsible once a pattern is configured; GEN007 is the process ID. No Description, no Level attribute, no multi-language |
| Required object attributes | SEQ102 typed participant (codegen); ACT006, GEN004, ACT005, CLS001, UC002 naming | **Partial.** The element's name and stereotype are its only attribute surface |
| Superior object; assignment cardinality | `trace --requirements <inventory> --fail-on-unknown-ref --fail-on-uncovered`, over footers aris2puml writes and the manifest it emits | **Partial.** Parent and child existence are checked through the inventory. The one-to-one cardinality is not: two diagrams realising one process ID pass |
| Group placement | none — no rule reads a file path | **Gap** |
| Name identity | GEN010 duplicate name within a file; XD003/XD004 case collisions across files | **Gap.** No rule ties the diagram name to its file stem or its title |
| Occurrence policy | none | **Gap**, repository-specific by nature |
| Library echo | XD001, XD002, XD005 cross-diagram kind and stereotype consistency | **Partial.** Consistency across diagrams is checked; existence in a canonical library diagram is not. The inventory passed to `trace` is the nearest "library" |
| Required relationship | UC001 orphan actor/use case, SEQ002 unused participant, STA002 unreachable state | **Comparable in spirit** on three diagram types. Activity diagrams have no edge relation in the model (`ActivityNode` is a flat list), so no PO10 analogue can reach them |
| Document linking | none | **Gap**, out of scope: PlantUML links and notes are unparsed |

And the reverse direction, which is the larger finding. The following
pumllint families have **no counterpart anywhere in the 35 rules**:

- structural well-formedness — ACT001, ACT002, ACT004, SEQ003, SEQ004,
  SEQ008, SEQ009, STA001, CLS004;
- labelling — ACT003, SEQ005, SEQ007, CLS003, STA003;
- naming by regex — GEN004, ACT005, ACT006, CLS001, UC002;
- size limits — GEN005, GEN008, GEN009, SEQ011, CLS005;
- the codegen profile, SEQ101–SEQ109;
- scoring, `trace`, `fix`, the LSP, the exit-code contract, the GitHub
  action and the pre-commit hooks.

So of pumllint's 43 base rules (52 with the codegen profile), three (UC001, SEQ002, STA002) have a
ONE Standard rule of the same intent, four (GEN001/002/006/007) a partial
one, and the rest none. Of the eleven ONE Standard families, zero are
fully covered, five partially, six not at all — four of those six
unreachable without a repository. The earlier reading in
[docs/business-processes.md](business-processes.md) §1 ("ARIS's own
semantic checks are the tool; nothing here replaces them") stands, and is
now specific: they are different tools for different properties of the
same process.

## 4. Two pipeline consequences

**ONE Standard's L4 is BPMN, not EPC.** Processes are Enterprise BPMN
Collaboration diagrams (one white-box pool, role lanes, tasks, events,
gateways, data objects), with an optional L5 Enterprise BPMN Process
diagram. aris2puml's report-script template is written for EPCs
(function, event, xor, and, or, interface). The mapping in
business-processes.md §2 already states the BPMN correspondence — tasks
for functions, lanes for org units, exclusive gateways as `if`/`switch`,
parallel gateways as `fork`, one diagram per pool — so the emitter needs
nothing; a ONE Standard adopter needs a report script that walks a BPMN
collaboration diagram instead of an EPC. That is aris2puml's, recorded
there, not here. Inclusive gateways land where OR connectors already do.

**L1–L3 are value-added chain diagrams, which is the inventory, not a
diagram.** The Process Landscape is a three-level tree whose leaves are
Process objects with exactly one BPMN assignment each. pumllint has no
VACD and needs none: that tree, exported as the manifest, is what
business-processes.md §7 already proposes passing to `trace` as the
inventory, so that `--fail-on-uncovered` names the landscape entries no
diagram realises. The ONE Standard conventions are the first published
statement that such an inventory exists and is governed.

## 5. Opportunity canvas

| Box | Content |
|---|---|
| Problems | The accelerator governs the repository and leaves the flow inside each L4 model unchecked. Its check runs interactively, on request, before release: no commit gate, no diff, no exit code, no history |
| Users and customers | ARIS CoE teams rolling out ONE Standard; the process owner each model's Person Responsible attribute names; architects consuming the exported PlantUML in repositories and wikis |
| Solutions today | The ONE Standard check for repository conformance; the stock ARIS BPMN profile for flow; bpmnlint on BPMN 2.0 XML (docs/bpmn-ecosystem-reexamined.md). Nothing on the exported view |
| User value | Well-formedness, labelling and naming on every process as a CI gate, with a maturity score per process and a landscape coverage report — none of it duplicating what the CoE's own check already does |
| Solution ideas | Keep the pipeline shape, aris2puml → pumllint. A BPMN collaboration-diagram report template on the aris2puml side. Two rule shapes with a published precedent, recorded in §7, not queued |
| User metrics | Processes linted per run; findings per process over time; landscape entries without a diagram (`--fail-on-uncovered`); processes no feature file names (`--fail-on-unverified`) |
| Adoption strategy | Position as the flow-side complement to the ONE Standard check, never a replacement. Enter through the converter and the copy-ready `conventions.toml` |
| Business challenges | Six of eleven ARIS families are gaps and four are repository-only by nature. The standing risk of being read as "pumllint checks BPMN" (docs/bpmn-ecosystem-evaluation.md) |
| Business benefits | A complementary niche with zero rule overlap against the accelerator, reached with machinery that already ships |
| Budget | Converter template work in aris2puml. Two small rules if an adopter asks. No parser work is needed for the complementarity claim |

## 6. SWOT

**Strengths.**

- Zero duplication with the accelerator's check: every family it lacks
  is one pumllint ships, CI-enforced, with an executable spec in RULES.md.
- The ARIS rule list is readable on one community page; this repository's
  is a pinned, tested document. On the "published oracle" criterion the
  2026-08-29 policy-as-code note set, pumllint is ahead of the incumbent.
- ACT006 enforces a ONE Standard convention that ONE Standard's own check
  does not.
- The converter already refuses what the activity pack cannot represent,
  so the pipeline's boundary is stated, not discovered.

**Weaknesses.**

- Attribute checking stops at four diagram-level tags; there is no
  per-element attribute surface and no Description.
- Activity diagrams still have no edge relation in the model, so no
  relationship rule reaches the one diagram type ARIS processes land on.
- The guide's "Those are ARIS semantic checks" (§8) over-promises for an
  adopter whose only installed profile is the accelerator's.

**Opportunities.**

- Name-identity and path-placement rules are small, cite a published
  precedent (PM9/PM10, PM6), and need no parser work.
- A BPMN front end for aris2puml opens the whole ONE Standard adopter
  base; the mapping is already written.
- Landscape-as-inventory for `trace` is documented and awaits its first
  user; ONE Standard now supplies the governed landscape it assumes.

**Threats.**

- An adopter expecting repository semantics (groups, assignments,
  occurrences) from a text linter.
- Scope creep into an ARIS/BPMN reader, decided against on 2026-08-27.
- ARIS folding its stock BPMN flow profile into the accelerator would
  shrink the complementary space — the one external move that changes
  this note's verdict.

## 7. Decision

- **Nothing to build; nothing queued.** The complementarity needs no code.
- *Recorded, not queued — two rule shapes with a ONE Standard precedent:*
  - **name identity** (PM9/PM10 analogue): the `@startuml` name, the
    `title` and the file stem agree, under a configured normalisation —
    a GEN-range rule, dormant until configured, on the `pattern_option`
    machinery;
  - **path placement** (PM6/PO7 analogue): a diagram's path matches a
    configured pattern derived from its owner tag or its process ID — a
    GEN-range rule reading `Path.as_posix()`, dormant until configured.
  Both are convention-gated by construction, like GEN006/GEN007, and
  both wait for an adopter who keeps processes in a governed tree.
- *Handed to aris2puml:* a report-script template for Enterprise BPMN
  Collaboration diagrams (ONE Standard L4), with pools as diagrams and
  role lanes as swimlanes; inclusive gateways take the OR warning path.
- *Never build*, in this question's vocabulary: a reader for ARIS exports
  (AML, ADF) or BPMN XML — the 2026-08-27 BPMN settlement, unchanged; a
  group tree, assignment or occurrence model inside pumllint; a
  value-added chain diagram type.
- *Re-litigate on:* an adopter running ONE Standard who asks for either
  recorded rule shape with diagrams in hand; the accelerator bundling the
  stock BPMN flow profile (check its release-notes page); aris2puml's
  BPMN template landing, which makes a paired run on a ONE Standard
  example database the next measurement.
- *Annotated in place:* business-processes.md §8's "Those are ARIS
  semantic checks" is read, from this note on, as the stock profiles —
  the sentence is left as written because the demo transcripts beside it
  are drift-guarded and the correction is this record.

## 8. Method and bounds

- The six accelerator pages (semantic check, conventions overview,
  process architecture and modelling, library modelling, group and
  assignment structure, release notes) were fetched on 2026-10-29 by a
  sibling cloud session after `ariscommunity.com` was allowed in the
  environment's network policy; the raw HTML was pulled and the article
  body extracted, so the appendix is verbatim apart from whitespace and
  table scaffolding. All six returned HTTP 200 without login.
- The stock ARIS semantic-check profiles were **not** read; the statement
  that they carry the BPMN flow rules rests on ARIS Community threads
  and the vendor help page's rule-type list (model, object and
  relationship attribute rules, existence rules, allocation rules), and
  is non-load-bearing: the verdict needs only that the accelerator's
  check has none, which the appendix shows.
- No ARIS instance was run. No ONE Standard example database was
  converted or linted; the paired run is the measurement §7 names.
- Repository claims were read at `b205cd7`: `pumllint/rules/catalog.toml`
  for the rule list, `pumllint --list-rules` for severities and
  dimensions, docs/business-processes.md §§1–2, 7–8 for the EPC mapping
  and limits. Baseline 742/742 stdlib.

## Appendix — the 35 rules, verbatim

Source: <https://ariscommunity.com/accelerators/one-standard-foundation-semantic-check>,
fetched 2026-10-29. Each entry: context (architecture; ARIS type),
validation, severity, issue description. The numbering gaps are on the
page.

**PM0 — Level identification.** Process Landscape L1–L3; Models.
Checks the represented model level based on the symbols used. Note or
Error. "Attribute(s) missing: [name of attribute type and the respective
value]".

**PM1 — Required model attribute is missing or not correct.** Process
Landscape L1–L3; Models. Checks whether the Process Landscape Model has
all required attributes correctly maintained; also validates all other
languages defined by the administrator. Error. "[Attribute is]/[Attributes
are] missing: [List] or [Attribute Type NAME] has an incorrect value".

**PM5 — Superior object is not correct.** Process Landscape L1–L3; Models.
Checks whether the Process Landscape Model has the correct superior
object. Error. "This Level [2/3] model must have exactly one superior
object, which is a [Process Area/Process Chain] element that occurs one
level above and in this model. A Level 1 model must not have a superior
object, except for structuring items."

**PM6 — Model is located in the wrong group.** Process Landscape L1–L3;
Models. Checks whether the Process Landscape Model is located in the
correct group. Error. Wrong group but correct group exists: move the
model under Process Landscape at the appropriate level node; correct
group no longer exists: contact the ARIS admin (Name / GUID).

**PM9 — Model name and group name are not the same.** Process Landscape
L1–L3; Models. Warning. "Model name and group name must be identical".

**PM10 — Model name and superior function are not the same.** Process
Landscape L2–L3; Models. Warning. "Model name and superior function name
must be identical".

**PO1 — Required object attribute is missing or not correct.** Process
Landscape L1–L3; Object Occurrence. Checks whether the occurred function
has all required attributes correctly maintained, in all configured
languages. Error.

**PO6 — Wrong assignment(s).** Process Landscape L1–L3; Object Occurrence.
Checks the assigned model type and assignment count. Error. "Too many
models are assigned, the wrong model is assigned, or wrong models are
assigned. Correct convention: Only one assignment of type [model type] is
allowed."

**PO7 — Object definition is in the wrong group.** Process Landscape
L1–L3; Object Occurrence. Error. "The correct group should be: [Group
path]".

**PO8.a / PO8.b — The mapped document / metric does not yet occur in the
library model.** Process Landscape L1–L3; Object Occurrence. Warning.
"You must also add this document [metric] to the Document [Metric]
Library model via occurrence copy."

**PO9 — Object has occurrences which are not allowed.** Process Landscape
L1–L3; Object Occurrence. Error. By symbol type: Process Category — only
one occurrence on Level 1 across the entire Process Landscape; Process
Area — one on Level 1 plus one in the assigned Level 2 model; Process
Group — one on Level 2 plus one in the assigned Level 3 model; Process —
one across the Process Landscape level, additional copies allowed in E2E
Level 2 models.

**PO10 — The object relationships are not correct.** Process Landscape
L1–L3; Object Occurrence. Checks the required connection in this model.
Error. "There is a connection missing between this object and another
[Process Category/Process Area/Process] object".

**EM0 — Level identification.** E2E Business Scenario L1–L2; Models.
Based on the symbols used and superior object occurrences. Note or
Error. "Identified and checked as Level [1/2] model."

**EM1 — Required model attribute is missing or not correct.** E2E L1–L2;
Models. As PM1. Error.

**EM5 — Superior object is not correct.** E2E L1–L2; Models. Error.
"This Level 2 model must have exactly one superior object, which is an
E2E Business Scenario element that occurs on the End-to-End Business
Scenario Map (Level 1)."

**EM6 — Model is located in the wrong group.** E2E L1–L2; Models. Error.
"The correct group should be: [Group path]".

**EM10 — Model name and superior function are not the same.** E2E L2;
Models. Warning.

**EO1 — Required object attribute is missing or not correct.** E2E L1–L2;
Object Occurrence. As PO1. Error.

**EO6 — Wrong assignment(s).** E2E L1–L2; Object Occurrence. As PO6.
Error.

**EO7a / EO7b — Object definition is in the wrong group.** E2E L1 / E2E
L2; Object Occurrence. Warning. L1: move under the End-to-End Business
Scenario group; L2: move under Process Landscape on Level 3.

**EO8.a / EO8.b — The mapped document / metric does not yet occur in the
library model.** E2E L1–L2; Object Occurrence. Warning. As PO8.

**EO9 — Wrong object or symbol reused.** E2E L1–L2; Object Occurrence.
Error. Level 1: no occurrence copies allowed, or the wrong symbol is used.
Level 2: only occurrence copies of Process objects from Process Landscape
Level 3 are allowed.

**LM1 — Required model attribute is missing or not correct.** Library
Models; Models. As PM1. Error.

**LM5 — Superior object is not correct.** Library Models; Models. Error.
"This library model has too many superior objects".

**LM6 — Model is located in the wrong group.** Library Models; Models.
Error.

**LO1 — Required object attribute is missing or not correct.** Library
Models; Object Occurrence. Error.

**LO7 — Object definition is in the wrong group.** Library Models; Object
Occurrence. Warning.

**BM5 — Model name and group name are not the same.** BPMN L4 + L5;
Models. Warning.

**BM6 — Model name and superior function are not the same.** BPMN L4 +
L5; Models. Warning.

**BM8 — Required model attribute is missing or not correct.** BPMN L4 +
L5; Models. Error.

**GM1 — Document files have been linked incorrectly.** All; Models.
Checks whether the model has documents linked via attributes to ADS or
any other file location. Error. "Documents can only be attached to
functions of each level via Satellite Modeling."

**GO1 — Document files have been attached incorrectly.** All; Object
Occurrence. As GM1, on the occurred function. Error.

**DO1 — Document file is not correctly mapped.** All; Function. Checks
whether the mapped document object has the file link attributes correctly
maintained. Error. "The document file must be mapped to
[InfoCarrierObj.Name] either via the attribute [ARIS Document storage
Link 1] for ADS or [Link 1] for other systems. In this case, the link is
missing or both attributes are maintained, which is incorrect."

Required attributes, from the convention pages (the check page names
none): on every model, Description and Person Responsible; on Process
Landscape and E2E models additionally the Level attribute; on Document
objects Document description, owner, type, ID, version, language and
exactly one link; on Metric objects Description, Metric Category, Formula,
Units. Events and gateways carry no attributes beyond the name.

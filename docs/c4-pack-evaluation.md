# Would a C4-PlantUML rule pack fit?

*Dated fit evaluation, 2026-07-27. A supply-side fit analysis plus a small
measured probe of current behavior — **not** a demand measurement; the
demand instrument for this decision is the pilot census
(`tools/pilot_census.py`), which already counts C4 macro calls as a
dialect marker. Verdict up front: **fit verified — wait for census
pull.** The decision is recorded in [ROADMAP.md](../ROADMAP.md) § Settled
questions. External claims below were verified against primary sources on
2026-07-27; behavioral claims were measured on v0.23.0 with default
config. The evaluation originated as an external draft assessment and was
verified element-by-element against this repository and the primary
sources before being recorded.*

## Why this evaluation ran

The Arc C candidate list names "component and deployment first, the
common architecture-documentation forms" as the directions a concrete
user might pull toward. C4-PlantUML is the form in which much of that
demand actually arrives: teams writing container/component-grade
architecture documentation increasingly write it as C4 macros over
PlantUML, not as raw component diagrams. If a census of a real corpus
shows C4 macro usage, this note is the groundwork that makes the
resulting build decision fast.

## The fit case

**1. The defect list is externally authored.** The
[C4 review checklist](https://c4model.com/diagrams/checklist) reads as a
rule specification someone else wrote: the diagram needs a title, a
recognizable diagram type, a stated scope, and a key/legend; every
element needs a name, a clear abstraction level, an understandable
purpose, and technology choices where relevant; every relationship needs
a label describing its intent, a description matching its direction, and
technology/protocol where applicable. (Each item verified present on the
checklist, 2026-07-27.) For governance-minded audiences the traceability
matters as much as the rules: findings cite a published standard rather
than a house style.

**2. The macro surface is closed and regular.** Verified from the
[C4-PlantUML README](https://github.com/plantuml-stdlib/C4-PlantUML/blob/master/README.md):
`Container(alias, label, ?techn, ?descr, ?sprite, ?tags, ?link,
?baseShape)`, `Rel(from, to, label, ?techn, ?descr, ?sprite, ?tags,
?link)`, element families Person/System/Container/Component with
`Db`/`Queue`/`_Ext` variants, four boundary macros, and
`Deployment_Node`/`Node`/`Node_L`/`Node_R`. That is a much smaller
recognition problem than the sequence dialect was
(`parser/sequence.py`, 475 lines), and the macro names are textbook
"type markers no other form uses" for the new-parser pattern.

**3. Nothing checks hand-written C4-PlantUML.** C4-PlantUML is a macro
library with no validation of its own — its README concedes that
PlantUML "does not prevent you from drawing inconsistent diagrams"
(a drawing tool, not a modeling tool, in its own framing). A search on
2026-07-27 surfaced no third-party C4-PlantUML linter (absence of a
find, not proof of absence).

## The market boundary (claim language)

**Structurizr does check completeness — on its own workspaces.** Its
[inspections feature](https://docs.structurizr.com/workspaces/inspections)
flags missing element descriptions (person, software system, container,
component, deployment/infrastructure nodes), missing container and
component technology, missing relationship descriptions and technology,
orphaned elements, and empty views — default severity `error`. It runs
against Structurizr workspaces (DSL/Java model), not against `.puml`
files.

The claim this permits: **no tool checks hand-written C4-PlantUML
files** — teams get Structurizr's checks only by migrating to its
workspace format. The claim it forbids: "nothing on the market checks
C4 completeness." Pitch material must use the narrow form. Structurizr
DSL support is out of scope for any pack built from this note: it is a
different language with its own toolchain, and adding it would double
the surface area.

## Measured: what v0.23.0 does with C4 input today

Three hand-written samples (appendix), linted and scored with default
config. Results are deterministic and reproducible.

**Sample A — pure-macro container diagram** with two planted defects: a
`Rel` referencing an undeclared alias (`mainframe`) and a `Container`
with no technology or description. Result: one finding (GEN002, no
diagram name) and **Level 1 (Sketchy), 99/100**, via the
zero-modelled-elements integrity cap (SCORING.md — coincidentally the
cap named C4). Both planted defects invisible: no parser models the
macros, so the diagram has no elements to check.

**Sample B — pure-macro dynamic diagram** (`C4_Sequence.puml` include,
`Rel()`-only relationships). Identical result to A. Notably, the file
was **not** claimed by the sequence recognizer — `Rel()` lines contain
no arrow tokens, so nothing types the file. (An earlier draft of this
evaluation assumed C4 dynamic diagrams would look sequence-ish and
misfire SEQ rules; measured, they do not. The real misfire mechanism is
sample C's.)

**Sample C — macros mixed with raw arrows** (`client --> gateway :
submits payment order` alongside `Person`/`Container` declarations — a
legal and not unusual hand-written style). Result: the arrow lines typed
the file **sequence**, the macros were ignored, and it drew 2× SEQ009
(dashed C4 relationships read as returns pairing with no call) plus
1× SEQ006 (a legitimate C4 self-dependency read as a sequence
self-message) — all three false in C4 semantics — and scored **Level 4
(Precise), 89/100**.

**Read:** on C4 input the current output is misleading in *both*
directions — well-formed C4 under-scores to Level 1 (and, via the
worst-diagram rule, caps its whole model set at Level 1), while
arrow-mixed C4 over-scores as a spurious sequence diagram with false
findings. A pack would not merely add coverage; it would correct wrong
output on an input class the tool currently misreads. This is the
strongest internal motivation on file — *if* the census shows C4.

## Candidate rule catalog (sketch, not a spec)

Recorded so the build starts from something when the trigger fires.
RULES.md Gherkin authoring happens then, under the usual two-phase
discipline — nothing here is specified to acceptance level. Numbering
would mirror the sequence family: base rules `C4001+`, codegen-profile
rules `C4101+` (the existing codegen pack is SEQ101–109). Several
governance rules apply to a new type for free via `applies_to = ["*"]`
(GEN001 title, GEN002 name, GEN003 skinparam, GEN008/GEN009 density and
size guards).

**Tier 1 — base, mechanical, level-independent:** undeclared alias
referenced in a `Rel` (PlantUML silently invents a node); duplicate
alias; orphan element (declared, never related); unlabelled
relationship; missing element description; missing technology on
`Container`/`Component`; missing legend (`SHOW_LEGEND()` /
`LAYOUT_WITH_LEGEND()` absent); self-relationship; relationship label
not a directed verb phrase (lexicon-gated).

**Tier 2 — level-dependent (fires only when the level is confidently
known):** abstraction mixing (`Component()` in a container diagram,
`Container()` in a context diagram); containers from more than one
software system in a single container diagram (scope is explicitly
[one system](https://c4model.com/diagrams/container), verified
2026-07-27); missing or duplicated `System_Boundary` for the system in
scope; externals not marked `_Ext` or drawn inside the boundary;
deployment constructs in static levels (the container page explicitly
scopes clustering/load-balancing out to deployment diagrams).

**Tier 3 — codegen profile (`C4101+`, escalated severity, gated behind
`profiles = ["codegen"]` like SEQ101–109):** technology mandatory and
non-placeholder on every Container/Component; `$techn` mandatory on
inter-container relationships; the codegen vagueness/non-informative
lexicons (the config-overridable `lexicon()` machinery in
`rules/sequence/codegen.py`) applied to labels and descriptions;
description that merely restates the element name; explicit sync/async
typing on queue and external dependencies.

## Known hard parts (recorded so estimation survives)

- **Argument tokenizer.** Commas inside quoted strings, `$tags=`/`$link=`
  named arguments in arbitrary order after positionals, line
  continuations — a small real tokenizer, not a regex split.
- **Level detection.** The main false-positive risk: teams include
  `C4_Container.puml` and draw a context diagram. Explicit-first (a
  config setting or `' pumllint: c4-level=…` pragma), an
  include-plus-macro-population heuristic as fallback, and tier-2 rules
  silent when the level is unknown.
- **Macro indirection.** Teams wrap C4 macros in their own `!procedure`s
  and pull labels from `!$variables`. A config map of alias macros
  covers the common case; full preprocessor resolution would mean
  shelling out to the PlantUML jar, which breaks the zero-dependency
  promise — opt-in at most, mirroring the include-resolution stance.
- **Typing precedence.** C4 macros/includes become the type markers;
  first-typed-wins then prevents raw arrow lines from re-typing the file
  (declarations precede arrows in practice — sample C would have been
  typed at its first `Person(…)` line). Residual edge: arrow-only files
  whose only C4 marker is the `!include` line.

## Sizing against the Arc C pack bar

The largest pack since sequence. For comparison, the activity pack is a
213-line parser plus 162 lines of rules; this needs the tokenizer, level
detection, and roughly twenty rules across three tiers — and the Arc C
bar is deliberately higher than parser + rules: corpus mutation ladders
and clean probes, a deliberate additive golden re-freeze, pilot
regeneration, and ideally an evidence extension (does C4 completeness
move codegen outcomes the way sequence maturity measurably does? — an
Arc D-shaped question, noted, not promised).

## Decision and triggers

**Wait for census pull.** `tools/pilot_census.py` already counts
`Person`/`System`/`Container`/`Rel` macro calls as a dialect marker and
is designed to run first on any real corpus. Build triggers, as recorded
in ROADMAP § Settled questions: material C4 macro usage in a census of a
real corpus, or a concrete user asking. Until then this note is the
record — don't re-derive it.

## Appendix — the measured samples

Sample A (`c4_container.puml` — planted defects: undeclared `mainframe`
alias; `api` container without technology/description):

```plantuml
@startuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml

title Container diagram for Internet Banking System

Person(customer, "Personal Banking Customer", "A customer of the bank")

System_Boundary(c1, "Internet Banking System") {
    Container(web_app, "Web Application", "Java, Spring MVC", "Delivers static content and the SPA")
    Container(spa, "Single-Page App", "JavaScript, Angular", "Provides banking functionality via the browser")
    Container(api, "API Application")
    ContainerDb(database, "Database", "Oracle 19c", "Stores user registration, auth credentials, messages")
}

System_Ext(email_system, "E-Mail System", "The internal Microsoft Exchange system")

Rel(customer, web_app, "Uses", "HTTPS")
Rel(web_app, spa, "Delivers to the customer's browser")
Rel(spa, api, "Uses", "JSON/HTTPS")
Rel(api, database, "Reads from and writes to", "JDBC")
Rel(api, mainframe, "Uses", "XML/HTTPS")
Rel(email_system, customer, "Sends e-mails to")

SHOW_LEGEND()
@enduml
```

Sample B (`c4_dynamic.puml` — pure-macro dynamic diagram):

```plantuml
@startuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Sequence.puml

title Dynamic diagram - sign in flow

Person(customer, "Personal Banking Customer")
Container(spa, "Single-Page Application", "JavaScript and Angular")
Container(api, "API Application", "Java and Spring MVC")
ContainerDb(database, "Database", "Relational Database Schema")

Rel(customer, spa, "Submits credentials to", "HTTPS")
Rel(spa, api, "Submits credentials to", "JSON/HTTPS")
Rel(api, database, "select * from users where username = ?", "JDBC")
Rel(database, api, "Returns user data to", "JDBC")
Rel(api, spa, "Sends back an authentication token to", "JSON/HTTPS")
@enduml
```

Sample C (`c4_mixed_arrows.puml` — macros plus raw arrows; typed
`sequence` today):

```plantuml
@startuml
!include C4_Container.puml

title Payments platform - containers

Person(client, "Corporate Client")
Container(gateway, "Payment Gateway", "Kong", "Routes and authenticates API traffic")
Container(engine, "Payment Engine", "Java 21, Spring Boot", "Validates and executes payment orders")

client --> gateway : submits payment order
gateway --> engine : forwards validated request
engine -> engine : applies sanctions screening

SHOW_LEGEND()
@enduml
```

Measured outputs (v0.23.0, default config, 2026-07-27): A and B →
GEN002 only, Level 1 (99/100), gap text "diagram has no modelled
content"; C → SEQ009 ×2 + SEQ006, Level 4 (89/100); model set over the
three → Level 1 (worst-diagram rule).

Sources:
[C4 review checklist](https://c4model.com/diagrams/checklist) ·
[C4 container diagram](https://c4model.com/diagrams/container) ·
[C4-PlantUML README](https://github.com/plantuml-stdlib/C4-PlantUML/blob/master/README.md) ·
[Structurizr inspections](https://docs.structurizr.com/workspaces/inspections)

# The `ilograph-typescript` package, evaluated — what a type system can and cannot take away from a linter

*Dated evaluation, 2026-08-31, written against `0e43c77` (v0.30.0). The
question as posed: investigate the `ilograph-typescript` package, then
assess the boundaries, overlap, fit, gap, sense and nonsense of the
different fits against pumllint's roadmap and ecosystem. Thirty-seventh in
the series, fourth consecutive note on the Ilograph ecosystem, and the
first to answer a standing objection to pumllint's premise with a
measurement instead of an argument.*

**Verdict up front: no fit — third-party, unlicensed, stale for 3.9 years,
and it authors a format pumllint does not read. The yield is the
measurement. This is diagrams-as-code in a *typed general-purpose
language*, which is the strongest available form of "make defects
unrepresentable rather than check for them" — the move this series has
watched model-based tools make four times. Run against a six-defect
battery under `--strict`, `tsc` rejected **five of six** at compile time,
including **dangling references, which the public API makes structurally
impossible**. The sixth compiled clean: **duplicate names.** And that
dividing line is exact and general — **a type system catches what is a
property of the program's *shape*, and nothing that is a property of its
*values*.** A `--strict`-clean program emits YAML the vendor's own
validator rejects with a **Fatal Error**. Mapped onto pumllint's rules,
the strongest possible unrepresentability argument retires the
declared-vs-referenced class and **leaves the identity, reachability and
ambiguity classes exactly where they were** — which is where most of
pumllint lives.**

*Bounds. `ilograph-typescript@1.0.2` was installed and **compiled and
executed**: six defect cases through `tsc --strict`, two programs emitted
to YAML, and both emissions run through the vendor's `validate-ilograph`.
**Its GitHub repository was not read** — everything here is from the
published npm tarball, so nothing reports the author's intent, issue
history or docs beyond the shipped README. **The Ilograph editor was not
run**, so whether either emitted file renders as intended is unverified;
"valid" here means the vendor validator is silent. The compile battery is
**six hand-chosen cases, not a census** of what the type system does and
does not catch — the shape/value dividing line is a reading of those six
plus the type declarations, and a reader should treat it as a
well-supported generalization rather than an exhaustive proof. The
mapping onto pumllint's rule classes in §5 is **my classification of
pumllint's own rules**, not a measurement of them.*

## 1. What it is, and who it is not

`ilograph-typescript@1.0.2` — **Christian Eder**
(`christian.eder@zuehlke.com`). **Not the vendor.** The Ilograph account
publishes exactly two packages, and this is not one of them.

> *This library allows you to define Ilograph workspaces using TypeScript,
> and to get the corresponding YAML workspace definition as an export.*

**It has no licence.** No `LICENSE` file in the tarball, and **no
`license` field** in its `package.json` — the key is simply absent. That
is not permissive; absent a grant, default copyright reserves everything.

Which gives this ecosystem **four tools with four distinct licence
postures**:

| Tool | Licence |
|---|---|
| `validate-ilograph` (vendor) | **MIT** — grant present |
| `export-ilograph` (vendor) | **All rights reserved** — MIT disclaimer, grant removed |
| MCP server (community) | **MIT** |
| **`ilograph-typescript`** (community) | **none stated** |

The ninth note's ground (2) claimed a uniformly closed ecosystem; the 34th
corrected it to "not fully closed"; the 36th narrowed that to "one
permissively-licensed component". **The accurate statement is that this
ecosystem has no licence posture at all — it has four.**

## 2. The vitality result completes

**All three versions were published on 2022-10-08** — the same day. Never
touched since: **1423 days, 3.9 years**.

| Tool | Last release | Idle |
|---|---|---|
| `export-ilograph` (**vendor**) | 2026-07-26 | **~5 weeks** |
| `validate-ilograph` (**vendor**) | 2025-12-03 | ~9 months |
| MCP server (community) | 2025-06-16 | **440 days** |
| `ilograph-typescript` (community) | **2022-10-08** | **1423 days** |

**Every third-party Ilograph tool found is dead. Only the vendor's
tooling is alive.** Two data points is not a law, but it is now the
consistent shape, and it sharpens the 35th note's rule — *check a
community tool's last commit before citing its existence as evidence of a
live niche* — into something stronger for this ecosystem: **the community
tooling here is archaeology.**

## 3. The compile battery — measured

Six defects, `tsc --strict`, `skipLibCheck: false`.

| # | Defect | `tsc` | Diagnostic |
|---|---|---|---|
| D1 | missing required `name` | **REJECTED** | TS2345 — not assignable to `ResourceProperties` |
| D2 | `style: "dotted"` | **REJECTED** | TS2322 — closed union of 5 |
| D3 | `icon: "…Athena.svgg"` | **REJECTED** | TS2820 — ***"Did you mean `…Athena.svg`?"*** |
| D4 | **dangling reference** | **REJECTED** | TS2345 — `string` not assignable to `Resource` |
| D5 | **duplicate names** | **COMPILES** | — |
| D6 | `backgroundColour:` typo | **REJECTED** | TS2561 — ***"Did you mean `backgroundColor`?"*** |

**D4 is the interesting one.** The internal relation interface does use
`from: string; to: string` — but it is not exported, and the public method
is:

```ts
addRelation(fromResource: Resource, toResource: Resource,
            relationProperties?: Omit<RelationalPerspectiveRelation, 'from' | 'to'>): void
```

`Omit<…, 'from' | 'to'>` **deliberately removes the string form from the
public surface.** You cannot name a resource; you must hand over the
object. So the check that the vendor's validator performs
(`Referenced resource "X" not found in the resource tree`) and that the
community MCP server **entirely lacks** — its worst false negative — is
here not a check at all. It is **unrepresentable**.

Two smaller results worth keeping. `Icon` is a **907-member closed union**
of literal paths, so a mistyped icon is a compile error *with a spelling
suggestion* — **stricter than the vendor's own validator**, which accepts
any string there. And D3/D6 show the compiler giving better repair
guidance than any of the three Ilograph checkers.

## 4. The dividing line, and the end-to-end proof

**D5 is the whole finding.** A type system sees types, and two `Resource`
objects with the same `name` have identical types. Equal *values* are
invisible to it.

The proof, run end to end:

```ts
const a = new Resource({ name: "Athena::CapacityReservation", subtitle: "one" });
const b = new Resource({ name: "Athena::CapacityReservation", subtitle: "two" });
w.resources.push(a, b);
p.addRelation(a, b, { label: "uses" });     // two distinct objects
```

`tsc --strict` — **clean, exit 0.** Emitted:

```yaml
resources:
  - name: Athena::CapacityReservation
    subtitle: one
  - name: Athena::CapacityReservation
    subtitle: two
perspectives:
  - name: relations
    relations:
      - from: Athena::CapacityReservation
        to: Athena::CapacityReservation
        label: uses
```

Vendor validator:

```
3 [Fatal Error] Duplicate name or id "Athena::CapacityReservation" used for two or more sibling resources
```

**And it is worse than a missed check.** `effectiveId` is `id ?? name`, so
two objects the type system knows to be distinct **collapse into one
string** on the way out. `addRelation(a, b)` emitted `from: X` → `to: X` —
**a self-relation the program never expressed.** The type system's
object-identity guarantee is real inside the program and **does not
survive serialization**; nothing carries it across `toYAML()`.

**In fairness: the library is not broken, and the escape hatch works.**
The same program with explicit distinct `id`s emits `from: res-a` →
`to: res-b`, and the vendor validator is **silent**. (Which also confirms
the vendor's rule is about *effective* identity, not raw names — the
duplicate `name` is fine once ids disambiguate.) What is lossy is the
**default** path, silently, at the boundary.

**Coverage, because "unrepresentable" cuts both ways.** `Workspace` models
**2 of the spec's 4** top-level properties — no `contexts`, **no
`imports`**. Sequence steps omit `subSequence`; relations omit `via`. A
closed typed API forbids the defects it anticipated *and* the valid
constructs it did not: with no `imports`, this library cannot express a
multi-file Ilograph model at all.

## 5. The yield — mapped onto pumllint's own rules

This is the standing objection to pumllint's premise, in its strongest
form: *why check for defects when you could make them unrepresentable?*
§3–4 answer it with a measurement rather than a position. Sorting
pumllint's rule classes by the D4/D5 line:

**Shape — a typed authoring layer could retire these.**

| pumllint | why |
|---|---|
| **SEQ001** undeclared participant | exactly D4: reference an object, not a name |
| **GEN001** missing title | a required field, exactly D1 |
| schema/unknown-property concerns | exactly D6 |

**Value — no type system reaches these.**

| pumllint | why |
|---|---|
| **XD001–005** cross-diagram identity | exactly D5 — equal string values across objects |
| **SEQ002** unused participant | a property of the assembled graph, not of any type |
| **STA002** unreachable state | in-degree over the emitted graph |
| **DIM-AMB**, codegen lexicons | natural-language content of a label |
| **GEN009 / SEQ011** density budgets | counts over the whole artefact |

**So the strongest possible unrepresentability argument retires the
declared-vs-referenced class and leaves identity, reachability, ambiguity
and density exactly where they were** — which is where most of pumllint
lives, and which is precisely the class the vendor's own flagship file
fails **eight times**.

**This completes a three-note arc on one claim.** The ninth note read
Ilograph's `id`/`instanceOf` design as corroborating the XD pack's thesis,
*"solved structurally by a tool that has a model"*. The 34th corrected the
mechanism — it is **linted**, and the vendor's own file fails the lint.
This note supplies the third and strongest data point: **even a typed
authoring layer cannot make it structural.** Identity does not need a
checker by accident of tooling. It needs one necessarily.

## 6. Boundaries, overlap, sense, nonsense

**Boundaries.** (1) **Artefact** — authors Ilograph YAML; pumllint reads
PlantUML. (2) **Layer** — it is an *authoring* library, upstream of any
file; pumllint checks files that exist. (3) **Licence** — none granted,
so nothing here is usable regardless. (4) **Liveness** — 3.9 years idle.

**Overlap: none in code.** The overlap is *conceptual*, and §5 is what it
yielded.

**S1. The shape/value line is the most useful thing this ecosystem has
given the roadmap.** It converts "should we make defects impossible
instead of checking?" from a matter of taste into a bounded question with
a measured answer, and the boundary is not close: one of pumllint's rule
classes is on the shape side.

**S2. A closed union beats a validator on its own ground.** 907 typed icon
paths with compiler-generated "did you mean" is better repair guidance
than any of the three Ilograph checkers give. Worth remembering that
*enumerating the legal values* is sometimes strictly better than
*checking* them — where the set is closed and known.

**S3. Guarantees do not survive serialization, and that is general.** The
type system proved `a !== b` and the emitter wrote them as one string. Any
scheme that establishes a property in one representation and then converts
must re-establish it downstream. **That is an argument for a checker at
the artefact, which is where pumllint sits.**

**N1. A TypeScript (or any typed) authoring layer for PlantUML. Refused.**
§5 shows the payoff is one rule class, and §4 shows even that leaks at the
serialization boundary. It would also contradict the zero-dependency
constraint and put a compiler between the author and the diagram.

**N2. Reading D4 as evidence that identity rules could be designed away.
Refused — D5 is the direct counter-example**, measured in the same
battery.

**N3. Anything depending on this package. Refused on licence alone** — no
grant exists — before liveness or artefact are considered.

## 7. Fit — graded

### F1 — any `ilograph-typescript` capability. **No.** Wrong artefact, wrong layer, no licence, 3.9 years idle.

### F2 — the shape/value dividing line. **The result, recorded.** §5. Not a change to pumllint; a bounded answer to a standing objection, and a lens for classifying any future rule.

### F3 — the XD pack's premise. **Confirmed a third and final way.** §5. Identity needs a checker necessarily, not incidentally.

### F4 — the ecosystem's licence record. **Settled at four postures.** §1.

| Declared constraint | Where this lands |
|---|---|
| **Zero runtime dependencies** | Refused before it arises — but note the contrast: this approach requires a compiler and a package tree to produce one diagram. |
| **Deterministic product path, no LLM** | Untouched. |
| **Exit codes 0/1/2** | Untouched here; `tsc` has its own, and §4 shows a clean exit proving nothing about the artefact. |
| **Golden score contract** | Untouched; nothing proposes a scoring change. |
| **Licence posture** (GPL-3.0-or-later) | **No grant at all** — the hardest blocker of the four tools in this ecosystem. |

## 8. SWOT

Scope: *pumllint's position relative to `ilograph-typescript`*.

**Strengths**

- Most of pumllint's rule classes are on the value side of a line that a
  strong type system cannot cross (§5).
- pumllint checks the artefact, which is where guarantees established
  upstream have already been lost (§4, S3).

**Weaknesses**

- The declared-vs-referenced class (SEQ001 and kin) *is* addressable by
  authoring design. Not actionable for PlantUML, but honestly the one
  place a different tool shape would do better.
- Nothing here gives repair guidance as good as TS2820's "did you mean".
  Recorded as an observation about closed value sets, not a defect.

**Opportunities**

- None pursued. §5 is a lens, not a proposal.

**Threats**

- None from this package — unlicensed, idle, wrong artefact.

## 9. Decision

**Decision: no fit, no build, nothing queued. One measured result and one
settled record.**

**Never build:** a typed authoring layer for PlantUML (N1); anything
depending on this package (N3).

**Recorded, not queued:**

1. **The shape/value dividing line** (§5) — a type system catches what is
   a property of the program's shape and nothing that is a property of its
   values. Use it to classify any future rule, and cite it when the
   "make it unrepresentable" objection is raised. Measured on six cases,
   not a census.
2. **Identity needs a checker necessarily** (§5) — the third and strongest
   data point, completing the arc from the ninth note's "solved
   structurally" through the 34th's "actually linted".
3. **The Ilograph ecosystem has four licence postures, not one** (§1), and
   **every third-party tool in it is dead** (§2).

**Re-litigate on:** nothing. All four grounds are structural.

## Related reading

- [The `export-ilograph` package, evaluated](export-ilograph-package-evaluation.md)
  — the vendor's other package; the licence record §1 completes.
- [The Ilograph ecosystem, re-examined](ilograph-ecosystem-reexamined.md)
  — the vendor's validator, used here as the oracle in §4, and the note
  that corrected "solved structurally" to "linted".
- [The unofficial Ilograph MCP server, evaluated](ilograph-mcp-server-evaluation.md)
  — the dangling-reference check it lacks, which §3's D4 makes
  unrepresentable.
- [The Ilograph ecosystem, evaluated](ilograph-ecosystem-evaluation.md) —
  the ninth note, whose S4 this completes.
- [ROADMAP.md](../ROADMAP.md) — the rule classes §5 sorts.

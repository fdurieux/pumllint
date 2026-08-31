# The Ilograph ecosystem, re-examined — the vendor's validator, executed

*Dated evaluation, 2026-08-30, written against `6ac924c` (v0.30.0).
Thirty-fourth in the series and the **fourth re-examination**, after BPMN
(22nd), Mermaid (32nd) and D2 (33rd). The Ilograph ecosystem was settled
ninth (2026-08-27, `7043819`); that note is not re-opened. This one runs
what its bounds said had not been run.*

**Verdict up front: the refusal stands, and every one of its three
grounds needed correcting to get there. Ground (1) — not a diagram
notation — is untouched and now verified rather than read. Ground (2) —
"the first fully commercial, fully closed ecosystem, with no open-source
component at all" — is **FALSE**: the vendor ships an **MIT-licensed**
validator on npm, published 2025-12-03, nine months *before* the ninth
note asserted it did not exist. Ground (3) — "it is a YAML property" — is
**mis-located**: the trigger is the line shape `- key: value`, not the
format, and a plain **Markdown** bullet list reproduces the hazard at
**Level 4 (Precise), 99.22/100, exit 0**. The refusal survives all of
this because it never depended on any of the three being *this* wrong.**

**The headline number.** The validator ships a real vendor-authored
model, `lib/aws.ilograph` — 176 KB, 8175 lines, the AWS service catalogue.
Wrapped in `@startuml…@enduml`, pumllint recovers **one participant,
named `name`**, receiving **1438 messages**, and reports:

```
Level 4 (Precise) — 100.0/100          (composite 99.99, exit 0)
```

*Four of six dimensions score a flat 100.0.* The ninth note measured
99.82 on a 40-resource reconstruction and called that the sharpest number
the series had produced. On real vendor content the composite reaches
**99.99, displayed as `100.0/100`** — a perfect user-facing score for a
file the tool understands not at all.

## Why this ran

The precondition set by the D2 re-examination: *a re-examination is
warranted when a note makes a comparative capability claim about another
tool, because that kind of claim needs the tool **run**, not read.*

The ninth note makes several, and its bounds concede them:

> **No Ilograph tool was executed** — it is closed commercial software and
> was not licensed or installed, so nothing here reports what its editor
> accepts or rejects. The sample model is **reconstructed** from the
> published spec's property list … that it is YAML is taken from
> Structurizr's exporter documentation … and is characterized, not
> verified against Ilograph's own docs.

Two of those bounds turned out to be **debt, not limitation**. The tool
was obtainable the whole time — not the editor, but the vendor's
validator, on the public npm registry, under a permissive licence. One
`npm install` retired both bounds at once, because the validator ships a
real `.ilograph` file with it.

**A correction to my own scan, first.** The bounds scan of 2026-08-30
listed Ilograph as **NOT OBTAINABLE**, and yesterday's Capella turn
restated the reason as distribution form — *"GUI desktop applications
shipped as installers rather than registry packages"*. That is right about
the **editor** and wrong about the **ecosystem**: `validate-ilograph` is an
ordinary npm package with a `bin`, and it is what actually answers the
questions the ninth note left open. This is the **fourth consecutive
correction to that one scan entry**, after the D2 runnability row, the
SysML/DMN-engine omission, and the open-source mislabelling. Every one was
found by an outside request; none by the list.

## 1. What was executed

`validate-ilograph@0.0.1` — `author: "Ilograph LLC"`, maintainer
`ilograph <billy@ilograph.com>`, published **2025-12-03**. The vendor
account publishes exactly two packages (registry search, `total: 2`):
this and `export-ilograph@0.2.5`.

> **SCOPE NOTE added 2026-08-31 by
> [the `export-ilograph` evaluation](export-ilograph-package-evaluation.md),
> which ran that second package.** Nothing in this note is corrected — the
> MIT finding below is scoped to `validate-ilograph` by name throughout,
> and correctly. **But the two packages carry two different licences.**
> `export-ilograph` ships the MIT *warranty disclaimer* with the
> *permission grant removed* — "All rights reserved", verified by direct
> count: the grant string occurs once in the validator's licence and
> **zero** times in the exporter's. **So "Ilograph ships MIT" is false;
> one of its two packages does.** The accurate statement is narrow:
> *a commercial, closed product that has published exactly one
> permissively-licensed component.* That note also finds the exporter is
> the vendor's **most-maintained** artefact — 23 releases over 4.6 years,
> against this validator's single `0.0.1` — and that it performs **no
> semantic validation at all** while being the tool the vendor documents
> for **CI/CD**.

```
$ validate-ilograph --help
validate-ilograph [inputfile]
Validate an Ilograph diagram
  -l, --level  Level to validate. 0 = Fatal errors only. 1 = Errors only.
               2 = Errors and warnings.                [number] [default: 1]
```

## 2. Ground (2) is false — the licence, and everything drawn from it

`LICENSE.txt` is the **verbatim MIT permission grant**, under a
`Copyright 2025 Ilograph LLC / All rights reserved` header:

> Permission is hereby granted, free of charge, to any person obtaining a
> copy of this software … to deal in the Software without restriction,
> including without limitation the rights to use, copy, modify, merge,
> publish, distribute, sublicense, and/or sell copies …

Three claims in the ninth note fall with it:

| Ninth note | Measured |
|---|---|
| "the **first fully commercial, fully closed** ecosystem in the series … **no open-source component at all**" | The vendor ships an MIT-licensed npm package. |
| "there is **no source to check a recognizer against**" | There is — `index.js`, shipped, MIT. |
| Fit table, licence posture: "**No answer available**" | MIT — and GPL-3.0-compatible, so the answer is not merely available but favourable. |

**Two honest qualifications, because this is a correction and it should
not over-swing.** The shipped `index.js` is **minified** — 103 KB on one
line — so "source available" means readable with effort, not a developed
open codebase. And the *product* remains commercial and closed:
re-verified from the vendor's pricing page today, **Free $0 / Pro $18/mo /
Team $25/editor/mo / Team+ custom / Desktop $11.99/mo**, which matches the
ninth note's table. What is wrong is the absolute — *fully* closed, *no*
open component, *no* answer — not the characterization of the product.

## 3. Ground (1) holds, and F4 gets **stronger**

The ninth note's F4 recorded the no-grader streak's "first caveated
entry":

> Ilograph ships no validator, so its non-grading is close to vacuous.
> This is the first entry in the streak that should not be cited without
> its caveat.

**The caveat is wrong, and deleting it upgrades the entry from the
weakest in the streak to one of the strongest.** Ilograph *does* ship a
validator. It does not grade:

- `score`, `grade`, `maturity`, `rating`, `percent`, `quality` — **zero
  occurrences** in its source.
- Output is `lineNumber [Type] message`. No composite, no level, no gap
  report.
- The `--level 0/1/2` flag is a **severity filter**, not a grade — it
  chooses which findings to print, and prints nothing else.

That is the substantive form of the observation the streak wants: not
"this ecosystem has no validator so it cannot grade", but "this ecosystem
has a competent validator with three severities that **chose not to
grade**." Entry nine should now be cited *without* a caveat.

The rule catalogue is real. Extracted from the (minified) source, ~40
distinct diagnostic templates, including duplicate sibling name/id,
dangling resource references, circular imports, context-tree cycles,
unrecognized properties, reserved identifiers, and "must be defined
before it is referenced" ordering. Analysis runs in phases that stop
early — `Schema problem(s) found, stopping analysis`, then
`Semantic…`, then `Circular import(s)…`.

**§3's "no activation concept" claim, read from the spec, is now verified
by execution.** The validator recognises `start`, `steps`, `toAndBack`,
`toAsync`, `restartAt`, `subSequence` — and no `activate`/`deactivate` of
any kind. SEQ003/SEQ108 and their codegen kin still have no counterpart.

## 4. Two things pumllint has that the vendor's validator does not

Both were invisible to the ninth note, which had run nothing.

**4.1 An exit code.** Measured without a pipe, three ways:

| Input | Findings | Exit |
|---|---|---|
| the vendor's own `aws.ilograph` | **8 × Fatal Error** | **0** |
| a dangling reference | 1 × Warning | **0** |
| a clean file | none | 0 |

`cli.js` calls `exit(1)` only for a missing input file or a thrown error.
**Findings never change the exit code.** A validator that always exits 0
cannot gate anything — which is precisely the contract CLAUDE.md names
first for pumllint, and which `action.yml` and both pre-commit hooks
depend on.

**4.2 A default that shows you the problem.** A dangling reference —
`Referenced resource "DoesNotExist" not found in the resource tree` — is
classified **Warning**, so at the **default** `-l 1` it prints *nothing*.
You must know to pass `-l 2`.

**And the vendor's own shipped model fails the vendor's own validator**:
8 Fatal Errors, every one `Duplicate name or id "…" used for two or more
sibling resources`. That bears on the ninth note's S4, which credited
Ilograph with solving identity *"in the model, by construction"*. It does
not. Identity is **checked by a linter**, exactly as the XD pack checks
it — and the vendor's flagship sample does not pass. S4's *conclusion*
(that this corroborates one-entity-one-identity) survives and is
strengthened; its stated *mechanism* was wrong.

## 5. Ground (3) is mis-located — and the correction widens the hazard

### 5.1 `.ilograph` is YAML — now verified, not inferred

The ninth note took this from Structurizr's exporter documentation and
flagged it as unverified. `lib/aws.ilograph` settles it from vendor
content: `resources:` at top level, `#` comments, `- name:` list items.

### 5.2 The scaling result, on real vendor content

Truncating the real file at resource boundaries — same content
throughout, no reconstruction:

| resources | level | score | elements | findings | exit |
|---|---|---|---|---|---|
| 3 | 4 (Precise) | 98.44 | 4 | 2 | 0 |
| 10 | 4 (Precise) | 99.43 | 11 | 2 | 0 |
| 25 | 4 (Precise) | 99.76 | 26 | 2 | 0 |
| 40 | 4 (Precise) | *99.73* | 41 | 3 | 0 |
| 100 | 4 (Precise) | 99.84 | 101 | 4 | 0 |
| 400 | 4 (Precise) | 99.96 | 401 | 4 | 0 |
| **1438 (all)** | **4 (Precise)** | **99.99** | **1439** | 4 | **0** |

Level 4 and exit 0 throughout, and the composite climbs from 98.44 to
99.99 — further than the reconstruction reached, to the displayed
maximum.

**One correction to the ninth note's phrasing.** It said the composite
"**rises monotonically**". On real content it does not: 25 → 40 dips
(99.76 → 99.73), because real resources vary in shape where the synthetic
sample was uniform. *Rises with volume* is true and is the finding;
*monotonically* was an artefact of the reconstruction and should not be
cited.

### 5.3 The recorded probe, executed — and it inverts

§8.4 recorded the next probe: *"Whether the same mechanism affects JSON,
TOML or Markdown wrapped in `@startuml` is unmeasured … the mechanism
suggests they may behave differently again."* Same model, four carriers:

| carrier | type | level | score | elements |
|---|---|---|---|---|
| YAML | `sequence` | 4 (Precise) | 99.8 | 82 |
| JSON | `unknown` | **1** | 95.0 | **0** |
| TOML | `unknown` | **1** | 95.0 | **0** |
| Markdown | `unknown` | **1** | 95.0 | **0** |

They behave differently, and *in pumllint's favour*: all three land at
`unknown` with zero elements and Level 1, which is the honest outcome.
The hazard did **not** generalize to structured carriers. Cap C6 does its
job for three of the four.

### 5.4 The actual trigger — and this is the new finding

The Markdown sample above failed to trigger it for a reason worth
isolating: its bullets had no colons. With colons:

```
@startuml
# Service inventory

- Owner: Alice
- Owner: Bob
- Status: active
- Status: retired
- Contact: platform-team
@enduml
```

| file | type | level | score | elements | exit |
|---|---|---|---|---|---|
| Markdown bullets **with** `:` | `sequence` | **4 (Precise)** | **99.22** | 8 | 0 |
| the same bullets **without** `:` | `unknown` | 1 | 95.0 | 0 | 0 |

**The trigger is the line shape `- key: value`. It is not YAML.** Dash
becomes the arrow, key becomes the target participant, value becomes the
message label — and any format that produces that shape triggers it.

This matters because it **widens** the hazard the ninth note described
while correcting its framing. That note concluded *"it is not an Ilograph
property — it is a **YAML** property"*, and N2 ruled that *"pumllint has no
business reading YAML at all"*. Both mis-locate the risk. `- key: value`
bullets are ordinary Markdown — ADR bodies, README sections, design docs,
issue templates — and Markdown is far more common in a repository than
`.ilograph`, and far more likely to be pasted between `@startuml` and
`@enduml` by someone who thinks a bullet list is a diagram sketch.

**Any fix for the type-fallback class must be validated against
`- key: value`, not against "YAML".** A fix scoped to a file format would
miss the Markdown case entirely; a fix scoped to the line shape catches
both, and catches the carriers nobody has thought of yet.

## 6. What is corrected, and what stands

| Ninth note | Status |
|---|---|
| Ground (1): not a diagram notation | **Stands**, now verified by execution (§3) |
| Ground (2): fully closed, no open-source component | **FALSE** — MIT validator on npm (§2) |
| Ground (2): no source to check a recognizer against | **FALSE** — shipped, minified (§2) |
| Fit table: licence posture "no answer available" | **FALSE** — MIT, GPL-compatible (§2) |
| §1.3: "vendor has published no validator" | **FALSE** — published 2025-12-03 (§1) |
| F4: streak entry nine is caveated/vacuous | **Caveat withdrawn — the entry is stronger** (§3) |
| §3: no activation concept | **Stands**, verified (§3) |
| §5/S4: identity solved "by construction" | **Mechanism wrong** — it is linted, and the vendor's own file fails (§4) |
| §8.4: sample reconstructed, fidelity unverified | **Resolved** — real vendor file (§5.1) |
| §8.4: YAML unverified, taken from Structurizr docs | **Resolved** — verified from vendor content (§5.1) |
| §8.3: composite rises **monotonically** | **Rises — but not monotonically** (§5.2) |
| §8.4: JSON/TOML/Markdown unmeasured | **Measured — they do not trigger it** (§5.3) |
| §8: "it is a YAML property"; N2 "no business reading YAML" | **Mis-located — the trigger is `- key: value`** (§5.4) |

**The refusal itself is unchanged.** Ilograph is still not a diagram
notation, its product is still commercial and closed, and pumllint should
still never read it. What changed is that three of the reasons given were
overstated, and the one genuinely valuable finding was described in terms
too narrow to act on.

## 7. Fit — revised

### F1 — an Ilograph reader or rule pack. **Still no**, on ground (1) alone.
Grounds (2) and (3) no longer support it. That is fine: one sufficient
ground is sufficient. But the ninth note's "three refusals, each
sufficient" should be cited as **one**.

### F2 — a YAML front-end. **Still no**, and for a better reason.
N2's conclusion survives its broken premise. The fix for §5 is still to
stop scoring the unrecognized rather than to recognize more — and §5.4
shows why a carrier-shaped fix would have been the wrong tool anyway.

### F3 — the type-fallback candidate. **Amended a third time, and this is the one that changes what a fix must do.**
Validate against the line shape `- key: value`, not against a file
format. Real-content ceiling is **99.99 at 1439 elements**, displayed
`100.0/100`.

### F4 — the no-grader streak. **Holds at nine, caveat withdrawn.**
The strongest form of the observation, not the weakest (§3).

### F5 — a licence-posture answer for Ilograph. **Now available: MIT.**
Recorded because the ninth note recorded its absence, not because
anything should depend on it.

## 8. SWOT

Scope: *pumllint's position relative to Ilograph*, revised.

**Strengths**

- Cap C6's honest outcome held for JSON, TOML and Markdown-without-colons
  — three of four carriers land at `unknown`/Level 1/0 elements (§5.3).
- pumllint has an exit-code contract the vendor's validator does not
  (§4.1), and a default that does not hide dangling references (§4.2).

**Weaknesses**

- The type-fallback class reaches **99.99, displayed `100.0/100`**, on
  8175 lines of real vendor content recovered as **one participant named
  `name`** (§5.2).
- The hazard is broader than recorded: ordinary Markdown bullets trigger
  it (§5.4).
- Four of the ninth note's claims about a third party were wrong, and all
  four were checkable by one `npm install` available at the time.

**Opportunities**

- **[Scope, 2026-08-31: this applies to the validator only — the vendor's
  other package is all rights reserved.]** An MIT-licensed reference
  implementation of a validator for a
  model+perspectives format — readable, if minified — is available to
  study. Not a dependency, and not proposed as one.

**Threats**

- Unchanged in substance and worse in reach: the failure is silent,
  confident, improves with size, and is one careless paste away — now
  demonstrably from a **Markdown** document, not only from YAML.

## 9. Decision

**Decision: no change to the refusal. Ground (1) carries it alone.
Four corrections to the ninth note, one withdrawal, and one materially
widened finding.**

**Never build** (unchanged): an Ilograph reader or rule pack; a YAML
front-end; anything premised on the Structurizr→Ilograph export being a
pipeline.

**Recorded, not queued:**

1. **The type-fallback candidate, amended a third time.** The fix must be
   validated against the line shape `- key: value` — reproduced from
   Markdown, not only YAML — and against a real 8175-line file, where the
   composite reaches 99.99 and displays as `100.0/100`. Maintainer
   self-demand; inherits the existing candidate's decision and golden
   re-freeze.
2. **F4's caveat is withdrawn.** Cite streak entry nine without it.
3. **The ninth note's "three refusals, each sufficient" is now one.**

**Re-litigate on:** nothing an adopter can bring. Ground (1) is
structural.

*Bounds. Everything above was executed at `6ac924c` with default config,
from a working directory outside the repository — verified by GEN006 and
GEN007 staying dormant, matching the ninth note's methodology. (A first
run from inside the repo fired both and reported GEN001 as `major`; that
run is discarded, and it is a standing reminder that this series'
measurements are config-sensitive.) **The Ilograph editor was still not
run** — the desktop and web applications remain paid and GUI-only, so
nothing here reports what the editor itself accepts; the validator is the
vendor's, but it is not the editor. The rule-catalogue count (~40
templates) is a **heuristic extraction from minified source** and should
be treated as a floor, not a census. The pricing table was re-read from
the vendor's pricing page today; no purchase was made. Per this session's
repository scope no GitHub repository was read, so the unofficial MCP
server remains uninspected — the ninth note's claim that it "validates
without grading" is **still unverified**, and is now the only claim in
that note left standing on description alone. **[RETIRED 2026-08-30 — this
bound was session scope, not obtainability, and session scope is
extensible: the repository is public and was one clone away. Executed in
[the MCP server evaluation](ilograph-mcp-server-evaluation.md); the claim
is corrected. Fifth consecutive turn in which a bound recorded as a
limitation turned out to be debt.]** Adoption is not measured.*

## Related reading

- [The Ilograph ecosystem, evaluated](ilograph-ecosystem-evaluation.md) —
  the ninth note, which this corrects in four places and whose refusal it
  upholds.
- [The D2 ecosystem, re-examined](d2-ecosystem-reexamined.md) — the
  precondition this note applied, and the previous re-examination.
- [The ArchiMate ecosystem, evaluated](archimate-ecosystem-evaluation.md)
  — candidate 1 for the type-fallback class, amended here a third time.
- [The measured minimum sufficient stack](minimum-sufficient-stack.md) —
  W3's carrier table, cited by the ninth note's ground (3).
- [ROADMAP.md](../ROADMAP.md) — the bounds scan corrected here for the
  fourth consecutive time.

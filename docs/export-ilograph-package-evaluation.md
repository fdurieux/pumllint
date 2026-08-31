# The `export-ilograph` package, evaluated — the vendor split checking from gating

*Dated evaluation, 2026-08-31, written against `c82487e` (v0.30.0). The
question as posed: investigate the `export-ilograph` package, then assess
the boundaries, overlap, fit, gap, sense and nonsense of the different
fits against pumllint's roadmap and ecosystem. Thirty-sixth in the series,
and the third consecutive note on the Ilograph ecosystem — the ninth note
recorded it as unreadable, and it has now yielded three runnable tools.*

**Verdict up front: no overlap on the artefact, and the sharpest
positioning datum the series has produced. Four things measured. (1) It is
**not MIT** — the licence is the MIT *warranty disclaimer* with the
*permission grant removed*, "All rights reserved". The vendor's two npm
packages carry two different licences, and a reader of the last two notes
could easily over-generalise. (2) Its README says it exists for **CI/CD
workflows** — and it performs **zero semantic validation**: none of the
validator's ~40 diagnostics appear in it, its entire error vocabulary is
four I/O messages, and it exports the vendor's own 7-fatal-error sample at
**exit 0**. (3) But it **does** exit 1 on a parse failure — making it the
**first Ilograph tool in this series with a usable exit code**. (4) So:
**the vendor's validator checks but cannot gate; the vendor's exporter
gates but does not check. Neither has both. Wiring the documented CI/CD
path does not invoke the validator at all.** pumllint has both in one
tool, and CLAUDE.md names that exit-code contract first.**

*Bounds. `export-ilograph@0.2.5` was installed from npm and **executed**
seven times. **The paid path was not tested** — no API key was purchased,
so everything here is the free path, and **whether the export API performs
server-side validation when given a real key is unknown**. That bound does
not weaken the central finding, which is about what the *packages* do:
no semantic check runs client-side, verified against the source. **Demo
mode ignores the input file entirely** (§4), so nothing here reports the
fidelity of a real export. Only two files were sent to
`api.ilograph.com`: a **four-line diagram of my own** with no meaningful
content, and **the vendor's own publicly published sample**, in the tool's
documented demo mode. The **Ilograph Desktop app** that authors these files
remains unrun — paid and GUI-only, as recorded since the ninth note. The
`aws.ilograph` divergence (§6) is a byte comparison of two published
artefacts, not a claim about the vendor's internal process.*

## 1. Why this ran, and what the last two notes left

The ninth note (2026-08-27) recorded Ilograph as a closed ecosystem with
nothing to read. Three turns later that has not survived: the vendor's
**validator** was run (34th note), the community **MCP server** was cloned
and run (35th), and this is the vendor's **exporter** — the third runnable
tool in an ecosystem originally recorded as having none.

The 34th note found this package and did the minimum honest thing: it
recorded that the vendor account publishes exactly two packages and named
this one. It made no capability claim about it, so nothing here is a
correction of that note. **It is the claim that note did not make.**

## 2. What it is — and the vitality inversion

`export-ilograph@0.2.5`, `author: "Ilograph LLC"`, maintainer
`ilograph <billy@ilograph.com>`. Dependencies: `js-yaml`, `node-fetch`,
`archiver`, `yargs`.

**23 published versions, 2021-12-04 → 2026-07-26** — four years and eight
months of continuous maintenance, the most recent about five weeks before
this note.

Set against the ecosystem's other two tools, that inverts the picture the
ninth note drew:

| Tool | Releases | Span | Last release |
|---|---|---|---|
| **`export-ilograph`** (vendor) | **23** | **4.6 years** | **2026-07-26** |
| `validate-ilograph` (vendor) | 1 (`0.0.1`) | — | 2025-12-03 |
| MCP server (community) | — | — | 2025-06-16 (**dead 440 days**) |

**The vendor's most-maintained public artefact is its exporter, by an
order of magnitude.** Its validator is a single `0.0.1`. The ninth note's
core observation — that Ilograph's published effort does not go into
checking — turns out to be **right, and better supported than the evidence
it was drawn from**: not because the vendor publishes no validator (it
does), but because the validator is a one-release afterthought beside a
23-release exporter.

## 3. The licence — not MIT, and the difference is the whole grant

The 34th note found `validate-ilograph` under the **verbatim MIT grant**
and corrected the ninth note's "no open-source component at all". This
package is **not** under that licence, and the difference is exactly the
part that matters:

| | `validate-ilograph/LICENSE.txt` | `export-ilograph/license` |
|---|---|---|
| `Copyright 2025 Ilograph LLC` | ✓ | ✓ |
| **"Permission is hereby granted, free of charge …"** | **✓ present** | **✗ absent** |
| `"All rights reserved"` | in the header block | **the operative term** |
| `THE SOFTWARE IS PROVIDED "AS IS"` … | ✓ | ✓ |

Verified by direct count: the grant string occurs **once** in the
validator's licence and **zero** times in the exporter's. What ships here
is the MIT *warranty disclaimer* without the MIT *licence* — a
**proprietary, all-rights-reserved package distributed on a public
registry**.

**This does not correct the 34th note**, which scoped its MIT finding to
`validate-ilograph` by name, as did the ROADMAP entry. **It guards against
the over-generalisation those notes invite**: "Ilograph ships MIT" is
false. One of its two packages does. Recorded because the ninth note's
ground (2) has now been re-litigated three times, and the accurate
statement is narrow: *Ilograph is a commercial, closed product that has
published exactly one permissively-licensed component.*

## 4. Demo mode ignores your diagram

Run without `-k`, the CLI warns *"No API key provided. Exporting a demo
diagram"* and returns a 494 KB HTML file at **exit 0**.

It is not a watermarked export of your input. **It does not contain your
input at all.** Searched four ways against a four-line source diagram —
raw, case-insensitive, URL-encoded, and by base64-decoding every long
blob in the file — every one of `Checkout UI`, `OrderService`,
`places order` and `Web frontend` returns **zero hits**.

So the free path produces an artefact **unrelated to the file you gave
it**. The tool is not usable for its stated purpose without a purchased
key; it is a working demo of the *renderer*, not a limited export.

**What the output is** matters for the ninth note's surviving ground. The
494 KB is a **self-contained interactive viewer application** — bundled
JS, `<canvas>`, SVG, and UI strings like *"Add extended description"* and
*"to add notes to this perspective"*. Even Ilograph's **export** is a
navigation experience, not a picture. **Ground (1) of the ninth note — the
one refusal that survived all three re-examinations — is confirmed from a
new direction: there is no static artefact anywhere in this ecosystem for
a linter to read.**

## 5. The finding — checking and gating live in different packages

The README: *"Used to export diagrams created with Ilograph Desktop in
**CI/CD workflows**."* So this is Ilograph's CI story. Measured:

| Input | Exit | Artefact produced |
|---|---|---|
| nonexistent file | **1** | none |
| syntactically invalid YAML | **1** | none |
| valid diagram | 0 | 494 KB |
| **dangling reference** (validator flags it) | **0** | 494 KB |
| **the vendor's own sample — 7 Fatal Errors** | **0** | 493 KB |

It exits 1 only on **read/parse failure**. And it carries no semantic
checks at all — none of the validator's signature diagnostics appears
anywhere in its source:

| Diagnostic | validator | exporter |
|---|---|---|
| `Duplicate name or id` | 1 | **0** |
| `not found in the resource tree` | 1 | **0** |
| `Circular import` | 1 | **0** |
| `unrecognized property` | 1 | **0** |
| `Fatal Error` / `Warning` | 1 / 1 | **0 / 0** |

Its entire error vocabulary is four I/O failures: *reading the input file*,
*creating a zip*, *retrieving the HTML from the export API*, *writing the
output file*.

**The two vendor tools have exactly complementary halves of one job:**

| | semantic checking | exit code signals failure |
|---|---|---|
| `validate-ilograph` | **yes** (~40 diagnostics) | **no** — always 0, even on 8 Fatal Errors |
| `export-ilograph` | **no** — YAML parse only | **yes** — 1 on parse/read failure |
| MCP server (community) | partial, four defects | n/a — returns a dict |
| **pumllint** | **yes** | **yes — 0/1/2, a named contract** |

**Wire Ilograph into CI as its own README documents and nothing checks
your model.** The tool in the pipeline cannot detect a dangling reference
or a duplicate id; the tool that can detect them cannot fail the build.
Neither package alone is a gate, and the vendor ships no glue between
them.

This is the third independent confirmation, from three separate tools in
one ecosystem, of the thing CLAUDE.md lists first among pumllint's
contracts. The 35th note found that a linter for a model has no exit code;
this one finds that **a tool with an exit code may have nothing to say**.
The contract is not the exit code alone — it is *checking and gating in
the same tool*.

## 6. The two bundled samples have drifted

Both vendor packages ship `lib/aws.ilograph`. **They are not the same
file** — 60 diff lines, 1438 vs 1439 top-level resources. The exporter's
copy drops a duplicate `CodeBuild::Project` and adds `ECS::ContainerInstance`
entries.

Run against the vendor's own validator:

| copy | Fatal Errors |
|---|---|
| shipped with `validate-ilograph` | **8** |
| shipped with `export-ilograph` | **7** |

The 34th note found that the vendor's flagship sample fails the vendor's
own validator. The fuller picture: **there are two divergent copies of it,
in two packages, and both fail** — one having lost a single duplicate
somewhere along the way. Not a stale asset but an **unvalidated asset,
duplicated and drifting**, in an ecosystem whose validator would catch it
in under a second.

Recorded because it is the cleanest illustration in the series of what a
validator that cannot gate is worth: the vendor *has* the check, ships it,
and does not run it on its own published files.

## 7. Boundaries, overlap, sense, nonsense

**Boundaries.** (1) **Artefact** — input is Ilograph YAML, output is an
HTML application. Neither is a diagram notation pumllint reads. (2)
**Terminal** — the HTML is an end product, not an interchange format;
nothing consumes it. (3) **Network and licence** — it is a thin client for
a paid remote API, all rights reserved. There is nothing here to depend on
even if the artefact matched.

**Overlap: none.** No rule, dimension or cap of pumllint's has a
counterpart. The one shared *concern* is the exit-code contract, and §5 is
about how differently the two projects resolved it.

**S1. The complementary-halves result is the strongest positioning
evidence the series has produced, and it is not an argument pumllint
made.** An independent commercial vendor, maintaining three tools, split
checking from gating across two packages and shipped no glue. That is
market evidence for the shape of pumllint's contract, arrived at by
someone else's decisions.

**S2. Ground (1) is now confirmed three ways.** Read from the spec (ninth
note), verified against the vendor's validator (34th), and now shown to
hold even of the *export*: the artefact at the end of Ilograph's own CI
pipeline is an interactive application. Nothing static exists to lint.

**S3. "The vendor doesn't invest in checking" was right for the wrong
reason.** The ninth note inferred it from an absence that was not there.
The release histories support the same conclusion properly: 23 exporter
releases to one validator release.

**N1. Reading Ilograph's HTML export. Refused.** A 494 KB bundled viewer
app is not a description, and §4 shows the free path does not even contain
your model.

**N2. Treating `structurizr-cli export -f ilograph` → `export-ilograph`
as a pipeline pumllint could join. Refused**, and more firmly than the
ninth note's N5. The chain now provably terminates in an HTML application.

**N3. Citing "Ilograph ships MIT". Refused** — §3. One of two packages.

**N4. Building an export or render capability because a competitor has
one. Refused.** PlantUML's rendering is upstream's job; GEN002 already
covers the only export concern pumllint has (stable filenames).

## 8. Fit — graded

### F1 — any `export-ilograph` capability. **No.** Wrong artefact, terminal output, proprietary, network-bound.

### F2 — the exit-code contract as a differentiator. **Confirmed, and worth citing.** §5. Three tools in one ecosystem, none combining checking with gating. Not a change to pumllint — evidence for a decision already made.

### F3 — the ninth note's ground (1). **Confirmed a third way.** §4, S2.

### F4 — the licence record. **Corrected in scope, not in fact.** §3.

| Declared constraint | Where this lands |
|---|---|
| **Zero runtime dependencies** | Not reached — F1 fails on the artefact first. |
| **Deterministic product path, no LLM** | Untouched. |
| **Exit codes 0/1/2** | **Independently corroborated** (§5) — the contract's value is checking *and* gating in one tool. |
| **Golden score contract** | Untouched; nothing here proposes a scoring change. |
| **Licence posture** (GPL-3.0-or-later) | **All rights reserved** — a hard blocker were anything ever proposed, unlike the MIT validator. |

## 9. SWOT

Scope: *pumllint's position relative to `export-ilograph`*.

**Strengths**

- The exit-code contract combines checking and gating; no tool in this
  ecosystem does (§5).
- pumllint's artefact is a text description under version control. The
  whole Ilograph chain terminates in a binary-ish HTML app (§4).

**Weaknesses**

- None surfaced. This is the first Ilograph note in four to find no
  pumllint defect — the previous three found the type-fallback ceiling,
  the `- key: value` trigger, and the streak's phrasing.

**Opportunities**

- None pursued.

**Threats**

- None from this package. The standing one is unchanged: this ecosystem
  has now produced **three** runnable tools after being recorded as
  producing none, and each was one registry command or one clone away.

## 10. Decision

**Decision: no fit, no build, nothing queued. One scope correction, one
confirmation, one recorded positioning result.**

**Never build:** any Ilograph export or render capability (N1, N4);
anything premised on the export chain being a pipeline into pumllint (N2).

**Recorded, not queued:**

1. **The exit-code contract's value is *checking and gating in the same
   tool*.** §5 — three tools in one ecosystem, two vendor-published, and
   none combines them. Cite this when the contract is questioned.
2. **"Ilograph ships MIT" is false — one of two packages does.** §3.
   Annotated into the 34th note so the scope travels with the claim.
3. **The ninth note's ground (1) is confirmed a third way** (§4), and its
   "the vendor doesn't invest in checking" instinct is vindicated by
   release histories rather than by the absence it wrongly asserted (§2).

**Re-litigate on:** nothing. Ground (1) is structural, and no adopter
changes an HTML export into a description.

## Related reading

- [The Ilograph ecosystem, re-examined](ilograph-ecosystem-reexamined.md)
  — the vendor's validator; the MIT finding this note scopes, and the
  `aws.ilograph` sample this note finds a second, divergent copy of.
- [The unofficial Ilograph MCP server, evaluated](ilograph-mcp-server-evaluation.md)
  — "a linter for a model has no exit code"; §5 here is its counterpart,
  a tool with an exit code and nothing to say.
- [The Ilograph ecosystem, evaluated](ilograph-ecosystem-evaluation.md) —
  the ninth note, whose ground (1) this confirms a third way.
- [ROADMAP.md](../ROADMAP.md) — the exit-code contract §5 corroborates.

# The Ilograph Desktop app, evaluated — the checking was in the product all along, and I said it wasn't

*Dated evaluation, 2026-08-31, written against `e4a144a` (v0.30.0). The
question as posed: investigate the Ilograph Desktop app, then assess the
boundaries, overlap, fit, gap, sense and nonsense of the different fits
against pumllint's roadmap and ecosystem. Thirty-ninth in the series,
sixth and last consecutive note on the Ilograph ecosystem.*

**Verdict up front: no fit, and the note's yield is a correction to my own
last two notes. (1) The standing bound falls — **fifth time in six
turns**. "Paid and GUI-only, not obtainable" has been carried since the
ninth note; in fact Desktop is a **direct download, no account,
120 MB Linux AppImage**, which extracts and can be read without a display.
(2) **Desktop bundles the validator, in the editor.**
`electron/dist/editor.js` carries the same diagnostic templates as
`validate-ilograph`, so Ilograph validates **live as you type** — a
capability documented nowhere. **[GENERALIZED 2026-08-31 by
[the web app evaluation](ilograph-web-app-evaluation.md): the web app's
`/dist/editor.js` is **byte-identical** to this one (`sha256 cddd923b…`),
so this is not a fact about Desktop but about **the Ilograph editor,
wherever it runs**. Desktop is an Electron shell around the same editor;
what is Desktop-only is licensing, activation and export plumbing.]** (3) **That falsifies a claim I made in the
38th note** — twice in that note, and again in its ROADMAP entry: *"the
vendor ships a validator and surfaces it in no product at all."* It is in
the product. The ninth note's careful
wording — *"Ilograph **documents** no validation"* — was right all along;
my paraphrase of it over-reached, twice. (4) The sharpest form of the
running thread: **the currently-shipping Desktop app bundles a validator
that reports 7 Fatal Errors in a standard library the same app ships.**
(5) And Desktop has **no CLI and no headless mode**, so it checks and
cannot gate — which is exactly why `export-ilograph` exists.**

*Bounds. **The GUI was never run** — there is no display here, and that
part of the old bound stands. Everything below is from **extracting and
reading the shipped bundle**: the AppImage was unpacked and its
`app.asar` extracted, so the findings are about what the binary
*contains*, not about what the running editor *shows*. In particular, "it
validates live as you type" is an inference from the validator's presence
in `editor.js` plus the strings `Validate` / `validation` / `Problems` in
the renderer bundle — **strong, but not observed**. No licence was
purchased and no trial started; nothing here required one, and nothing was
patched, bypassed or circumvented — a public download was read, exactly as
the npm packages were. The diagnostic comparison is a **sample of five
templates**, not a full diff of the two builds. `aws.ilograph` copy counts
are byte comparisons of published artefacts, not claims about the vendor's
internal process.*

## 1. The bound falls, for the fifth time in six turns

Every Ilograph note has carried some form of this:

> The **Ilograph Desktop app** that authors these files remains unrun —
> paid and GUI-only, as recorded since the ninth note.

Two of those three words were wrong. Measured today:

| | |
|---|---|
| Download | `https://www.ilograph.com/desktop/release/Ilograph Desktop-2.4.4.AppImage` |
| Account required | **no** — HTTP 200, `binary/octet-stream`, no auth |
| Size | 119 906 214 bytes (120 MB) |
| `last-modified` | **2026-08-29** — the same day as Confluence plugin v2.13.0 |
| sha256 | `5af341215e2c44323ff1f564aa1bfa5011d19811882052c2677ff54bde3a4f0d` |
| Platforms | Mac (M / Intel), Windows, **Linux x86-64 and arm64** |

**"GUI-only" conflated *running* it with *obtaining* it.** An AppImage is
an archive; `--appimage-extract` unpacks it with no display involved, and
the Electron `app.asar` inside is readable JavaScript. The GUI still
cannot run here — that half of the bound was right — but **everything this
note found needed no GUI at all.**

The scoreboard for the six-note Ilograph run: **five bounds recorded as
limitations turned out to be debt** (the validator, the MCP server, the
exporter, the TypeScript library, this), and **one was real** (the
Confluence plugin, Atlassian-hosted with no artefact). The habit named in
the 35th note holds: *this series has repeatedly mistaken "I did not do
it" for "it could not be done."*

## 2. Desktop bundles the validator — and I said twice that no product did

`grep` over `app.asar` for the validator's signature diagnostics:

| Diagnostic | in `app.asar` |
|---|---|
| `Duplicate name or id` | **yes** |
| `not found in the resource tree` | **yes** |
| `Circular import` | **yes** |
| `unrecognized property` | **yes** |
| `Cycle detected in context tree` | **yes** |
| `is a reserved identifier` | **yes** |
| `stopping analysis` | **yes** |
| `Fatal Error` | **no** — the CLI's severity label, not the app's |

It lives in **`electron/dist/editor.js`** — the editor bundle, not a
background job — alongside renderer strings `Validate`, `validation` and
`Problems`. Five sampled diagnostic templates appear in both `editor.js`
and `validate-ilograph/index.js`. Same validator, embedded in the
authoring surface.

**This falsifies my own claim.** The 38th note asserted it twice — in its
verdict and again in its §3 — and its ROADMAP entry a third time:

> the vendor ships a validator and surfaces it in **no product at all**

That is false. It is surfaced in the product; it is absent from the
**documentation**. *(The 36th note, checked before writing this, did **not**
make the claim — it said only that the validator is a one-release
afterthought beside a 23-release exporter, which is true and stands. The
first draft of this note asserted both notes were wrong; that would have
been a fabricated self-correction, and it was caught by going and reading
them.)*

**What survives is the ninth note's original wording**, which was careful
where mine was not: *"Ilograph **documents** no validation, linting or
semantic checking of its own."* A statement about documentation. The 34th
note even annotated the distinction correctly — *"'documents no
validation' is literally true, 'has published no validator' is false"* —
and then I widened it four notes later into a claim about products, which
nobody had measured.

**Seventh instance of the "sound premise, over-reaching conclusion"
shape**, and the most instructive: the over-reach was mine, it was
downstream of a hedge I had myself written in the 34th note, and one
`grep` over a public download would have caught it the same day.

**The lesson generalizes past its occasion: documentation is a bad oracle
for capability.** The ninth note inferred a product's capabilities from
its docs and was right about the docs and wrong about the product. To know
what a tool does, run it or read it — not its documentation. That is the
same rule this series has applied to *other people's* claims for six
notes; it applies to inferences from absence too.

## 3. The sharpest form of the running thread

Desktop ships `electron/lib/aws.ilograph` — a **fourth** published copy of
the vendor's flagship standard library. All four, through the vendor's own
validator:

| Copy | Resources | Bytes | **Fatal Errors** |
|---|---|---|---|
| GitHub `standard-libraries` (2024-10-11) | 1441 | 176 280 | **8** |
| `validate-ilograph` npm (2025-12-03) | 1438 | 175 993 | **8** |
| `export-ilograph` npm (2026-07-26) | 1439 | 176 977 | **7** |
| **Desktop 2.4.4** (2026-08-29) | 1439 | 176 977 | **7** |
| **web app** (fetched 2026-08-31) | **1441** | **177 156** | **8** |

> **A FIFTH COPY, added 2026-08-31** — the **live web app** serves
> `/lib/aws.ilograph`, distinct from all four above. **Five copies, four
> checksums, and the production one is the worst of them.** See
> [the web app evaluation §3](ilograph-web-app-evaluation.md). The
> "two vintages" reading below still holds for the four npm/GitHub/Desktop
> copies; the live web copy is a third.

**Four copies, three distinct checksums** — and a refinement worth
recording, because it is fairer than the 38th note's framing: **Desktop
2.4.4 and `export-ilograph` 0.2.5 ship the byte-identical file.** The
drift is between *release vintages*, not chaos, and the two newest
artefacts agree. What the 38th note called divergence is better described
as **two vintages, the older pair carrying 8 errors and the newer pair 7**.

But the finding underneath sharpens rather than softens:

**The currently-shipping Desktop app bundles a validator that reports
seven Fatal Errors in a standard library the same app ships.** The check
is in the binary. It is not run against the binary's own payload.

*In fairness, the file the app opens on first run —
`electron/demo/initial.ilograph` — is **clean**.*

## 4. It checks, and it cannot gate

No CLI. No headless mode. The `--` switches in `main.js` (`--noconfirm`,
`--allow-unsigned-rpm`, `--force-run`, `--proxy`, …) belong to bundled
updater libraries, not to Ilograph. There is no way to ask Desktop to
check a file and tell you the answer.

**Which is precisely why `export-ilograph` exists** — its README:
*"Used to export diagrams created with **Ilograph Desktop** in CI/CD
workflows."* The vendor built a separate CLI because the app has no
command line, and that CLI, as the 36th note measured, does no semantic
checking at all.

So the surface table takes its **most important correction**, and the
bottom line does not move:

| Surface | Checks? | Can gate? |
|---|---|---|
| **Desktop app** | **YES — live, in-editor** *(was "not documented")* | **no** — no CLI, no headless |
| `validate-ilograph` CLI | yes, ~40 diagnostics | no — always exits 0 |
| `export-ilograph` CLI | no — parse only | yes — exits 1 on parse failure |
| MCP server (community) | partial, four defects | n/a — returns a dict |
| `ilograph-typescript` | compile-time **shape** only | via `tsc` |
| Confluence plugin | not documented | no — no CI surface at all |
| **pumllint** | **yes** | **yes — 0/1/2, a named contract** |

**Six Ilograph surfaces. The count that combine checking with gating is
still zero** — and now it is zero for a more interesting reason than
"nobody built the checking." **The checking exists, is good, and lives
where builds cannot see it.**

## 5. The result — editor checking is not CI checking

This is the note's contribution to the roadmap, and it is a better
argument for pumllint's contract than any previous note in the run,
because it is no longer about a vendor's neglect.

Ilograph has **live semantic validation in its authoring surface**:
duplicate identity, dangling references, circular imports, context cycles,
reserved identifiers — checked as you type, in the editor, undocumented
but present. That is genuinely good, and better than the 38th note
credited.

**And none of it can fail a build.** A defect flagged in the editor is
flagged to the person typing, at the moment of typing, and to nobody else
ever again. If they ignore it, save, and commit, nothing downstream knows.
The vendor's own flagship library demonstrates exactly this: **seven
errors the shipping editor would flag, shipping anyway.**

**pumllint's exit-code contract is the answer to that, and this is what it
is for.** Not "Ilograph forgot to check" — Ilograph checks well. The gap
is that *editor-time checking and build-time checking are different
products*, and an ecosystem can have an excellent one and no instance of
the other.

**Held honestly the other way**: pumllint has **no** editor-time story.
Nothing in it validates as you type. The 35th note found a linter for a
model with no exit code; the 38th, a surface with no gate; this one finds
a good editor-time checker that cannot gate — and pumllint is the mirror
image, a good gate with nothing at authoring time. That is a real
asymmetry, not a win, and it belongs in the record as such.

*[2026-09-03: true when written, false since 2026-08-31 — `pumllint lsp`
shipped that day (diagnostics, code actions, hover, completion, rename,
document symbols), stdlib-only, on a concrete ask. The ROADMAP mirror of
this note was annotated at the time; this source was not. Every sentence
below that says "no editor-time story", "unrequested", "refused" or
"different product" reads as the 2026-08-31 state.]*

## 6. Boundaries, overlap, sense, nonsense

**Boundaries.** (1) **Artefact** — Ilograph YAML; pumllint reads PlantUML.
(2) **Time** — Desktop checks at *authoring* time; pumllint at *build*
time. (3) **Licence** — `"Copyright 2025 Ilograph LLC. All rights
reserved."`, a sixth licence data point and the same posture as the
exporter. (4) **Runtime** — a 120 MB Electron app against a
zero-dependency Python CLI.

**Overlap:** the *check catalogue* genuinely overlaps — identity
uniqueness, dangling references, cycles — but at a different time, on a
different artefact, in a different product shape.

**S1. Editor-time checking is real and pumllint has none.** §5. Recorded
as an asymmetry, not a gap to close: closing it would mean an LSP or
editor plugin, which is a different product with different constraints.
*[2026-09-03: the prediction failed in the informative direction — it was
the same product, same constraints, zero third-party imports.]*

**S2. "Documentation is a bad oracle for capability."** §2. The rule this
series applies to other people's claims applies to its own inferences from
absence.

**S3. A check that cannot reach a build is invisible to everyone but the
author.** §5, and demonstrated by the vendor's own shipping library.

**N1. An editor plugin or LSP for pumllint. Refused — for now, and not
because it is a bad idea.** §5 makes the case that it is the missing half.
But it is a new product surface, it would need a runtime pumllint does not
have, and nothing in the Arc E bar has asked for it. **Recorded as the
strongest unclaimed idea the Ilograph run produced**, gated on demand like
everything else. *[BUILT 2026-08-31 — the maintainer asked, which is the
demand the Arc E bar names, and the "runtime pumllint does not have" worry
did not materialise: a stdlib JSON-RPC server was enough.]*

**N2. Reading §3 as "the vendor is careless." Refused.** They ship a good
checker in the editor; the library predates the current release and its
errors are duplicate abstract definitions in a 1439-resource generated
catalogue. The finding is structural — *checks that cannot gate do not get
run* — not a judgment of care.

**N3. Any Ilograph capability. Refused**, unchanged since the ninth note's
ground (1).

## 7. Fit — graded

### F1 — any Desktop capability. **No.** Wrong artefact, wrong time, all rights reserved.

### F2 — "editor-time checking is not CI checking." **The result.** §5. The clearest statement yet of what the exit-code contract buys, and the first that concedes the other side has something pumllint lacks.

### F3 — the surface table. **Corrected and completed.** §4. Six surfaces, zero combining checking with gating.

### F4 — my own claim in note 38. **Falsified and annotated**, in both places it appears there and in its ROADMAP entry. §2.

| Declared constraint | Where this lands |
|---|---|
| **Zero runtime dependencies** | Untouched — and the contrast is stark (120 MB Electron). |
| **Deterministic product path, no LLM** | Untouched. |
| **Exit codes 0/1/2** | **The operative one.** §5 — what it buys, stated against an ecosystem that checks well and cannot gate. |
| **Demand-driven / Arc E bar** | **Gates N1.** The editor-plugin idea is real and unrequested. *[Requested and built 2026-08-31.]* |
| **Licence posture** | All rights reserved; not a dependency candidate. |

## 8. SWOT

Scope: *pumllint's position relative to Ilograph Desktop*.

**Strengths**

- The exit-code contract reaches a place editor-time checking cannot
  (§5), demonstrated by the vendor's own library shipping with seven
  errors its editor would flag.

**Weaknesses**

- **pumllint has no authoring-time story at all.** *[Until 2026-08-31;
  see §5's annotation.]* Ilograph's editor
  checks identity, references and cycles as you type. This is the first
  note in the run where the other side clearly has something pumllint
  lacks (§5).
- **The record was wrong for a note and a day** because I inferred a
  product's capability from its documentation (§2).

**Opportunities**

- An editor plugin or LSP (N1) — recorded, refused for now, gated on
  demand. The strongest unclaimed idea the Ilograph run produced.
  *[Claimed: built 2026-08-31.]*

**Threats**

- None from this product.

## 9. Decision

**Decision: no fit, no build. One self-correction, one completed table,
one recorded idea.**

**Never build:** any Ilograph capability (N3).

**Recorded, not queued:**

1. **"Editor-time checking is not CI checking"** (§5) — what the
   exit-code contract buys, argued against an ecosystem that checks
   *well*. Cite with its concession: pumllint has no authoring-time story.
2. **An editor plugin / LSP** (N1) — the missing half, unrequested, gated
   on the Arc E bar. *[BUILT 2026-08-31.]*
3. **"Documentation is a bad oracle for capability"** (§2) — applies to
   this record's own inferences from absence, not only to other people's
   claims.

**Re-litigate on:** a concrete user asking for editor-time checking. Not
on Ilograph. *[That user arrived; re-litigated and built 2026-08-31.]*

**Corrected in this turn:** note 38, inline, in both places it claims the
validator is surfaced in no product, and its ROADMAP entry; note 38's
`aws.ilograph` divergence framing, refined to two release vintages.

## Related reading

- [The Ilograph Confluence Cloud plugin, evaluated](ilograph-confluence-plugin-evaluation.md)
  — the surface table this corrects, and the claim this falsifies.
- [The `export-ilograph` package, evaluated](export-ilograph-package-evaluation.md)
  — the CLI that exists *because* Desktop has no command line (§4). Its
  claims stand; it did not make the one §2 falsifies.
- [The Ilograph ecosystem, re-examined](ilograph-ecosystem-reexamined.md)
  — the validator whose code Desktop bundles, and the oracle for §3.
- [The Ilograph ecosystem, evaluated](ilograph-ecosystem-evaluation.md) —
  the ninth note, whose careful wording survives where my paraphrase did
  not (§2).
- [ROADMAP.md](../ROADMAP.md) — the exit-code contract §5 is about.

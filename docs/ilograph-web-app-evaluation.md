# The Ilograph web app, evaluated — one checker, every authoring surface, never wired to a build

*Dated evaluation, 2026-08-31, written against `d2f636d` (v0.30.0). The
question as posed: investigate the Ilograph web app, then assess the
boundaries, overlap, fit, gap, sense and nonsense of the different fits
against pumllint's roadmap and ecosystem. Fortieth in the series, and the
**seventh and last** on the Ilograph ecosystem — the surface inventory is
now exhausted.*

**Verdict up front: no fit, and the run closes on a structural result that
shrinks the whole picture. (1) The web app's client bundles are **public,
no account** — `/dist/editor.js`, `/dist/frame.js`, `/dist/config.js`,
`/js/a.js` all serve to an anonymous fetch. (2) **The web app's
`editor.js` is BYTE-IDENTICAL to Desktop's** — `sha256 cddd923b…` on both.
Desktop is an Electron shell around the same editor, so every finding in
the 39th note transfers here, including the bundled validator. (3) What
actually differs is **licensing, activation and export plumbing**
(`license.js`, `offlineActivation.js`, `exportOptions.js`, `manualChit.js`
— Desktop-only, verified) — **not the editor, and not the checking**. (4)
A **fifth** published copy of `aws.ilograph`, and **the live production
one is the worst of the five**: 1441 resources, **8 Fatal Errors**, served
today by an app that bundles the validator reporting them. (5) So the
thread's final form: the vendor has one good checker, ships it in every
authoring surface, and has never wired it to a build.**

*Bounds. **The app was never used** — that needs an account, and I
declined to create one, exactly as with Confluence. Everything here is
from **fetching public static assets and comparing them to the Desktop
bundle**, so findings are about what is *served*, not about what a
logged-in session does. In particular "the web app validates live as you
type" is inherited from the byte-identical editor bundle plus the 39th
note's reading of it — **strong, but still not observed in a running
editor**. No paid tier was purchased and nothing was patched or bypassed.
A **method correction is recorded in §5**: `app.ilograph.com` returns
HTTP 200 with the SPA shell for *any* unknown path, and a first pass of
this evaluation reported five files that do not exist; the numbers below
are the corrected ones.*

## 1. Obtainable, and the last surface to be so

| Asset | Result |
|---|---|
| `/` (app shell) | HTTP 200, 88 110 bytes, **no auth** |
| `/dist/editor.js` | **real**, 126 769 bytes |
| `/dist/frame.js` | **real**, 314 818 bytes |
| `/dist/config.js` | **real**, 492 bytes |
| `/js/a.js` | **real**, 11 380 bytes |
| `/lib/aws.ilograph` | **real**, 177 156 bytes |
| `/dist/main.js` | **not served** — Desktop-only |

*Using* the app needs an account (the Free tier is $0), and **I declined
to create one** — the same line drawn at the Confluence plugin. Nothing
here required it.

The Ilograph run's final scoreboard on obtainability: **six of seven
surfaces were inspectable without an account**, and the one that was not
(Confluence) is Atlassian-hosted with no artefact to fetch. The bound
recorded in the ninth note — a closed ecosystem with nothing to read —
was wrong six times over.

## 2. The structural result — Desktop *is* the web app

```
$ sha256sum dapp/electron/dist/editor.js web/editor.js
cddd923b55dcc2dd38adacc11f67ecd0210d6342aa6f980f8128f5dddaeb02f1  dapp/electron/dist/editor.js
cddd923b55dcc2dd38adacc11f67ecd0210d6342aa6f980f8128f5dddaeb02f1  web/editor.js
```

**Byte-identical**, verified by re-downloading the 120 MB AppImage rather
than inferring from the size match that first suggested it.

So the 39th note's central finding is not a fact about the *Desktop* app.
It is a fact about **the Ilograph editor**, wherever it runs: the
validator — duplicate name or id, dangling references, circular imports,
context-tree cycles, reserved identifiers — is in the bundle the web app
serves to every user, logged in or not.

**What is Desktop-only**, verified against the catch-all (§5) rather than
by a bare 200:

| Module | Desktop | Web |
|---|---|---|
| `license.js` | ✓ | **not served** |
| `offlineActivation.js` | ✓ | **not served** |
| `exportOptions.js` | ✓ | **not served** |
| `manualChit.js` | ✓ | **not served** |
| `main.js` (Electron main, 660 KB) | ✓ | **not served** |

**The difference between the paid desktop product and the web product is
licensing, activation and export plumbing. The editor is the same file,
and so is the checking.** A tidy result: the vendor built one editor and
two shells, and put the commercial machinery in the shell.

## 3. A fifth copy, and the live one is the worst

`/lib/aws.ilograph` is served from production today. Through the vendor's
own validator, alongside the four the run already found:

| Source | Resources | Bytes | **Fatal Errors** |
|---|---|---|---|
| GitHub `standard-libraries` (2024-10-11) | 1441 | 176 280 | **8** |
| `validate-ilograph` npm (2025-12-03) | 1438 | 175 993 | **8** |
| `export-ilograph` npm (2026-07-26) | 1439 | 176 977 | **7** |
| Desktop 2.4.4 (2026-08-29) | 1439 | 176 977 | **7** |
| **web app (fetched today)** | **1441** | **177 156** | **8** |

**Five published copies, four distinct checksums** — only Desktop and the
exporter share one. The web copy is the **largest**, is **distinct from
the GitHub copy** despite matching its resource count, and carries **8
Fatal Errors**.

**The live production web app serves a standard library with eight fatal
errors, from an app that bundles the validator which reports them.** That
is the sharpest the thread gets, and it is where it ends.

## 4. The thread closes — one checker, seven surfaces, no gate

Filling the last row, and then collapsing it:

| Surface | Checks? | Can gate? |
|---|---|---|
| **Web app** | **yes — the same `editor.js`** | **no** — no build, no exit code |
| Desktop app | yes — byte-identical editor | no — no CLI, no headless |
| Confluence plugin | not documented | no — no CI surface at all |
| `validate-ilograph` CLI | yes, ~40 diagnostics | **no** — always exits 0 |
| `export-ilograph` CLI | **no** — parse only | yes — exits 1 on parse failure |
| MCP server (community) | partial, four defects | n/a — returns a dict |
| `ilograph-typescript` | compile-time **shape** only | via `tsc` |
| **pumllint** | **yes** | **yes — 0/1/2, a named contract** |

**Seven Ilograph surfaces. Still zero combining checking with gating.**

But §2 collapses the table in a way the earlier notes could not see. The
seven surfaces are **not** seven checking implementations. They are:

- **one editor validator**, shipped byte-identical to web and Desktop
  (and, on the evidence, Confluence);
- **one CLI validator** of the same lineage, on npm, that always exits 0;
- **one community reimplementation** (the MCP server), measurably worse —
  no duplicate-`name` check, no dangling-reference check at all;
- **one type system** (`ilograph-typescript`), which catches shape and
  cannot see values.

**So the vendor has exactly one good checker. It ships in every authoring
surface it owns. It has never been wired to a build** — the CLI edition
cannot fail one, and the CI tool the vendor documents
(`export-ilograph`) does not call it.

That is a better closing statement than "this ecosystem does not check",
which is what the ninth note believed and what four of these seven notes
have been progressively dismantling. **It checks well. It checks in the
one place a build cannot see.**

## 5. A method correction, caught in flight

`app.ilograph.com` returns **HTTP 200 with the 88 110-byte SPA shell for
any unknown path** — not a 404. A first pass of this evaluation probed for
files by status code and reported five that do not exist
(`/dist/license.js`, `/dist/offlineActivation.js`, `/dist/exportOptions.js`,
`/aws.ilograph`, `/dist/main.js` on the web). Every one was the catch-all.

Caught by fetching a control path certain not to exist
(`/definitely-not-a-real-path-xyz123`) and byte-comparing every candidate
against it. The corrected inventory is §1's.

**Generalized: on a single-page app, HTTP 200 is not evidence that a file
exists.** Same class as two errors already in this record — *registry
presence is not runnability* (the D2 row in the bounds scan) and *a test
failure under the wrong dependency version is not a defect* (the 35th
note's fastmcp artefact). Third instance of **"a cheap signal stood in for
the expensive check"**, and the first caught before it reached a note.

## 6. Boundaries, overlap, sense, nonsense

**Boundaries.** (1) **Artefact** — Ilograph YAML held server-side; pumllint
reads PlantUML files in a repository. (2) **Storage** — diagrams live in
the vendor's cloud, not in version control, so there is no commit to hook,
exactly as with Confluence. (3) **Time** — authoring-time checking, not
build-time. (4) **Licence** — `Copyright 2025 Ilograph - All rights
reserved` in the served HTML.

**Overlap: none in code.** The check *catalogue* overlaps (identity,
references, cycles); nothing else does.

**S1. One editor, two shells, is good engineering and worth noticing.**
The vendor did not fork its editor for desktop. The commercial machinery
sits in the shell. Nothing for pumllint to copy — it has one shell — but
it is the cleanest explanation of why every surface checks identically.

**S2. The closing statement is stronger for being generous.** Four notes
were spent correcting "this ecosystem does not check" into "it checks
well, in the wrong place." The second is both truer and a better argument
for pumllint's contract, because it cannot be answered by the vendor
shipping a checker — they already did.

**S3. HTTP 200 is not existence** (§5), and the general form is the one
this record keeps relearning: *a cheap signal stood in for the expensive
check.*

**N1. Any web-app capability. Refused** — wrong artefact, server-side
storage, no gate, all rights reserved.

**N2. Reading §3 as carelessness. Refused**, as in the 39th note. The
errors are duplicate abstract definitions in a 1441-resource generated
catalogue. The finding is structural — *checks that cannot gate do not get
run* — and it is now demonstrated on the vendor's live production asset.

## 7. Fit — graded

### F1 — any web-app capability. **No.** N1.

### F2 — the surface table. **Complete at seven, and collapsed to four checking implementations.** §4.

### F3 — "one checker, every authoring surface, never wired to a build." **The run's closing statement.** §4.

### F4 — "on an SPA, HTTP 200 is not existence." **Recorded** (§5), with the general form.

| Declared constraint | Where this lands |
|---|---|
| **Zero runtime dependencies** | Not reached — F1 fails on the artefact. |
| **Deterministic product path, no LLM** | Untouched. |
| **Exit codes 0/1/2** | **The operative one**, and §4 is the run's best statement of what it buys. |
| **Demand-driven / Arc E bar** | Unchanged; nothing here is proposed. |
| **Licence posture** | All rights reserved; not a dependency candidate. |

## 8. SWOT

Scope: *pumllint's position relative to the Ilograph web app*.

**Strengths**

- The exit-code contract reaches where an editor-embedded checker cannot,
  demonstrated on the vendor's **live production** library (§3).

**Weaknesses**

- Unchanged from the 39th note and still the honest counterweight:
  **pumllint has no authoring-time story at all**, while Ilograph's is
  good and ships everywhere. An editor plugin / LSP remains the strongest
  unclaimed idea of the run, refused on demand rather than merit.

**Opportunities**

- None pursued.

**Threats**

- None from this product.

## 9. Decision, and the run closes

**Decision: no fit, no build, nothing queued. The Ilograph surface
inventory is exhausted — seven surfaces across seven notes (9th, 34th–40th).**

**Never build:** any Ilograph capability, on ground (1) of the ninth note,
which survived every re-examination.

**Recorded, not queued:**

1. **"One checker, every authoring surface, never wired to a build"**
   (§4) — the run's closing statement, and the strongest form of the
   exit-code argument this series has produced.
2. **Web and Desktop ship a byte-identical editor** (§2); the paid
   difference is licensing and export plumbing, not checking.
3. **"On an SPA, HTTP 200 is not existence"** (§5) — third instance of *a
   cheap signal standing in for the expensive check*, and the first caught
   before publication.
4. **An editor plugin / LSP for pumllint** — carried forward unchanged
   from the 39th note. Unrequested; gated on the Arc E bar.

**Re-litigate on:** nothing in this ecosystem. A concrete user asking for
editor-time checking re-opens item 4, and that is the only live thread
left.

## Related reading

- [The Ilograph Desktop app, evaluated](ilograph-desktop-app-evaluation.md)
  — the byte-identical editor, and the validator finding this generalizes.
- [The Ilograph Confluence Cloud plugin, evaluated](ilograph-confluence-plugin-evaluation.md)
  — the one surface that genuinely could not be inspected.
- [The Ilograph ecosystem, re-examined](ilograph-ecosystem-reexamined.md)
  — the CLI validator, the oracle used throughout §3.
- [The Ilograph ecosystem, evaluated](ilograph-ecosystem-evaluation.md) —
  the ninth note, whose ground (1) is the only one still standing.
- [ROADMAP.md](../ROADMAP.md) — the exit-code contract §4 closes on.

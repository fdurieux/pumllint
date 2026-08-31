# The Ilograph Confluence Cloud plugin, evaluated — the surface with the most documentation gravity has the least checking

*Dated evaluation, 2026-08-31, written against `994bb93` (v0.30.0). The
question as posed: investigate the Ilograph Confluence Cloud plugin, then
assess the boundaries, overlap, fit, gap, sense and nonsense of the
different fits against pumllint's roadmap and ecosystem. Thirty-eighth in
the series, fifth consecutive note on the Ilograph ecosystem, and the
first of the five where **the artefact genuinely could not be obtained** —
the previous four were each one registry command or one clone away.*

**Verdict up front: no fit, and for once the honest headline is a
measurement I could not make plus three I could. (1) **Not obtainable, and
this time that is real** — a Confluence Cloud app is Atlassian-hosted with
no downloadable artefact, its source is not public, and the only path to
running it is creating an Atlassian account, provisioning a Confluence
Cloud site and starting a commercial trial. **I declined to do that**;
that is a choice, not an inability, and it is recorded as such. (2) The
public listing data is hard and citable: **20 installs**, **1 review**,
and **version 2.13.0 released 2026-08-29 — two days before this note**,
making it the **most recently updated artefact in the entire ecosystem**.
(3) **Neither the Marketplace listing nor the vendor's own documentation
for this app mentions validation, linting, error checking or
diagnostics** — so the ninth note's *"Ilograph documents no validation"*
holds on the fifth surface, and the vendor's npm validator is surfaced in
**no product at all**. (4) The through-line of the last three notes
completes: **this is a surface with no CI surface — there is nowhere for a
gate to stand — and it is the surface where architecture documentation
actually lives.** The most documentation gravity, the least checking.**

*Bounds. **The plugin was not run.** Everything about its behaviour is
from the Atlassian Marketplace listing and the vendor's own documentation
page, read today — not observed. Nothing here reports what its editor
accepts or rejects, and the "no validation" finding in §3 is **an absence
in two documents, not a proof of absence in the product** (exactly the
hedge the ninth note used, and it is the right one). **Install counts are
one public number from one marketplace**: they may lag, may exclude
trials, and I did not corroborate them against any second source. Pricing
figures could not be extracted — the Marketplace pricing tab and the
vendor's `confluence.html` both failed to yield numbers to two fetches, so
**no pricing is claimed here** beyond "paid, with a 30-day trial". The
side-discovery in §5 — the vendor's `ilograph-standard-libraries`
repository — **was cloned and its file validated**, and those numbers are
measurements.*

## 1. Why this ran, and why it stops short

The ninth note named this plugin once, in a list of Ilograph's surfaces:
*"web, desktop and a Confluence Cloud plugin"*. It has never been
examined.

The four preceding notes each began with a bound the record called a
limitation and found it was debt — the validator was one `npm install`
away, the MCP server one clone, the exporter and the TypeScript library
one command each. **Five for five would have been the pattern. It is four
for five**, and the fifth is worth stating precisely because the
distinction matters:

| Path | Status |
|---|---|
| npm / PyPI package | **none exists** — searched both; the only `ilograph` npm packages are the two already evaluated |
| public source | **none** — the vendor's GitHub org holds one repository, and it is not this |
| downloadable artefact | **none by construction** — "Runs on Atlassian" means Atlassian hosts it; there is no build to fetch |
| run it | requires an **Atlassian account + a Confluence Cloud site + a commercial trial** |

**I declined the last one.** Creating accounts on third-party services and
starting commercial trials is well outside what "evaluate this plugin"
implies, and it would attach a real identity to a vendor relationship for
the sake of a documentation note. **Recorded as a decision, not an
inability** — someone with an existing Confluence Cloud instance could
close this gap in an afternoon, and §7 says what they should measure.

## 2. What the public record says

**"Ilograph Interactive Diagrams for Confluence"**, vendor **Ilograph
LLC**, Marketplace app `1229877`.

| | |
|---|---|
| Installs | **20** |
| Rating | 5/5, from **1 review** |
| Version | **2.13.0, released 2026-08-29** |
| Hosting | **Confluence Cloud only** |
| Type | "Runs on Atlassian" |
| Pricing | paid via Atlassian, 30-day free trial (figures not obtained) |
| Security | *"not part of the Marketplace Bug Bounty program"* |

The vendor's documentation describes it as **fully standalone**:

> your diagrams are accessed from (and **stored entirely within**) your
> Confluence Cloud instance

with **no Ilograph account or Desktop install required**, and embedding
via an *"Embedded Ilograph Diagram macro"* typed as `/ilo`.

So it is not a view onto the SaaS product. **It is a sixth, independent
copy of the authoring surface**, with its own storage and its own
commercial channel.

## 3. No validation here either — the fifth surface, the same absence

Neither the Marketplace listing nor the vendor's own
`docs/ilograph-for-confluence-cloud/` page mentions **validation, linting,
error checking, diagnostics or autocomplete**. The documentation covers
installation, creation, publishing and embedding.

This is an absence in two documents, not a proof of absence in the
product — but it is the *same* absence the ninth note found, now on a
fifth surface, and it supports something stronger than that note could
claim:

**The vendor ships a validator and surfaces it in none of its products.**
`validate-ilograph` exists on npm, has ~40 diagnostics, and appears in no
product documentation for the web app, the Desktop app, or this plugin.
It is a CLI for a CI pipeline, in an ecosystem whose CI tool
([the exporter](export-ilograph-package-evaluation.md)) does not call it.

## 4. The surface table completes — and this one has nowhere for a gate to stand

Three notes have now been circling one question: *what happens to checking
and gating as you change the delivery surface?* With the fifth surface the
table closes:

| Surface | Checks? | Can gate? | Why |
|---|---|---|---|
| `validate-ilograph` CLI | **yes**, ~40 diagnostics | **no** — always exits 0 | the exit code was never wired |
| `export-ilograph` CLI | **no** — YAML parse only | **yes** — exits 1 on parse failure | it is an exporter, not a checker |
| MCP server (community) | partial, four defects | **n/a** — returns a dict | its consumer is a model |
| `ilograph-typescript` | compile-time **shape** only | via `tsc` | values invisible to it |
| **Confluence plugin** | **not documented** | **no — there is no CI surface at all** | a wiki page has no build to fail |
| **pumllint** | **yes** | **yes — 0/1/2, a named contract** | both, in one tool |

**The Confluence plugin is the far end of the spectrum.** The previous
four each *had* a place a gate could stand and did not stand there. This
one has no such place: a diagram authored in a wiki macro and stored in
the wiki never passes through a build. There is no commit, no pipeline, no
exit code to return to anyone.

**And that is the surface where architecture documentation actually
lives.** Confluence is where a great many organisations keep their
architecture pages. So the ecosystem's checking capability is furthest
from the place its artefacts are most likely to be. **The most
documentation gravity, the least checking** — recorded because it is a
general observation about wiki-hosted description, not a fact about
Ilograph.

## 5. Side-discovery — a third copy of the sample, and it fails too

Searching for the plugin's source surfaced a **sixth vendor artefact** the
series had not seen: **`github.com/ilograph/ilograph-standard-libraries`**
— *"Standard libraries for use with Ilograph Interactive Diagrams"*, MIT,
`Copyright (c) 2021 billy-pilger`, last commit **2024-10-11**. It contains
one file: `aws.ilograph`.

Which makes **three published copies** of the vendor's flagship sample.
All three run through the vendor's own validator:

| Copy | Resources | Bytes | **Fatal Errors** |
|---|---|---|---|
| GitHub `standard-libraries` (2024-10-11) | 1441 | 176 280 | **8** |
| `validate-ilograph` npm (2025-12-03) | 1438 | 175 993 | **8** |
| `export-ilograph` npm (2026-07-26) | 1439 | 176 977 | **7** |

**Three distinct checksums — no two identical. All three fail.**

The 34th note found that the vendor's flagship sample fails the vendor's
own validator. The 36th found a second, divergent copy that also fails.
This is the third, it is the **canonical public one**, and it has carried
eight Fatal Errors in a public MIT repository since **October 2024 — 22
months**.

**A validator that cannot gate is a validator that does not run.** That is
now measured across three distribution channels and two years, and it is
the cleanest empirical argument in the whole series for why pumllint's
exit-code contract is a contract and not a convenience.

*A fifth licence posture, incidentally: this repository is MIT but
copyright an **individual** (`billy-pilger`), not Ilograph LLC — distinct
again from the four recorded in the 37th note.*

## 6. Vitality — the record completes, and inverts cleanly

| Artefact | Last updated | Idle |
|---|---|---|
| **Confluence plugin** (vendor) | **2026-08-29** | **2 days** |
| `export-ilograph` (vendor) | 2026-07-26 | ~5 weeks |
| `validate-ilograph` (vendor) | 2025-12-03 | ~9 months |
| `standard-libraries` (vendor) | 2024-10-11 | ~22 months |
| MCP server (community) | 2025-06-16 | 440 days |
| `ilograph-typescript` (community) | 2022-10-08 | 1423 days |

**The vendor's product surfaces are actively maintained; its validator is
its least-maintained code artefact; every third-party tool is dead.** The
ninth note's instinct — that this ecosystem does not invest in
checking — is now supported by six artefacts' release histories rather
than by the absence it wrongly asserted.

## 7. Boundaries, overlap, sense, nonsense

**Boundaries.** (1) **Artefact** — Ilograph YAML in a wiki; pumllint reads
PlantUML files in a repository. (2) **Storage** — diagrams live *inside
Confluence*, not in version control, so there is no commit for a linter to
hook. (3) **Surface** — §4: no build, no gate. (4) **Obtainability** —
§1.

**Overlap: none.** Not even conceptual, beyond §4's lesson.

**S1. 20 installs is a real market number, and it is small.** This is the
vendor's own first-party wiki integration of a commercial product with
four SaaS tiers and a desktop app — the best effort available for
"diagrams-as-code inside a wiki" — and it has 20 installs and one review.
Treated carefully (one marketplace, one number, uncorroborated), it is
still the only quantitative demand signal this series has found for the
category.

**S2. It bears on a question pumllint has already answered, and agrees
with the answer.** [The demand scan](demand-scan-embedded-plantuml.md)
measured demand for linting PlantUML embedded in markdown specs and
returned *"no — watch, don't build"* against the Arc E bar. **Confluence
is the same shape of question one surface over**, and the number here
points the same way. Recorded because the demand scan never considered
Confluence — pumllint's docs contain no mention of it outside these
Ilograph notes.

**S3. Wiki-hosted description is structurally un-gateable.** Not a
criticism of this plugin. If the artefact never enters version control, no
CI-shaped tool can check it, whoever builds it. That is worth holding onto
before anyone proposes a wiki integration for pumllint.

**N1. A Confluence (or any wiki) integration for pumllint. Refused, on
two independent grounds.** §4 — there is no gate on that surface, and
pumllint's contract is exit codes 0/1/2, which such an integration cannot
carry. And §7/S1–S2 — the demand signal available points the other way,
against a bar that is explicitly build-only-for-a-concrete-user.

**N2. Reading "20 installs" as a verdict on the category. Refused.** One
marketplace, one number, uncorroborated, and install counts are a poor
proxy for use. It is a signal, cited with its caveats, not a finding.

**N3. Treating §3's absence as proof the plugin has no validation.
Refused** — it is an absence in two documents. §1 says who could settle it
and how.

## 8. Fit — graded

### F1 — any Confluence capability for pumllint. **No**, on the gate (§4) and on demand (S1–S2).

### F2 — the surface/gating table. **Complete, and recorded as the series' clearest statement of what the exit-code contract is for.** §4.

### F3 — "a validator that cannot gate is a validator that does not run." **Now measured across three channels and 22 months.** §5.

### F4 — the ecosystem's vitality and licence records. **Both complete** — six artefacts, five licence postures. §5, §6.

| Declared constraint | Where this lands |
|---|---|
| **Zero runtime dependencies** | Not reached — F1 fails on the surface first. |
| **Deterministic product path, no LLM** | Untouched. |
| **Exit codes 0/1/2** | **The operative constraint.** §4 — a wiki surface cannot carry it, which is why N1 refuses. |
| **Demand-driven / Arc E bar** | **The other operative one.** S1–S2 — the only number available points away. |
| **Licence posture** | Not reached; nothing here is a dependency candidate. |

## 9. SWOT

Scope: *pumllint's position relative to the Confluence plugin*.

**Strengths**

- pumllint's artefacts are files in version control, which is the only
  place a gate can stand (§4).

**Weaknesses**

- **Reach.** Everything §4 says in pumllint's favour is also the shape of
  its limit: descriptions that live in a wiki are outside its scope
  entirely, and that is where a lot of architecture documentation is.
  Recorded honestly — the constraint is structural, not a defect, but it
  is not costless.

**Opportunities**

- None pursued. N1 refuses the obvious one on two grounds.

**Threats**

- None from this plugin (20 installs, different artefact, different
  surface).

## 10. Decision

**Decision: no fit, no build, nothing queued. One measurement declined and
recorded as declined; three records completed.**

**Never build:** a Confluence or wiki integration (N1) — no gate on that
surface, and the demand signal points away.

**Recorded, not queued:**

1. **The surface/gating table** (§4) — five Ilograph surfaces, none
   combining checking with gating, and the wiki surface having no place
   for a gate at all. The series' clearest statement of what the
   exit-code contract is *for*.
2. **"A validator that cannot gate is a validator that does not run"**
   (§5) — three published copies of the vendor's flagship sample, three
   checksums, all failing the vendor's own validator, the canonical one
   for 22 months.
3. **Wiki-hosted description is structurally un-gateable** (S3), and
   pumllint's reach ends where version control does (SWOT/Weaknesses).
   Hold both before anyone proposes a wiki integration.

**Re-litigate on:** a concrete user with a Confluence-hosted PlantUML
corpus asking for it — the Arc E bar, unchanged. Not on this plugin.

**Open, for anyone with a Confluence Cloud instance** (§1): install the
30-day trial and report whether the editor surfaces *any* diagnostics —
that settles §3's hedge, and it is the one question this note could not
answer.

## Related reading

- [The `ilograph-typescript` package, evaluated](ilograph-typescript-package-evaluation.md)
  — the fourth surface, and the licence record this extends to five.
- [The `export-ilograph` package, evaluated](export-ilograph-package-evaluation.md)
  — the CI tool that does not call the validator; §4's second row.
- [The Ilograph ecosystem, re-examined](ilograph-ecosystem-reexamined.md)
  — the validator used as the oracle in §5, and the first of the three
  failing sample copies.
- [Is there demand for linting PlantUML inside markdown specs?](demand-scan-embedded-plantuml.md)
  — the same question one surface over, and the same answer (S2).
- [ROADMAP.md](../ROADMAP.md) — the exit-code contract and the Arc E bar,
  the two constraints that decide §8.

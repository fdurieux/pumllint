# Is there demand for linting PlantUML inside markdown specs?

*Dated evidence note, 2026-07-26. A demand measurement, not a product
experiment: before building anything, the roadmap's wait-for-pull bar was
tested against public data. Verdict up front: **no — watch, don't build.**
The decision is recorded in [ROADMAP.md](../ROADMAP.md) § Settled
questions. Every number below is a direct measurement of public GitHub on
2026-07-26; no LLM judgment is involved anywhere in the pipeline. Cost:
$0 (≈45 authenticated code-search queries), ≈15 minutes wall clock.*

## Why this scan ran

A July 2026 review of the vendor/practitioner literature on AI-assisted
code generation (the engineering-layer companion to
[Where tooling pays](sdlc-tooling-landscape.md)) surfaced one
product-shaped candidate for this repository: **extract and lint fenced
PlantUML from markdown files**. The reasoning: the 2025–26 "spec-driven
development" wave (GitHub spec-kit, AWS Kiro) keeps its artifacts as
markdown documents, Kiro's design documents are described as containing
sequence diagrams, and pumllint today only discovers
`.puml/.plantuml/.iuml/.wsd` files (`collect_files()`,
`pumllint/engine.py`) — a diagram fenced inside a markdown spec is
invisible to it.

The Arc E bar is build-only-for-a-concrete-user. Here, uniquely, the pull
could be *measured* instead of waited for: if the spec-driven ecosystem
embedded PlantUML in its markdown artifacts in meaningful numbers, public
GitHub would show it.

## Pre-registered decision rules (stated before any query ran)

- **E1 — build signal:** PlantUML in ≥ 2% of Kiro `design.md` files, or
  ≥ 50 spec-artifact files across ecosystems containing `@startuml`.
- **E2 — against:** near-zero (< 10 files) in spec directories *and*
  Mermaid ≥ 50× ahead in the same directories.
- **E3 — general-feature fallback:** global `@startuml`-in-markdown
  ≥ 10,000 files would support extraction as a general-docs feature even
  without spec-driven demand; < 2,000 would mean weak everywhere.

## Method

GitHub code search (legacy REST API via `gh`, authenticated, throttled to
its 10 requests/minute), 2026-07-26. Ecosystem markers were validated
before use: spec-kit's `plan-template.md` verifiably contains the literal
heading "Constitution Check" (fetched from `github/spec-kit`), and a
control query confirmed `path:.kiro` ≈ `path:.kiro/specs` for `design.md`
(1,780 vs 1,760) — the path qualifier behaves as intended. Neither
spec-kit's templates nor Kiro's spec documentation mandates a diagram
notation (both checked), so the counts below reflect organic and
generator behavior, which is the honest measure.

Three phases:

1. **Footprint and comparison queries** — 17 queries: ecosystem
   denominators, PlantUML numerators, Mermaid comparisons, global
   baselines (full table below).
2. **Repo-level join** — 25 spec-kit repos sampled (every 4th from the
   first 100 indexed `constitution.md path:.specify` hits, deduplicated),
   each queried for `startuml` in any file.
3. **Inspection** — unique-repo deduplication of all 61 Kiro hits,
   breakdown by file type and `.kiro/` subdirectory, and raw fetch of
   sample hit files to verify what actually matched.

## Results

| Query | Count | Reads as |
|---|---|---|
| `filename:requirements.md path:.kiro` | 2,120 | public Kiro spec sets (denominator) |
| `filename:design.md path:.kiro` | 1,780 | Kiro design docs — the claimed diagram home |
| `filename:design.md path:.kiro/specs` | 1,760 | control: path-qualifier semantics |
| `filename:constitution.md path:.specify` | 3,160 | spec-kit repos (denominator) |
| `filename:plan.md "Constitution Check"` | 3,320 | spec-kit plan.md files (denominator) |
| `startuml path:.kiro` | 61 | PlantUML source under `.kiro/`, any file type |
| `plantuml path:.kiro` | 236 | 'plantuml' token under `.kiro/` (fences + prose + config) |
| `startuml path:.specify` | 36 | `.specify/` internals (templates/scripts), not spec content |
| `"Constitution Check" startuml extension:md` | 3 | spec-kit plan.md embedding PlantUML |
| `startuml path:specs extension:md` | 93 | generic `specs/` directories (noisy) |
| `mermaid path:.kiro` | 4,664 | Mermaid under `.kiro/` — **76×** PlantUML |
| `mermaid path:.specify` | 936 | Mermaid in `.specify/` internals |
| `"Constitution Check" mermaid extension:md` | 1,312 | spec-kit plan.md embedding Mermaid — **437×** |
| `startuml extension:md` | 8,068 | global embedded PlantUML-in-markdown |
| `mermaid extension:md` | 444,480 | global Mermaid-in-markdown (noisier term) — **55×** |
| `startuml extension:puml` | 131,008 | standalone `.puml` ecosystem — **16×** the embedded form |
| `startuml filename:README.md` | 2,256 | README embeds (subset of global) |

**Repo-level join:** 0 of 25 sampled spec-kit repos contain `@startuml`
in any file. Zero hits at n = 25 puts the true share below ~11% at 95%
confidence (rule of three); the file-level counts say it is far lower.

## Inspection — the raw count passed, the evidence failed

The 61 `.kiro/` hits deduplicate to **13 repositories**, two of which
(`linhdk0712/enterprise-cron`, `tommyyula/iTomCenter`) hold 40 of the 61
files. By type: **37 are standalone `.puml` files**, 21 are markdown, 3
are Python. Of the 21 markdown files, only **9 sit under `.kiro/specs/`**
(the rest are skills/steering/agents instruction files), and those 9 span
just **4 repositories**. Raw-fetching them cut further:

- `jeasoncc/grain` — false positive: the `@startuml` sits inside a
  TypeScript test fixture; the spec is *about* a diagram-editor feature.
  PlantUML is the subject matter, not the methodology.
- `ajayrajk/LowLevelDesign` — the genuine article: real ` ```plantuml `
  fences containing `@startuml` class and sequence diagrams inside
  `design.md`. The pattern exists; it is just rare.

Honest estimate of genuine embedded-PlantUML Kiro spec repos: **3–8 out
of ~2,120 public spec sets, ≈ 0.2%**. The three spec-kit file hits are an
archived doc, a SysML-tooling project (mentions `@startuml` because
diagrams are its domain), and a pasted session transcript — zero organic.

A note the repository's own evidence work makes obligatory: E1's absolute
arm was **nominally met** (61 + 3 = 64 ≥ 50 raw files) and **failed
inspection**; E2's "< 10 files" arm was nominally missed at 61 raw files
and **holds after the same inspection**. One correction, applied
symmetrically, flips both — raw token counts are not demand.

## Verdict against the pre-registered rules

- **E1: failed after inspection.** ≈ 0.2% of Kiro spec sets against the
  2% bar; ~3–8 genuine repos against the spirit of the 50-file bar.
- **E2: confirmed in substance.** Mermaid ahead 76× (`.kiro/`) and 437×
  (spec-kit plan.md); genuine embedded PlantUML below 10 files.
- **E3: failed.** 8,068 global embeds, under the 10,000 bar, 55× behind
  Mermaid — and 16× smaller than the standalone `.puml` ecosystem the
  tool already serves. Current file targeting covers the dominant public
  form of PlantUML.

**Decision: watch, don't build.**

## Three side-findings worth keeping

1. **Kiro users who do use PlantUML co-locate `.puml` files inside
   `.kiro/specs/`** (37 of the 61 hits: sequence, state, use-case
   diagrams as siblings of `requirements.md`). pumllint lints those
   **today** with zero new code — if a spec-driven adopter appears, this
   is a documentation pattern to show, not a feature to build.
2. **The agent-instruction layer mentions PlantUML more than the specs
   do**: 34 of the first 100 `plantuml`-token markdown hits under
   `.kiro/` are steering/skills/agents files — people teaching their
   agents to *author* PlantUML. A small corroboration for the
   agent-consumption-recipe candidate (documentation telling coding
   agents to run `score`, read the gap JSON, fix, and re-score) —
   since built as [Using pumllint from a coding agent](agents.md).
3. **Mermaid's dominance is the strategic datum.** If this category ever
   extends notation coverage, demand points at Mermaid — but that is a
   sibling stack (parser, corpus, calibration ladder, golden contract,
   evidence extension from zero), governed by the same Arc E bar.
   Recorded, not queued.

## Caveats

- **Public GitHub only.** Enterprise and private usage — arguably the
  category's main audience — is invisible to this scan. It measures the
  *public footprint* of demand, not demand itself.
- **GitLab excluded** (no practically accessible code-search API).
  GitLab renders PlantUML fences natively, so embedding is likelier
  there; this scan can only under-count that population.
- **Legacy code-search semantics:** approximate `total_count`, default
  branches only, files < 384 KB, forks excluded, long-inactive repos
  drop from the index. Matching is token-based, not fence-aware — a
  ` ```plantuml ` fence whose body omits `@startuml` counts for the
  `plantuml` query but not the `startuml` one, and prose mentions count
  for both. Errors run in both directions.
- **Phase-2 sampling frame:** every 4th repo from the first 100
  best-match results of 3,160 — systematic over a convenience frame, not
  uniform over the population.
- Single-day snapshot (2026-07-26).

## Re-litigate on

- a concrete user asking to lint fenced PlantUML in markdown;
- a spec-driven tool (spec-kit, Kiro, or a successor) emitting or
  recommending PlantUML in its artifacts;
- a GitLab-side measurement showing material embedded-PlantUML usage;
- the global embedded footprint passing the pre-registered 10,000 bar.

## Reproduction

Any authenticated `gh` can re-run the counts (mind the 10 requests/minute
code-search limit; space queries ≥ 7 s apart):

```sh
gh api -X GET search/code -f q='startuml path:.kiro' -F per_page=10 \
  --jq .total_count
# …repeat for each query in the results table.
# Repo-level join: for each sampled repo R:
gh api -X GET search/code -f q="startuml repo:R" --jq .total_count
```

Counts are index-dependent and will drift; the pre-registered rules above
are the fixed part.

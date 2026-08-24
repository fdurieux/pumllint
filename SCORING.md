# Maturity Scoring Model (360° Assessment)

> Spec section for `RULES.md`. The scoring model is a **reporter-layer aggregation** over
> rule findings. It introduces no new analysis machinery: every score is derived from
> existing rule results plus diagram element counts already available in the semantic
> `Diagram` model. Rules remain the single source of truth.

## 1. Purpose

The maturity score answers two questions per diagram (and per model set):

1. **How disciplined is this model?** (method-convention quality, ARIS-style)
2. **Is it precise enough for LLM code generation?** (the level-5 claim)

The report is prescriptive: alongside the level, it emits a **gap report** listing the
concrete findings that block promotion to the next level.

## 2. Dimensions

Each rule carries a `dimension` attribute in the registry (new metadata field, defaulted
per pack, overridable per rule). Seven dimensions:

| ID      | Dimension              | Source of signal                                            | Default weight |
|---------|------------------------|-------------------------------------------------------------|----------------|
| DIM-SYN | Syntactic validity     | `plantuml -checkonly` exit code (external gate, pass/fail)  | gate           |
| DIM-SEM | Semantic correctness   | All pack findings not claimed by a more specific dimension  | 0.20           |
| DIM-CMP | Completeness           | Typed params/returns, multiplicities, guards, alt/error paths, orphan elements | 0.30 |
| DIM-CON | Consistency            | Naming conventions; cross-diagram entity identity           | 0.15           |
| DIM-TRC | Traceability           | Title, ID, ownership, requirement/ADR links (GEN pack)      | 0.05           |
| DIM-RDB | Readability            | Participant count, nesting depth, size thresholds           | 0.05           |
| DIM-AMB | Ambiguity              | Vague verbs, unlabeled arrows, structure hidden in notes    | 0.25           |

Default weights are **signal-proportional** (calibrated in §9, revisited in
v0.12.0 after the TRC/RDB packs were thickened): weight follows the signal
the dimension emits *by default*. DIM-TRC's rules beyond title/name
(owner-tag GEN006, requirement-link GEN007) are convention-gated — dormant
until the project configures its pattern — and DIM-RDB's size guards
(GEN008/GEN009/SEQ011 alongside GEN005/SEQ008/CLS005) fire only at generous
tail thresholds, so both keep 0.05 composite weight apiece; the difference
stays with DIM-CMP/DIM-AMB, the dimensions that carry the
generation-readiness thesis. Note the per-dimension **gates** (Level 4/5
thresholds, cap C3) bind hardest on small diagrams: the penalty is
density-normalised, so on an element-rich diagram a single missing-title
finding leaves DIM-TRC above the thresholds and Method-complete intact (a
titleless 20-element diagram still scores Level 5 at 99.4/100). The gap
report lists blocking findings only below the target level; at or above
it, it is empty.

DIM-SYN is a **gate**, not a weighted dimension: if syntax fails, the diagram is Level 1
and no further scoring is reported.

## 3. Scoring formula

Per dimension *d*:

```
penalty(d)  = Σ severity_weight(f) for each finding f tagged with d
density(d)  = penalty(d) / max(1, element_count)
score(d)    = clamp(100 − K × density(d), 0, 100)
```

- `element_count` = participants + messages (SEQ), classes + relations (CLS), etc. —
  taken from the `Diagram` model, so large diagrams are not punished for size alone.
- `K` (scaling constant) default **50**, configurable.

Default severity weights (SonarQube-aligned):

| Severity | Weight |
|----------|--------|
| blocker  | 10     |
| critical | 8      |
| major    | 5      |
| minor    | 2      |
| info     | 0.5    |

(`critical` continues the decelerating multiplier ladder — ×4, ×2.5, ×1.6, ×1.25
— reading as "almost a blocker".)

**Suppressions.** Findings silenced by inline `' pumllint: disable` comments
are excluded from every penalty above — the score assesses the diagram as its
authors configured it, and an inline suppression is a reviewable, diff-visible
configuration act. The exclusion is disclosed, never silent: each scored
diagram carries a **suppressed-findings count** that every report surfaces
(§5), so a suppressed-clean diagram cannot pose as a clean one and
suppress-spamming cannot quietly inflate a level. `--no-suppressions`
re-scores with the comments ignored for a full audit.

Composite:

```
composite = Σ weight(d) × score(d)   for d in weighted dimensions (weights sum to 1.0)
```

Model-set aggregate (the "per model set" answer, 0.6.0):

```
set_level     = min(level(u))  for each scored unit u          # worst diagram
set_composite = Σ composite(u) × max(1, element_count(u)) / Σ max(1, element_count(u))
```

The set level is the *worst* per-diagram level — levels are claims, and a
claim about a set can only be as strong as its weakest member (this also
makes the `--min-level` gate and the set level agree by construction). The
set composite is element-weighted so a large detailed diagram moves it more
than a stub; empty diagrams weigh 1 so they still register.

## 4. Maturity levels

| Level | Name             | Criteria                                                                  |
|-------|------------------|---------------------------------------------------------------------------|
| 1     | Sketchy          | Syntax gate fails, **or** composite < 40                                  |
| 2     | Structured       | Syntax passes and composite ≥ 40                                          |
| 3     | Disciplined      | Composite ≥ 60 **and** zero blocker findings                              |
| 4     | Precise          | Composite ≥ 75, zero blockers, DIM-CMP ≥ 70 **and** DIM-AMB ≥ 70          |
| 5     | Method-complete  | Composite ≥ 90, every dimension ≥ 80, zero blocker **and** zero major     |

"Zero major" is read as **no finding at major severity or worse** (major,
critical, blocker) — a critical structural error also blocks Method-complete.

**Caps (anti-gaming rules):**

- C1: Any blocker finding caps the level at **2**, regardless of composite.
- C2: Syntax gate failure forces level **1**, regardless of anything else.
- C3: Any single dimension score < 40 caps the level at **3** (no dimension may be
  sacrificed to inflate the composite).
- C4: A diagram with **zero modelled elements** forces level **1** — scoring
  rewards absence of findings, so vacuous input must not score at all.
- C5: An **unrecognized diagram type** (`unknown`) caps the level at **2**.
- C6: Fewer than `l4_min_elements` elements (default **3**) caps the level at
  **3** — "Precise" requires enough content to be precise about.
- C7: Level **5** requires the profile named by `l5_requires_profile` (default
  **codegen**) to be active — the Method-complete claim is bound to the rule
  pack that gives it substance. Set to `null` to disable. The opt-in
  `c7_requires_applicable_rules` flag (default **false**) tightens the cap:
  the required profile must also carry at least one rule that *applies to the
  diagram's type*, or the Level-5 claim is vacuous — an active profile whose
  rules never examined the diagram proves nothing. Consequence worth knowing
  before enabling it: with the default codegen profile every SEQ10x rule is
  sequence-only, so under the flag no non-sequence diagram can reach Level 5
  until the profile grows rules for its type.

All thresholds, weights, and caps are configurable under the `scoring:` key
(YAML/TOML/JSON, same precedence as rule config).

## 5. Gap report (prescriptive advice)

For the next level up, the reporter computes the **minimal blocking set**:

1. Unsatisfied caps first (e.g., "1 blocker finding — resolve SEQ003 at line 42").
2. Unsatisfied dimension thresholds, listing the highest-weight findings in that
   dimension until the threshold would be met.
3. Composite shortfall, listing highest-weight findings overall.

Output format (text reporter):

```
Level 3 (Disciplined) — 68/100
To reach Level 4 (Precise):
  • DIM-CMP is 61, needs ≥ 70 — fix:
      SEQ012 major  order.puml:18  message 'process()' has untyped parameters
      SEQ014 minor  order.puml:23  alt branch missing failure path
  • DIM-AMB is 66, needs ≥ 70 — fix:
      GEN020 minor  order.puml:9   arrow label 'handle data' uses vague verb
```

JSON reporter emits `score`, `level`, `dimensions{}`, and `gap_report[]` as a top-level
`maturity` object. SonarQube reporter: the Generic Issue Import Format carries issues,
not measures, so the maturity object is written to the JSON report only; optionally one
`info`-severity synthetic issue summarizing the level can be emitted for visibility.

Suppression disclosure (§3) rides on every format: the JSON report carries
`suppressedCount` per diagram and summed on `modelSet`; the text and HTML
reports annotate any non-zero count next to the score — `100/100 (3
suppressed)` — and stay unannotated when nothing was suppressed, so clean
output is unchanged; the SonarQube synthetic issue appends the count to its
message.

## 6. CLI

```
pumllint score <paths> [--min-level N] [--check-syntax] [--baseline FILE [--update-baseline]]
```

- `--min-level N` — exit non-zero if any scored unit is below level N
  (equivalently: if the model-set level is below N). The CI gate.
- `--baseline FILE` — ratchet mode (0.6.0): compare per-diagram levels
  against FILE and exit non-zero only on *regression* (a diagram below its
  recorded level). A missing FILE is recorded on the spot; diagrams new since
  the baseline pass. `--update-baseline` rewrites FILE with the current
  levels. Makes the gate adoptable on brownfield model sets.
- Trend/delta (0.7.0): ratchet-compare runs annotate the text report per
  diagram and for the model set — `(Level 3 → 4 since last baseline)`,
  `(new since baseline)` — and the json format adds a machine-readable
  `"baseline": {"level": N, "delta": ±d}` (or `null`) per diagram and on
  `modelSet`. With `--update-baseline`, deltas are computed against the old
  file before it is rewritten.
- `-f badge` (0.7.0) — shields.io endpoint JSON stating the model-set level
  (`{"schemaVersion": 1, "label": "pumllint maturity", "message":
  "Level 3 — Disciplined", "color": "yellow"}`); level→color runs
  red/orange/yellow/yellowgreen/brightgreen, `lightgrey` when nothing was
  scored. Score-only: the lint command rejects it.
- `-f html` (0.15.0) — a single self-contained page for architect reviews:
  model-set verdict first, then per-diagram cards sorted worst-first (the
  set is only as trustworthy as its weakest diagram) with level pill,
  per-dimension score bars, the gap report to the next level, and baseline
  trend annotations when ratcheting. No scripts, no external requests, no
  timestamps — output is deterministic and renders offline (CI artifact,
  wiki, email). Score-only, like the badge.
- `--check-syntax` — run the DIM-SYN gate (`<command> -checkonly <file>` per
  file); failures force Level 1. Also enabled via config: `scoring:
  {syntax_gate: true, syntax_command: plantuml}` (`syntax_command` may be a
  string or argv list, e.g. `[java, -jar, plantuml.jar]`). Off by default —
  it needs a PlantUML/Java install the linter itself does not require. A
  string is split platform-appropriately, so a Windows path keeps its
  backslashes; the executable is resolved with `shutil.which`, so a
  `plantuml.bat`/`.cmd` wrapper on PATH is found.
  Because `syntax_command` is executed, the config file carries code-level
  trust — see SECURITY.md.
- Cross-diagram consistency (DIM-CON multi-file checks) activates when more than one
  file is passed; otherwise DIM-CON scores single-file naming rules only.

## 7. Acceptance criteria (Gherkin)

Structured for direct lift into `features/scoring.feature`. One promotion scenario and
one boundary/cap scenario per level threshold.

```gherkin
Feature: Maturity level assignment
  The scoring reporter aggregates rule findings into a 360 maturity level
  and a prescriptive gap report.

  Background:
    Given default scoring configuration

  # --- Level 1 / syntax gate ---

  Scenario: Syntax failure forces Level 1 regardless of findings
    Given a diagram that fails the plantuml -checkonly gate
    And the diagram would otherwise have a composite score of 95
    When the scoring reporter runs
    Then the maturity level is 1
    And no dimension scores are reported
    And the gap report states the syntax gate must pass first

  Scenario: Very low composite yields Level 1
    Given a syntactically valid diagram with composite score 35
    When the scoring reporter runs
    Then the maturity level is 1
    And the gap report lists the highest-weight findings needed to reach composite 40

  # --- Level 2 ---

  Scenario: Passing syntax with composite at threshold reaches Level 2
    Given a syntactically valid diagram with composite score 40
    And the diagram has one blocker finding
    When the scoring reporter runs
    Then the maturity level is 2

  Scenario: Blocker cap holds a high-scoring diagram at Level 2
    Given a syntactically valid diagram with composite score 92
    And every dimension score is at least 80
    And the diagram has one blocker finding
    When the scoring reporter runs
    Then the maturity level is 2
    And the gap report lists the blocker finding as the sole obstacle to Level 3

  # --- Level 3 ---

  Scenario: Composite 60 with zero blockers reaches Level 3
    Given a syntactically valid diagram with composite score 60
    And the diagram has no blocker findings
    When the scoring reporter runs
    Then the maturity level is 3

  Scenario: Weak dimension cap holds diagram at Level 3
    Given a syntactically valid diagram with composite score 78
    And the diagram has no blocker findings
    And dimension DIM-TRC has a score of 35
    When the scoring reporter runs
    Then the maturity level is 3
    And the gap report lists DIM-TRC findings required to lift the dimension above 40

  # --- Level 4 ---

  Scenario: Composite 75 with strong completeness and low ambiguity reaches Level 4
    Given a syntactically valid diagram with composite score 75
    And the diagram has no blocker findings
    And dimension DIM-CMP has a score of 70
    And dimension DIM-AMB has a score of 70
    And every dimension score is at least 40
    When the scoring reporter runs
    Then the maturity level is 4

  Scenario: High composite with ambiguous labels stays at Level 3
    Given a syntactically valid diagram with composite score 82
    And the diagram has no blocker findings
    And dimension DIM-AMB has a score of 65
    When the scoring reporter runs
    Then the maturity level is 3
    And the gap report lists DIM-AMB findings required to reach 70

  # --- Level 5 ---

  Scenario: Fully disciplined model reaches Method-complete
    Given a syntactically valid diagram with composite score 91
    And the codegen profile is active
    And every dimension score is at least 80
    And the diagram has no blocker findings
    And the diagram has no major findings
    When the scoring reporter runs
    Then the maturity level is 5

  Scenario: A single major finding blocks Method-complete
    Given a syntactically valid diagram with composite score 94
    And the codegen profile is active
    And every dimension score is at least 80
    And the diagram has exactly one major finding
    When the scoring reporter runs
    Then the maturity level is 4
    And the gap report lists the major finding as the sole obstacle to Level 5

  # --- Integrity caps (C4-C7) ---

  Scenario: An empty diagram cannot score
    Given a syntactically valid diagram with zero modelled elements
    When the scoring reporter runs
    Then the maturity level is 1
    And the gap report states the diagram has no modelled content

  Scenario: An unrecognized diagram type caps at Structured
    Given a diagram whose type is not recognized
    And the diagram would otherwise have a composite score of 100
    When the scoring reporter runs
    Then the maturity level is 2

  Scenario: A near-empty diagram cannot claim Precise
    Given a clean sequence diagram with 2 modelled elements
    When the scoring reporter runs
    Then the maturity level is 3
    And the gap report states Level 4 requires at least 3 elements

  Scenario: Method-complete requires the codegen profile
    Given a clean sequence diagram scored without the codegen profile
    And the diagram would otherwise reach Level 5
    When the scoring reporter runs
    Then the maturity level is 4
    And the gap report states Level 5 requires the codegen profile

  # --- CI gate ---

  Scenario: min-level gate fails the build below threshold
    Given a diagram scored at maturity level 3
    When pumllint score runs with --min-level 4
    Then the exit code is non-zero

  Scenario: min-level gate passes the build at threshold
    Given a diagram scored at maturity level 4
    When pumllint score runs with --min-level 4
    Then the exit code is zero
```

## 8. Implementation notes

- New registry metadata: `dimension=` parameter on the rule decorator, defaulted by pack
  (SEQ/CLS structural rules → DIM-CMP or DIM-SEM; GEN metadata rules → DIM-TRC, etc.).
  Existing rules need only a one-line annotation each.
- The scorer is a pure function `score(findings, diagram) -> MaturityResult` — trivially
  unit-testable and independent of reporters.
- Cross-diagram consistency (DIM-CON) is the only piece requiring new analysis
  (a symbol table across files); ship the scorer first with DIM-CON limited to
  single-file naming rules, and extend later.

## 9. Calibration notes (Phase 10)

The defaults above were validated against a generated calibration corpus
(`tools/gen_corpus.py`: mutation ladders over the good examples + synthetic
boundary probes, plus a wild tier harvested from public GitHub repos) using
the sensitivity harness `tools/calibrate.py`. Findings that fixed the numbers:

- **K = 50 confirmed.** Zero monotonicity violations at every K tested
  (25/50/75/100) — a degraded diagram never outscores its parent — but K = 25
  is too lenient (a known-bad example reaches the same level as its good
  counterpart) and K ≥ 75 doubles single-finding volatility with no
  discrimination gain.
- **Severity weight `critical = 8` confirmed.** `critical = 6` also passes all
  metrics; 8 is kept for the decelerating multiplier ladder (§3).
- **Dimension weights are signal-proportional** (§2): the 2-rule dimensions
  DIM-TRC/DIM-RDB carry 0.05 each; the freed weight goes to DIM-CMP/DIM-AMB.
  Versus the pre-calibration weights this reduces fragile near-boundary
  verdicts without changing any pair ordering or expected level. Revisit when
  the TRC/RDB packs are thickened with more rules.
- **Weights revisited after thickening (v0.12.0) — decision: unchanged.**
  The TRC pack grew to 4 rules and RDB to 6, but the *default* signal is what
  weight follows, and it did not move: GEN006/GEN007 are convention-gated
  (dormant until a project supplies its ownership/reference pattern — an
  always-on tag requirement would demote every diagram below the Level-5
  dimension gate of 80 by fiat), and GEN008/GEN009/SEQ011 are tail guards at
  generous defaults that no calibration-corpus unit reaches. Re-running the
  harness with the thickened packs active: zero monotonicity violations, zero
  expected-level misses, 6/6 pair orderings (the example-pair set was
  extended with the class/state/usecase pairs), golden scores byte-identical
  — no re-freeze required. Projects that enable GEN006/GEN007 are effectively
  opting their TRC dimension into real signal and can raise its weight via
  `scoring.dimension_weights` if they want the composite to reflect it.
- **Small-diagram coarseness is accepted, not patched.** Under ~10 elements a
  single finding moves a dimension by tens of points — by construction
  (density has a small denominator). Level assignments stay bounded (at most
  one density-driven level per single finding in the 5–9-element bucket;
  larger drops are cap-driven and intended, e.g. a blocker forcing Level 2).
  Cap C6 floors the tiniest diagrams, and the gap report keeps the verdict
  actionable even where it is coarse. K-damping and score bands were
  considered and rejected as complexity the user cannot reason about.
- **Scores are a public contract.** `tests/golden_scores.json` snapshots the
  level and composite of every deterministic corpus unit; the golden test
  fails on any drift. After a deliberate scoring change, re-freeze with
  `python tools/calibrate.py --freeze tests/golden_scores.json`.
- **Corpus extended to every diagram type (v0.14.0).** The deterministic
  corpus gained mutation ladders over the class/state/use-case good examples
  (CLS/STA/UC operators, same ladder discipline: element-adding operators are
  singles-only) and three per-type clean synthetic probes pinned at Level 4.
  The re-freeze was **purely additive** — 49 → 83 units, every pre-existing
  entry byte-identical — because no scoring behavior changed, only coverage.
  All metrics stayed clean (0 monotonicity violations, 0 expected-level
  misses, 6/6 pairs). The 5–9-element volatility bucket now records a
  2-level single-finding drop: the state pack's duplicate-initial blocker
  forcing Level 2 — cap-driven and intended, per the coarseness note above.

**Codegen-claim experiments (2026-07-22).** A 12-run pilot
($0.94; harness since retired in favor of the full tool — raw pilot data in
`pilot_results/report.json`) validated the protocol, then the full
experiment (`tools/codegen_experiment.py`: 25 diagrams spanning L1–L5 × 3
generations on claude-opus-4-8, judged independently by claude-sonnet-5
against a split invented-logic/embellishment rubric; 75/75 runs clean,
$5.24) measured the maturity→codegen relationship. Full write-up:
**EVIDENCE.md**. Headline results: composite↔fidelity correlation
**r ≈ 0.49** (holds within scenario families, r = 0.39–0.48); the
relationship is a **cliff, not a slope** — fidelity is roughly flat above
composite ~40 and collapses (~49/100, with invented business logic roughly
doubling) below it; and same-model self-judging inflates fidelity by ~15
points, so independent judging is mandatory in any rerun.

**Claim language (settled):** Level 5 — named **Method-complete** since
v0.27.0 — is described as *"method-convention
complete — the diagram-side preconditions for faithful generation"*, not
"guaranteed generation-ready": even pristine L5 diagrams average ~72/100
fidelity under a strict independent judge, because a sequence diagram
underdetermines an implementation. The evidence-backed marketing claims are
the correlation and the cliff: **low-maturity diagrams measurably poison
generation, and the `--min-level` CI gate is the demonstrated mitigation.**

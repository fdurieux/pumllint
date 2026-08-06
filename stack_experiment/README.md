# stack_experiment — W0 kits for the spec-stack research program

*Authored 2026-08-06 as W0 of the research program chartered in
[docs/research-charter.md](../docs/research-charter.md) (§7). This
directory is lab territory under the packaging settlement: nothing in
it ships in the product, and the product path stays deterministic.*

## What this is

The **CargoQuote adversarial-threshold reference system** and its
artifact kit — the measurement substrate for waves W1 (portfolio
ablation), W2 (redundancy/conflict), W3 (carrier equivalence) and W4
(dose–response), plus the wave pre-registration template.

**The confound it fixes:** the C4 detail-ladder experiment
(docs/c4-codegen-detail-experiment.md) measured R4−R3 = 0.0 pp executed
because LoanCheck's decision values were domain-canonical (approve at
700) — the generator's priors guessed them, so the suite could not see
what the companion spec pins. Every CargoQuote decision value is
**non-canonical by construction**: validation bounds 3/19 400, 25/7 150,
50/83 000; risk banding 41/42/66/67; tariff 0.87/1.13, surcharge 316
above 1 244 kg, ×1.19 from 4 912 km applied after the flat surcharge;
and one **prior-inverting** rule — a screening outage does not fail the
quote, it prices and holds it un-notified (DT-S note 5). The smoke
test's mutant arm (below) verifies these are adversarial in fact, not
by assertion: the canonical guess measurably fails.

## Inventory — and where each information class lives

| File | Carrier | Information it (alone) carries | W1 rung |
|---|---|---|---|
| `cargo_quote/brief.md` | prose | purpose, actors, capabilities — no rules, no failure policy | base |
| `cargo_quote/structure/containers.puml` | C4 container (checklist-complete) | elements, boundaries, technologies, relation intents | +structure |
| `cargo_quote/behavior/quote_flow.puml` | UML sequence, **Level 5 (100/100) under the codegen profile** | flow order, all failure paths, notify/price-per-row rules, the prior-inverting hold path — thresholds symbolic (`ACCEPT_MAX`), numbers deliberately absent | +behavior |
| `cargo_quote/behavior/quote_flow_bad.puml` | UML sequence, **Level 1 (29/100) under the codegen profile** | same intended system, below-cliff degraded | below-cliff-vs-absent arm (charter §4) |
| `cargo_quote/contract/spec.md` | companion spec | glossary, flow/error policy, API contract — numbers only by DT reference | +contract |
| `cargo_quote/contract/decision_table.md` | decision tables (DT-V/DT-S/DT-P) | **every numeric rule, exactly once** | +contract |
| `cargo_quote/contract/openapi.yaml` | OpenAPI 3.0 | request/response shapes, DT-V bounds as schema, status enum | +contract |
| `cargo_quote/contract/quote_states.puml` | UML state machine (lints clean, Level 4 100/100) | lifecycle: terminal states, hold/review resolution transitions | +contract |
| `cargo_quote/tests_input/acceptance.feature` | Gherkin (declarative) | 7 worked examples G1–G7, values distinct from the grading suite where declared | +tests-as-input |
| `cargo_quote/tests_input/oracle_overlap.md` | — | the per-scenario input-tests ↔ grading-suite overlap declaration (charter §7 W1 obligation) | pre-registration input |
| `cargo_quote/reference_impl.py` | Python | smoke-test oracle ONLY — never a generation input | — |
| `../tools/acceptance/cargo_quote_suite.py` | grading suite, 11 scenarios + overlays | the intended behavior, sensitivity-classed [flow]/[contract]/[prior-inverting] | oracle |
| `smoke_test.py` | — | deterministic calibration: reference 11/11 + 3 prior-mutants caught exactly | — |
| `PREREGISTRATION_TEMPLATE.md` | — | the house wave protocol as a fill-in template | — |

Deliberate design rule, restated: numbers live **only** in
`decision_table.md`; the behavior diagram carries symbolic guards and
the spec references the tables — so W1's rungs separate cleanly
(boundary scenarios are contract-sensitive, flow scenarios are
behavior-sensitive) and redundant restatement cannot drift. W2's
conflict conditions will *inject* controlled contradictions as
variants; the pristine kit contains none.

## Verified state (2026-08-06, this environment)

- `quote_flow.puml`: Level 5, 100/100, `--profile codegen`, default
  config (scored from a neutral cwd — the repo's own pumllint.toml
  configures convention rules and must not leak into kit scoring).
- `quote_flow_bad.puml`: Level 1, 29/100 — below the composite-40
  cliff.
- `quote_states.puml`: no findings; Level 4, 100/100.
- `python stack_experiment/smoke_test.py`: reference 11/11; mutants
  `prior_error_on_screening_outage` → fails exactly
  {screening_down_hold}, `canonical_accept_threshold_70` → fails
  exactly {review_boundary_42, refuse_boundary_67},
  `inverted_surcharge_order` → fails exactly {price_exact_both}.
- Syntax gate: all four `.puml` files pass `-checkonly` under the
  CI-pinned PlantUML 1.2026.6 (sha-verified jar, run 2026-08-06 —
  including the below-cliff variant: like the shipped bad examples,
  its damage is semantic, not grammatical). Note the CI syntax-gate
  job sweeps `examples docs` only; it does not cover this directory.
- Repo test suite unaffected (`python tests/run_tests.py`).

## What W0 deliberately does NOT do

- **No freeze.** The suite is authored and smoke-calibrated, not
  frozen: the house generation-calibration (pristine generated
  artifacts, à la the LoanCheck 36/36) runs at W1 pre-registration —
  it needs API keys this environment does not hold. No degraded or
  partial condition has been executed.
- **No W1 conditions material.** Rung composition, condition
  directories, and the W2 conflict variants are wave work, assembled
  from these kits under their own pre-registrations.
- **No harness changes.** `runner_child.py` untouched; the overlay
  mechanism generalizes the shipped c4 precedent driver-side.

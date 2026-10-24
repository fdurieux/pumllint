# Input quality and contribution assessment

Input commit: `88f656a39f47fe92a31e887e26888775658aa19b`. Every baseline score is preserved in `input-quality.json`. Final scores use 0–5 ordinal anchors; `—` means unverified/unassessed, not zero. No aggregate average is reported.

## Set assessment

The 221 supplied files contain 163 requirements, 130 tagged scenarios, and 257 collected cases. The independently recreated data behaviour passed all 246 non-chain cases. All 257 cases passed with explicitly substituted test-only shell externals; 11 independent checks also passed. The exact full integration gate remains blocked by the absent original externals.

| Dimension | Score | Reason |
|---|---|---|
| semantic_correctness | — | Independent domain truth not established; local arithmetic invariants passed. |
| completeness | 3 | Enough to recreate data behaviour; missing external scripts prevent the exact complete integration gate. |
| consistency | 3 | Recorded identifiers, counts, model domain and transport-shape mismatches require interpretation. |
| clarity | 4 | Detailed contracts provide numerical order, exact messages and validation order. |
| verifiability | 4 | 257 reproducible cases, recorded traffic and exact frames; live paths and external integration remain qualified. |

## Findings and resolutions

### F-001 — inconsistency (minor)

Source: `recreate_experiment/kit/README.md`

Requirements count says 162; requirements.json actually has 163.

Recorded resolution: Use the actual ID inventory, not the stale prose count.

Affected artefact completeness/consistency/clarity remains below 4; resolution is an implementation choice, not a repair to the supplied input.

### F-002 — missing (major)

Source: `recreate_experiment/handover/DONE.md`

Checks 4 and 5 require harness tools outside the permitted input set.

Recorded resolution: Do not consult them. Derive independent checks; do not claim those exact gates ran.

Affected artefact completeness/consistency/clarity remains below 4; resolution is an implementation choice, not a repair to the supplied input.

### F-003 — missing (major)

Source: `recreate_experiment/kit/contracts/chain.md`

events.sh and dashboard.sh are called given externals, but neither is supplied in kit or handover; conftest copies existing files instead of supplying stubs.

Recorded resolution: Keep production externals absent; run additional chain tests with explicitly labelled, independently written test doubles.

Affected artefact completeness/consistency/clarity remains below 4; resolution is an implementation choice, not a repair to the supplied input.

### F-004 — identifier_collision (minor)

Source: `recreate_experiment/kit/contracts/refusals.md`

X-10 names both absent differential and parser errors.

Recorded resolution: Identify findings by requirement ID and condition as well as refusal ID.

Affected artefact completeness/consistency/clarity remains below 4; resolution is an implementation choice, not a repair to the supplied input.

### F-005 — incomplete_domain (moderate)

Source: `recreate_experiment/kit/contracts/dmn/actions_gate.dmn`

Stamp domain includes none/before_today/today but omits future stamps; JDL-091 and real-clock injection allow future stamps.

Recorded resolution: Follow JDL-091: stamps on or after today are fresh. Treat DMN completeness as conditional on its restricted domain.

Affected artefact completeness/consistency/clarity remains below 4; resolution is an implementation choice, not a repair to the supplied input.

### F-006 — inconsistency (minor)

Source: `recreate_experiment/kit/CHANGES.md`

Closing-round section says three additions but lists more; JDL-163 and the wave-2 changes are absent.

Recorded resolution: Use pinned files rather than changelog as the complete inventory.

Affected artefact completeness/consistency/clarity remains below 4; resolution is an implementation choice, not a repair to the supplied input.

### F-007 — missing (moderate)

Source: `recreate_experiment/kit/contracts/universe.toml`

Packaged universe CSV paths refer to experiments files outside permitted inputs.

Recorded resolution: Ship the bytes as required; default full sync needs those external snapshots. Offline dry-run remains possible.

Affected artefact completeness/consistency/clarity remains below 4; resolution is an implementation choice, not a repair to the supplied input.

### F-008 — inconsistency (minor)

Source: `recreate_experiment/kit/uml/data_model.puml`

Transport request returns TransportResponse in the model, while prose and adapter describe (status, text).

Recorded resolution: Implement tuple transport per the explicit collector contract.

Affected artefact completeness/consistency/clarity remains below 4; resolution is an implementation choice, not a repair to the supplied input.

### F-009 — test_harness_limitation (moderate)

Source: `recreate_experiment/kit/features/steps/conftest.py`

The chain call logger writes arguments without escaping embedded newlines, then splits records by line. Valid multiline python -c arguments generate false call-list failures.

Recorded resolution: Use single-line escaped Python code arguments in daily.sh; leave supplied test code unchanged.

Affected artefact completeness/consistency/clarity remains below 4; resolution is an implementation choice, not a repair to the supplied input.

### F-010 — incorrect_example (minor)

Source: `recreate_experiment/kit/contracts/cli.md`

General JSON rules say non-ASCII is escaped, but display an unchanged section sign as the example. Python default JSON and the actual JSON examples use escaped Unicode.

Recorded resolution: Follow Python json defaults and the precise output contracts.

Affected artefact completeness/consistency/clarity remains below 4; resolution is an implementation choice, not a repair to the supplied input.

## Per-artefact final review

Columns: S semantic correctness; C completeness; A consistency/agreement; L clarity; V verifiability; U implementation usefulness. Confidence and dimension-specific evidence are in JSON. Each row is scoped to its file, not an estimate of causal quality improvement.

| Artefact | S / C / A / L / V / U | Comment and observed contribution |
|---|---|---|
| `recreate_experiment/kit/CHANGES.md` | — / 3 / 3 / 3 / 3 / — | Useful revision orientation, but does not comprehensively enumerate the latest wave-2 additions. Findings: F-006 |
| `recreate_experiment/kit/README.md` | — / 3 / 3 / 3 / 3 / — | Reading order and deliverables are directly usable; baseline instructions distinguish kit authority from navigation. Findings: F-001 |
| `recreate_experiment/kit/contracts/HARNESS_INTERFACE.md` | — / 4 / 4 / 4 / 4 / 5 | The adapter signatures allowed clock injection and replay without any copied prior implementation; adapter contains imports only. |
| `recreate_experiment/kit/contracts/adjustment.md` | 4 / 4 / 4 / 4 / 4 / 5 | Strict-before effective dates and explicit float operation order resolved implementation choices; independent fixed-point/effective-date checks support local arithmetic semantics. |
| `recreate_experiment/kit/contracts/chain.md` | — / 2 / 3 / 3 / 3 / 4 | Detailed stage arguments and error propagation enabled daily.sh; missing externals limit production integration and required test-only substitutes. Findings: F-003 |
| `recreate_experiment/kit/contracts/classifications.toml` | — / 4 / 4 / 4 / 4 / 4 | Packaged evidence shipped byte-identically. Historical vendor provenance was not independently reverified because external lookup is excluded. |
| `recreate_experiment/kit/contracts/classifications.toml.md` | — / 4 / 4 / 4 / 4 / 4 | Mapping separates agreement from evidence independence. Only the packaged valid input is currently needed; arbitrary invalid-file validation is not exposed. |
| `recreate_experiment/kit/contracts/cli.md` | — / 3 / 3 / 3 / 3 / 5 | Parser tables enabled a standalone parser with no runtime kit dependency; exact help and refusal scenarios exposed one generator spacing defect, corrected. Findings: F-010 |
| `recreate_experiment/kit/contracts/cli_help.md` | — / 4 / 4 / 4 / 4 / 4 | Verbatim oracle detected a spacing defect in generated status help; it contributes exact output validation rather than an independent behavioural source. |
| `recreate_experiment/kit/contracts/collectors.md` | — / 4 / 4 / 4 / 4 / 4 | Specified one retry policy for both live and replay traffic; independent tests exercised retries and rate limits without provider calls. |
| `recreate_experiment/kit/contracts/dmn/README.md` | — / 4 / 4 / 4 / 4 / — | Reading order and deliverables are directly usable; baseline instructions distinguish kit authority from navigation. |
| `recreate_experiment/kit/contracts/dmn/actions_gate.dmn` | 3 / 3 / 3 / 3 / 3 / 3 | Decision model: branch partitions were inspected and checked over the declared finite domains; completeness beyond those domains is not established. Findings: F-005 |
| `recreate_experiment/kit/contracts/dmn/basis.dmn` | 4 / 4 / 4 / 4 / 4 / 3 | Decision model: branch partitions were inspected and checked over the declared finite domains; completeness beyond those domains is not established. |
| `recreate_experiment/kit/contracts/dmn/command_store_state.dmn` | 4 / 4 / 4 / 4 / 4 / 3 | Decision model: branch partitions were inspected and checked over the declared finite domains; completeness beyond those domains is not established. |
| `recreate_experiment/kit/contracts/dmn/refusal_routing.dmn` | 4 / 4 / 4 / 4 / 4 / 3 | Decision model: branch partitions were inspected and checked over the declared finite domains; completeness beyond those domains is not established. |
| `recreate_experiment/kit/contracts/dmn/status_verdicts.dmn` | 4 / 4 / 4 / 4 / 4 / 3 | Decision model: branch partitions were inspected and checked over the declared finite domains; completeness beyond those domains is not established. |
| `recreate_experiment/kit/contracts/dmn/sync_window.dmn` | 4 / 4 / 4 / 4 / 4 / 3 | Decision model: branch partitions were inspected and checked over the declared finite domains; completeness beyond those domains is not established. |
| `recreate_experiment/kit/contracts/fixtures.md` | — / 4 / 4 / 4 / 4 / 4 | Request identity and replay ordering made offline collector validation possible; recorder secret checks were independently exercised. |
| `recreate_experiment/kit/contracts/glossary.md` | — / 4 / 4 / 4 / 4 / — | Supporting input inspected; contribution beyond navigation is not established. |
| `recreate_experiment/kit/contracts/leg.md` | — / 4 / 4 / 4 / 4 / 4 | Exact leg keys and ownership of clocks prevented clock injection from changing actions-file stamps. |
| `recreate_experiment/kit/contracts/pins.md` | — / 4 / 4 / 4 / 4 / 4 | Exact runtime pins installed successfully; CPython 3.12.14 used for specified traceback/help compatibility. Python 3.11 was not tested. |
| `recreate_experiment/kit/contracts/refusals.md` | — / 3 / 3 / 3 / 3 / 4 | Exact messages and wrapped/contained/traceback distinctions contributed direct CLI decisions; reused X-10 identifier weakens traceability. Findings: F-004 |
| `recreate_experiment/kit/contracts/seam_frame.md` | — / 4 / 4 / 4 / 4 / 4 | Volume dtype and unchanged-row rules prevented rounding/filtering at export; the suite compared the seam frames exactly. |
| `recreate_experiment/kit/contracts/status.example.json` | — / 4 / 4 / 4 / 4 / — | Supporting input inspected; contribution beyond navigation is not established. |
| `recreate_experiment/kit/contracts/status.schema.json` | — / 4 / 4 / 4 / 4 / — | Supporting input inspected; contribution beyond navigation is not established. |
| `recreate_experiment/kit/contracts/store.md` | — / 4 / 4 / 4 / 4 / 5 | The 21-column schema, write modes and lock discipline directly determined store.py; no-op, lock and invalid-date checks extend supplied examples. |
| `recreate_experiment/kit/contracts/sync_summary.example.json` | — / 4 / 4 / 4 / 4 / — | Supporting input inspected; contribution beyond navigation is not established. |
| `recreate_experiment/kit/contracts/sync_summary.schema.json` | — / 4 / 4 / 4 / 4 / — | Supporting input inspected; contribution beyond navigation is not established. |
| `recreate_experiment/kit/contracts/universe.toml` | — / 3 / 3 / 3 / 3 / 4 | Shipped byte-identically; its listing and nine-leg dry-run pass. Referenced external snapshot files are not supplied. Findings: F-007 |
| `recreate_experiment/kit/contracts/universe.toml.md` | — / 4 / 4 / 4 / 4 / 4 | Explicit validation order and exact refusals enabled deterministic parsing; invalid-universe scenarios check first-error behaviour. |
| `recreate_experiment/kit/features/README.md` | — / 4 / 4 / 4 / 4 / — | Reading order and deliverables are directly usable; baseline instructions distinguish kit authority from navigation. |
| `recreate_experiment/kit/features/actions.feature` | — / 4 / 4 / 4 / 4 / 4 | Executable scenarios provide observable assertions for the tagged requirements; passing them does not establish complete behavioural coverage. |
| `recreate_experiment/kit/features/adjustment.feature` | — / 4 / 4 / 4 / 4 / 4 | Executable scenarios provide observable assertions for the tagged requirements; passing them does not establish complete behavioural coverage. |
| `recreate_experiment/kit/features/chain.feature` | — / 4 / 4 / 4 / 4 / 4 | Executable scenarios provide observable assertions for the tagged requirements; passing them does not establish complete behavioural coverage. |
| `recreate_experiment/kit/features/cli.feature` | — / 4 / 4 / 4 / 4 / 4 | Executable scenarios provide observable assertions for the tagged requirements; passing them does not establish complete behavioural coverage. |
| `recreate_experiment/kit/features/collectors.feature` | — / 4 / 4 / 4 / 4 / 4 | Executable scenarios provide observable assertions for the tagged requirements; passing them does not establish complete behavioural coverage. |
| `recreate_experiment/kit/features/decisions.feature` | — / 4 / 4 / 4 / 4 / 4 | Executable scenarios provide observable assertions for the tagged requirements; passing them does not establish complete behavioural coverage. |
| `recreate_experiment/kit/features/differential.feature` | — / 4 / 4 / 4 / 4 / 4 | Executable scenarios provide observable assertions for the tagged requirements; passing them does not establish complete behavioural coverage. |
| `recreate_experiment/kit/features/fixtures/csv/bad_dates.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/crypto_feb.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/diff_b.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/flat_at.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/flat_over.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/future_crypto.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/future_stock.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/gap_stock.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/invalid_mix.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/invalid_values.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/jumps.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/mid_a.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/mid_b.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/missing_cols.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/new_a.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/no_dates.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/old_b.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/res_at.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/res_coarse.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/stock_feb.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/yahoo_shrunk.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/yahoo_small.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/zero_close_jump.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/zero_runs.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/csv/zero_single.csv` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/expected/ccstk_stored.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/expected/divy_export.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/expected/divy_stored.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/expected/late_stored.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/expected/pair_binance_stored.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/expected/pair_eodhd_stored.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/expected/small_export.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/expected/small_stored.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/expected/splt_run1_export.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/expected/splt_run1_stored.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/expected/splt_run2_stored.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/expected/weird_stored.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/expected/zero_stored.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/binance/limit/api_v3_klines_20c2e2b351.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/binance/pages/api_v3_klines_a2add2b3cc.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/binance/pages/api_v3_klines_c85b40df3f.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/binance_notlist/api_v3_klines_20c2e2b351.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/divy/run1/api_div_DIVY.US_3b636683f2.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/divy/run1/api_eod_DIVY.US_397b96f4f8.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/divy/run1/api_splits_DIVY.US_30b2414150.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/mixed/api_div_DIVY.US_3b636683f2.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/mixed/api_div_SPLT.US_dfa1bc38b1.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/mixed/api_eod_DIVY.US_397b96f4f8.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/mixed/api_eod_SPLT.US_34fa88fe69.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/mixed/api_splits_DIVY.US_30b2414150.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/mixed/api_splits_SPLT.US_42fc61fa7b.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/ns/api_div_CCSTK-USD.CC_898cb1c92c.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/ns/api_eod_CCSTK-USD.CC_59464f1e92.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/ns/api_eod_WEIRD.XX_8062ad67dc.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/ns/api_splits_CCSTK-USD.CC_622be4b8da.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/pair/above/api_eod_PAIR-USD.CC_aabf940923.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/pair/above/api_v3_klines_8fd156c7a6.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/pair/at/api_eod_PAIR-USD.CC_aabf940923.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/pair/at/api_v3_klines_8fd156c7a6.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/res/api_div_RES.US_5d09d73f67.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/res/api_eod_RES.US_f0132fdaa2.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/res/api_splits_RES.US_eac86de7f1.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/badsplit/api_div_SPLT.US_dfa1bc38b1.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/badsplit/api_eod_SPLT.US_34fa88fe69.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/badsplit/api_splits_SPLT.US_42fc61fa7b.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/both_fail/api_div_SPLT.US_dfa1bc38b1.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/both_fail/api_eod_SPLT.US_34fa88fe69.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/both_fail/api_splits_SPLT.US_42fc61fa7b.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/endcap/api_div_SPLT.US_dfa1bc38b1.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/endcap/api_eod_SPLT.US_fd9c388199.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/endcap/api_splits_SPLT.US_42fc61fa7b.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/eod404/api_div_SPLT.US_dfa1bc38b1.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/eod404/api_eod_SPLT.US_34fa88fe69.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/eod404/api_splits_SPLT.US_42fc61fa7b.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/late1/api_div_SPLT.US_dfa1bc38b1.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/late1/api_eod_SPLT.US_34fa88fe69.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/late1/api_splits_SPLT.US_42fc61fa7b.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/late2/api_div_SPLT.US_dfa1bc38b1.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/late2/api_eod_SPLT.US_54d3d07691.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/late2/api_splits_SPLT.US_42fc61fa7b.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/many/api_eod_SPLT.US_54d3d07691.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/notlist/api_div_SPLT.US_dfa1bc38b1.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/notlist/api_eod_SPLT.US_34fa88fe69.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/notlist/api_splits_SPLT.US_42fc61fa7b.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/replay/api_eod_SPLT.US_34fa88fe69.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/replay/manifest.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/replay/nested/api_div_SPLT.US_dfa1bc38b1.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/replay/renamed_on_purpose.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/run1/api_div_SPLT.US_dfa1bc38b1.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/run1/api_eod_SPLT.US_34fa88fe69.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/run1/api_splits_SPLT.US_42fc61fa7b.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/run2/api_div_SPLT.US_dfa1bc38b1.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/run2/api_eod_SPLT.US_34fa88fe69.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/run2/api_eod_SPLT.US_54d3d07691.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/run2/api_splits_SPLT.US_42fc61fa7b.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/splits503/api_div_SPLT.US_dfa1bc38b1.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/splits503/api_eod_SPLT.US_34fa88fe69.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/splits503/api_splits_SPLT.US_42fc61fa7b.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/wide/api_eod_SPLT.US_54d3d07691.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/zerosplit/api_div_SPLT.US_dfa1bc38b1.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/zerosplit/api_eod_SPLT.US_34fa88fe69.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/splt/zerosplit/api_splits_SPLT.US_42fc61fa7b.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/zero/endcap/api_eod_ZERO-USD.CC_db8c39bcce.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/http/zero/run1/api_eod_ZERO-USD.CC_782a3d5fa7.json` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/all_off.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/asset_class_bad.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/asset_class_missing.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/asset_key.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/asset_name.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/asset_table.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/bad_date.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/bare_ticker.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/collector_path.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/csv_path.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/csv_window.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/defaults_key.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/defaults_store.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/defaults_table.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/dupe_coord.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/dupe_name.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/enabled.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/first_wins.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/inverted.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/kind.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/modeled_disabled.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/modeled_type.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/no_assets.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/no_source.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/none_modeled.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/provider_bad.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/source_key.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/source_table.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/threshold.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/toml_syntax.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/top_key.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/bad/two_modeled.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/binance.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/classes.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/csv_leg.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/divy.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/mixed.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/ns.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/pair.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/paused.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/plan.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/splt.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/splt_end.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/zero.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/fixtures/universes/zero_end.toml` | — / — / — / — / 4 / — | Offline replay or expected-data input: supports concrete example validation; synthetic expected values are not an independent market-truth source. |
| `recreate_experiment/kit/features/seam.feature` | — / 4 / 4 / 4 / 4 / 4 | Executable scenarios provide observable assertions for the tagged requirements; passing them does not establish complete behavioural coverage. |
| `recreate_experiment/kit/features/status.feature` | — / 4 / 4 / 4 / 4 / 4 | Executable scenarios provide observable assertions for the tagged requirements; passing them does not establish complete behavioural coverage. |
| `recreate_experiment/kit/features/steps/conftest.py` | — / 3 / 3 / 3 / 3 / 4 | Adapter-driven numerical comparisons, log assertions and stubbed commands provided concrete checks; chain externals are not actually supplied and multiline argument logging is lossy. Findings: F-009 |
| `recreate_experiment/kit/features/steps/test_features.py` | — / 4 / 4 / 4 / 4 / 4 | Collected all 257 supplied acceptance cases unchanged. |
| `recreate_experiment/kit/features/store.feature` | — / 4 / 4 / 4 / 4 / 4 | Executable scenarios provide observable assertions for the tagged requirements; passing them does not establish complete behavioural coverage. |
| `recreate_experiment/kit/features/sync.feature` | — / 4 / 4 / 4 / 4 / 4 | Executable scenarios provide observable assertions for the tagged requirements; passing them does not establish complete behavioural coverage. |
| `recreate_experiment/kit/features/universe.feature` | — / 4 / 4 / 4 / 4 / 4 | Executable scenarios provide observable assertions for the tagged requirements; passing them does not establish complete behavioural coverage. |
| `recreate_experiment/kit/pumllint.toml` | — / 4 / 4 / 4 / 4 / — | Configures optional diagram linting only; not used to implement runtime behaviour or claim diagram quality gates. |
| `recreate_experiment/kit/requirements.json` | — / 4 / 4 / 4 / 4 / 4 | 163 unique IDs supplied numerical constants and branch conditions; static trace links each ID to implementation and tagged scenarios. |
| `recreate_experiment/kit/uml/basis_and_adjustment.puml` | — / 4 / 4 / 4 / 4 / — | Diagram: used for structural orientation with primary contracts; no independent semantic truth or causal contribution is inferred. |
| `recreate_experiment/kit/uml/component.puml` | — / 4 / 4 / 4 / 4 / — | Diagram: used for structural orientation with primary contracts; no independent semantic truth or causal contribution is inferred. |
| `recreate_experiment/kit/uml/daily_chain.puml` | — / 4 / 4 / 4 / 4 / — | Diagram: used for structural orientation with primary contracts; no independent semantic truth or causal contribution is inferred. |
| `recreate_experiment/kit/uml/data_model.puml` | — / 3 / 3 / 3 / 3 / — | Diagram: used for structural orientation with primary contracts; no independent semantic truth or causal contribution is inferred. Findings: F-008 |
| `recreate_experiment/kit/uml/series_state.puml` | — / 4 / 4 / 4 / 4 / — | Diagram: used for structural orientation with primary contracts; no independent semantic truth or causal contribution is inferred. |
| `recreate_experiment/kit/uml/status_run.puml` | — / 4 / 4 / 4 / 4 / — | Diagram: used for structural orientation with primary contracts; no independent semantic truth or causal contribution is inferred. |
| `recreate_experiment/kit/uml/sync_leg.puml` | — / 4 / 4 / 4 / 4 / — | Diagram: used for structural orientation with primary contracts; no independent semantic truth or causal contribution is inferred. |
| `recreate_experiment/kit/uml/sync_run.puml` | — / 4 / 4 / 4 / 4 / — | Diagram: used for structural orientation with primary contracts; no independent semantic truth or causal contribution is inferred. |
| `recreate_experiment/handover/AGENTS.md` | — / 4 / 4 / 4 / 4 / 4 | Established independence and allowed inputs before coding. Its no-network instruction is applied to behavioural research, with administrative transport and pinned dependency retrieval recorded. |
| `recreate_experiment/handover/ARCHITECTURE.md` | — / 4 / 4 / 4 / 4 / 4 | Provided module and operation sequencing orientation. Behavioural decisions were checked against detailed contracts. |
| `recreate_experiment/handover/DECISIONS.md` | — / — / — / 3 / 3 / 4 | Readable DMN view served as a branch checklist. It shares source information with DMN and is not separately counted as semantic coverage. |
| `recreate_experiment/handover/DONE.md` | — / 2 / 3 / 3 / 3 / — | Separates gate from optional checks and documents uncovered live paths; some required supporting files are excluded/missing, so its full gate is not claimed. Findings: F-002 |
| `recreate_experiment/handover/KNOWN-QUIRKS.md` | — / 4 / 4 / 4 / 4 / 5 | Prevented changing timestamp seconds, actions clock and absent-series tracebacks that would have violated the intended recreation. |
| `recreate_experiment/handover/README.md` | — / 4 / 4 / 4 / 4 / — | Reading order and deliverables are directly usable; baseline instructions distinguish kit authority from navigation. |
| `recreate_experiment/handover/REQUIREMENTS.md` | — / — / — / 3 / 3 / — | Navigable generated requirement view; primary JSON remains authoritative. No independent information gain is claimed. |
| `recreate_experiment/handover/TRACE.md` | — / — / — / 3 / 3 / — | Generated joins aided navigation. Independent requirement-trace.json was generated from the supplied tags; no prior experiment evidence was used. |
| `recreate_experiment/handover/build.py` | — / 4 / 4 / 4 / 4 / — | Read as a generated-view provenance aid; not executed because it depends on pumllint outside the allowed recreation input/environment. |
| `recreate_experiment/handover/diagrams/basis_and_adjustment.svg` | — / — / — / 3 / 3 / — | Supporting input inspected; contribution beyond navigation is not established. |
| `recreate_experiment/handover/diagrams/component.svg` | — / — / — / 3 / 3 / — | Supporting input inspected; contribution beyond navigation is not established. |
| `recreate_experiment/handover/diagrams/daily_chain.svg` | — / — / — / 3 / 3 / — | Supporting input inspected; contribution beyond navigation is not established. |
| `recreate_experiment/handover/diagrams/data_model.svg` | — / — / — / 3 / 3 / — | Supporting input inspected; contribution beyond navigation is not established. |
| `recreate_experiment/handover/diagrams/series_state.svg` | — / — / — / 3 / 3 / — | Supporting input inspected; contribution beyond navigation is not established. |
| `recreate_experiment/handover/diagrams/status_run.svg` | — / — / — / 3 / 3 / — | Supporting input inspected; contribution beyond navigation is not established. |
| `recreate_experiment/handover/diagrams/sync_leg.svg` | — / — / — / 3 / 3 / — | Supporting input inspected; contribution beyond navigation is not established. |
| `recreate_experiment/handover/diagrams/sync_run.svg` | — / — / — / 3 / 3 / — | Supporting input inspected; contribution beyond navigation is not established. |

## Evidence and limits

`requirement-trace.json` links all declared IDs to implementation files and scenario declarations. These are static trace links, not measured line or branch coverage. Tests can share assumptions with contracts and synthetic fixtures. Individual fixture and generated-view contributions were not causally isolated; unsupported scores remain unassigned.

- No prior implementation, hidden tests or experiment outcomes consulted.
- No live provider or real AWS integration was run.
- Missing original externals were never reconstructed as production files.
- Excluded optional harness gates were not executed.
- No SVG visual QA, full handover regeneration, code-coverage instrumentation, or controlled contribution ablation.
- Per-file unknowns remain null; no composite average score.

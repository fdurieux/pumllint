# The plant

Each degraded kit is the pristine kit (`../kit/`, 207 files) with the edits of `scripts/<arm>.json` applied by
`scripts/edit.py` (every edit an exact replacement that must match its stated count), then `tools/manifest.py`.
`patches/<arm>.patch` is the diff against the pristine kit. Never edited in any arm: `README.md`,
`features/README.md`, `pumllint.toml`, `tools/`, `contracts/externals/`, `contracts/HARNESS_INTERFACE.md`.

## Plant conventions (each fixes a case the frozen text did not foresee)

- **P1, every statement.** A W replaces, and an A rewords, every statement of the candidate in the arm's
  layers, in the candidate's role; an M deletes every statement of the clause. A statement may be data
  written in the value (an example epoch, an expected cell, a recorded request), and those are recomputed
  in the planted world. A statement whose scope covers the planted role and others keeps the others in
  the fewest words (adjustment.md's "All arithmetic is IEEE-754 binary64" gains "except the price
  division of §4, which is binary32").
- **P2, help text stays.** The help strings are pinned program output: JDL-160 pins them verbatim in
  cli.md's parser tables, and the suite reads `contracts/cli_help.md` as its oracle for `--help`. A
  plant leaves both as committed: editing cli_help.md fails V2 (D2) or V5 (D5, whose mutants keep the
  original help), and editing cli.md alone plants a contradiction no other defect carries. Where a layer
  states a candidate only in help text, the layer keeps it and this log says so.
- **P3, the externals' own mentions stay.** `contracts/externals/` is never edited, so a value the
  externals read keeps its committed spelling wherever the kit describes the externals (chain.md's
  `jef_publish_dashboard` row; chain.feature's restored-store steps and the WARN line, which
  `dashboard.sh` prints).
- **P4, an M neither requires nor forbids.** A scenario or Examples row exercising only the deleted
  clause goes, with any fixture used only by it. A kept scenario that states the clause's outcome
  incidentally drops that outcome and asserts the rest as a subsequence, through two generic steps
  added to the glue (`report {n} has notes including:`, `stdout contains the lines:`), so the scenario
  passes with or without the clause. V5 requires this of D5; D4's M is held to the same standard.
- **P5, plumbing.** D3's glue learns the dtype `int32` (`_expected_frame`, `_compare_frames`), without
  which the planted dtype would be compared as text.

## Per arm

### D1 (L5 only)

- W JDL-095: sync_leg.puml "detail says end predates the stored tail" -> "precedes".
- M JDL-134: sync_run.puml loses the arrow `SyncCommand --> Operator : "sync: {message}" on stderr, exit 1`
  (the command's handling of the wrapped refusal; the loader's UniverseError arrow, JDL-016's, stays).
- A JDL-049: series_state.puml "whole series re-derived from raw" -> "whole series re-derived";
  basis_and_adjustment.puml "divide open, high, low and close raw by F" -> "divide open, high, low and
  close by F" and "multiply volume_raw by F into volume" -> "multiply volume by F" (P1: the two activity
  steps state the same read-only-raw condition).

### D2 (L2, L3, L4)

- W JDL-060 (UTC as the bar date's zone -> America/New_York): JDL-060 (zone, the date-only rule and its
  example epoch 1704153600 -> 1704171600); store.md's timestamp and datetime rows, the timestamp note's
  example, the time-of-day example (10:30 -> `timestamp` 1704209400); seam_frame.md's worked row
  (timestamp 1704171600, datetime 2024-01-02 05:00:00+00:00). The zone's other roles (the run clock, the
  export Date, the year partition, stamps) keep UTC.
- M JDL-102 (construct a collector only when a non-dry-run leg first needs that provider): deleted from
  JDL-102 with its rationale ("a CSV-only or --dry-run invocation demands no key"), from JDL-104's
  restatement ("construct no collector"), and from the glossary's dry run ("no collector"). L3 states it
  only in the `--dry-run` help ("no network, no key needed"), which stays (P2). **Repair after V2:** a
  first plant also edited that help string in cli.md and cli_help.md; V2 failed (2 help scenarios), and
  both files were restored.
- A JDL-073 ("every stored row, zero-volume and NaN rows included", "no load policy of its own"):
  JDL-073 -> "The export shall pass every usable stored row through.", its rationale -> "the seam owns
  the load policy"; JDL-071 "one row per stored row" -> "one row per usable stored row"; JDL-074 "this
  program implements that policy nowhere except where status emulates" -> "this program applies that
  policy where it needs usable rows, as status does for"; seam_frame.md §1 ("exactly the stored rows ...
  Nothing is dropped, filtered, re-sorted or de-duplicated" -> "the usable stored rows ... Nothing is
  re-sorted or de-duplicated") and §5 ("does **not** apply this policy anywhere in the export" -> "applies
  this policy where it needs usable rows").

### D3 (every layer)

- W1 JDL-057 `market_data` -> `marketdata`: requirements (JDL-057, the load and import-csv messages),
  component.puml, cli.feature, decisions.feature, store.feature (layout listings, import message),
  cli.md, store.md, glossary. Kept (P3): chain.md's `jef_publish_dashboard`, chain.feature's
  restored-store steps and WARN line, the glue step that creates `data/market_data` for `dashboard.sh`.
- W2 JDL-047 float64 -> float32 price division: JDL-047; adjustment.md (the arithmetic sentence, P1;
  example 1's closes; example 2's "mains = raws" -> "mains = raws rounded to float32"); seam_frame.md
  §3's mains, seam row and the F = 1.0 row; JDL-075's and seam_frame.md's shortest-repr example
  (19.84952380952381 -> 19.849523544311523). L1 data regenerated from the combined mutant: seven expected
  frames (divy_export, divy_stored, late_stored, splt_run1_export, splt_run1_stored, splt_run2_stored;
  pair_eodhd_stored is split_adjusted and unchanged), five stored-cell rows, two export CSV prefixes. The
  regeneration ran an instrumented copy of the suite (`regen/`) that dumped each compared frame and
  cell; the formatter reproduces all 13 pristine expected files byte for byte, and recomputing the
  mains from the raw columns with the mutant's formula reproduces every regenerated frame.
- W3 JDL-072 int64 -> int32 (integral export Volume): JDL-072, JDL-075; seam_frame.md (dtype table,
  rule, closing sentence); basis_and_adjustment.puml; seam.feature (title, dtype row); divy_export and
  small_export dtypes; P5. `timestamp`'s int64 (JDL-059) is another role and stays.

### D4 (L1 only)

- W JDL-099 "row(s) imported" -> "row(s) loaded": decisions.feature (2), sync.feature, collectors.feature (2).
- M JDL-118 (the zero-volume NOTE): the outline "Zero-volume rows are noted ..." goes whole, with
  zero_single.csv and zero_runs.csv (its second row, the run extension of JDL-118's second clause and
  JDL-119, extends the deleted NOTE and cannot be asserted without it); the post-seam gap outline and the
  status table drop the NOTE line and assert the rest as a subsequence (P4).
- A JDL-003 ("accept only the keys"): the rows `asset_key` and `first_wins`, whose messages state the
  restriction, leave the exact-message outline for an outline asserting `stderr contains "universe:
  asset"`, which both readings pass (the other reading reports the next violation instead).

### D5 (every layer)

- M1 JDL-094 (for a declared-crypto leg, the end-guard `today - 1 day`): deleted from JDL-094 (the
  statement now: the fetch end is the universe `end`, open without one) and its rationale; from JDL-088
  ("the crypto end-guard"), JDL-100 ("whether it is end-guarded follows JDL-094"), JDL-086's rationale;
  leg.md; cli.md's dry-run example (the two crypto plans lose " to 2026-10-22"); the comments of the
  packaged universe.toml and classifications.toml; the glossary (the end-guard entry, "today", "window",
  "declared asset_type"); sync_window.dmn's rules fetch_end_r1 and fetch_end_r2 (the decision's input and
  output domains stay as written, so `today_minus_1` remains a declared output value); sync_leg.puml's
  window note. The sync help text keeps "crypto end-guarded at the previous UTC day" (P2). In L1 the
  fetch-end outline loses its rows r1 and r2 and is retitled; three titles lose the guard; the scenario
  "An empty series sends its request" now uses zero_end.toml (with zero.toml's new end it would pass the
  mutant's request); and, so that guard and no guard send the same recorded requests (P4), each crypto
  source the suite syncs declares the end its scenario's clock implies: zero.toml 2024-02-09, pair.toml
  2024-01-20 (both sources), plan.toml's PAIR 2024-02-29, ns.toml's WEIRD 2024-05-10 (its legs listing
  follows), binance.toml's LIM 2024-06-30, and the new pgs.toml's PGS 2024-01-15. **A possible hint, stated:**
  every such end is the day before its scenario's clock.
- M2 JDL-136 (` [disabled]` for a disabled asset): deleted from JDL-136 and universe.toml.md §6; the listing
  scenario drops the paused asset's header line and asserts the rest as a subsequence (P4), retitled.
- M3 JDL-084 (keep only the assets the asset filter names): deleted from JDL-084, leg.md, cli.md's sync
  section ("`--provider` a repeatable filter, `--asset` repeatable"), sync_run.puml's selection note
  ("filtered by provider"). The `--asset` help text stays (P2); JDL-085's refusal of an unknown asset name
  is another requirement's clause and stays. In L1: the filter scenario keeps its provider filter only
  (seven legs, retitled); the selection-refusal row `sync --asset GONE` is re-routed to `sync --provider
  binance` (same refusal, reached without the asset filter); the three Binance scenarios drop
  `assets=...`, binance.toml keeps LIM only and PGS moves to a new pgs.toml.

## Consistency checks (V), on the final kits

| check | result |
|---|---|
| V1 | pass: files changed outside MANIFEST.sha256 - D1 4 (L5); D2 4 (L2, L3 x2, L4); D3 21 (all five layers); D4 8 (L1; two of them the removed fixtures); D5 22 (all five layers; one of them the added pgs.toml); no never-edited file touched |
| V2 | pass: D1 and D2 `features/` byte-identical to the pristine kit; both suites 258/258 on the original (after the D2 repair above) |
| V3 | pass: D3's suite 258/258 on the combined mutant (D3-all), 241/258 on the original |
| V4 | pass: D4's suite 256/256 on its W mutant, 252/256 on the original (the four failures are the W's); the A outline passes on the original and on A-003 (only the W's four fail on each) |
| V5 | pass: D5's suite 256/256 on the original and 256/256 on the combined absence mutant (D5-all) |
| (D4-M, the V5 standard) | D4's suite on M-118 fails only the W's four |

## Gate readouts (G), before any rebuild

| kit | G1 lint | G2 score | G3 trace | G4 dmn_check | G5 glossary_check | G6 calibration |
|---|---|---|---|---|---|---|
| pristine | green | green (L5, 100/100) | green (163/163 covered, 163/163 verified) | green | green | 258/258 |
| D1 | green | green | green | green | green | 258/258 |
| D2 | green | green | green | green | green | 258/258 |
| D3 | green | green | green | green | green | **241/258** |
| D4 | green | green | **red**: JDL-118 and JDL-119 unverified (the deleted outline was their only scenario) | green | green | **252/256** |
| D5 | green | green | green | **red**: fetch_end has 2 gaps (declared_crypto = true, either universe_end_declared) | green | 256/256 |

The frozen M definition said an M plant leaves the trace gate untouched because no id is removed. D4
refutes that: deleting a requirement's only scenario leaves it unverified.

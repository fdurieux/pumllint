# The selection walk

Order: requirement ids by `sha256("20261028:" + id)`, hex ascending (`tools/order.py`).
Slots in the frozen order D1-W, D1-M, D1-A, D2-W, D2-M, D2-A, D3-W1..3, D4-W, D4-M, D4-A, D5-M1..3.
Each slot walks from rank 1, skipping requirements already accepted.

## Conventions adopted during the walk (none changes a test; each fixes an ambiguity the frozen text left)

- **C1, the baseline.** A mutant's observing set is what differs from an unmutated copy run the
  same way (`null`, or `nullc` when the mutant carries its own chain), with the mutant's root path
  normalised to `<mut>` in every artefact. Measured against the reference instead, every mutant
  "differs" on the three traceback artefacts, whose source paths name the copy.
- **C2, line counts.** A mutant keeps every file's line count (deleted lines become blank or `pass`),
  so a traceback's line numbers cannot move. Two early mutants deleted lines (D1M-150, D1M-139);
  both were rebuilt line-preserving and re-observed, and the verdicts below are the rebuilt ones.
- **C3, which value or clause.** When a requirement pins several values (W, A) or has several
  conditional clauses (M), the candidate is the first in statement order that passes T1 and T2;
  T3 is tested on that one only, and a T3 failure rejects the requirement for the slot.
- **C4, what a value is (W, A).** In statement order: numbers; exit codes; string literals the
  program emits, writes or compares (message text, keys, flag names, file and directory names,
  formats); flag defaults; members of a declared vocabulary (basis names, dtypes, units, time zones,
  signal names, first/last). Not values: operators and procedural words; absence representations
  (an empty list, null, "none"); a name the statement only refers to because another requirement
  pins it (JDL-047's price columns are JDL-059's; a subcommand's name is JDL-133's; JDL-037's
  `startTime` is JDL-036's). A value whose only alternative of its type is pinned by the same
  statement has no admissible W (JDL-093's "oldest": "newest" is in the same sentence).
- **C5, T2 in role.** T2 greps the layer and keeps a hit only where the layer states the value or
  clause in this requirement's role: the literal where the program uses it, or, for a unit, a
  format or a time of day, data written in it (fixture request parameters, expected cells). The
  same text in another role does not count (JDL-037's "00:00" in datetime cells; `ctx.tmp` in the
  step glue). The D1 rows above already read T2 this way. Where a purely textual T2 would pick a
  different candidate, the verdict is the same: the one such case that needed a mutant, JDL-037's
  time of day (01:00 instead of 00:00, `D3-037t`), is observed outside the K2 set as well.
- **C6, what a clause is (M).** A clause has a condition and an outcome: explicit ("when", "if",
  "while", "unless", "except", "only when", "for a leg whose ...") or a default ("X defaults to Y":
  when X is absent, Y). An inventory or a restriction whose refusal the statement does not state
  ("offer exactly ...", "accept only the keys ...", "required") is not a clause; the refusal, where
  stated, is its own requirement's clause (so JDL-133's subcommand list was never a candidate). A
  compound outcome under one condition splits into one clause per outcome, in statement order (as
  JDL-058's write-tmp-and-rename was taken alone). T1 also asks that the clause's absence be one
  definable behaviour. Written down before any D4-M or D5 mutant was observed.
- **C7, which A candidate (A).** A's candidates are the values (C4) and the qualifiers, in statement
  order. A qualifier is wording that narrows a condition or a scope ("only", "every ... included",
  "never from ...", "from raw", "the oldest of", "strict", "exact", "with the 21 columns"); loosening
  it, by dropping or generalising it, gives the second reading. A condition with no qualifier
  ("without arguments", "while the series has no stored row", "when the file is absent") has no
  natural second reading and fails T1 for A. For a value, the looser wording names its role
  instead of the value ("a termination signal"), and the alternative reading is a concrete other
  value, as for W but without W's collision rule. It matches the D1-A rows. It was written down
  during D4-A, after A-053, A-093 and A-003 had been observed, so its effect is stated: it decides
  four candidates (JDL-150, -044, -063, -093), and with the bare condition as the candidate instead
  the first three are rejected on mutants already run (D1M-150, M-044, M-063 read the condition
  away); for JDL-093 no second reading of "no stored row" was found that any harness input reaches.
  The D4-A selection is the same either way.
- **Revisions.** Three D2/D3 rejections were first reasoned on other grounds and re-derived under
  C4/C5 with fresh mutants: JDL-139 (first mutant renamed the subcommand, `D2W-139`; C4 makes the
  flag `--symbol` the first value, `D2W-139b`), JDL-156 (the stage renamed in STAGE only,
  `D1A-156b`, for D1; the consistent rename in STAGE, `jef_emit` and `jef_put`, `D2W-156`, for D2
  and D3) and JDL-035 (first rejected at T1; re-derived as a T2 failure, with the consistent rename
  `D3-035` unobserved). Every verdict held.

## Walk

| slot | rank | id | T1 | T2 | T3 | T4 | verdict | note |
|---|---|---|---|---|---|---|---|---|
| D1-W | 1 | JDL-095 | pass | pass | pass | pass | **accepted** | W on the detail literal "predates the stored tail" (sync_leg.puml: "detail says end predates the stored tail"); mutant "precedes"; observing s09 sync_out, s09 sync_summary; pristine suite 2 failed |
| D1-M | 2 | JDL-073 | fail | | | | rejected | no conditional clause: one rule (every row passes, no load policy) |
| D1-M | 3 | JDL-133 | fail | | | | rejected | the conditional clause bundles five argparse behaviours; its absence is the parser library's, not one definable behaviour (and JDL-161 restates it) |
| D1-M | 4 | JDL-150 | pass | pass | fail | | rejected | clause "without arguments, re-exec through timeout" (daily_chain.puml timeout group); absence mutant line-preserving: observing set empty (the harness does not stub timeout) |
| D1-M | 5 | JDL-156 | pass | fail | | | rejected | clause "exit with rc when non-zero": not drawn in daily_chain.puml for the status stage |
| D1-M | 6 | JDL-139 | pass | pass | fail | | rejected | first conditional clause: split_adjusted or empty series refused (series_state.puml Refused); absence mutant: observing s23 cli_adjust_crypto_refused only, outside the K2 set |
| D1-M | 7 | JDL-049 | fail | | | | rejected | one rule (read only *_raw) with its consequences; no separable condition-outcome clause |
| D1-M | 8 | JDL-026 | pass | pass | fail | | rejected | first clause "except files named manifest.json" (component.puml "reads every *.json except manifest.json"); absence mutant: observing set empty (no manifest.json among the hidden inputs) |
| D1-M | 9 | JDL-134 | pass | pass | pass | pass | **accepted** | first clause "a refusal the command wraps prints {command}: {message}, exit 1" (sync_run.puml: "sync: {message}" on stderr, exit 1); absence: the wrapped refusals propagate as tracebacks; observing 16 s21 refusal artefacts; pristine suite 46 failed |
| D1-A | 2 | JDL-073 | pass | fail | | | rejected | the "every row, zero-volume and NaN included" condition is drawn in no diagram |
| D1-A | 3 | JDL-133 | fail | | | | rejected | the drawn values are a subcommand list and a count; no rewording keeps the original as one reading and gives a concrete second one |
| D1-A | 4 | JDL-150 | pass | pass | fail | | rejected | first value TERM (daily_chain.puml "sends TERM"); alt-reading mutant INT: observing set empty; a kill-after 60 to 30 mutant also empty (timeout is not stubbed by the harness) |
| D1-A | 5 | JDL-156 | pass | pass | fail | | rejected | first value the stage name (drawn stage_status); mutant STAGE=health: observing set empty; a mutant dropping --json changes chain call logs outside the K2 set |
| D1-A | 6 | JDL-139 | pass | fail | | | rejected | the adjust message literal is drawn in no diagram |
| D1-A | 7 | JDL-049 | pass | pass | pass | pass | **accepted** | the precise condition "read only the *_raw columns" (series_state.puml "whole series re-derived from raw"); A rewords to "whole series re-derived", admitting re-derivation from the current main columns; mutant reads the mains: observing s10 export_eodhd_AAPL.US, s10 stored_eodhd_AAPL.US; pristine suite 13 failed |
| D2-W | 2 | JDL-073 | fail | | | | rejected | pins no value: one rule (every row passes, no load policy) |
| D2-W | 3 | JDL-133 | pass | pass | fail | | rejected | first value the executable name `jef-data` (cli.md); mutant `jefdata` in the program strings and the chain's calls (D2W-133): observing 22, 5 outside the K2 set (s24 chain logs) |
| D2-W | 4 | JDL-150 | pass | pass | fail | | rejected | first value TERM (chain.md hard cap); mutant INT (D1A-150b): observing set empty |
| D2-W | 5 | JDL-156 | pass | pass | fail | | rejected | first value the stage name `status` (chain.md stage table); mutant `health` in STAGE, `jef_emit` and `jef_put` (D2W-156): observing 5, 4 outside (s24 chain logs) |
| D2-W | 6 | JDL-139 | pass | pass | fail | | rejected | first value adjust's flag `--symbol` (cli.md; C4); mutant `--ticker` (D2W-139b): observing 3, 1 outside (s23 cli_adjust_crypto_refused) |
| D2-W | 8 | JDL-026 | pass | pass | fail | | rejected | first value the glob `*.json` (fixtures.md); mutant `*.fixture` (D2W-026): observing 89, 2 outside |
| D2-W | 10 | JDL-060 | pass | pass | pass | pass | **accepted** | the bar's `date` field is not JDL-060's (C4); first value UTC, the zone the bar date is parsed in (store.md, seam_frame.md); W America/New_York (parsed there, converted to UTC); observing 13 stored frames; pristine suite 14 failed |
| D2-M | 2 | JDL-073 | fail | | | | rejected | no conditional clause (as D1-M) |
| D2-M | 3 | JDL-133 | fail | | | | rejected | as D1-M |
| D2-M | 4 | JDL-150 | pass | pass | fail | | rejected | clause "without arguments, re-exec through timeout" (chain.md hard cap); absence mutant D1M-150: observing set empty |
| D2-M | 5 | JDL-156 | pass | pass | fail | | rejected | clause "exit with rc when non-zero" (chain.md exit table); absence mutant, the status gate deleted (D2M-156): observing s24 chain_status_red only, outside the K2 set |
| D2-M | 6 | JDL-139 | pass | pass | fail | | rejected | first clause: a split_adjusted or empty series is refused (cli.md); absence mutant D1M-139: s23 cli_adjust_crypto_refused only, outside |
| D2-M | 8 | JDL-026 | pass | pass | fail | | rejected | clause "except files named manifest.json" (fixtures.md); absence mutant D1M-026: observing set empty |
| D2-M | 11 | JDL-067 | fail | | | | rejected | no conditional clause: one report shape |
| D2-M | 12 | JDL-058 | pass | pass | fail | | rejected | first clause "when a year file is written, write data.parquet.tmp and rename it over" (store.md); absence mutant writes in place (D2M-058): observing set empty |
| D2-M | 13 | JDL-102 | pass | pass | pass | pass | **accepted** | first clause "construct a collector only when a non-dry-run leg first needs that provider" (L3 in role: cli.md's `--dry-run` help, "no network, no key needed"; L4: the glossary's dry run, "no collector"); absence: both collectors constructed before the dry-run branch (no EODHD key in the environment, so that construction fails); observing 5 (s19 legs_packaged, sync_out, sync_summary; s22 cli_dry_run_packaged, cli_dry_run_r1); pristine suite 18 failed; disjoint from D2-W |
| D2-A | 2 | JDL-073 | pass | pass | pass | pass | **accepted** | precise condition "every stored row, zero-volume and NaN rows included" (seam_frame.md); A rewords it so that it also reads "every usable row"; alternative-reading mutant drops zero-volume and NaN rows at export; observing 6 export artefacts (s01, s16, s18, s22 x3); pristine suite 3 failed; disjoint from D2-W and D2-M |
| D3-W1 | 3 | JDL-133 | pass | pass | fail | | rejected | `jef-data` (cli.feature); mutant D2W-133: 5 outside |
| D3-W1 | 4 | JDL-150 | pass | pass | fail | | rejected | TERM (chain.feature); mutant D1A-150b: observing set empty |
| D3-W1 | 5 | JDL-156 | pass | pass | fail | | rejected | the stage name `status` (chain.feature's emit lines); mutant D2W-156: 4 outside |
| D3-W1 | 6 | JDL-139 | pass | pass | fail | | rejected | `--symbol` (decisions.feature, row r7); mutant D2W-139b: 1 outside |
| D3-W1 | 8 | JDL-026 | pass | pass | fail | | rejected | `*.json` (the replay scenario's fixture tree, collectors.feature); mutant D2W-026: 2 outside |
| D3-W1 | 11 | JDL-067 | pass | pass | fail | | rejected | first value the key `"date"` (the revision tables of store.feature and adjustment.feature); mutant `"day"` (D3-067): observing set empty |
| D3-W1 | 12 | JDL-058 | pass | fail | | | rejected | L1 states none of its own values (the tmp names, the lock wait, the lock message); the tmp-name mutant (`.part`, D3-058) is unobserved as well |
| D3-W1 | 14 | JDL-063 | pass | fail | | | rejected | L1 states neither the read's keep-first nor its 0..n-1 numbering (the suite's keep-first scenarios are the collector's, JDL-029/032, and the CSV import's, JDL-070); the zero-row frame is an absence representation and the 21 columns are JDL-059's (C4); the keep-last mutant (D3-063) is unobserved as well |
| D3-W1 | 15 | JDL-119 | pass | pass | fail | | rejected | first value the unit, row position (status.feature's run notes, as data); mutant counts calendar days (D3-119): observing set empty |
| D3-W1 | 16 | JDL-053 | pass | pass | fail | | rejected | first value `split_adjusted` for eodhd + crypto (adjustment.feature); mutant `provider_adjusted` (D3-053): observing 6, 1 outside |
| D3-W1 | 17 | JDL-044 | pass | pass | fail | | rejected | the empty list and null are absence representations (C4); first value `Z` (actions.feature stamps); mutant replaces `z` instead (D3-044): observing set empty |
| D3-W1 | 18 | JDL-093 | pass | pass | fail | | rejected | "none" is an absence representation and "oldest" has no admissible W (C4); first value the format `YYYY-MM-DD` (fixture request parameters); mutant `YYYYMMDD` (D3-093): observing 92, 2 outside |
| D3-W1 | 19 | JDL-052 | pass | pass | fail | | rejected | first value the ratio bound 0 (adjustment.feature's degenerate split); mutant bound 0.5 (D3-052): observing set empty |
| D3-W1 | 20 | JDL-037 | pass | pass | fail | | rejected | `startTime` is JDL-036's (C4); first value the unit, Unix milliseconds (fixture request parameters, C5); mutant seconds (D3-037): observing 48, 1 outside |
| D3-W1 | 21 | JDL-057 | pass | pass | pass | pass | **accepted** | first value the directory `market_data` (store.feature, cli.feature, chain.feature); mutant `marketdata` (the store root and the load and import-csv messages); observing s22 cli_import_csv; pristine suite 4 failed |
| D3-W2 | 1-21 | | | | | | | as D3-W1 (T1-T3 do not depend on the slot within an arm); rank 21 now used |
| D3-W2 | 22 | JDL-035 | pass | fail | | | rejected | its values, the two volume-basis names, are stated in no L1 file (C5; `split_adjusted` as a price basis is JDL-053's); the consistent rename (D3-035) is unobserved as well |
| D3-W2 | 23 | JDL-047 | pass | pass | pass | pass | **accepted** | the price and factor columns are JDL-059's (C4); first value float64, the division's precision (adjustment.feature: "All values are exact float64"); mutant divides in float32; observing 10 stored and exported frames (TLT s01/s05/s07/s15, AAPL s10); pristine suite 12 failed; disjoint from W1 |
| D3-W3 | 1-23 | | | | | | | as above; ranks 21 and 23 used |
| D3-W3 | 24 | JDL-118 | pass | pass | fail | | rejected | first value the bound 0 in n > 0 (status.feature's zero-volume notes); mutant n > 1 (D3-118): observing set empty |
| D3-W3 | 25 | JDL-003 | pass | pass | fail | | rejected | first value the key `name` (the universe fixtures); mutant `title` (D3-003): observing 144, 4 outside |
| D3-W3 | 26 | JDL-072 | pass | pass | pass | pass | **accepted** | first value int64, the integral export's Volume dtype (seam.feature, the expected export frames); mutant int32; observing 12 export artefacts; pristine suite 2 failed; disjoint from W1 and W2 |
| D4-W | 1-26 | | | | | | | as D3 (T2 for D4 is L1 alone, which every D3 verdict above already read); ranks 21, 23 and 26 used |
| D4-W | 27 | JDL-005 | pass | pass | fail | | rejected | first value "integer", a type the threshold accepts (universe.feature: `threshold = -1` read as -1.0); W "string" (the types float and boolean are pinned by the same statement); mutant accepts a string or a float (D4W-005): observing set empty (no harness universe carries a threshold) |
| D4-W | 28 | JDL-099 | pass | pass | pass | pass | **accepted** | the provider name, the path base and the overwrite mode are JDL-006's, JDL-009's and JDL-070's (C4); first value the detail `{rows} row(s) imported` (sync.feature, decisions.feature, collectors.feature); mutant "loaded" (D3-099); observing 6 (s01, s05, s06 sync_out and sync_summary); pristine suite 4 failed |
| D4-M | 3 | JDL-133 | fail | | | | rejected | as D1-M |
| D4-M | 4 | JDL-150 | pass | pass | fail | | rejected | clause "without arguments, re-exec through timeout" (chain.feature's call log); absence mutant D1M-150: observing set empty |
| D4-M | 5 | JDL-156 | pass | pass | fail | | rejected | clause "exit with rc when non-zero" (chain.feature's red status run); absence mutant D2M-156: outside |
| D4-M | 6 | JDL-139 | pass | pass | fail | | rejected | first clause: an empty or split_adjusted series is refused (adjustment.feature's refusal rows); absence mutant D1M-139: outside |
| D4-M | 8 | JDL-026 | pass | pass | fail | | rejected | clause "except files named manifest.json" (collectors.feature); absence mutant D1M-026: observing set empty |
| D4-M | 11 | JDL-067 | fail | | | | rejected | no conditional clause |
| D4-M | 12 | JDL-058 | pass | fail | | | rejected | L1 states none of its clauses (tmp-and-rename, the tmp sweep, prune ordering, the lock) |
| D4-M | 14 | JDL-063 | pass | pass | fail | | rejected | the read's first outcome (concatenate the year files) has no definable absence; its sort, keep-first and numbering are stated in no L1 file (C5); first clause passing T1 and T2: "a series with no year file reads as a zero-row frame" (adjustment.feature: "has 0 rows"); absence mutant reads it like any series and raises (M-063): observing 90, 3 outside |
| D4-M | 15 | JDL-119 | fail | | | | rejected | its one clause (among equally long runs, the earliest) has no definable absence: some run is still reported |
| D4-M | 16 | JDL-053 | pass | pass | fail | | rejected | first clause "eodhd + crypto -> split_adjusted" (adjustment.feature); absence: eodhd always raw (M-053): observing 6, 1 outside |
| D4-M | 17 | JDL-044 | pass | pass | fail | | rejected | first clause "an absent actions file reads as no events" (actions.feature: "splits may be absent"); absence: the read raises (M-044): observing s23 cli_adjust_crypto_refused only, outside |
| D4-M | 18 | JDL-093 | pass | pass | fail | | rejected | first clause "while the series has no stored row, start at the universe start" (decisions.feature's first fills); absence: the tail branch on an empty series (M-093): observing 94, 2 outside |
| D4-M | 19 | JDL-052 | pass | pass | fail | | rejected | first clause "a non-finite or non-positive ratio is refused" (adjustment.feature); absence: no check (M-052): observing set empty |
| D4-M | 20 | JDL-037 | fail | | | | rejected | no conditional clause (the `startTime` condition is JDL-036's) |
| D4-M | 22 | JDL-035 | pass | fail | | | rejected | its clause (the volume basis is consulted only for a raw series) is stated in no L1 file |
| D4-M | 24 | JDL-118 | pass | pass | pass | pass | **accepted** | first clause "n > 0 zero-volume rows add the NOTE" (status.feature's zero-volume outline); absence: no NOTE (M-118); observing s16 status.json; pristine suite 6 failed; disjoint from D4-W |
| D4-A | 3 | JDL-133 | pass | pass | fail | | rejected | first candidate the value `jef-data`; its alternative reading is mutant D2W-133: 5 outside |
| D4-A | 4 | JDL-150 | pass | pass | fail | | rejected | "without arguments" carries no qualifier whose loosening gives a second reading (C7); first candidate TERM; alternative reading INT (D1A-150b): observing set empty |
| D4-A | 5 | JDL-156 | pass | pass | fail | | rejected | the stage name `status`; alternative reading D2W-156: outside |
| D4-A | 6 | JDL-139 | pass | pass | fail | | rejected | `--symbol`; alternative reading D2W-139b: outside |
| D4-A | 8 | JDL-026 | pass | pass | fail | | rejected | `*.json`; alternative reading D2W-026: outside |
| D4-A | 11 | JDL-067 | pass | pass | fail | | rejected | the key `"date"`; alternative reading D3-067: observing set empty |
| D4-A | 12 | JDL-058 | pass | fail | | | rejected | L1 states none of its values or conditions |
| D4-A | 14 | JDL-063 | pass | fail | | | rejected | its qualifiers ("in path order", "stable", "with the 21 columns") and values are stated in no L1 file in role; "with no year file" has no qualifier to loosen (C7) |
| D4-A | 15 | JDL-119 | pass | pass | fail | | rejected | the unit, row position (status.feature's run notes); alternative reading calendar days (D3-119): observing set empty |
| D4-A | 16 | JDL-053 | pass | pass | pass | | rejected | first candidate the qualifier "the DECLARED asset_type only, never from the symbol suffix" (adjustment.feature: "the declared class, never the .CC suffix"); loosened to "the asset type", it admits the type the suffix implies; alternative-reading mutant resolves eodhd's basis from the suffix (A-053): observing set empty -> **T3 fail** |
| D4-A | 17 | JDL-044 | pass | pass | fail | | rejected | the absent-file condition has no qualifier to loosen (C7); first value `Z`; alternative reading D3-044: observing set empty |
| D4-A | 18 | JDL-093 | pass | pass | pass | fail | rejected | "while the series has no stored row" has no qualifier to loosen (C7); first candidate the qualifier "the oldest of" the newest tail sessions (sync.feature, decisions.feature); loosened, it admits starting at the newest; alternative-reading mutant (A-093): observing 14, inside; pristine suite 15 failed; T4 fail: shares s05 and s06 sync_out and sync_summary with D4-W |
| D4-A | 19 | JDL-052 | pass | pass | fail | | rejected | the bound "non-finite or <= 0" (adjustment.feature's 0.0 ratio); no harness split reaches the check (D3-052 bound 0.5 and M-052 no check: both observing sets empty), so neither alternative reading (NaN allowed, 0 allowed) is observed |
| D4-A | 20 | JDL-037 | pass | pass | fail | | rejected | the unit, Unix milliseconds; alternative reading seconds (D3-037): outside |
| D4-A | 22 | JDL-035 | pass | fail | | | rejected | as D3 |
| D4-A | 25 | JDL-003 | pass | pass | pass | pass | **accepted** | first candidate the qualifier "only" in "accept only the keys" (universe.feature's unknown-key rows); loosened, it admits accepting other keys; alternative-reading mutant accepts unknown asset keys (A-003); observing s21 cli_bad_kind, cli_bad_unknown_key; pristine suite 2 failed; disjoint from D4-W and D4-M |
| D5-M1 | 3-22 | | | | | | | as D4-M (T2 for D5 is requirements.json and L1, which every D4-M verdict read); ranks 24 and 25 now used |
| D5-M1 | 27 | JDL-005 | pass | pass | fail | | rejected | first clause "when an asset carries threshold, accept an integer or a float, not a boolean" (universe.feature); absence: no type check (M-005): observing set empty |
| D5-M1 | 29 | JDL-146 | pass | pass | fail | | rejected | "JEF_S3_BUCKET (required)" is a restriction whose refusal is JDL-151's (C6); first clause the JEF_ASSETS default (chain.feature, JEF_ASSETS unset); absence: no default, so an unset list stops the chain (M-146): observing 5, 4 outside (s24 chain logs) |
| D5-M1 | 30 | JDL-094 | pass | pass | pass | pass | **accepted** | first clause "for a leg whose DECLARED asset_type is crypto, the end-guard today - 1 day" (adjustment.feature: "end-guarded at the previous UTC day"); absence: no guard (M-094); observing 13 (s13, s16 BTC frames, sync logs and status; s19 sync_out; s22 cli_dry_run_packaged); pristine suite 19 failed |
| D5-M2 | 31 | JDL-136 | pass | pass | pass | pass | **accepted** | first clause "plus ` [disabled]` for a disabled asset" (universe.feature: "GONE ... [disabled]"); absence: no marker (M-136); observing s22 cli_universe_paused; pristine suite 1 failed; disjoint from M1 |
| D5-M3 | 32 | JDL-124 | pass | pass | fail | | rejected | first clause "whose previous adjusted close is non-zero" (decisions.feature, zero_close_jump.csv); absence: the move computed over a zero close (M-124z): observing set empty. (An earlier mutant took the alert clause, M-124, before the zero-close row was found in L1; it is not the candidate.) |
| D5-M3 | 33 | JDL-152 | fail | | | | rejected | no conditional clause ("before changing directory" orders; "uses only the externals' functions" restricts without a stated refusal) |
| D5-M3 | 34 | JDL-130 | fail | | | | rejected | no conditional clause: one document shape |
| D5-M3 | 35 | JDL-084 | pass | pass | pass | pass | **accepted** | "every enabled asset" restricts without a stated refusal (C6); first clause "keeping only assets named by the asset filter when it is given" (sync.feature's filter scenario); absence: the asset filter ignored (M-084); observing 6 (s07, s08 sync_out and sync_summary; s14 paused_named; s21 cli_paused_only); pristine suite 4 failed; disjoint from M1 and M2 |

## Selection

| arm | slot | requirement | defect | mutant | observing |
|---|---|---|---|---|---|
| D1 | W | JDL-095 | detail "predates the stored tail" -> "precedes" | D1W-095 | 2 |
| D1 | M | JDL-134 | the wrapped refusal's `{command}: {message}`, exit 1, deleted | D1M-134 | 16 |
| D1 | A | JDL-049 | "re-derived from raw" -> "re-derived" | D1A-049 | 2 |
| D2 | W | JDL-060 | bar dates parsed in UTC -> America/New_York | D2W-060 | 13 |
| D2 | M | JDL-102 | lazy collector construction deleted | D2M-102 | 5 |
| D2 | A | JDL-073 | "every stored row, zero-volume and NaN included" loosened | D2A-073 | 6 |
| D3 | W1 | JDL-057 | `market_data` -> `marketdata` | D3-057 | 1 |
| D3 | W2 | JDL-047 | float64 division -> float32 | D3-047 | 10 |
| D3 | W3 | JDL-072 | integral export Volume int64 -> int32 | D3-072 | 12 |
| D4 | W | JDL-099 | detail "row(s) imported" -> "row(s) loaded" | D3-099 | 6 |
| D4 | M | JDL-118 | the zero-volume NOTE deleted | M-118 | 1 |
| D4 | A | JDL-003 | "accept only the keys" loosened | A-003 | 2 |
| D5 | M1 | JDL-094 | the crypto end-guard deleted | M-094 | 13 |
| D5 | M2 | JDL-136 | the ` [disabled]` asset marker deleted | M-136 | 1 |
| D5 | M3 | JDL-084 | the asset filter deleted | M-084 | 6 |

One mutant was built but never needed: M-129 (the spread NOTE of JDL-129, rank 36), observed in parallel with M-084 before
M-084's pristine-suite run accepted rank 35; it is in the bundle as unused evidence.

Fifteen slots, none empty. Walked 2026-10-28 to 2026-10-29 (UTC). Every mutant named in this log is kept in
the bundle as a patch against J-F `8f6d6b0`, with its observing set and, where run, its pristine-suite summary.

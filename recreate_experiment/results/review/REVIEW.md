# Review: kit (A) versus existing (B) diagrams, adjudicated against the source

## Summary

I compared 8 kit diagrams (A) with the 9 existing diagrams (B, plus `sources.toml`) and checked both against `src/jef/data/` and `deploy/daily.sh`. Where `daily.sh` calls into `deploy/externals/`, I read those scripts for their interface only. I found **33 places where A and B disagree**. **A is right in 19, B is right in 8.** Both are right at different levels of detail in 3, both are wrong in 2, and 1 cannot be decided from the source (B's model leg, whose `model.sh` is not in the tree).

**Defects (claims the source contradicts): B has 25, A has 13.** The two sets go wrong in different places:
- **B's errors are mostly structural.** The selector `select_legs` is placed on `Universe`. `actions` is put on the source. `ParquetStore` gets a `base_path` it does not have. Two dependency arrows are invented: collector to store, and store to contract. In the leg diagrams, the guards are narrower than the code. In the daily chain, three gates are drawn wrong: a restore failure and a sync failure are shown continuing, and the binning loop is shown not breaking.
- **A's errors are about who does what in the actions refresh**, and about the chain. In the actions refresh, A collapses `sync_actions` into the runner and has `get_splits` fetch dividends too. In the chain, A drops the status gate entirely and draws a binning failure as still reaching the publish. A also states the stored `timestamp` in seconds when it is in milliseconds.

**Blind spots (true claims that only one set makes): B misses 16 that A has, A misses 15 that B has.**
- **A alone covers** the CLI's error and summary paths, collector lifecycle, the basis-partitioned series states, the status output envelope, and a far more complete type model.
- **B alone covers** the store write path (lock, atomic replace, write-only-on-change), the non-transactional two-file actions write, the classification loading, the cross-venue no-measurement notes and the dashboard publish.

## Counts

| Measure | A (kit) | B (existing) |
|---|---|---|
| Disagreement rows won | 19 (`A right`) | 8 (`B right`) |
| `both right (different altitude)` | 3 | 3 |
| `both wrong` | 2 | 2 |
| `undecidable from source` | 1 | 1 |
| Defects (claims contradicted by source) | 13 | 25 |
| Blind spots (true claims only the other set makes) | 15 | 16 |

Total disagreement rows: 33.

## Correspondence

| Subject | Kit (A) | Existing (B) | `sources.toml` pins (B) |
|---|---|---|---|
| One sync run over the legs (CLI to summary) | `sync_run.puml` | `data_universe_sync.puml` | `cli.cmd_sync`, `universe.load_universe`, `sync.run_sync,select_legs,sync_summary` |
| One EODHD leg (actions gate, window, reconcile, reapply) | `sync_leg.puml` | `data_leg_reconcile.puml` | `sync.run_sync`, `actions.last_updated,load_splits,sync_actions`, `eodhd.get_eod`, `store.recent_dates,reconcile_bars,reapply_adjustment,latest_date` |
| Corporate-actions refresh | inside `sync_leg.puml` (actions `opt`) | `data_actions_sync.puml` | `actions.sync_actions,save_splits,save_dividends`, `eodhd.get_splits,get_dividends` |
| Store write path | no sequence: one step in `basis_and_adjustment.puml` ("store the rows through reconcile, append or overwrite") and one edge in `component.puml` ("Parquet year files under a lock") | `data_store_write.puml` | `store.reconcile_bars,load` |
| The status run | `status_run.puml` | `data_status_health.puml` | `cli.cmd_status`, `health.py`, `store.load,latest_date`, `actions.last_updated,load_splits`, `universe.load_universe`, `classification.load_classifications,compare` |
| Basis resolution and the adjustment pass | `basis_and_adjustment.puml` (also draws the export projection) | `data_ingest_basis.puml` | `sync.select_legs,run_sync`, `store.ingest_bars,reconcile_bars,reapply_adjustment,ingest_yahoo_csv,save`, `adjust.py` |
| One stored series across runs | `series_state.puml` (partitioned by basis) | `data_series_state.puml` (partitioned by activity and health) | `sync`, `store`, `actions`, `adjust`, `health.check_source,expected_sessions_between` |
| Class model | `data_model.puml` (and the module view in `component.puml`) | `data_contract_model.puml` | `actions.py`, `collectors/eodhd.py` (unscoped) |
| The daily chain | `daily_chain.puml` | `ops_daily_chain.puml`, daily section | none (a `.sh` file cannot be pinned) |
| Model leg (`model.sh`) | none | `ops_daily_chain.puml`, model section | none; `model.sh` is not in the tree |
| Module and external-system view | `component.puml` | none (closest is `data_contract_model.puml`'s dependency arrows) | none |

## Disagreements

Source citations name the function and the file line.

| # | Subject | A says | B says | Source says | Verdict |
|---|---|---|---|---|---|
| 1 | Chain: restore failure | `group failure: a non-zero restore exit stops the chain` | `alt [store_restored == True] ... else [s3 restore error] VenueBucket --> DailyRunner : aws_error`, then `sync` follows unconditionally | `set -euo pipefail` (daily.sh:14). The `aws s3 sync` restore (daily.sh:108) is unguarded, so a failure exits the script. | A right |
| 2 | Chain: sync failure gate | `alt sync exit status is not zero` / `DailyChain --> Scheduler : exit with the sync status` before status runs | `DailyRunner -> DataCli : sync(...)` then `status(...)` unconditionally | `[[ ${rc} -eq 0 ]] \|\| exit ${rc}` right after the sync put (daily.sh:125). Status never runs on a red sync. | A right |
| 3 | Chain: status failure gate | No gate. After the `else sync green` block the binning `loop` runs unconditionally. | `alt [status_exit == 0]` binning and publish, `else [status_exit != 0]` | `[[ ${rc} -eq 0 ]] \|\| exit ${rc}` after the status put (daily.sh:140) | B right |
| 4 | Chain: binning loop extent | `loop for each asset until the first failing one` | `loop [asset in daily_assets]`, with no break | `[[ ${a_rc} -eq 0 ]] \|\| { rc=${a_rc}; break; }` (daily.sh:167) | A right |
| 5 | Chain: binning failure versus publish | The group says `a non-zero binning exit is emitted, then ends the loop`, then the publish group follows with no gate | `publish_green` is drawn right after the loop inside `status_exit == 0`, with no binning gate. Only B's note says `any non-zero exit stops the run BEFORE the publish`. | `jef_put binning` then `[[ ${rc} -eq 0 ]] \|\| exit ${rc}` (daily.sh:169-170), before any `aws s3 sync` publish | both wrong (in the drawing; B's note states it correctly) |
| 6 | Chain: ledger emission | One `jef_emit_and_put` after sync, one after status, and a `jef_emit` per binning asset, through `EventsExternal`, each `always zero` | One `put_stage_events` drawn once after status, direct to `VenueBucket` (the note says "once PER STAGE") | Emit and put per stage, each before that stage's rc gate (daily.sh:122-125, 137-140). Binning emits per asset and puts once after the loop (daily.sh:163, 169). Every function returns 0 (events.sh `jef_emit` and `jef_put`). | A right (A omits the binning `jef_put`, listed under A's defects) |
| 7 | Chain: dashboard publish | Note only: `EXIT trap publishes the dashboard (JDL-153)` | Drawn as `PublisherCli publish` plus `put_dashboard` after the green publish. The note says it runs from an EXIT trap on green and red alike, and that an absent store skips it. | `trap 'jef_publish_dashboard' EXIT` (daily.sh:104). The skip on an absent store and the always-0 return are in dashboard.sh `jef_publish_dashboard`. | both right (different altitude) |
| 8 | Chain: what a red sync publishes | `exit with the sync status, nothing published` | Note: a red day publishes nothing to store/runs, but the dashboard publishes `on green AND red exits alike` | The EXIT trap (daily.sh:104) runs `jef_publish_dashboard` on the red exit too. Only store/ and runs/ are green-gated (daily.sh:175-180). | B right |
| 9 | Model leg | Not drawn | `ModelRunner` fetches binning inputs, runs `run_anaconda`, and publishes the model on green | `model.sh` is absent. daily.sh mentions it only in comments (daily.sh:51). | undecidable from source |
| 10 | Who selects the legs | Inside `run_sync` (note: `legs = enabled asset x enabled source, filtered, in universe order`); `component`: `Cli ..> Sync : run_sync and select_legs` | `SyncDriver -> Universe : select_legs(universe, assets)`; `class Universe { +select_legs(assets, providers) }` | `select_legs` is a free function of `sync.py` (sync.py:65), called by `run_sync` (sync.py:352) and `cmd_status` (cli.py:276) | A right |
| 11 | Which leg failures are contained | `any exception escapes the leg (failure contained)`, with detail `"{ExceptionClass}: {message}"` | `else [leg raised CollectorError]` (universe_sync); `else [leg raised StoreError or CollectorError]` (leg_reconcile) | `except Exception as exc` with detail `f"{type(exc).__name__}: {exc}"` (`run_sync`, sync.py:396-397). This includes a `ValueError` from a missing EODHD key and `AdjustmentRefused`. | A right |
| 12 | Dry run | `SyncRunner -> ParquetStore : recent_dates(...)`, then every leg ok with detail `planned` | `SyncDriver -> LegRunner : describe_plan(leg, tail, today)` returning `plan_line` (a single call, no loop) | A loop over the legs calls `_describe_plan`, which calls `_window`, which calls `store.recent_dates`. Results are `dict(leg, ok=True, detail="planned")` (sync.py:356-360). | both right (different altitude) |
| 13 | When `last_updated` is read | Unconditionally, then `alt force_actions or no stamp or stamp UTC date before today` | `opt [force_actions == False] last_updated(symbol)` | `updated = actions_store.last_updated(...)` runs before the `if force_actions or ...` (`_run_leg`, sync.py:225-226) | A right |
| 14 | Actions refresh guard | `force_actions or no stamp or stamp UTC date before today` | `[force_actions == True or updated_day < today]` (no case for a missing stamp) | `force_actions or updated is None or updated.date() < today` (sync.py:226) | A right |
| 15 | Who performs the actions refresh | `SyncRunner -> Eodhd : get_splits` and `SyncRunner -> ActionsStore : save_splits_then_dividends`; `component`: `Sync ..> EodhdModule : get_eod, get_splits, get_dividends` | `LegRunner -> ActionsSync : sync_actions(...)`. `ActionsSync` then calls `get_splits`, `get_dividends`, `save_splits` and `save_dividends` | `_run_leg` calls `sync_actions(collector, actions_store, symbol)` (sync.py:227). That free function makes the four calls (actions.py:179-182). | B right |
| 16 | What `get_splits` fetches | Inside `get_splits`: `http_get(splits_path)` and `http_get(div_path)`, returning `split events and dividends sorted by date` | `get_splits` (to `fetch_split_events`) and a separate `get_dividends` (to `fetch_dividend_events`) | `get_splits` requests only `/splits/` (eodhd.py:111-120). `get_dividends` requests `/div/` (eodhd.py:122-131). | B right |
| 17 | Fetch guard | `alt series has rows and start is after end (inverted window)`: no request is sent, `else` fetch | `opt [start <= end] get_eod` | Fetch unless `latest is not None and end is not None and start > end` (sync.py:236). A first fill with `start` or `end` of None still fetches, which `start <= end` cannot express. | A right |
| 18 | Class check versus a never-filled source | `opt provider is eodhd compare(...)` before `latest_date`, then `alt no stored row` | The class check is drawn only inside `alt [source_outcome == "measured"]`. The never-filled `else` branch has no check. | `_check_declared_class` runs before `latest_date` and its early return (`check_source`, health.py:278-284) | A right |
| 19 | Contract validation on the ingest path | The basis activity continues after `store the rows` into `project stored rows ...` and then `validate the frame and render the report` | `No contract validation runs on this path ... both [callers] are hand-run subcommands` | `validate` is called only by `cmd_validate` and `cmd_export` (cli.py:130, 208). sync.py and store.py never call it. | B right |
| 20 | Trigger for re-adjustment | `RawSeries --> RawSeries : split synced later, whole series re-derived from raw` | `Current --> Readjusting : sync-actions found a new split / reapply_adjustment` | `reapply_adjustment` runs on every raw-basis sync with stored rows (sync.py:273-275) and rewrites only when a value moves (store.py:425). `cmd_sync_actions` only writes the JSON files and never re-adjusts (cli.py:136-149). | A right |
| 21 | Series state axes | States by basis: `RawSeries`, `PreAdjusted`, `Pinned`, `Refused` | States by activity and health: `FirstFill`, `Current`, `Reconciling`, `Readjusting`, `Stale` | Basis is a stored per-row fact (`price_basis`; `_frame_from_bars`). Stale is a status verdict (`check_source`), not stored state. Both axes are real. | both right (different altitude) |
| 22 | Which series can be pinned (inverted window) | Only `RawSeries --> Pinned : stored rows reach past a declared end` | Leg note: `a series with rows past its end (start > end) fetches nothing ... green`, for any leg | The inverted-window branch in `_run_leg` (sync.py:236) applies to every collector leg, eodhd crypto and binance included | B right |
| 23 | Universe shape | `Universe { defaults : Defaults; assets : list }`, `Asset` (`asset_class`, `asset_type`, `threshold`), and `Asset *-- Source` | `class Universe <<config>>` with methods `load_universe`, `select_legs` and `modeled_source`, and `Universe *-- AssetSource` with no asset level | `load_universe` returns `{"defaults", "assets"}`. Each asset carries `sources` (universe.py:198-206, 269). `load_universe` and `modeled_source` are module functions. | A right |
| 24 | Where `actions` lives | On `Leg` (`+actions : bool`), not on `Source` | `AssetSource { +actions: bool }` | A source dict has no `actions` key (`_parse_source`, universe.py:115-142). `actions` is set per leg in `select_legs` (sync.py:111-112). | A right |
| 25 | ParquetStore root attribute | `+root : str`, `+lock_timeout : float = 300.0` | `+base_path: str` | `self.root = os.path.join(base_path, "market_data")`. No `base_path` is kept (store.py:101). | A right |
| 26 | `SplitEvent.date` type | `+date : date` (plus `split_string`) | `+date: str` | `date: date` (actions.py:43) | A right |
| 27 | ContractReport fields | `errors`, `notes` | `errors`, `warnings` | `errors` and `notes` (contract.py:251-252). There is no `warnings`. | A right |
| 28 | Volume basis attribute | Lower-case `volume_basis` on each subclass: EODHD `"split_adjusted"`, Binance `"raw"` | `BaseCollector { +VOLUME_BASIS: str }` | Class attribute `VOLUME_BASIS = "raw"` on `BaseCollector` (base.py:251), overridden by EODHD (eodhd.py:70). A's values are right but its name and placement are wrong. | B right |
| 29 | Is `BaseCollector` abstract? | Plain `class BaseCollector` | `abstract BaseCollector` | A plain class with no ABC and no abstract members, fully implemented (base.py:243-315) | A right |
| 30 | `get_splits` / `get_dividends` signature | `get_splits(symbol)`, `get_dividends(symbol)` | `get_splits(symbol, start, end)`, `get_dividends(symbol, start, end)` | `(self, symbol, start=None, end=None)` (eodhd.py:111, 122) | B right |
| 31 | Who lands bars in the store | `Sync ..> Store : reconcile_bars and reapply_adjustment` | `EODHDCollector ..> ParquetStore : lands bars in` | The collector never references a store. `_run_leg` calls `store.reconcile_bars` (sync.py:260). | A right |
| 32 | Store versus contract | `Cli ..> Contract : validate`; no link from the store | `ParquetStore ..> ContractReport : validated against` | `store.py` imports only `REQUIRED_COLUMNS` (store.py:47), for a presence check in `ingest_yahoo_csv`. `validate` is called only from the CLI. | A right |
| 33 | `reconcile_bars` / `ingest_bars` signatures | `reconcile_bars(exchange, symbol, bars, splits, price_basis, volume_basis)`, `ingest_bars(exchange, symbol, bars, splits, price_basis, volume_basis, mode)` | `reconcile_bars(bars, splits, volume_basis)` (class), `(bars, splits, price_basis)` (store_write), `ingest_bars(bars, splits, price_basis)` | Both also take the required positionals `asset_type` and `currency` (and `asset_subtype`). These are stored in every row (store.py:266, 334). A reader building from either set cannot label the rows. | both wrong |

Verdict tally: A right 19 (rows 1, 2, 4, 6, 10, 11, 13, 14, 17, 18, 20, 23, 24, 25, 26, 27, 29, 31, 32). B right 8 (3, 8, 15, 16, 19, 22, 28, 30). Both right at different altitudes 3 (7, 12, 21). Both wrong 2 (5, 33). Undecidable 1 (9).

## B's defects (claims in B the source contradicts) — 25

1. `ops_daily_chain`: a restore failure is drawn as a branch the chain continues past. Under `set -e` the unguarded `aws s3 sync` exits (daily.sh:14, 108).
2. `ops_daily_chain`: status is drawn as running after any sync result. A red sync exits first (daily.sh:125).
3. `ops_daily_chain`: the binning loop is drawn over every asset. It breaks at the first failure (daily.sh:167).
4. `ops_daily_chain`: `publish_green` is drawn after the binning loop with no binning gate (daily.sh:169-170). Only the note corrects it.
5. `ops_daily_chain`: the ledger put is drawn once, after status. It happens per stage, before each rc gate, and is direct to the bucket only through events.sh (daily.sh:122-124, 137-139, 169).
6. `data_universe_sync` and `data_contract_model`: `select_legs` is attributed to `Universe`. It lives in sync.py (sync.py:65).
7. `data_universe_sync` and `data_leg_reconcile`: leg failure is narrowed to `CollectorError` or `StoreError|CollectorError`. The code catches any `Exception` (sync.py:396).
8. `data_leg_reconcile`: `last_updated` is drawn only when `force_actions == False`. It is always read (sync.py:225).
9. `data_leg_reconcile`: the refresh guard omits the `updated is None` case (sync.py:226).
10. `data_leg_reconcile`: the fetch guard `[start <= end]` is undefined for a first fill without a start or end. The code tests `latest is not None and end is not None and start > end` (sync.py:236).
11. `data_status_health`: the declared-class check is drawn only for stored series. It runs before the never-filled return (health.py:278-284).
12. `data_series_state`: `Current --> Readjusting : sync-actions found a new split`. The `sync-actions` subcommand never re-adjusts (cli.py:136-149). Re-adjustment runs on every raw sync (sync.py:273-275).
13. `data_series_state`: `FirstFill --> Stale : collector raised CollectorError`. A failed first fill writes nothing. The series stays absent, and status reports it `never filled`, not stale (health.py:281-284).
14. `data_series_state`: `Current --> [*] : asset disabled`. Disabling only drops the asset from `select_legs` (sync.py:84). The stored series is untouched and loadable, and re-enabling resumes the tail refresh.
15. `data_contract_model`: `AssetSource.actions`. That is a leg key, not a source key (universe.py:115-142; sync.py:111).
16. `data_contract_model`: `ParquetStore.base_path`. The attribute is `root` (store.py:101).
17. `data_contract_model`: `SplitEvent.date: str`. The type is `date` (actions.py:43).
18. `data_contract_model`: `ContractReport.warnings`. The field is `notes` (contract.py:252).
19. `data_contract_model`: `EODHDCollector ..> ParquetStore : lands bars in`. The collector has no store reference (eodhd.py). Sync lands the bars (sync.py:260).
20. `data_contract_model`: `ParquetStore ..> ContractReport : validated against`. No validation happens in the store (store.py:47, 399-402).
21. `data_contract_model`: `ParquetStore ..> SplitEvent : re-derives raw columns from`. The pass derives the main columns from `*_raw`. Only `volume_raw` is touched, and only at ingest (adjust.py `adjust`; store.py:323-329).
22. `data_contract_model` and `data_store_write`: the `reconcile_bars` and `ingest_bars` signatures drop `exchange`/`symbol` (in places) and the required `asset_type`/`currency` (store.py:266, 334).
23. `data_ingest_basis`: yahoo-csv legs are routed through the provider edge's `Drop non-positive closes`. `ingest_yahoo_csv` keeps every row (store.py:390-410) and has no fetch window.
24. `data_contract_model`: `+ok()` as a method. It is a `@property` (contract.py:254). Minor; A shares it.
25. `data_contract_model`: `abstract BaseCollector`. The class is concrete (base.py:243). Weak.

## A's defects (claims in A the source contradicts) — 13

1. `daily_chain`: no status gate. Binning is drawn as running after any status result, but a red status exits (daily.sh:140).
2. `daily_chain`: a failing binning asset is drawn as still reaching `s3_sync_and_copy`. The chain exits after `jef_put binning` (daily.sh:169-170).
3. `daily_chain`: `exit with the sync status, nothing published`. The EXIT trap publishes the dashboard on a red exit (daily.sh:104), which A's own note says.
4. `daily_chain`: binning shows `jef_emit` per asset but no `jef_put` after the loop, so the stage's ledger object is never uploaded in the drawing (daily.sh:169).
5. `sync_leg`: the actions refresh is drawn as `SyncRunner` calling the collector and the store directly. It is delegated to the free function `actions.sync_actions` (sync.py:227; actions.py:172-183).
6. `sync_leg`: `get_splits` is drawn issuing both the splits request and the dividends request and returning both. `get_dividends` is a separate method and call (eodhd.py:111-131; actions.py:179-180).
7. `component`: `Sync ..> EodhdModule : get_eod, get_splits, get_dividends`. Sync calls only `get_eod` (sync.py:248). Splits and dividends are fetched by `actions.sync_actions`.
8. `basis_and_adjustment`: `timestamp in Unix seconds`. It is Unix milliseconds (store.py:58, 305).
9. `basis_and_adjustment`: export projection and validation are sequenced after the ingest write in one activity. They belong to the separate `export` subcommand (`cmd_export`, cli.py:202-211). Ingest never validates.
10. `series_state`: `Pinned` is reachable only from `RawSeries`. Pre-adjusted collector legs (eodhd crypto, binance) take the same inverted-window branch (sync.py:236).
11. `data_model`: `volume_basis` is lower-case and declared per subclass. The attribute is `VOLUME_BASIS`, with the base default `"raw"` (base.py:251; eodhd.py:70).
12. `data_model`: `get_splits(symbol)` and `get_dividends(symbol)` omit the optional `start`/`end` window (eodhd.py:111, 122).
13. `data_model`: the `reconcile_bars` and `ingest_bars` signatures omit the required `asset_type`/`currency` (store.py:266, 334). `ContractReport.ok()` is drawn as a method where it is a property (contract.py:254).

## Blind spots of B (claims only A makes that the source confirms) — 16

1. `--summary-json`: `sync_summary` is written on red runs too, as sorted JSON with indent 1 (cli.py:253-261; sync.py:285-320). B's own `sources.toml` flags this as missing.
2. CLI error path: `UniverseError` or `SyncError` gives `sync: {message}` on stderr and exit 1 (cli.py:251-252). Status does the same (cli.py:278-279).
3. Collectors are built lazily, once per provider, and closed in `finally`. Injected collectors are not closed (sync.py:362-403).
4. A missing EODHD key fails each eodhd leg. The `ValueError` is raised in the `EODHDCollector.__init__` key check, inside the per-leg `try` (eodhd.py:77-81; sync.py:187).
5. yahoo-csv legs import their whole file without a collector, in overwrite mode (sync.py:180-185; store.py:390-410).
6. Leg detail composition: `"actions fresh; "`, the inverted-window text, the page-limit guard, `"{count} bar(s), {r} revised cell(s)"`, and the today-dated suffix (sync.py:229-281).
7. Pre-adjusted versus raw is a lifetime partition of a series, and the `adjust` command raises `AdjustmentRefused` on a split_adjusted series, leaving it unchanged (adjust.py:257-264; cli.py:172-182; store.py:420-424).
8. A degenerate split ratio (non-finite or <= 0) raises `AdjustmentRefused` (adjust.py:241-244).
9. Export projection: Volume is int64 when every value is finite and integral, else float64 (`to_contract_frame`, store.py:444-447).
10. Status output: the JSON envelope (`schema_version`, `store`, `reports`, `pairs`, `alerts_total`, `warnings_total`) or the table and summary line. Warnings never affect the exit (cli.py:305-365).
11. The order of the per-source checks: stale, today-dated, zero volume, post-seam gap, resolution, jumps, actions freshness (health.py:286-384).
12. Chain prologue: other arguments are exec'd instead of the chain, the `--inner` re-exec goes under `timeout`, and the TERM trap emits rc 143 (daily.sh:61-68, 96-97).
13. Status runs once with `--json`, teed to `status.json` (daily.sh:134-136).
14. Retry policy: 429, 5xx and network errors are retried up to `max_retries + 1 = 5` attempts with exponential backoff, and any other non-200 fails at once (`get_json`, base.py:262-297).
15. Type model coverage B lacks entirely:
    - the Asset level (`asset_class`, `asset_type`, `threshold = -0.05`), and the Source fields (`kind`, `modeled`, `note`, `path`, `start`, `end`) (universe.py:115-206);
    - `Leg`, `LegResult`, `Revision`, `SyncSummary`;
    - the `StoredRow` schema (store.py:57-80);
    - `RecordingTransport`, `TransportResponse`;
    - the exception hierarchy;
    - `SourceReport`, `PairReport`, `Resolution`.
16. `ParquetStore.latest_date`, `recent_dates` and `ingest_yahoo_csv` as members, and `ReplayTransport` loading every `*.json` except `manifest.json` (base.py:171-179).

## Blind spots of A (claims only B makes that the source confirms) — 15

1. Writer lock: a per-symbol `fcntl.flock` polled up to `lock_timeout`, then `StoreError`. It is released by closing the descriptor (`_locked`, store.py:167-199).
2. Crash-safe year files: a temp `data.parquet.tmp` plus `os.replace`, and readers stay lock-free (`_write_frame`, store.py:234-263).
3. Reconcile compares only `RECONCILE_COLUMNS` and writes only when rows were replaced or are new (store.py:54-55, 365-388).
4. `reapply_adjustment` refuses an empty series (`StoreError`), which is why the gate needs stored rows. It compares on every sync and writes only on change (store.py:420-427).
5. The actions refresh is two separate whole-file writes, splits first, with no transaction (actions.py:181-182). The freshness gate reads `kind="splits"`, so lost dividends are not retried until the next UTC day (actions.py:113; sync.py:225-226).
6. Neither actions fetch is windowed: `sync_actions` passes no start or end (actions.py:179-180).
7. Each envelope's `exchange` is `collector.exchange` (actions.py:181-182). Splits are stored as typed `SplitEvent`s and dividends as provider rows verbatim (eodhd.py:119, 131).
8. Status loads the classification evidence (`load_classifications`) before `compare` (health.py:248-252). Crypto resolves to a note, not a verdict, because BTC is recorded as `Currency` (classification.py:192-197; classifications.toml).
9. Cross-venue: each leg's `latest_date` is checked before `load`. There are three "spread not measured" notes (no rows, no common session, zero mid) and no alert (`_pair_report`, health.py:476-498).
10. Actions freshness is counted in sessions through `expected_sessions_between`. `actions_missed_k = 2` is not a CLI flag, and never-synced alerts at any threshold (health.py:371-384; cli.py:507-563).
11. Staleness uses `expected_sessions_between`: weekdays only for stock/etf, every day for crypto (health.py:85-95, 286-292).
12. Status calls `load_universe` (cli.py:275).
13. Contract validation has exactly two callers, `cmd_validate` and `cmd_export`. `validate_or_raise` has no caller in the package, and `ingest_yahoo_csv` checks column presence only (cli.py:130, 208; contract.py:348; store.py:399-402).
14. Daily chain: `JEF_ASSETS` defaults to `AAPL BTC TLT NVDA TSLA IBM` (daily.sh:71). The digest is exported before the exec guard (daily.sh:29-46). The dashboard publish skips when the store is absent and puts the health snapshot (externals `dashboard.sh`; interface only).
15. `CorporateActionsStore.needs_update` and the `kind` parameter of `last_updated` (actions.py:113-160). `BaseCollector.close` (base.py:314-315).

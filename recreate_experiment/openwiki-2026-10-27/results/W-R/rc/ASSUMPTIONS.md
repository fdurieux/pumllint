# Assumptions

Every point where the wiki was silent, ambiguous or contradictory, what was
chosen, and why. One entry each, numbered in the order they were made.

## Packaging and layout

1. **Module layout.** The wiki describes `src/jef/data/{__init__,__main__,actions,adjust,classification,cli,contract,differential,health,store,sync,universe}.py`, `collectors/{base,eodhd,binance}.py` and packaged `universe.toml` / `classifications.toml`. Rebuilt one-for-one as `src/jef_data_rc/...` (src layout, as the original's `where = src` discovery implies). The original's `jef` namespace level is dropped because the required package name is `jef_data_rc`.
2. **Dependency pins.** The wiki says the metadata declares `pandas`, `numpy` and `scikit-learn` and gives no version numbers. Declared exactly those three, unversioned. `pyarrow` and `requests` are deliberately *not* declared (the wiki says the original does not declare them either; persistence and live HTTP need them supplied by the environment).
3. **pyarrow import point.** The wiki says `ParquetStore` imports `pyarrow` directly and that `import jef.data` does not. `store.py` imports `pyarrow` at module level, so any command that opens the store (sync incl. `--dry-run`, status, load, adjust, import-csv, export, differential, sync-actions) fails with `ModuleNotFoundError` when pyarrow is absent, while `validate` and `universe` keep working, as the wiki describes for the original.
4. **Distribution name.** Not stated. Used `jef-data-rc` (version `0.1.0`), setuptools backend.
5. **Console script.** `jef-data-rc = jef_data_rc.cli:main`; `python -m jef_data_rc` calls the same `main()`.
6. **Messages naming the command.** The one message string the wiki quotes that names the command (`never filled - no stored rows (jef-data sync first)`) is reproduced byte for byte, i.e. it still says `jef-data`, not `jef-data-rc`.

## Universe

7. **Top-level keys.** Wiki: unknown keys rejected at top, defaults, asset and source levels, but only `[defaults]` and `[[asset]]` are named. Top level accepts exactly `defaults` and `asset`; at least one `[[asset]]` is required.
8. **Source currency.** `currency` is not a listed source field; the "source currency" the wiki says is produced is the asset's resolved currency (asset `currency`, else `defaults.currency`).
9. **`threshold` default.** Optional; absent means `None` in the normalized asset (the wiki only says it must be numeric when present). Booleans are rejected as non-numeric.
10. **Canonical EODHD symbol rule.** "Must already be canonical `TICKER.EXCHANGE`": implemented as a non-empty ticker part, a dot, and a non-empty alphanumeric exchange suffix (after the last dot), no whitespace.
11. **Date fields.** `start`/`end` accept a TOML date or an ISO `YYYY-MM-DD` string; a TOML datetime (with a time) is rejected. Normalized to ISO strings; absent is `None`. `start == end` is allowed ("must not follow").
12. **Duplicate coordinates.** Any two sources (enabled or not, same asset or not) with the same `(exchange, symbol)` are rejected, not only cross-asset ones.
13. **`modeled` normalization.** The normalized source keeps the declared `modeled` flag; the implicit sole-source choice is made only by `modeled_source()`.
14. **Yahoo CSV `path` resolution.** Kept as written in the TOML and opened relative to the process working directory (the daily chain runs from `JEF_APP_DIR`).
15. **Error text.** `UniverseError` messages are `"<file>: <location>: <problem>"` with locations like `asset[2] 'TLT' source[0]`; exact wording invented.
16. **Packaged universe content.** Wiki gives the asset list (AAPL, BTC, TLT, NVDA, TSLA, IBM), that AAPL and BTC have a modeled EODHD source plus snapshot/cross-check sources, Binance BTC `start = 2017-08-01`, and the `experiments/AAPL.csv` path seen in an `import-csv` example. Chosen: AAPL = `eodhd AAPL.US` (modeled) + `yahoo-csv yahoo:AAPL path=experiments/AAPL.csv`; BTC = `eodhd BTC-USD.CC` (modeled, crypto) + `binance BTCUSDT start=2017-08-01`; TLT = `bond_etf eodhd TLT.US`; NVDA/TSLA/IBM = `stock eodhd X.US`. No EODHD `start`/`end` bounds and no `threshold` values (none are documented).

## Contract validator

17. **Contract message wording.** The wiki lists the error and note categories but no strings. Wording is invented (`missing required column(s): ...`, `<col>: N non-numeric value(s)`, `N duplicate date(s)`, `N row(s) with High < Low`, notes ending in "the loader drops/sorts ..."). A missing required column returns immediately with that single error.
18. **"Newly coerced" non-numeric.** A cell counts as non-numeric when it was non-null and `pd.to_numeric(errors="coerce")` made it NaN; original nulls are notes (NaN rows), not errors. Negative and `High < Low` checks run on the coerced values.
19. **Date parsing.** `pd.to_datetime(errors="coerce")` with pandas' default format inference; "no parseable dates" is an error, unparseable-but-some-parseable is a note. Duplicates and ordering are judged on parseable dates only.
20. **Clean rows.** A row is clean when its date parses, its volume is not zero and no column (extra columns included) is null. The advisory note fires when clean rows < `min_rows`.
21. **Report rendering.** `ERROR: ...` lines, then `note: ...` lines, then `contract OK|FAILED (E error(s), N note(s), C clean row(s))`. The `validate` command first prints `<path>: <rows> row(s)`.

## Corporate actions and adjustment

22. **`last_updated` format.** Not specified. Written as the UTC `datetime.isoformat()` of the run clock (`2026-10-28T09:00:00+00:00`). Freshness reads its UTC calendar date. Both files of one refresh get the same stamp.
23. **Action JSON layout.** `json.dump(indent=2)` plus a trailing newline. Split entries are `{date, ratio, split}` (ER-diagram order); dividends are stored as the provider's entry dicts, sorted by `date`.
24. **`sync_actions` order.** Fetch splits, then dividends, then save splits, then dividends (a failed dividend fetch leaves the split stamp untouched).
25. **Split string parsing.** EODHD `"4.000000/1.000000"` -> `4.0` (numerator / denominator); other shapes are a `CollectorError`.
26. **Factor multiplication order.** Ratios are multiplied in ascending effective-date order into a float64 factor initialised to 1.0, per row (`factor[d < split.date] *= ratio`).
27. **`adjust()` refusal.** Any `price_basis` value other than `raw` (including null) or a missing `price_basis` column is refused with `AdjustmentError`; missing `*_raw` or `datetime` columns likewise.

## Store

28. **`asset_subtype`.** Named once in the prose but absent from the ER diagram, with no source of values. Stored as an all-null column placed right after `asset_type`; column order otherwise follows the ER diagram.
29. **Column dtypes.** `timestamp` int64 Unix ms of the session date at 00:00 UTC; `datetime` `datetime64[ns, UTC]`; all numeric columns float64.
30. **Rawized volume and main volume.** For raw basis with split-adjusted served volume: `volume_raw = served / factor(d)`, then `adjust()` sets `volume = volume_raw * factor(d)` (not re-using the served value, so a 1-ulp difference is possible, as the formula implies).
31. **Revision equality.** Identity cells compare with exact float equality; NaN equals NaN. A revision record is `{date: "YYYY-MM-DD", column, stored, served}` (NaN rendered as null), ordered by date, then by identity-column order.
32. **Reconcile writes.** Only the years containing a changed or new supplied timestamp are rewritten; replaced rows take the full served row (including its freshly derived main values and the new declared `asset_type`).
33. **`recent_dates` / tail start.** Read from the stored `timestamp` column; the tail start is the oldest date among the newest `tail` distinct stored timestamps.
34. **Yahoo CSV import.** `pd.read_csv`, dates parsed with `pd.to_datetime` (an unparseable date raises), every value converted with `float()` (an invalid value raises), NaN and zero-volume rows kept, duplicate dates first-wins. The returned/reported count is the number of rows written.
35. **Export `Date` dtype.** `Date` is a `YYYY-MM-DD` string column (from the UTC `datetime`), not a datetime column; prices float64; `Volume` int64 only when every value is finite and integral. An empty store exports an empty seven-column frame.
36. **Lock error text.** `timed out after <n>s waiting for the writer lock <path>`.

## Collectors

37. **EODHD base URL.** `https://eodhd.com/api`, so fixture paths are `/api/eod/{symbol}`, `/api/splits/{symbol}`, `/api/div/{symbol}`, `/api/search/{query}`. Every request carries `api_token` and `fmt=json`; EOD adds `order=a`, `period=d`, and `from`/`to` only when bounded. Splits/dividends are requested unbounded by sync.
38. **Binance request.** `GET https://api.binance.com/api/v3/klines` with `symbol`, `interval=1d`, `limit=1000`, `startTime` (only when a start/cursor exists) and `endTime` = last millisecond of the `end` UTC date (only when an end exists). A full page advances the cursor to last open time + 86 400 000 ms; a short page, an empty page, or a cursor past `endTime` ends paging.
39. **Fixture file shape.** "The kit's contracts" are not in the wiki. The replayer accepts `{"request": ..., "response": ...}` where `request` is a `{method, path|url, params}` object, a `[method, path, params]` triple, or a `"METHOD path?query"` string, and `response` holds `status` plus `json` (or `body`/`text`/`data`). When two fixtures share an identity, the later file in sorted path order wins. Files without both keys are skipped.
40. **Replay key path.** Host is ignored; only the URL path is used. `api_token` is dropped from both the recorded and the live identity.
41. **Recorder output.** `{"request": {method, path, params}, "response": {status, json}}`, `indent=2, sort_keys=True`, file `<path-slug>-<sha256[:12]>.json`.
42. **Rate limiter edge.** When the 60-second window is full it sleeps `60 - (now - oldest)`, then evicts expired entries (and, if the injected clock did not advance, the oldest entries) before recording.
43. **Collector error wording.** `GET <path>: HTTP <status> after <n> attempt(s)`, `GET <path>: HTTP <status>: <200-char body>`, `GET <path>: network failure after <n> attempt(s): ...`, `GET <path>: invalid JSON: ...`; redaction replaces a secret with `***`.
44. **EODHD row parsing.** Rows missing any OHLCV key are a `CollectorError`; a missing/null `adjusted_close` falls back to `close`; non-positive close rows are dropped before de-duplication (first row per date wins).
45. **`normalize_symbol` pair rule.** Both sides in a fiat set -> `BASEQUOTE.FOREX`; either side in a known crypto set -> `BASE-QUOTE.CC`; otherwise refused. The fiat and crypto sets are invented.
46. **EODHD key error.** `CollectorError("EODHD requires an API key: pass api_key= or set EODHD_API_KEY")`, raised before the transport exists.
47. **Binance `VOLUME_BASIS`.** Declared `"raw"` (no splits); it is never consulted because Binance is stored split-adjusted.

## Classification evidence

48. **Evidence file grammar.** Top level exactly `schema` (must be integer 1) and `[[instrument]]`; instrument keys exactly `exchange, symbol, code, query_exchange, vendor_type` (required, non-empty strings) plus optional `isin`, `name`, `last_verified` (ISO date). Errors raise `ClassificationError`.
49. **Packaged evidence content.** Not given. Recorded one entry per packaged EODHD source: AAPL/NVDA/TSLA/IBM `Common Stock`, TLT `ETF`, BTC-USD.CC `Currency` (ISINs are the public ones). So the packaged universe yields `agree` x5 and `not_comparable` x1, no `no_evidence`.
50. **`declared_class_check` shape.** The wiki names the key but not its value. Chosen: `{"verdict", "declared", "vendor_type", "mapped"}` (`vendor_type`/`mapped` null when absent).
51. **Classification note/warning text.** Invented; `disagree` is the only verdict routed to `warnings`.

## Status / health

52. **Report key order.** `asset, exchange, symbol, alerts, warnings, notes`, then `declared_class_check` (EODHD only), then `last_session, missed_sessions, rows`, then `resolution`; the order the wiki's line references imply (class check, freshness, seam measurements, jump/actions).
53. **Finding order inside a report.** Class note/warning; stale alert; today note; zero-volume note; post-seam note; resolution note; jump alerts (oldest first); action-freshness alert.
54. **Jump window.** For each of the newest `--window` rows, the one-row return `close[i] / close[i-1] - 1` against its predecessor (which may lie just outside the window); alert when `abs(ret) > threshold` and no saved split has that exact date. NaN/inf returns are ignored.
55. **Price-resolution measurement.** Traded = main `volume > 0`; prices are `close_raw` values that are non-null and > 0 on traded rows, or, if none, main `close` likewise; the newest `--resolution-window` of those are used. `distinct_ratio = distinct / sessions`; smallest relative step = `min(diff(sorted_unique) / sorted_unique[:-1])` (null with one distinct value); `flat_share = count(price[i] == price[i-1]) / (sessions - 1)`. The `resolution` object is `{sessions, distinct, distinct_ratio, min_rel_step, flat_share, price}`.
56. **Zero-volume and post-seam rules.** Zero volume means main `volume == 0`; runs are consecutive stored rows. Post-seam survivors are rows with main `volume > 0` and non-null main `close`; the note fires at `max gap >= --gap-k` and names the widest gap (first one on ties).
57. **Action freshness.** Only legs with `actions = true`. No (or unparseable) split-file stamp -> alert; otherwise expected sessions strictly between the stamp's UTC date and today, on the leg's calendar, `>= 2` -> alert.
58. **Today / future bars.** A last session equal to today adds the today note; a last session after today counts zero missed sessions and adds no note.
59. **Cross-venue labels and grouping.** Pair labels `a`/`b` are `exchange:symbol`; pairs are `itertools.combinations` of an asset's live legs in leg order; assets in order of first appearance. When the common date has duplicate rows the last one is used. `threshold` echoes `--spread-threshold`.
60. **Spread message text.** Notes/warnings are invented; the measured note always precedes the breach finding. A missing frame on side A is reported before side B.
61. **Status JSON formatting.** `json.dumps(document, indent=1)`: the wiki's sample envelope is printed with one-space indentation, taken as the real format. `store` is the store path string as given (or the universe default).
62. **Status text format.** One line per report (`ALERT|WARN|ok`, asset, `exchange:symbol`, `last .. missed .. rows ..`), indented resolution and finding lines, pair lines, and a summary `N source(s)[, P venue pair(s)], A alert(s), W warning(s) -> store <path>`. Invented beyond the wiki's description.
63. **Evidence loading.** The packaged evidence is loaded once per status run, at the first EODHD leg, outside any error handling, so a malformed file crashes the command (traceback, exit 1).
64. **Selections with only CSV legs.** `status --provider yahoo-csv` is a valid selection that yields zero reports and exits 0 (only an empty *selection* is an error).

## Differential

65. **Default tolerance.** Not stated (examples pass `1e-4` explicitly). Default `1e-6`.
66. **Within tolerance.** A cell passes when `rel <= tolerance`; it fails when `rel > tolerance`. Worst cell = largest `rel` (first on ties) and its date.
67. **Date alignment.** Both `Date` columns are compared as strings (`astype(str)`), no re-parsing.
68. **Report text.** `differential: A vs B (relative tolerance T)`, `aligned dates: N`, `only in A: ...`, `only in B: ...`, one line per column, `verdict: PASS|FAIL`. `--output` writes the same text to the file as well as stdout.

## Sync

69. **Leg dict keys.** "The kit's contract" is not in the wiki. Legs are `{asset, provider, exchange, symbol, asset_type, currency, start, end, path, actions}` (`start`/`end` ISO strings or null; `path` null for collector legs; `actions` true only for EODHD legs whose type is not crypto).
70. **Leg order.** Declared asset order, then declared source order within an asset.
71. **Filter validation.** An `--asset` value must name a declared asset (enabled or not); a `--provider` value must be one of `eodhd, binance, yahoo-csv`. Selection is validated before `tail`.
72. **Dry-run return value.** `run_sync(dry_run=True)` prints one plan line per leg plus a closing line and returns `([], True)`, so a dry-run summary has zero legs.
73. **Dry-run action label.** `sync-actions + load` for every action-eligible leg regardless of the stamp's freshness; `load` for other collector legs; `import-csv <path>` for CSV legs.
74. **Freshness gate.** Actions refresh when forced, when the split file has no stamp (or it cannot be parsed), or when the stamp's UTC date is before `now`'s UTC date. The refresh happens before the inverted-window check, so an inverted raw leg still refreshes actions and still re-derives.
75. **Leg detail string.** `"; "`-joined parts: action state (`actions refreshed (S split(s), D dividend(s))` / `actions fresh`), inverted-window or page-limit diagnostic, `N bar(s), R revised cell(s)`, and `re-derived from raw` when the reapplication rewrote the series. CSV legs: `imported N row(s) from <path>`. Failures: `<ExceptionType>: <message>`.
76. **Console lines.** `ok     <asset> <provider> <exchange>:<symbol>: <detail>`, up to ten `revised <date> <column>: <stored> -> <served>` lines and a `... N more revised cell(s) in the summary` line, `FAILED <label>: <detail>`, then the wiki's `<legs> leg(s), <failed> failed -> store <store>`.
77. **Page-limit warning.** Fires when the series was empty, the source has no `start`, the collector has a page limit (Binance 1000; EODHD none), and exactly that many bars came back. It is part of the detail and does not fail the leg.
78. **Summary document.** `{schema_version: 1, legs, failed, revised_cells, ok, results: [{asset, provider, exchange, symbol, ok, detail, revised_cells, revisions}]}`, written with `indent=1` (matching the status envelope); the parent directory is created if missing.
79. **Collector construction failure.** A missing `EODHD_API_KEY` is raised when the first EODHD leg asks for its collector, inside that leg's error containment: each EODHD leg fails, other legs still run.
80. **Manual `load` window.** Without `--start`, an established series resumes the day after its latest stored session; a first load is unbounded. Splits come from the stored action file (none are fetched).
81. **NaN-row note scope.** Rows "containing NaN" are counted over every column except `Date` (numeric columns after coercion, extra columns as read), so a row with an unparseable date is reported once, under unparseable dates.

## Command-line surface

82. **Configuration/selection error exit code.** The wiki says these render as `sync: ...` (and are "command errors" for status) but gives no code. Chosen: message on stderr, exit **2** (`sync: `, `status: `, `universe: `, `load: ` prefixes). Argparse usage errors are also 2.
83. **Operational failure exit code.** A store/collector/adjustment failure in a focused command (`sync-actions`, `load`, `adjust`, `import-csv`, `export` with no rows) prints `<command>: <message>` on stderr and exits 1, the same code as a failed verdict.
84. **`--provider` is not an argparse `choices`.** Unknown providers must surface as the runner's `SyncError` (`sync: unknown provider(s): ...`), not as an argparse usage error.
85. **`--asset-type` vocabulary.** `choices` = the sorted store types derived from the class mapping: `crypto, etf, stock` (for `load` and `import-csv`).
86. **Store defaults.** `sync`/`status` default to the universe's `defaults.store`; every other command defaults `--store` to `data`.
87. **Focused-command flag defaults.** `--exchange` defaults to `eodhd` for `sync-actions`, `load`, `adjust`, `export`, and `differential`'s `--a-exchange`/`--b-exchange`; to `yahoo` for `import-csv`. `--currency` defaults to `USD`. `import-csv` requires `--csv`, `--symbol`, `--asset-type`; `export` requires `--symbol`, `--output`; `differential` requires `--a-symbol` and exactly one of `--b-symbol`/`--b-csv`.
88. **Symbol normalization in manual commands.** `sync-actions` and `load` pass `--symbol` through `normalize_symbol()` (bare `AAPL` -> `AAPL.US`); `adjust`, `export`, `import-csv` and `differential` use the symbol verbatim as a store coordinate.
89. **`load` type rules.** Missing `--asset-type` on a non-`.CC` symbol, or a non-crypto type on a `.CC` symbol, is a usage error (exit 2) checked before any collector is built.
90. **Success lines.** Invented: `validate` `<path>: N row(s)` + report; `export` `wrote N row(s) to <path>` + report (exit by `report.ok`); `import-csv` `imported N row(s) into <exchange>:<symbol> (split_adjusted) -> store <store>`; `adjust` `<exchange>:<symbol>: re-derived|unchanged with S split(s)`; `sync-actions` `<exchange>:<symbol>: S split(s), D dividend(s) saved -> store <store>`; `load` `<exchange>:<symbol>: loaded N bar(s) as <type> (<basis>) -> store <store>`.
91. **`universe` output.** Plain text, not JSON: a header `universe <path|(packaged)>: store S, currency C`, one line per asset (`name class -> type currency enabled|disabled [threshold]`), one indented line per source (`provider exchange:symbol [path] [start] [end] [modeled|disabled] # note`). The implicit sole modeled source is shown as `modeled`.
92. **Dry-run plan text.** `<asset> <provider> <exchange>:<symbol>: <action> first fill from <start|the provider's earliest bar> | reconcile tail of N session(s) from <date>, to <end|latest> (pinned end ..; crypto completed-day guard ..)[ - inverted window ...]`, then `dry run: N leg(s) planned, nothing fetched or written -> store <store>`.
93. **`export` of an empty series.** Refused (`export: no stored rows for ...`, exit 1) rather than writing a header-only CSV.
94. **`export` creates the output's parent directory**; `differential --output` does not.

## Chain script

95. **Helper location.** `events.sh` and `dashboard.sh` are sourced from the script's own directory (`$(dirname "${BASH_SOURCE[0]}")`), as instructed; `JEF_APP_DIR` is only the working directory for `data/` and `out/`.
96. **Data command name.** The chain calls `jef-data` (the name the wiki uses), not `jef-data-rc`.
97. **ECS metadata lookup.** Done with `python3` + `urllib` (2 s timeout) only when `JEF_IMAGE_DIGEST` is unset and `ECS_CONTAINER_METADATA_URI_V4` is set; `JEF_TASK_VCPU = Limits.CPU`, `JEF_TASK_MEMORY_GB = Limits.Memory / 1024` (ECS reports MiB), each only if not already set.
98. **Stage bookkeeping.** `STAGE` starts as `unknown`; it becomes `sync`, `status`, `binning` (no separate stage name for the final publication, so a TERM there is reported as `binning`). The TERM trap clears itself, emits `jef_emit <stage> 143 <t0> <now>`, `jef_put <stage>`, then `exit 143`.
99. **Diagnostics paths.** `out/<UTC date>/.diagnostics/{sync,status}.json`; `sync.json`/`status.json` are attached with `jef_attach_if_present`; binning emits once per asset with `--asset <asset>` plus `--attach out/<date>/.diagnostics/<asset>-manifest-keys.json` when a `run_manifest*.json` (first in sorted order) exists in the asset's output directory.
100. **Restore/publish commands.** `aws s3 sync s3://$B/store/ data/ --only-show-errors`; publication `aws s3 sync data/ s3://$B/store/`, `aws s3 sync out/<date>/ s3://$B/runs/<date>/`, then `printf '%s\n' "$JEF_IMAGE_DIGEST" | aws s3 cp - s3://$B/runs/<date>/image_digest.txt`, all with `--only-show-errors`. `data/` and the diagnostics directory are created before the restore. The script prints nothing of its own.
101. **`STORE` and `RUN_DATE`.** Exported as `data` and the UTC date because the given `dashboard.sh`/`events.sh` read them.

## Harness adapter

102. **"No rate limiting in effect".** `make_collector` gives the collector a `RateLimiter(per_minute=10**12, daily_budget=10**15)` and a no-op sleeper for both the limiter and the retry backoff, so a replayed 429/5xx still goes through all five attempts and fails, but instantly.
103. **`actions_state.last_updated`.** Taken from the splits file envelope (the stamp sync and status use); `None` when that file is absent. Splits/dividends are the stored JSON entries verbatim.
104. **`stored_frame`.** `ParquetStore.load()`: every column, rows ascending by `timestamp`, fresh `RangeIndex`; an empty store gives an empty frame with the schema's columns and dtypes.
105. **`status_json` clock.** `now=None` uses the real UTC clock, as the command does; the returned exit code is `1` iff `alerts_total > 0`.
106. **Unreadable inputs.** A CSV `validate`/`differential --b-csv` cannot read, or a store that cannot be opened (no pyarrow), raises out of the command (Python traceback, exit 1) instead of a formatted message.
107. **Read-path partition discovery.** Year files are read one at a time with `pyarrow.parquet.read_table(path, partitioning=None)` so the `exchange=/symbol=/year=` directory names never add columns to `load()`.

## Late additions (found on review)

108. **"Adjusted-close jump" (contradiction).** A claim says status alerts on a recent "adjusted-close jump", while the page says the scan uses the main `close` (the split-adjusted, model-facing close). Chosen: main `close`; the provider `adjusted_close` column (which also moves on dividends) is not scanned.
109. **"Recognized crypto quote" (contradiction).** The example `BTC/USD -> BTC-USD.CC` has a fiat quote, so "crypto quote" cannot be literal. Chosen: a pair is crypto when either side is a known crypto code, checked after the both-fiat FOREX rule (entry 45).
110. **Leg "update order".** The wiki says sync makes "update order explicit" / owns "source-specific ordering" without stating a rule other than actions-before-bars inside a raw EODHD leg. Chosen: legs run in declared order (entry 70); no reordering by provider or modeled flag.
111. **`symbol` on yahoo-csv sources.** Required like every other source ("missing ... symbols" is an error); it is the `yahoo` store coordinate's symbol.
112. **Provider/class combinations.** The parser does not restrict providers by class (e.g. a `binance` source on a `stock` asset parses); policy then follows the rules as written (Binance always split-adjusted, crypto guard only for declared crypto).
113. **Exception hierarchy.** `DailyBudgetExhausted` subclasses `CollectorError`; `TransportConnectionError` does not (it is only the retryable signal inside `get_json`). `UniverseError`, `SyncError`, `ContractError`, `AdjustmentError`, `ClassificationError` subclass `ValueError`; `StoreError` and `CollectorError` subclass `RuntimeError`.
114. **Live transport details.** `HttpTransport` uses a `requests.Session` with a 30 s timeout (not stated); only `requests` `ConnectionError`/`Timeout` become `TransportConnectionError`.
115. **EODHD `search` exchange names.** `EXCHANGE_MAP` content is invented (NASDAQ/NYSE/... -> `US`, LSE, XETRA, ...); unknown names pass through unchanged as the `exchange` parameter.
116. **`modeled` marker in `universe` output for the sole source.** Shown as `[modeled]` even when not declared, because `modeled_source()` would choose it.
117. **Binance kline date.** The UTC date of the kline open time; OHLCV converted with `float()`, `adjusted_close = close`.

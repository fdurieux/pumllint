# Assumptions

Every point where the wiki was silent, ambiguous or contradictory, what was
chosen, and why. One entry each, recorded while building.

## Method

A0. Evidence hashes not used as an oracle. The `.claims` sidecars carry, per
evidence span, base64 JSON with sha256 hashes of the cited source lines
(one hash was checked against `set -euo pipefail`, a line the wiki quotes
verbatim, to understand the format). Brute-forcing guesses against those
hashes would amount to reading the source the task says cannot be opened, so
no source text was recovered that way. Everything below comes from the prose
and the claim statements only.

## Packaging

A1. Dependency pins. The wiki states the metadata declares `pandas`, `numpy`
and `scikit-learn` and gives no version specifiers. Choice: exactly those
three, unpinned. `pyarrow` and `requests` are deliberately not declared (the
wiki says the environment must supply them); they are imported lazily, as the
wiki describes (`ParquetStore` imports pyarrow, `HttpTransport` imports
requests on construction).

A2. Module layout. The wiki describes `src/jef/data/{__init__,__main__,actions,
adjust,classification,cli,contract,differential,health,store,sync,universe}.py`,
`collectors/{base,eodhd,binance}.py`, and packaged `universe.toml` and
`classifications.toml`. Choice: the same layout as a flat package
`src/jef_data_rc/...` (src layout, as in the original's `pyproject`).
Console script `jef-data-rc = jef_data_rc.cli:main`; `python -m jef_data_rc`
calls the same `main()`.

A3. Build backend. Not stated. Choice: setuptools with `package-data` for the
two TOML files.

A4. `import jef_data_rc` and pyarrow. The wiki says importing the package
root does not import pyarrow or requests. The package root imports only the
contract module (pandas, numpy). In this venv pandas 3 itself imports
pyarrow when it is installed, which the package cannot prevent; requests is
never imported at package import.

A5. Command name inside message text. The one verbatim status message,
`never filled - no stored rows (jef-data sync first)`, is reproduced byte for
byte, including `jef-data`, even though this build's console script is
`jef-data-rc`.

## Universe grammar

A6. Top-level keys. Only `[defaults]` and `[[asset]]` are accepted (the wiki
lists no others); anything else is an unknown-key error.

A7. `threshold`. The wiki says it must be numeric and is carried as a float
for display. It does not say whether it is required. Choice: optional,
default `None`; booleans are rejected as non-numeric.

A8. Flag defaults. Not stated. Choice: asset `enabled = true`, source
`enabled = true`, `modeled = false`, `kind = "eod"`, `exchange` = provider
default tag (`eodhd`, `binance`, `yahoo`).

A9. Source currency. Sources have no `currency` key in the documented list;
the normalized source's currency is the asset's resolved currency (asset
`currency` or `defaults.currency`).

A10. Dates. `start`/`end` accept a TOML date or a `YYYY-MM-DD` string and
normalize to an ISO string; a TOML datetime is rejected as an invalid date.

A11. Canonical EODHD symbol. "Must already be canonical TICKER.EXCHANGE".
Choice: regex `^[^.\s]+\.[A-Za-z0-9]+$` (exactly one dot-separated suffix).

A12. Duplicate store coordinates. The wiki says a coordinate "claimed by more
than one asset" is an error and elsewhere "duplicate store coordinates".
Choice: any repeated `(exchange, symbol)` is an error, within one asset or
across assets.

A13. Modeled rules on disabled assets. Choice: "disabled source marked
modeled" and "more than one enabled modeled source" apply to every asset;
"no enabled source" and "several enabled sources but no modeled marker"
apply only to enabled assets, as the wiki words them.

A14. Error wording. `UniverseError` texts are not given; they name the
location as `asset[i] 'NAME' source[j]: ...`.

A15. Packaged `universe.toml` contents. The wiki names the six assets, that
AAPL and BTC have a modeled EODHD source plus snapshot/cross-check sources,
that BTC's Binance source has `start = 2017-08-01`, and the CSV path
`experiments/AAPL.csv` appears in an import example. Choice: AAPL = EODHD
`AAPL.US` (modeled) + enabled `yahoo-csv` `AAPL` at `experiments/AAPL.csv`;
BTC (crypto) = EODHD `BTC-USD.CC` (modeled) + Binance `BTCUSDT` from
2017-08-01; TLT (`bond_etf`) and NVDA, TSLA, IBM (`stock`) one EODHD `.US`
source each. No thresholds and no EODHD `start` values, since none are
documented.

A16. `universe` command output. "Prints the normalized configured assets and
sources" with no format given. Choice: a plain text listing, one line per
asset (class, type, currency, modeled coordinate) and one indented line per
source, plus a count line.

## Selection and sync

A17. Leg dict keys. The wiki says a leg carries the asset name, provider,
store coordinate, declared asset_type, currency and start/end, and an
`actions` flag. Choice: exactly `asset, provider, exchange, symbol,
asset_type, currency, start, end, path, actions` (`path` is needed by the
CSV branch; it is None for collector legs). No `price_basis` key: basis is
derived per leg at run time.

A18. Unknown provider filter. Choice: unknown means outside the supported
vocabulary (`eodhd`, `binance`, `yahoo-csv`), not "absent from this
universe". Naming a disabled asset is not "unknown"; it just contributes no
legs, and an empty result is the "no enabled legs" error.

A19. Validation order. `tail < 1` is checked before leg selection. Both are
`SyncError`.

A20. Config/selection error exit code. The wiki says errors print as
`sync: ...` (and `status` likewise); it gives no code. Choice: the message
goes to stderr and the exit code is 2 (argparse usage convention), keeping
1 for "a leg failed" and "alerts".

A21. Inverted window scope. The wiki describes the no-fetch inverted case
for an established series. Choice: only established series are checked; a
first fill whose start exceeds the crypto guard still requests.

A22. Crypto guard date. "Previous completed UTC day" = `now(UTC).date() - 1`.
It is combined with a configured `end` by taking the earlier date.

A23. Action refresh freshness. Refresh when the split file's `last_updated`
is absent or unparseable, its UTC date is before today's UTC date, or
`--force-actions`. The window is computed first and actions are refreshed
before any bar request (flowchart order); refresh happens even when the
window then turns out inverted.

A24. Action fetch bounds. `sync_actions()` calls `/splits/{symbol}` and
`/div/{symbol}` with no `from`/`to` (full history), fetching both before
writing either file.

A25. `last_updated` format. Not given. Choice: `now.astimezone(UTC).isoformat()`,
e.g. `2026-10-28T12:00:00+00:00`, written to both action files.

A26. Page-limit warning. "When an empty series with no declared start
receives exactly a collector's page limit". Only Binance has a page limit
(`limit`, default 1000); EODHD's single request has none, so the warning
can only fire for Binance. It is added to the leg's detail text.

A27. Leg outcome text. Only the shapes `FAILED`, `actions fresh`,
`sync-actions + load` vs `load`, and `<legs> leg(s), <failed> failed ->
store ...` are documented. Choice: the totals line is exactly
`{n} leg(s), {failed} failed -> store {store}`; per-leg lines are
`ok     ASSET provider exchange/symbol: N row(s), R revision(s)[; detail]`,
`FAILED ASSET provider exchange/symbol: ExcType: message`, at most ten
`       revised DATE COLUMN: stored -> served` lines, then `... K more
revision(s)`. Details: `actions fresh`, `actions refreshed (S split(s), D
dividend(s))`, the inverted-window text, the page-limit warning,
`re-derived from raw` when reapplication changed the store. CSV legs report
`imported N row(s) from PATH`. The count is bars fetched (collector) or
rows imported (CSV).

A28. Dry-run output and result. The plan action is chosen by eligibility
(`sync-actions + load` for raw EODHD legs, `load` otherwise), not by today's
freshness stamp. Lines are `plan   ASSET provider exchange/symbol: ...`,
followed by `dry run: N leg(s) planned, nothing fetched or written -> store
S` (the documented totals line belongs to the execution loop, which a dry
run never reaches). `run_sync` returns one ok `LegResult` per leg with the
plan text as detail, and `ok = True`.

A29. Result object. Per-leg results are `LegResult(leg, ok, detail, rows,
revisions)`; `detail` is one string, with parts joined by `; `.

A30. Summary JSON keys. The wiki lists the contents (schema version, total
and failed leg counts, total revised cells, aggregate ok, per-leg identity,
success, detail, revised-cell count, all revisions) but not the key names.
Choice: `schema_version` (1), `ok`, `legs_total`, `legs_failed`,
`revised_cells_total`, `legs` [ {`asset`, `provider`, `exchange`, `symbol`,
`ok`, `detail`, `rows`, `revised_cells`, `revisions`} ]. Non-finite floats
become null. Written with `indent=1`, parents created, also for a red run
and for a dry run.

A31. Revision record keys. "date, column, stored value, and served value".
Choice: `{"date": "YYYY-MM-DD", "column": <identity column>, "stored": float,
"served": float}`, ordered by date then by the identity-column order
`open_raw, high_raw, low_raw, close_raw, volume_raw, adjusted_close`.
Equality is exact float equality with NaN == NaN.

A32. Leg failure containment covers every `Exception` raised by a leg,
including collector construction (missing `EODHD_API_KEY`) and
`DailyBudgetExhausted`.

## Store

A33. Column order and `asset_subtype`. The ER diagram lists the columns
without `asset_subtype`, which the prose adds as part of classification.
Choice: order `timestamp, datetime, open, high, low, close, volume, symbol,
exchange, asset_type, asset_subtype, open_raw, high_raw, low_raw, close_raw,
volume_raw, adjusted_close, adjustment_factor, cumulative_split_factor,
currency, price_basis`. No source of a subtype value is documented, so it
is null for every ingest path.

A34. Physical types. Not given. Choice: `timestamp` int64 Unix ms at UTC
midnight of the session date. `datetime` is
`pd.to_datetime(timestamp, unit="ms", utc=True)`; under this venv's pandas 3
that is `datetime64[ms, UTC]` (no unit is forced, so the frame keeps what
pandas infers). Numeric fields are float64 and text fields are strings.
Arrow types are inferred, except that an all-null column (`asset_subtype`)
is cast to string so it does not land as the null type.

A35. Symbol directory naming. The wiki mentions `/` -> `_` only for action
filenames, so market-data paths use the symbol verbatim.

A36. Row construction. Main and raw values come from the bar dict;
`adjusted_close` falls back to `close` when absent or null;
`adjustment_factor = adjusted_close / close_raw`. Raw basis: if the
collector's volume basis is `split_adjusted`, `volume_raw = served volume /
factor(date)`, then `adjust()` derives the main fields. Split-adjusted
basis: main = raw = served, factor 1.0.

A37. Reconcile write scope. Reconciliation rewrites the year partitions that
hold replaced or new rows. On an empty series it writes all served rows and
reports no revisions. A replaced row takes the whole served row, including
the newly declared `asset_type`/`price_basis` (the comparison itself never
looks at them). An empty bar list returns at once, without taking the lock.

A38. Append semantics. Existing rows go first, then a stable sort by
timestamp, keeping the first row per timestamp; only years present in the
incoming frame are rewritten. Overwrite writes every new year file and
then removes year directories absent from the new frame.

A39. Lock. `{symbol_dir}/.lock` is created on demand (which creates the
symbol directory). `LOCK_EX|LOCK_NB` is polled every 0.5 s until
`lock_timeout` (300 s) on the injected monotonic clock, then `StoreError`
`timed out after Ns waiting for the writer lock on EX/SYM`. Leftover
`data.parquet.tmp` files are swept at the start of each locked write.

A40. Yahoo import. Each value goes through `float()`, so a non-numeric cell
raises (pandas already reads `null` as NaN, which converts). The date is
the first ten characters as an ISO date. The default mode is overwrite.
The reported count is the number of rows landed after timestamp
de-duplication; it equals the CSV row count when dates are unique.

A41. Yahoo path resolution. A `yahoo-csv` `path` is used as given, so a
relative path resolves against the current working directory.

A42. `adjust()` input checks. It requires `datetime` and the five `*_raw`
columns. A `price_basis` column is checked when present: any non-`raw` or
null value is refused. Row dates are UTC dates of `datetime`, compared to
split dates as ISO strings. Factors are multiplied in ascending split-date
order.

A43. Export frame. `Date` is a `YYYY-MM-DD` string column (not datetime64).
Prices are float64. `Volume` is int64 when every value is finite and
integral (an empty frame counts as integral), otherwise float64.

## Corporate actions

A44. Split JSON entry shape: `{"date", "ratio", "split"}` (ER diagram). The
envelope key order is `symbol, exchange, last_updated, splits|dividends`,
written with `indent=2`. The envelope `exchange` is the leg's exchange tag.
The ratio is parsed from the provider `split` string `NEW/OLD` as
float(NEW)/float(OLD). Dividend entries are stored exactly as the provider
returned them, date-sorted.

A45. `actions_state.last_updated` is the split file's stamp; the splits and
dividends lists are the stored entries verbatim.

## Collectors

A46. Base URLs. `https://eodhd.com/api` (paths `/api/eod/...`,
`/api/splits/...`, `/api/div/...`, `/api/search/...`) and
`https://api.binance.com` (`/api/v3/klines`). Because replay keys use the
URL path, these prefixes matter; they are the providers' public hosts.

A47. EODHD params. `get_eod` always sends `order=a`, `period=d` and
`fmt=json`, plus `from`/`to` only when set; `api_token` is always sent and
never part of the key. Splits/dividends send `fmt` (+ optional bounds).

A48. Binance params and pagination. Always `symbol`, `interval=1d`,
`limit`; `startTime` = UTC-midnight ms of start (omitted when no start);
`endTime` = last ms of the end date (omitted when no end). The next page
starts at last open time + 86 400 000 ms. It stops on a short page or
when the next cursor would pass `endTime`.

A49. Fixture file shape. The wiki: a public `request` identity
(uppercased method, URL path, sorted string params without `api_token`) and
a `response` with `status` and the JSON body. Choice when writing:
`{"request": {"method", "path", "params"}, "response": {"status", "json"}}`,
named `<path-slug>-<sha256[:12]>.json`. When replaying, the identity is
also accepted with `url` in place of `path`, or as a `"GET /path?query"`
string, and the body under `json`, `body` or `data`. That tolerance is
there because the harness's fixtures come from the original's recorder,
whose exact key names the wiki does not give.

A50. Replay strictness. An unknown request raises `CollectorError` naming
the request and the known keys; there is no fuzzy fallback.

A51. Exception hierarchy. `DailyBudgetExhausted` subclasses
`CollectorError`; `TransportConnectionError` is a separate retryable
exception, not a `CollectorError`.

A52. Error texts. Not given. They are: `GET PATH: network failure after N
attempt(s): ...`, `GET PATH: HTTP S after N attempt(s)`, `GET PATH: HTTP S:
<redacted body[:200]>`, `GET PATH: invalid JSON in response: ...`, `daily
request budget of B exhausted for DATE (UTC)`, `pagination exceeded 100
pages; ...`. Secrets are redacted as `***`. The backoff before retry k
(0-based) is `backoff * 2**k`.

A53. Rate limiter with a frozen fake clock. If, after the computed sleep,
the window is still full (an injected clock that did not advance), the
oldest entries are evicted so `acquire()` cannot loop forever.

A54. `normalize_symbol` vocabularies. Not given. Choice: a fixed fiat set
(USD, EUR, GBP, JPY, CHF, CAD, AUD, NZD, ...) and crypto set (BTC, ETH,
USDT, USDC, ...). fiat/fiat -> `BASEQUOTE.FOREX`; a crypto base or quote ->
`BASE-QUOTE.CC`; else refused. `EXCHANGE_MAP` contents for `search` are
likewise a guess.

A55. Volume-basis constants. EODHD `split_adjusted` (stated). Binance is
not stated; choice `raw`. It is never consulted, because Binance legs are
stored pre-adjusted.

A56. EODHD row filtering. A row without `date` raises `CollectorError`. A
null or non-numeric `close` counts as non-positive and is dropped, and so is
a NaN close for Binance.

A57. Harness collectors. `make_collector` injects a `ReplayTransport`, a
`RateLimiter` with effectively unlimited budgets, and no-op sleeps for both
limiter and retry backoff. Results are unchanged; only wall time differs.

## Health / status

A58. Report shape. Keys in order `asset, exchange, symbol, alerts, warnings,
notes`, then `declared_class_check` (EODHD only, computed before the
never-filled return), then `last_session, missed_sessions, rows` and the
optional `resolution`. There is no `provider` key (the wiki does not list
one).

A59. `declared_class_check` value. Shape not given. Choice:
`{"verdict", "declared", "vendor_type", "mapped"}`.

A60. `resolution` value. Shape not given. Choice: `{"basis":
"close_raw"|"close", "sessions", "distinct", "distinct_ratio", "min_step",
"flat_share"}`, where `min_step` is the smallest (u[i+1]-u[i])/u[i] over
sorted distinct closes (null when only one) and `flat_share` = equal
adjacent closes / (n-1).

A61. Finding order. Alerts: stale, phantom jump(s), action freshness.
Notes: class verdict, today-dated, zero-volume, post-seam gap, resolution.
This follows the cited health.py line ranges (staleness, then the
measurement notes, then jumps and action freshness).

A62. Jump return. `(close[i] - close[i-1]) / close[i-1]` (pct_change form),
over adjacent pairs inside the newest `--window` rows only (window rows give
window-1 returns), strictly greater than the threshold. Suppressed when a
saved split has that row's date. Split dates are read for every leg (absent
file = none).

A63. Action-freshness count. Missed refresh sessions = expected sessions
strictly between the stamp's UTC date and today, with the leg's calendar.
The alert fires at >= `actions_missed_k` (2). A missing or unparseable stamp
always alerts.

A64. Post-seam gap. Measured only between adjacent survivor rows (volume > 0,
non-null close), not from the last survivor to today; noted at >= `gap_k`.
The weekday count uses `numpy.busday_count` over the open interval.

A65. Zero-volume note. Fires on any zero-volume row; the run length and
span are added only when the longest consecutive run exceeds one row.

A66. Resolution input. Rows with volume > 0. `close_raw` values that are
finite and > 0 are used when there is at least one; otherwise main `close`
filtered the same way. The newest `--resolution-window` values are kept,
and nothing is measured below 60.

A67. Cross-venue details. Pairs are `itertools.combinations` of the
asset's live legs in declaration order. Labels `a`/`b` are
`exchange/symbol`. A pair with an empty frame gets a note naming the empty
side(s). The common date is the max of the intersection of the two frames'
newest-`window` dates. The spread is `abs(a-b)/((a+b)/2)` on main `close`.
`threshold` echoes the option value. The measured-spread note is always
added before the breach finding.

A68. Finding texts. Apart from the never-filled message none are given.
All the alert, warning and note sentences (stale, today-dated, jump,
actions, zero-volume, seam, resolution, class verdicts, spread) are this
build's own wording. The stale text mentions verifying a multi-day holiday,
and the no-evidence text asks for evidence to be recorded, as the wiki
describes.

A69. Status JSON formatting. The wiki's example envelope is indented by one
space, so `json.dumps(envelope, indent=1)`. `store` is `str(Path(store))`.

A70. Status text format. Not given beyond its contents. One head line per
report (`ALERT`/`WARN`/`ok` lead label, asset, coordinate, `last`,
`missed`, `rows` or `no rows`), an indented resolution line, then indented
`ALERT:`/`WARN:`/`note:` lines. Pairs follow, then `N source(s)[, P venue
pair(s)]: A alert(s), W warning(s)`, preceded by a `store:` line.

A71. Status with only CSV legs selected. Not covered. Choice: an empty
report list and exit 0 (the selection itself was non-empty).

A72. Malformed classification evidence. It is not caught, so the command
exits through an uncaught `ClassificationError` (traceback, exit 1), as the
wiki says it fails loudly.

## Classification evidence

A73. Evidence file grammar. Top-level `schema` (must be 1) and
`[[instrument]]`. Instrument keys: required `exchange, symbol, code,
query_exchange, vendor_type`; optional `isin, name, last_verified` (a date).
The array name `instrument` follows the wiki's "instrument fields".

A74. Packaged evidence content. The wiki does not list it. Choice: entries
for the six packaged EODHD coordinates: `Common Stock` for AAPL, NVDA,
TSLA, IBM; `ETF` for TLT; `Currency` for BTC-USD.CC, with public ISINs.
Any other symbol gets `no_evidence`.

## Contract, export, differential

A75. Contract message texts and render format (`ERROR: ...`, `note: ...`,
`contract: ok` / `contract: FAILED (n error(s))`) are this build's own. The
`validate` command prints `PATH: N row(s)` and then the report.

A76. Contract details. "Newly coerced non-numeric" = non-null before
`pd.to_numeric(errors="coerce")` and NaN after. Dates are parsed with
`pd.to_datetime(errors="coerce")`. "No parseable dates" is an error only for
a non-empty frame. The unsorted check uses parseable dates. NaN rows are
counted over the six numeric columns plus extra columns. Clean rows have a
parseable date, no NaN and non-zero volume.

A77. `validate` unreadable file: `validate: <error>` on stderr, exit 2.

A78. `export`. `--output` is required. An empty series prints `export: no
stored rows ...` on stderr and exits 1. Otherwise it prints `wrote N row(s)
to PATH`, then the contract report, and exits 1 only on contract errors.
The help text names `jef.binning.loading.load_eod_store` as the bit-exact
consumer path.

A79. Differential default tolerance. Not stated (the examples pass `1e-4`
explicitly). Choice: `1e-6`.

A80. Differential alignment. Both `Date` columns are normalized through
`pd.to_datetime` to `YYYY-MM-DD`, falling back to the raw text when
unparseable. The first row wins on a duplicate date. A column missing on
either side counts as failing. The report text and its `--output` handling
(write the file, print only the verdict line) are this build's own.

## Other commands

A81. `sync-actions` flags: `--symbol` (required), `--exchange eodhd`,
`--store data`. A missing key exits 1.

A82. `load` flags: `--symbol` (required, passed through
`normalize_symbol`), `--asset-type {crypto,etf,stock}`, `--start`, `--end`,
`--exchange eodhd`, `--currency USD`, `--store data`. Asset-type refusals
exit 2. A missing key or a fetch failure exits 1. Saved splits are used
without fetching, and a raw-basis load without saved actions prints a
stderr hint. The load appends, then re-derives a raw-basis series.

A83. `adjust` with no stored rows exits 1. A refusal on a pre-adjusted
series prints `adjust: ...` and exits 1.

A84. `import-csv` flags: `--csv`, `--symbol`, `--asset-type` (all required),
`--exchange yahoo`, `--currency USD`, `--store data`. Any import failure
exits 1.

A85. Default `--store` for the focused commands (`sync-actions`, `load`,
`adjust`, `import-csv`, `export`, `differential`) is `data`. `sync` and
`status` default to the universe's `defaults.store`.

## Chain script

A86. Helper location and working directory. `events.sh` and `dashboard.sh`
are sourced from the script's own directory. The inner chain `cd`s into
`JEF_APP_DIR` (default `/app`), so `data/`, `out/` and the dashboard
helper's relative `dashboard/index.html` resolve there. The data command is
invoked as `jef-data`, the name the wiki gives.

A87. ECS metadata fetch. The wiki says one best-effort request; it does not
say which tool makes it. Choice: `python3` urllib with a 2 s timeout, done
only when `JEF_IMAGE_DIGEST` is unset and `ECS_CONTAINER_METADATA_URI_V4` is
set. `JEF_TASK_VCPU` = `Limits.CPU`, and `JEF_TASK_MEMORY_GB` =
`Limits.Memory / 1024` (ECS reports MiB). Each is set only when not already
supplied.

A88. Restore and publish flags. Every `aws s3` command passes
`--only-show-errors`; there is no `--delete`. The image digest is uploaded
from stdin (`aws s3 cp -`).

A89. Stage telemetry wiring. The sync and status events attach their JSON
through `jef_attach_if_present`. Binning emits one event per asset with
`--asset NAME`, plus `--attach` of a keys file when a `run_manifest*.json`
exists under that asset's output dir (first match, sorted; keys file at
`out/<date>/.diagnostics/binning-<asset>-keys.json`). One `jef_put binning`
runs after the loop.

A90. `STAGE` values. Only `sync`, `status` and `binning` are assigned, as the
wiki names those stages. A TERM during restore reports `unknown`, and a TERM
during publication reports the last stage (`binning`). The TERM event's
`t0` is the current stage start (or now when unset).

A91. Diagnostics directory. `out/<UTC-date>/.diagnostics` is created by the
script before sync, so `tee` and the summary writer have a target.

A92. Gate messages. The script echoes one stderr line when a stage stops
the chain. That wording is this build's own; the exit code is the stage's
real code.

## Process

A93. Test scratch location. The build was exercised with synthetic stores,
replay fixtures and chain stubs that I wrote myself, kept in
`wr-W2/scratch/` (outside `out/`, so they are not part of the deliverable).
The few of those self-made files I displayed are listed in READ.log. No
file outside the wiki and `out/` other than my own test artifacts was read.

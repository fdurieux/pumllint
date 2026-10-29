# Assumptions made while rebuilding `jef-data` as `jef_data_rc` / `jef-data-rc`

One entry per point where the kit was silent, ambiguous or contradictory:
what I chose and why. Numbered in the order they were met.

## A-01 Package and module path in traceback lines
The kit names the original package `jef` / module `jef.data.*`; the brief
requires the package `jef_data_rc`. Unwrapped errors therefore end in
`jef_data_rc.<module>.<ErrorClass>: <message>` instead of
`jef.data.<module>.<ErrorClass>: ...`. The suite only checks the line
suffix (`ErrorClass: message`), so this is the only visible difference.
Module layout mirrors `uml/component.puml`: `cli`, `universe`, `sync`,
`health`, `classification`, `actions`, `adjust`, `store`, `contract`,
`differential`, `collectors.base` / `collectors.eodhd` /
`collectors.binance`, plus `collectors.transport` for the three transports.

## A-02 Console script name versus parser prog
The console script is `jef-data-rc` (brief), but `prog` is set explicitly
to `jef-data` (cli.md "Parser surface"), so usage, help and error lines
read `jef-data ...` exactly as the contract prints them. Package version is
the pinned `0.6.0`.

## A-03 Chain invokes `jef-data`, not `jef-data-rc`
chain.md names the data command `jef-data` and the chain scenarios stub
exactly that name, so `daily-rc.sh` calls `jef-data`. A venue running this
rebuild must expose `jef-data-rc` under that name (e.g. a symlink).

## A-04 Installing without network
`pip install -e out` with default build isolation would fetch setuptools
from an index. The kit forbids nothing here but the brief forbids the
network, so I install with `pip install --no-build-isolation -e out`
(setuptools is already in the provided venv). The pyproject declares
`setuptools>=61` as its build backend and exactly the four runtime pins.

## A-05 Kit statement on the transport return shape versus glossary/component diagram
CHANGES.md (F-008) says the transport returns a `TransportResponse` object;
the glossary and `uml/component.puml` still write `(status, text)`. Built the
object (`status`, `text`, `json()`), per the precedence rule (requirements
over glossary/diagrams). Reported as a residual inconsistency in the kit.

## A-06 `adjusted_close` fallback is per bar
store.md §4 / JDL-056: "the bar's adjusted_close when the bar carries that
key, else its close". Implemented per bar (a bar without the key falls back
to its own close) rather than per frame (which would give NaN for a missing
key in a mixed list). No fixture mixes the two.

## A-07 Stored split ratios are read with `float()`
JDL-041 says `ratio` is read from the file. I convert it with `float()`,
so a hand-written integer ratio `0` renders as `0.0` in the degenerate-ratio
message. The suite's fixtures always write floats.

## A-08 Error body redaction order
collectors.md gives `{body[:200], token as ***}`: I slice the first 200
characters, then replace the token. A token straddling character 200 would
leave a partial token; the kit does not order the two operations.

## A-09 Non-list `/splits/` or `/div/` answers
Only the `/eod/` and klines non-list refusals are specified. A non-list
splits or dividends answer raises `CollectorError: splits {SYM}: expected a
JSON list` / `div {SYM}: expected a JSON list` (same pattern), failing the leg.

## A-10 Replay walk order of subdirectories
fixtures.md §4 says "os.walk order; inside one directory, files in sorted
name order". `os.walk` leaves subdirectory order to the file system, so I sort
subdirectories too (deterministic). Only matters when two files in different
directories carry an equal key; no kit fixture set does.

## A-11 Where the lock is taken relative to row building
store.feature requires that a refused import (unparseable dates, missing
columns) leaves the store with no files at all, so the `.lock` file must not
be created before the rows are built. I build (parse, raw-ize, validate split
ratios) before taking the lock for reconcile, append and overwrite. The
re-adjustment reads under the lock as store.md §6 says, so `adjust` on an
absent series creates the symbol directory and `.lock` before raising
`StoreError: nothing stored for ...` (no scenario checks files there).

## A-12 Collector construction per leg and on failure
JDL-102: "a failed EODHD construction (no key) fails each eodhd leg in turn".
The pool retries construction for each eodhd leg (none is cached on failure);
the collector is obtained at the start of each collector leg, before the
actions gate. Injected collectors are never closed by the sync; constructed
ones are closed after the last leg.

## A-13 Today-dated check uses the date text of the newest bar
JDL-098 "the newest fetched bar is dated today": compared on the first ten
characters of the last bar's `date` string after the collector's ascending
sort.

## A-14 Export validates the in-memory frame
cli.md: "prints ... then the validation report of the frame". seam_frame.md
§4 says "on the frame it just wrote". I validate the frame in memory (the
CSV round trip yields the same values for every kit fixture) with the
default minimum of 1115 rows.

## A-15 Differential details the kit leaves open
* The `--b-csv`/`--b-symbol` refusal is checked before either side is read,
  so an absent A side with neither flag gets the wrapped refusal, not the
  traceback.
* Duplicate dates inside one side: the first row per Date (after a stable
  sort by Date) is compared; `rows:` still counts every row.
* "first 5 sorted, comma-separated" is joined with `", "`.
* With no common dates the within-tolerance line prints `max 0.000%`.

## A-16 Validation details
* Unparseable dates are counted as every NaT after
  `pd.to_datetime(errors="coerce")`, empty Date cells included.
* "no parseable dates" is also the result for a zero-row CSV.
* The NaN-row note counts rows with NaN in Date (raw) or in any of the six
  numeric columns after coercion.
* pandas' "Could not infer format" UserWarning is left to reach stderr; the
  kit never pins stderr for `validate`.

## A-17 Chain: set-if-unset treats empty as unset
chain.md says JEF_TASK_VCPU / JEF_TASK_MEMORY_GB are set "only if unset"; an
empty value is treated like an unset one (as JEF_IMAGE_DIGEST and
JEF_RUN_STAMP are, "empty/unset"). Both are exported only when the size parse
succeeds, so a failed parse leaves them unset (the scenario checks
`<unset>`).

## A-18 Chain: "first run_manifest*.json"
Found with `find DIR -maxdepth 1 -name 'run_manifest*.json' -print -quit`
(directory order, the first match find prints); `find` is in chain.md's list
of external commands and `sort`/`head` are not. An absent output directory
yields no manifest.

## A-19 Chain: JEF_ASSETS splitting
`read -r -a` on `${JEF_ASSETS:-AAPL BTC TLT NVDA TSLA IBM}`: whitespace
splitting on the first line, no glob expansion; an empty JEF_ASSETS falls
back to the default list.

## A-20 Binance start/end given as a TOML date-time
The universe may carry a date-time start (`2024-01-01T10:00:00+00:00`);
collectors.md converts "the start date at 00:00 UTC", so the collector uses
the first ten characters (the date) of whatever text it is given.

## A-21 Resolution and window knobs at zero
`--resolution-window 0` measures nothing (empty tail, then the `close`
fallback is empty too, so no resolution); `--window 0` scans no jumps and
finds no common session. The kit does not define zero windows.

## A-22 sync-actions stores under the symbol as given
cli.md `sync-actions` does not say the symbol is normalised for the file
name; the collector normalises it for the request, the actions files are
written under `--symbol` exactly as typed (the printed line uses it too).
`load` reads splits under the normalised symbol, as cli.md step 5 implies.

## A-23 Text of a transport connection failure
collectors.md: connection errors and timeouts become a retryable
TransportConnectionError "(token redacted)", and the final CollectorError
reads `{label}: network failure after 5 attempts: {error}`. The text of
`{error}` is not given; mine is `{requests exception class}: {its message}`
with the API key replaced by `***`. Not reachable from the suite (replay
never raises it).

## A-24 Store method signatures carry the labels
`uml/data_model.puml` draws `reconcile_bars(exchange, symbol, bars, splits,
price_basis, volume_basis)` and `ingest_bars(..., mode)` without the
asset_type and currency every stored row is labelled with (JDL-062). I add
them as keyword arguments (`asset_type=`, `currency=`); the diagram never
decides behaviour (precedence rule 5).

## A-25 Hand-run `load` has no crypto end-guard
cli.md `load` sets end = `--to` and nothing else; the end-guard (JDL-094) is
described for sync legs only, so a hand-run load of a .CC symbol without
`--to` fetches open-ended (the provider may serve the in-progress day).

## A-26 Lock file mode
`.lock` is created with `os.open(..., 0o644)`, so the effective mode is
0644 minus the process umask (0644 under the usual 022).

## A-27 Pruned year directories
A prune deletes the stale `year=YYYY/data.parquet` file and leaves the empty
`year=YYYY` directory; store.md only speaks of files, and readers glob
`year=*/data.parquet`, so an empty directory is invisible to every read.

## A-28 Small kit inconsistencies noticed (no behavioural choice needed)
* README "Reading order" numbers its items 1, 2, 5, 3, 4.
* refusals.md lists X-11 before X-10.
* glossary/component diagram transport signature, see A-05.
* store.md §3 documents `timestamp` as milliseconds-intended while every
  requirement and fixture has Unix seconds; built seconds (JDL-060).

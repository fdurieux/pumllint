# Assumptions

Every point where the kit was silent, ambiguous or contradictory, what the
rebuild does, and why. One entry each, numbered in the order they were met.

## A-01 Session instant: UTC midnight, not America/New_York (contradiction)

JDL-060, store.md §3/§4 and seam_frame.md §3 say a date-only bar date is the
day's 00:00 America/New_York (2024-01-02 -> timestamp 1704171600, datetime
05:00 UTC). The acceptance suite (adjustment.feature, collectors.feature and
every `fixtures/expected/*_stored.json`) records 00:00 UTC (2024-01-02 ->
1704153600, `2024-01-02T00:00:00+00:00`), and `uml/basis_and_adjustment.puml`
also says "parse each bar date at 00:00 UTC". Under the kit's precedence the
suite wins: bar dates are parsed as UTC instants. A date with a time of day
keeps it, read as UTC (store.md's 10:30 New York example -> 1704209400 is
therefore not reproduced; it would be 1704191400). Reported as a kit defect.

## A-02 `timestamp` unit

Computed as the microsecond-resolution epoch integer-divided by 10^6
(whole seconds), as store.md's timestamp note describes, whatever unit pandas
parsed at.

## A-03 Module layout

The component diagram names the modules `cli`, `universe`, `sync`, `health`,
`classification`, `actions`, `adjust`, `store`, `contract`, `differential`,
`collectors.base`, `collectors.eodhd`, `collectors.binance`; the package uses
exactly those under `jef_data_rc`. The diagram draws `HttpTransport`,
`ReplayTransport` (and the data model `RecordingTransport`) without a module
name; they live in `jef_data_rc.collectors.transport`. The two packaged TOML
files sit in the package root.

## A-04 Exception module paths in tracebacks

Tracebacks name `jef_data_rc.<module>.<Error>` where the original printed
`jef.data.<module>.<Error>`; the suite only checks the line's ending.

## A-05 A non-string `kind`

JDL-016's string check does not list `kind`; any `kind` value other than
`"eod"` (a non-string included) gets the U-16 "is not supported" refusal.

## A-06 Store-coordinate uniqueness counts disabled entries

JDL-021 says "declare"; the duplicate-coordinate check runs over every
source of every asset, enabled or not, in file order (first owner = the
earlier asset).

## A-07 Empty filter lists

An empty `assets`/`providers` list behaves like no filter (the CLI never
produces one; argparse gives None).

## A-08 Date-time `start`/`end` reaching a collector

A TOML date-time window bound is carried as full ISO text (JDL-008). EODHD
receives that text verbatim as `from`/`to`; Binance converts it through its
date part (first 10 characters) to the 00:00 UTC millisecond bound. The
inverted-window and end-guard minimum compare the texts as strings.

## A-09 Non-list `/splits/` and `/div/` answers

Only `/eod/` and klines have a specified "expected a JSON list" refusal. The
same shape is used for the other two: `splits {SYM}: expected a JSON list`,
`div {SYM}: expected a JSON list` (CollectorError, fails the leg).

## A-10 Order of truncation and redaction in error bodies

`{label}: HTTP {status}: ...` and `response is not JSON: ...` take the first
200 characters of the body and then replace the token with `***`
(collectors.md writes the template as `{text[:200]}`).

## A-11 `sync-actions` stores under the normalised symbol

The collector normalises the symbol before every call (collectors.md §2);
the actions files are written under that normalised symbol too, so a later
`adjust --symbol AAPL.US` finds them. The printed line keeps `S` as given.

## A-12 A failed collector construction is cached for the run

"At most once per provider per run" and "fails each eodhd leg in turn" are
reconciled by constructing once, lazily at the first leg needing the
provider, and re-raising the same ValueError for every later eodhd leg.

## A-13 Zero served bars

A reconcile handed no bars returns `(0, [])` without taking the lock, so an
empty first fill creates no `.lock` file or directory.

## A-14 Rows are built before the lock is taken

Date parsing, ratio validation and volume raw-ization run before the series
lock is acquired, so a refused import or reconcile (unparseable dates,
degenerate ratio) leaves no `.lock` or directory behind; the suite's
"store holds exactly the files" checks after `import-csv` refusals require
that for imports.

## A-15 `adjust` on an absent series

The StoreError `nothing stored for ...` is raised before the lock is taken
(no directory or `.lock` is created for a series that does not exist), and
re-checked under the lock.

## A-16 `differential` checks the B arguments first

With neither `--b-csv` nor `--b-symbol` the wrapped refusal is printed
before the A series is read, so an absent A with no B side refuses rather
than raising the X-11 traceback.

## A-17 Differential "only in" separator and empty overlap

The first five unmatched dates are joined with `", "`. With no common
date every column prints `within tolerance (max 0.000%)`.

## A-18 Status reads the main `volume` column

"rows with volume > 0" / "volume exactly 0" (JDL-118, JDL-120, JDL-122) are
evaluated on the stored main `volume` column.

## A-19 Task size variables: set only when unset

JDL-147 says "only when unset"; an exported empty JEF_TASK_VCPU /
JEF_TASK_MEMORY_GB is kept as it is (JEF_RUN_STAMP, by contrast, is "unset
or empty").

## A-20 Chain: the first manifest

"The first `run_manifest*.json` directly inside that directory" is
`find DIR -maxdepth 1 -name 'run_manifest*.json' -print -quit`, run only
when the output directory exists (find's order).

## A-21 Packaging

Distribution `jef_data_rc` 0.6.0 (pins.md names the original `jef` 0.6.0),
setuptools backend with an unpinned build requirement. It was installed
with `pip install --no-build-isolation --no-deps -e out` because the working
rules forbid the network (build isolation would download setuptools).

## A-22 Export passes every stored row

"usable stored row" (JDL-071, JDL-073) is not defined; every stored row is
exported (the suite's zero-volume row passes through).

## A-23 Lock-timeout text

The StoreError reads `after {lock_timeout:g}s`, i.e. `after 300s`.

## A-24 Classification `last_verified` strings

A string `last_verified` must be exactly a 10-character `YYYY-MM-DD` date;
a TOML local date is rendered with `isoformat()`.

## A-25 Overwrite with no rows

A yahoo-csv overwrite with zero CSV rows removes every year file of the
series (the series is replaced by an empty one).

## A-26 Bare tickers are upper-cased

The glossary's `aapl -> AAPL.US`: a bare ticker is upper-cased when it gains
`.US`; a dotted symbol passes through unchanged (JDL-031).

## A-27 `load` closes its collector twice on a refusal

The refusal is printed after an explicit close (cli.md: "after closing the
collector"); the surrounding `finally` closes it again, which is harmless.

## A-28 Replay walk order

`os.walk` with directory names sorted in place, files in sorted name order;
a later file with an equal key replaces an earlier one.

## A-29 Transport answer shape (contradiction, minor)

JDL-023 and collectors.md (revision 2026-10-24) give `request()` a
`TransportResponse` object (`status`, `text`, `json()`); the glossary and
the `Transport` interface in `uml/component.puml` still say
`-> (status, text)`. The requirement wins: transports return a
`TransportResponse`, which also unpacks as a `(status, text)` pair so either
reading works. Reported as a kit defect (stale glossary/diagram text).

## A-30 Command name inside the chain versus the console script

The rebuild's console script is `jef-data-rc` (task instruction) while the
parser's `prog` is fixed to `jef-data` (JDL-160) and `daily-rc.sh` calls
`jef-data` as chain.md and JDL-155/156 require; a deployment of this rebuild
therefore needs `jef-data` on PATH (an alias or wrapper of `jef-data-rc`).
The chain scenarios stub `jef-data`, so they are unaffected.

## A-31 Splitting JEF_ASSETS

"split on whitespace" is done with `read -r -d '' -a` (default IFS), so
spaces, tabs and newlines all separate names; a JEF_ASSETS that is empty
falls back to the default list (`${JEF_ASSETS:-...}`).

## A-32 Metadata parsing in the chain prologue

The one `curl` fetch is parsed by two one-line `python3 -c` programs (digest,
then size); `python3 -c` calls are outside the recorded calls, and either
failing independently gives `unknown` / leaves the size unset. A body whose
`Containers` parse but whose `Limits` do not sets the digest only.

## A-33 Validation counts

`{n} duplicate date(s)` counts every parsed date that repeats an earlier one
(`duplicated().sum()`); "NaN in any required column" for the NaN-row note
includes a missing `Date` cell.

## A-34 Status table placeholders

`{missed_sessions or -}` and `{rows or 0}` are read as "absent field" (a
never-filled report), not Python truthiness, so a filled series with zero
missed sessions prints `0 missed` (as the suite's table shows).

## A-35 Non-finite stored closes in status

A NaN previous close is not zero, so the jump is computed and, being NaN,
never exceeds the threshold; a NaN close drops out of the post-seam survivor
set (JDL-120) and of the resolution sample (JDL-122).

## A-36 Binance page cursor without an end

With no end bound only the short-page and empty-page rules stop the
paging; the 100-page refusal is raised before a 101st request is sent.

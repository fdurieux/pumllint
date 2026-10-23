# Assumptions

Each entry records a point where the kit was silent, ambiguous or contradictory,
what the rebuild chose, and why.

## A-01 Console-script name versus the documented `jef-data`
The kit names the executable `jef-data` (pins.md, JDL-133); the task requires the console
script `jef-data-rc`. Chose: console script `jef-data-rc`, parser `prog` set explicitly to
`jef-data` (JDL-160 says prog is set explicitly, so help/usage text is unchanged), and the
chain script invokes `jef-data` as chain.md specifies.

## A-02 Package version
pins.md gives `jef` 0.6.0; the task fixes the package name `jef_data_rc`. Chose version 0.6.0
under the name `jef_data_rc`.

## A-03 Module layout for the transports
component.puml names the modules cli, universe, sync, health, classification, actions, adjust,
store, contract, differential, collectors.base, collectors.eodhd, collectors.binance, but does
not say which module holds Transport/HttpTransport/ReplayTransport/RecordingTransport/RateLimiter.
Chose: all of them in `collectors/base.py`, beside the retry logic that uses them.

## A-04 Build backend
The kit states runtime pins only. Chose setuptools as the build backend (build-time only; the
offline uv cache holds it), so no runtime dependency is added.

## A-05 Universe: `asset_class` that is not a string
JDL-012 says "asset_class presence then value"; refusals.md U-09 lists asset_class among the
keys refused as `must be a non-empty string`. Chose: presence, then the non-empty-string check,
then the vocabulary check (`unknown asset_class ...`).

## A-06 Universe: `kind` that is not a string
No type rule is given for `kind`. Chose: any value other than the string `eod` (including a
non-string) gets the `kind {value!r} is not supported` refusal.

## A-07 Universe: order of the yahoo-csv key rules
JDL-012 lumps "CSV/collector key rules" into one step. For a yahoo-csv source missing `path`
and also declaring `start`/`end`, chose: the missing `path` is reported first, then the
start/end rule.

## A-08 Universe: which sources count for the duplicate store-coordinate rule
JDL-021 does not say whether disabled sources or disabled assets count. Chose: every declared
source of every asset counts (the partition would be claimed the moment it is enabled).

## A-09 Universe: `path`/`start`/`end` validated before the provider-specific placement rules
The individual value checks (`path` non-empty string, `start`/`end` ISO date) run in the
JDL-012 order (`path`, `start`, `end`) before the CSV/collector placement rules, so a
malformed `start` on a yahoo-csv source reports the date error first.

## A-10 Symbol normalisation: case of bare tickers and pair parsing
JDL-031 says pairs are upper-cased but says nothing about bare tickers. Chose: a bare ticker
gains `.US` with its case unchanged; a pair is upper-cased before the fiat/crypto-quote tests
and split at its first `/`; the refusal quotes the symbol exactly as given.

## A-11 Non-list `/splits/` and `/div/` answers
JDL-032 and JDL-038 define the non-list refusal for bars only. Chose the same shape for the
two actions endpoints: `splits {SYM}: expected a JSON list` / `div {SYM}: expected a JSON list`
(CollectorError).

## A-12 Redaction versus truncation in HTTP error texts
"first 200 characters of the body, token redacted" admits both orders. Chose: truncate the body
to 200 characters first, then redact the registered token.

## A-13 Binance start/end given as ISO date-time text
The universe can carry a TOML date-time as full ISO text (JDL-008) but the Binance window is
defined on dates (JDL-037). Chose: use the calendar date of the first ten characters.

## A-14 Replayer directory order
fixtures.md says "os.walk order". Chose: os.walk with sub-directories visited in sorted name
order and files in sorted name order, so a later file with an equal key wins deterministically.

## A-15 Rows are built (and refused) before the series lock is taken
JDL-058 puts every read-modify-write under the lock; the import scenarios require that a CSV
with unparseable dates or missing columns leaves no file at all (not even `.lock`). Chose: bars
are parsed, raw-ized and adjusted in memory before the lock is taken (so date, volume-basis and
degenerate-ratio refusals write nothing); the lock covers the read of the stored series and the
writes. A reconcile or append handed zero bars returns without taking the lock.

## A-16 Ratio validation before volume raw-ization
JDL-054 raw-izes EODHD volume with the factor before the adjustment pass (JDL-052) would refuse
a degenerate ratio, and a zero ratio would otherwise divide by zero first. Chose: the factor
computation itself validates every ratio (non-finite or <= 0 -> AdjustmentRefused
`split {date} has degenerate ratio {ratio!r}`), so the refusal text is the one the scenario
expects whichever step meets the ratio first.

## A-17 Duplicate timestamps inside one write
Collectors already keep one bar per date; the CSV import keeps the first row per timestamp
(JDL-070). For the reconcile and append writes the same rule is applied (sorted by timestamp,
stable, first kept) so a year file never holds a duplicated timestamp.

## A-18 Pruned year directories
JDL-058 says stale year files are deleted after the new ones are in place. Chose: delete the
stale `data.parquet` and then remove its `year=` directory when it is empty.

## A-19 The re-adjustment "changed" comparison
JDL-069 rewrites "only when any value changed". Chose: compare the six derived columns (open,
high, low, close, volume, cumulative_split_factor) exactly, NaN equal to NaN; the adjustment
never touches any other column.

## A-20 Re-adjust of an empty series takes the lock first
store.md lists "Under the lock. Read the whole series (StoreError ... when empty)". Chose the
literal order, so `adjust` of an absent series creates its symbol directory and `.lock` before
refusing.

## A-21 Re-adjust gate after a reconcile
JDL-097 re-adjusts "whenever the series has at least one stored row". Chose to test that with
the latest-session read after the reconcile (store.md §5 names latest session as the sync's
reapply gate).

## A-22 When the sync constructs a collector
JDL-102 says "only when a non-dry-run leg first needs that provider". Chose: at the start of
each eodhd/binance leg (before the actions gate), so a keyless run fails every eodhd leg with
the construction ValueError even when its actions are fresh and its window inverted. A failed
construction is not cached, so each eodhd leg retries it and fails the same way.

## A-23 The today-dated bar check
JDL-098 says "the newest fetched bar is dated today". Chose: compare the first ten characters of
the last bar's date (bars are ascending) with today's ISO date.

## A-24 Naive actions stamps
JDL-044 reads stamps by replacing `Z` with `+00:00`. A stamp without any offset is taken as UTC.

## A-25 `sync-actions` and `load` file naming for bare symbols
JDL-042/JDL-143 sync "the corporate actions of S"; `load` normalises S before reading splits.
Chose: `sync-actions` writes the files under S as given (the request uses the normalised
symbol); `load` reads the splits of the normalised symbol. For dotted symbols the two agree.

## A-26 Differential: order of the B-side refusal and alignment with repeated dates
Chose: the `pass --b-csv or --b-symbol` refusal is checked before any store read. Alignment is
an inner join on the Date text after each frame is sorted by Date (stable); "dates in common"
is the joined row count, and the max of an empty comparison is reported as 0.000%.

## A-27 Validation: "sorted ascending" and the all-unparseable test
Chose: dates are "not sorted ascending" when the parsed dates (unparseable ones dropped) are not
monotonically non-decreasing, so repeated dates alone do not add the note. The "no parseable
dates" error applies only to a frame with at least one row.

## A-28 Status: zero-length windows
For `--window 0` or `--resolution-window 0` the kit gives no rule. Chose: no rows are scanned
(no jumps, no resolution; a pair reports no common session).

## A-29 Chain: digest/size parsing and the set-if-unset rule
chain.md parses the metadata with `python3 -c`. Chose two single-line `python3 -c` calls (one
for the digest, one for the size) so each stays one recorded call; "set only if unset" is taken
literally for JEF_TASK_VCPU/JEF_TASK_MEMORY_GB (an exported empty value is kept), while
JEF_IMAGE_DIGEST and JEF_RUN_STAMP are recomputed when empty or unset as the kit says. An empty
JEF_ASSETS falls back to the default list.

## A-30 Chain: the manifest search
JDL-157 asks for "the first run_manifest*.json directly inside that directory". Chose
`find DIR -maxdepth 1 -name 'run_manifest*.json' -print -quit` (find's directory order), with a
missing directory treated as no manifest.

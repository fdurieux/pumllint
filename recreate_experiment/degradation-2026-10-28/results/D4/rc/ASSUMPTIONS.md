# Assumptions, ambiguities and contradictions

One entry per point where the kit was silent, ambiguous or contradictory:
what was chosen and why. Precedence applied when documents disagree is the
kit README's (suite > requirements > contracts > DMN/glossary > UML).

## A-01 Detail of a successful yahoo-csv sync leg: "loaded", not "imported"
JDL-099 and `contracts/sync_summary.example.json` give the detail
`{rows} row(s) imported`; every scenario that exercises a CSV leg
(collectors.feature, sync.feature, decisions.feature r3/r5) expects
`{rows} row(s) loaded`. The suite wins: the rebuild prints `loaded`.
Reported as a kit defect (requirement and example disagree with the suite).

## A-02 Module layout
The component diagram names the modules `cli`, `universe`, `sync`,
`health`, `classification`, `actions`, `adjust`, `store`, `contract`,
`differential`, `collectors.base`, `collectors.eodhd`, `collectors.binance`.
The rebuild uses exactly these under `jef_data_rc/`, plus
`collectors/transport.py` for the three transports and `TransportResponse`
(the diagram draws them as components of the package without naming a
module).

## A-03 Distribution name and version
pins.md names the package `jef` 0.6.0 and the console script `jef-data`;
the task fixes the import package `jef_data_rc` and the console script
`jef-data-rc`. The distribution is `jef-data-rc`, version 0.6.0 (the pinned
version kept), console script `jef-data-rc = jef_data_rc.cli:main`. The
parser's `prog` stays `jef-data` (JDL-160), so every message reads
`jef-data`.

## A-04 Installing without network
`pip install -e out` with build isolation would download setuptools; the
environment has no network. The package uses the setuptools backend already
present in the venv and is installed with `--no-build-isolation`. No runtime
dependency beyond the four pins (pandas 3.0.5, numpy 2.4.6, requests 2.34.2,
pyarrow 25.0.1).

## A-05 Universe: where the yahoo-csv `path` requirement sits in the check order
JDL-012 lists `... note, path, start, end, CSV/collector key rules,
start-after-end` without saying what the `path` step checks. Chosen: at the
`path` step a yahoo-csv source must carry a non-empty `path` (else
`missing required key 'path'`), and a collector source's `path`, if present,
must be a non-empty string; `start`/`end` are then validated as dates for
every provider, and only afterwards do the CSV/collector key rules refuse a
window on a CSV source or a `path` on a collector source.

## A-06 Universe: a non-string `provider` / `asset_class`
Not stated which message a non-string or empty `provider` or `asset_class`
gets. Chosen: the generic `{where}: {key} must be a non-empty string, got
{value!r}` (refusals.md U-09 lists both keys), checked before the
enumeration check.

## A-07 Universe: duplicate store coordinates across disabled entries
JDL-021 does not say whether disabled assets or sources take part in the
coordinate check. Chosen: every declared source of every asset takes part
(a paused asset still owns its partition).

## A-08 Universe: duplicate names list
`{sorted names}` is read as the sorted list of the names that occur more
than once, each listed once.

## A-09 EODHD symbol normalisation upper-cases a bare ticker
JDL-031 says a bare ticker "gains .US"; the glossary's example
`aapl -> AAPL.US` upper-cases it. Chosen: bare tickers are upper-cased
before `.US` is appended; a dotted symbol passes through unchanged (not
upper-cased), and the pair branch upper-cases both sides as specified.

## A-10 Redaction and truncation order in collector error texts
`{text[:200]}` with "token redacted as ***" does not fix the order.
Chosen: the message is built with the first 200 characters of the body and
the token is then replaced by `***` in the whole message.

## A-11 Splits and dividends answers that are not JSON lists
Only `/eod/` and klines have a specified "expected a JSON list" refusal.
Chosen: the same pattern for the other two calls,
`CollectorError: splits {SYM}: expected a JSON list` and
`div {SYM}: expected a JSON list`.

## A-12 Replay load order
fixtures.md says "os.walk order; inside one directory, files in sorted name
order". Chosen literally: directories in the order `os.walk` yields them
(not re-sorted), files sorted by name, a later equal key replacing an
earlier one; `manifest.json` skipped at any depth.

## A-13 Binance window bounds given as full date-time text
A TOML date-time `start` is carried as ISO date-time text (JDL-008), but the
Binance cursor is "Unix ms of that date at 00:00 UTC". Chosen: the date part
(first 10 characters) of the text is used. EODHD passes the text verbatim as
`from`/`to`.

## A-14 The series lock is taken before reading, also when the read finds nothing
JDL-058/JDL-069 put every read-modify-write under the lock and the
re-adjustment reads "under the series lock". Chosen: `adjust` on an absent
series takes the lock first (creating the series directory and `.lock`),
then raises `StoreError: nothing stored for ...`. No scenario checks the
files left by that refusal.

## A-15 Rows are built before the lock is taken
Date parsing (JDL-061), the CSV column check (JDL-070) and the split-factor
computation (including the degenerate-ratio refusal) run before the lock,
so a refused import or reconcile leaves no file at all; the suite requires
this for the import refusals ("the store holds exactly the files:" empty).

## A-16 A reconcile handed zero bars
JDL-068 does not say whether zero served bars take the lock. Chosen: zero
bars return `(0, [])` without touching the store (no directory, no
`.lock`); the re-adjustment of JDL-097 still runs when the series has rows.

## A-17 Status table: `{missed_sessions or -}`
Read as "the field, or `-` when absent": a measured 0 prints `0 missed`
(the suite's `last 2099-03-11, 0 missed`), not `-`. Same for
`{last_session or -}`; `{rows or 0}` prints 0 for an absent field.

## A-18 Differential with no common dates, and alignment
The kit does not say what `max` prints over zero common dates or how
duplicate dates inside one side align. Chosen: an inner merge on `Date`
(duplicates expand as pandas merges them); the per-column maximum is
pandas' `Series.max()`, which is NaN on an empty series and prints `nan%`.

## A-19 Differential refusal checked before reading the A side
With neither `--b-csv` nor `--b-symbol` and an absent A series, either the
refusal or the AttributeError could come first. Chosen: the refusal is
checked first (it needs no store access).

## A-20 `sync-actions --symbol S`: file name of the actions store
JDL-143 prints `{S}` as given but does not say whether the actions files
are keyed by S or by its normalised form. Chosen: the symbol is normalised
(collectors.md §2) and the files are written under the normalised symbol,
so `sync-actions --symbol AAPL` and `load --symbol AAPL` meet on
`AAPL.US.json`; the printed line keeps S as given.

## A-21 A failed EODHD construction inside one sync run
JDL-102 says collectors are constructed at most once per provider and a
failed construction fails each eodhd leg in turn. Chosen: the construction
error is cached and re-raised for every later eodhd leg of the run (no
second construction attempt).

## A-22 `load`: order of the declaration refusals
D-03 (an asset_type outside the vocabulary, reachable only below the
parser) is checked first, then D-01 (no declaration, not `.CC`), then D-02
(`.CC` declared other than crypto). The pair-symbol CollectorError of
normalisation comes before all three (it is raised by normalisation). The
collector is constructed first and closed before the refusal is printed.

## A-23 Chain: set-if-unset of the task size
chain.md says JEF_TASK_VCPU / JEF_TASK_MEMORY_GB are set "only if unset".
Chosen: bash `:=`, i.e. set when unset or empty; a parse failure of
`Limits` leaves both untouched and unexported. The digest falls back to
`unknown` whenever the one-line `python3 -c` parse prints nothing.

## A-24 Chain: "the first run_manifest*.json directly inside that directory"
Chosen: `find DIR -maxdepth 1 -name 'run_manifest*.json' -print -quit`
(find's directory order), errors silenced so a missing output directory
means "no manifest".

## A-25 Parquet writing details
store.md fixes the Parquet types; how the file is produced is open. Chosen:
`pyarrow.Table.from_pandas` with an explicit 21-field schema (int64,
timestamp[ms, tz=UTC], double, string), no index column, snappy, pandas
metadata kept; rows of a year file in timestamp order.

## A-26 Timestamp arithmetic
JDL-060: the stored `timestamp` is the pandas parse of the bar date
(format inferred from the first bar, `utc=True`, unparseable values
coerced to NaT and refused) cast to int64 (microseconds under pandas 3.0.5)
and integer-divided by 10**6, giving Unix seconds.

## A-27 NaN rows in the validation report
"NaN in any required column" is read as a NaN among the six numeric
columns or a missing `Date` cell; the clean-row count uses the six numeric
columns as JDL-079 says.

## A-28 Dividend sort key
"a missing date sorts as the empty string" is implemented as
`entry.get("date") or ""`, so a null date also sorts first.

## A-29 Transport response shape
JDL-023 (revised) says the transport returns a `TransportResponse` object
with `status`, `text` and `json()`; the glossary still draws a
`(status, text)` pair. Chosen: the object; it also unpacks as
`(status, text)` so both readings hold.

## A-30 Dry-run results
leg.md: dry-run results carry no `revisions` key. The summary renders an
absent `revisions` as `[]` and `revised_cells` 0, as the suite expects.

## A-31 Status on a selection of only yahoo-csv legs
The selection is non-empty, so it is not a refusal; the report lists
`0 source(s), 0 alert(s)` and exits 0 (suite). A selection that matches no
leg at all is still the S-04 refusal.

## A-32 pandas warnings on stderr
`validate` on a Date column whose format pandas cannot infer lets pandas'
own UserWarning ("Could not infer format ...") reach stderr, as the pinned
pandas emits it; no scenario checks stderr there. numpy division warnings
(0/0 in `adjustment_factor`) are silenced, matching pandas' own Series
arithmetic, which never warns.

## A-33 Rate limiter
collectors.md: 1000 per sliding 60 s, 100000 per UTC day. Chosen: the
daily count resets when the UTC date changes and is checked before the
per-minute wait; the per-minute wait sleeps `60 - (now - oldest)` and then
drops entries at least 60 s old. The harness collectors disable the
limiter and suppress backoff sleeps.

## A-34 The adjustment's refusal order
`adjust` checks `price_basis` first (any non-`raw` value), then the
presence of the raw columns and `datetime`, then every split ratio (before
any arithmetic). A split event stored without a split string is written as
`{ratio:g}/1`.

## A-35 Module path in traceback last lines
refusals.md gives the traceback's last line as
`{module path}.{ErrorClass}: {message}`; the original's module path is
`jef.data.<module>` (component diagram), the rebuild's is
`jef_data_rc.<module>` (the package name the task fixes), e.g.
`jef_data_rc.store.StoreError: nothing stored for eodhd/NONE.US`. The
exception classes are not given a forged `__module__`; the message part
after the class name is identical. Where each error class lives is not
stated: UniverseError in `universe`, SyncError in `sync`, StoreError in
`store`, AdjustmentRefused in `adjust`, CollectorError and
DailyBudgetExhausted in `collectors.base`, TransportConnectionError in
`collectors.transport`, ContractError in `contract`, ClassificationError in
`classification`, DeclarationRefused in `cli`.

## A-36 Verbatim texts that name the original's own paths
Help strings and messages that mention `src/jef/data/universe.toml`,
`jef.data.sync`, `jef.binning.loading.load_eod_store` and
`jef.data.universe.ASSET_TYPE_BY_CLASS` (D-03) are reproduced byte for byte
although the rebuild's modules are named differently: the texts are
contract, not a description of the rebuild.

## A-37 Differential: separator of the unmatched-date list
JDL-083 says "first 5 sorted, comma-separated"; the only example has one
date. Chosen: `", "` (comma and space).

## A-38 Chain: position of the bucket check
chain.md lists the bucket check among the guards, JDL-151 says it comes
"before sourcing the externals, installing traps or running any stage".
Chosen: it is the first statement of the inner run (before RUN_DATE and the
asset list are computed); `${JEF_S3_BUCKET:?...}` makes bash print
`<script>: line N: JEF_S3_BUCKET: JEF_S3_BUCKET must name the venue bucket`
and exit 1.

## A-39 Chain: `--inner` followed by more arguments
Only "first argument is not `--inner`" is specified. Chosen: when the first
argument is `--inner`, the inner run starts and any further arguments are
ignored.

## A-40 Chain: an empty JEF_ASSETS
Chosen: `${JEF_ASSETS:-AAPL BTC TLT NVDA TSLA IBM}`, so an empty value also
falls back to the default list (an empty filter list would select the whole
universe instead).

## A-41 A naive injected clock
The harness passes timezone-aware UTC datetimes. A naive `now` is
converted with `astimezone(timezone.utc)`, i.e. read as local time; the
same holds for an actions stamp without a zone.

## A-42 Lock-timeout message number format
`after 300s` is rendered from the timeout with `:g` (300.0 -> `300`).

## A-43 Glossary vs requirements on the transport
glossary.md and component.puml still draw the transport as returning
`(status, text)`; JDL-023 (revised 2026-10-24) and collectors.md say the
TransportResponse object. Requirements win (see A-29). Reported as a kit
defect (the glossary row was not revised with F-008).

## A-44 Kit housekeeping noticed while reading
README's reading order is numbered 1, 2, 5, 3, 4; refusals.md lists X-11
before X-10. Neither changes behaviour; noted for the kit owner.

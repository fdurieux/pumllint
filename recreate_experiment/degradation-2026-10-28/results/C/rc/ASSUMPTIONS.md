# Assumptions of the rebuild

Every point where the kit was silent, ambiguous or contradictory, what was
chosen and why. One entry each, numbered in the order they were met.

## A-01 Console script name versus the parser's prog
The task names the console script `jef-data-rc`; cli.md fixes the parser's
`prog` as `jef-data`, "set explicitly, so it does not depend on how the
program is launched", and cli_help.md prints `jef-data` everywhere.
Chosen: entry point `jef-data-rc`, argparse `prog="jef-data"`, so every help
text, usage line and `{prog}: error:` line reads `jef-data` as recorded.

## A-02 Distribution name and version
pins.md names the original distribution `jef` 0.6.0; the task requires the
package `jef_data_rc`. Chosen: distribution `jef-data-rc`, version `0.6.0`,
import package `jef_data_rc`, runtime dependencies exactly the four pins
(pandas==3.0.5, numpy==2.4.6, requests==2.34.2, pyarrow==25.0.1).

## A-03 Module layout
The component diagram names the modules of `jef.data` (cli, universe, sync,
health, classification, actions, adjust, store, contract, differential,
collectors.base, collectors.eodhd, collectors.binance) but not where the
transports live. Chosen: the same module names under `jef_data_rc`, with the
Transport classes (HttpTransport, ReplayTransport, RecordingTransport) and
the fixture-key helpers in `collectors/base.py`, and the two TOML files as
package data.

## A-04 Module path in traceback last lines
refusals.md says a traceback ends `{module path}.{ErrorClass}: {message}`.
The original's path is `jef.data....`; this rebuild's is `jef_data_rc....`
(e.g. `jef_data_rc.store.StoreError: ...`). The suite only checks the line's
ending, which is identical. Builtin errors (ValueError, FileNotFoundError,
AttributeError) print with no module path, as in the original.

## A-05 Where the yahoo-csv `path` requirement is checked
JDL-012 lists the per-source order `... note, path, start, end, CSV/collector
key rules, start-after-end`, without saying whether "path missing for
yahoo-csv" belongs to the `path` step or to the key rules. Chosen: the `path`
step only type-checks a present value; the key-rules step then raises, for
yahoo-csv, `missing required key 'path'` before `start/end apply to collector
sources only`, and for collectors `path applies to yahoo-csv sources only`.

## A-06 A non-string `kind` or `asset_class`
U-09's list of string-typed keys omits `kind` but includes `asset_class`.
Chosen: a non-string `kind` gets the "kind ... is not supported" message
(its value repr); a non-string `asset_class` gets the "must be a non-empty
string" message before the value check.

## A-07 Duplicate store coordinates and disabled sources
JDL-021 says two assets "declare" the same coordinate. Chosen: every source
of every asset counts, enabled or not, in file order; the first clash found
is reported.

## A-08 Replay directory walk order
fixtures.md fixes "os.walk order; inside one directory, files in sorted name
order" but os.walk's subdirectory order is filesystem order. Chosen:
subdirectories are visited in sorted order too, so a later file with an
equal key replaces an earlier one deterministically.

## A-09 Splits and dividends answers that are not JSON lists
JDL-032 and JDL-038 give the non-list refusal for bars only. Chosen: the
splits and dividends calls refuse the same way with their own labels
(`splits {SYM}: expected a JSON list`, `div {SYM}: expected a JSON list`).

## A-10 A failed EODHD construction inside one sync run
JDL-102 says a collector is constructed at most once per provider per run and
a failed EODHD construction fails each eodhd leg. Chosen: the construction is
attempted once; its exception is kept and re-raised for every later eodhd leg
of the run (same message as a retry would give).

## A-11 When the series lock is taken
store.md §6 says every write operation runs "under the lock" while JDL-061 and
the import refusal scenarios require that a refused write leaves no file at
all. Chosen: reconcile, append and overwrite build (and so validate) their
incoming rows before taking the lock, so a refusal creates nothing, not even
`.lock`; re-adjustment takes the lock first and then reads, as its contract
reads (an `adjust` of an absent series therefore leaves an empty symbol
directory with its `.lock`).

## A-12 Order of the adjustment refusals
JDL-051 and JDL-052 give three refusals without an order. Chosen: missing raw
columns first, then a non-raw price_basis, then a degenerate split ratio.

## A-13 What "any value changed" compares on re-adjustment
JDL-069 rewrites only "when any value changed". Chosen: the derived columns
the adjustment writes (open, high, low, close, volume,
cumulative_split_factor) are compared exactly, NaN equal to NaN; the other
columns are carried unchanged by construction.

## A-14 Calendar of the corporate-actions freshness count
JDL-125 counts "expected sessions strictly between the stamp's UTC date and
today" without naming the calendar. Chosen: the same expected-session rule as
staleness (JDL-115) with the leg's declared asset_type; eligible legs are never
crypto, so in practice weekdays.

## A-15 `differential` with no B side and an absent A series
JDL-140 (refusal `pass --b-csv or --b-symbol`) and JDL-163 (traceback on an
absent stored side) do not say which wins when both hold. Chosen: the missing
B side is refused first, before any store read.

## A-16 Symbol used by the hand-run `sync-actions`
cli.md says it syncs "S's corporate actions"; the collector normalises S for
the URL. Chosen: the actions files are written under S exactly as given (the
form the sync uses, which is always canonical already); only the request path
uses the normalised symbol.

## A-17 What counts as a NaN row in the validation
JDL-079 says "NaN in any required column". Chosen: a missing Date cell counts
as well as a NaN in the six numeric columns; an unparseable (but present) date
string does not, it has its own note.

## A-18 Warnings printed by date parsing
pandas emits a UserWarning when it cannot infer a date format (the
`no_dates.csv` case). The kit does not show stderr for `validate`. Chosen:
date parsing in validation and in the store runs with warnings suppressed, so
stderr carries nothing but refusals and tracebacks.

## A-19 Chain: set-if-unset for the task size
JDL-147 says JEF_TASK_VCPU and JEF_TASK_MEMORY_GB are set "only when unset".
Chosen: bash `:=` (unset or empty), the shell idiom for set-if-unset; both are
exported only when the metadata parse succeeded, so a failed parse leaves them
truly unset in the children.

## A-20 Chain: the metadata parse is two one-line `python3 -c` programs
chain.md says the digest and the size are parsed with `python3 -c`, one
physical line each. Chosen: one program prints the digest (ImageDigest, else
ImageID, else `unknown`; any failure -> `unknown`), a second prints
`CPU Memory/1024`; a failure of the second leaves the size unset without
touching the digest.

## A-21 Chain: an empty JEF_ASSETS
JDL-146 gives the default list for JEF_ASSETS but not for an empty value.
Chosen: `${JEF_ASSETS:-...}`, so an empty value also means the default list;
the list is split on IFS whitespace with globbing off.

## A-22 Chain: the binning stage's t0
chain.md: each stage sets STAGE_T0 first, "binning: t0 per asset". Chosen:
STAGE_T0 is set once at the stage start (the TERM trap reads it) and each
asset's emit uses its own t0 taken just before its jef-binning call.

## A-23 Chain: finding the manifest
"The first run_manifest*.json directly inside that directory" is found with
`find DIR -maxdepth 1 -name 'run_manifest*.json' -print -quit` (find's own
order; a missing directory yields no manifest).

## A-24 Stamps without a zone
JDL-044 reads a stamp by replacing Z with +00:00. Chosen: a stamp that still
parses without a zone is taken as UTC.

## A-25 Live rate limiter details
JDL-023 fixes the numbers (1000 per sliding 60 s, 100000 per UTC day). Chosen:
a monotonic clock for the window, the UTC calendar date of the real clock for
the budget (reset when the date changes), and the budget checked before the
window so an exhausted day raises without sleeping.

## A-26 Redaction of error bodies
JDL-028 says "first 200 characters of the body, token redacted". Chosen: the
body is cut to 200 characters first and the cut text is redacted.

## A-27 Binance window from a date-time start
The universe may carry a TOML date-time as `start` (full ISO text). Chosen:
the Binance collector converts the date part (first 10 characters) to the
00:00 UTC milliseconds of JDL-037; EODHD receives the text unchanged as `from`.

## A-28 actions_state stamp
HARNESS_INTERFACE says `last_updated: str | None`. Chosen: the splits file's
`last_updated` text exactly as stored (not re-formatted).

## A-29 Volume basis of a leg that fetched nothing
An inverted-window leg sends no request and may never construct a collector.
Chosen: the reconcile of its zero bars uses the provider's declared volume
basis (eodhd split_adjusted, binance raw) without constructing a collector; with
no bars it has no effect.

## A-30 A zero-bar reconcile of an empty series
JDL-068 says nothing is written when nothing is replaced or new. Chosen: a
zero-bar reconcile of an empty series takes the lock (creating `.lock`) and
writes no year file.

## A-31 The data command the chain invokes
The task names the console script `jef-data-rc`; chain.md, JDL-155/156 and the
chain scenarios call `jef-data`. Chosen: `daily-rc.sh` calls `jef-data`, the
contract's name, so a deployment of this rebuild must put a `jef-data` on PATH
that runs `jef-data-rc` (e.g. a symlink); the chain itself is unchanged.

## A-32 A differential with no common date
JDL-083 renders `{col}: within tolerance (max {max rel:.3%})` but says nothing
of an empty intersection, where the maximum is undefined. Chosen: the maximum
of no cells is 0.0 (`max 0.000%`), and the verdict then reports the unmatched
dates.

## A-33 Where DeclarationRefused lives
The data model draws DeclarationRefused (a ValueError) without a module.
Chosen: it is raised and caught in `cli.py`, the only caller (`load`); D-03
(an asset_type outside the vocabulary) is implemented there too, reachable
only below the parser.

## A-34 Recording a non-JSON body
fixtures.md says the `json` member holds the parsed body. A recorder meeting
a body that is not JSON (never in the kit) stores the raw text as a JSON
string. The replayer is what the scenarios use; the recorder is provided for
completeness and is not used by any command.

## A-35 The help description
JDL-160 makes the CLI module docstring the parser description. Chosen: the
rebuild's `cli.py` docstring is the kit's quoted text verbatim (it names the
original's paths, e.g. `src/jef/data/universe.toml`, because the help text
must print them byte for byte); every subcommand and option help string is the
kit's table text, `%` doubled where argparse needs it.

## A-36 A replayed request with no fixture is not retried
fixtures.md §4 says a matching request answers with the recorded status and
retries apply to 429/5xx. Chosen: an unmatched request raises CollectorError
straight from the replayer (it is neither a status nor a connection error), so
it is reported once, never retried.

## A-37 `load` and the incremental start
cli.md step 4: start = `--from`, else the day after the latest stored session
of `eodhd/SYM`. Chosen: an empty `--from` counts as absent; the latest stored
session is read with the same rule as everywhere (JDL-064).

## A-38 The `adjust` command's exchange
`adjust --exchange X --symbol S` re-adjusts `X/S` with the stored splits of
`S`; the corporate-actions store is keyed by symbol only (store.md §8), so the
exchange tag never selects the splits.

## A-39 A zero-sized status window
`--window 0` or `--resolution-window 0` is accepted by the parser (any int).
Chosen: a window of 0 holds no row (no jump is scanned, no common session
exists, no resolution is measured), as pandas `tail(0)` reads, rather than
Python's `values[-0:]`, which would mean every row.

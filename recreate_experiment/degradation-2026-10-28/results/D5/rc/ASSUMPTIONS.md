# Assumptions of the rebuild

One entry per point where the kit was silent, ambiguous or contradictory:
what was chosen and why. Ids are in the order they were met.

## A-01 Crypto end-guard: help text vs JDL-094 (contradiction)
The verbatim `sync` help (contracts/cli_help.md) says "crypto end-guarded at
the previous UTC day", `fixtures/universes/zero_end.toml` says "an end below
the guard", and `dmn/sync_window.dmn` `fetch_end` lists the output values
`today_minus_1` / `min_universe_end_today_minus_1` while its only rules are
r3/r4 (declared_crypto = false; rows r1/r2 absent, a gap for crypto). Against
that, JDL-094, the glossary ("window"), uml/sync_leg.puml ("end = universe
end") and leg.md all say the fetch end is the universe `end`, else open.
Every crypto scenario declares `end` = run date - 1, so the suite cannot tell
the two apart. Chosen: no guard (end = universe end, else open), because the
requirement outranks the contracts/DMN/diagrams by the kit's precedence rule
and the suite is neutral. Reported as a kit defect: the help string and the
fixture comment describe behaviour the requirements deny.

## A-02 Installing without network
`pip install -e out` with build isolation would download setuptools. The
build backend is setuptools (present in the venv); the package was installed
with `pip install --no-build-isolation -e out`. The pyproject is a plain
setuptools project, so a networked `pip install -e` works too.

## A-03 Replay walk order across subdirectories
fixtures.md §4 says "os.walk order; inside one directory, files in sorted
name order". os.walk does not sort subdirectories; the rebuild sorts them
too so the walk is deterministic (only matters when two files share a key).

## A-04 Redaction and the 200-character cut
JDL-028 says "first 200 characters of the body, token redacted"; collectors.md
writes `{text[:200]}` and says the token is replaced in every error text.
Chosen: the message is built with `text[:200]` and the whole message is then
redacted (every occurrence of the key replaced by `***`).

## A-05 Non-list /splits/ or /div/ answers
The kit defines `expected a JSON list` only for `/eod/` and klines. A
non-list splits or dividends answer raises CollectorError
`splits {SYM}: expected a JSON list` / `div {SYM}: expected a JSON list`
(same shape as the eod refusal) rather than an incidental TypeError.

## A-06 Symbol used for the actions files of the hand-run commands
`sync-actions --symbol S` writes the files under S as given (the printed line
uses S as given, and the collector normalises only the URL). `load` reads the
splits of the normalised symbol SYM, because it stores under eodhd/SYM. Inside
`sync` the two coincide (universe eodhd symbols are canonical).

## A-07 Type check of `path` on a collector source
JDL-012 orders `path` before the CSV/collector key rules. A `path` present on
any source is first checked as a non-empty string; only then does a collector
source with `path` get `path applies to yahoo-csv sources only`.

## A-08 A date-time `start`/`end` on a Binance source
JDL-008 carries a TOML date-time as its full ISO text; JDL-037 converts "a
date" to ms at 00:00 UTC. The rebuild parses the text with
`datetime.fromisoformat` and uses its UTC calendar date. EODHD receives the
text verbatim as `from`/`to`.

## A-09 Duplicate store coordinates include disabled sources
JDL-021 speaks of coordinates "declared"; disabled sources and disabled
assets are included in the cross-asset coordinate check.

## A-10 Order of the adjustment refusals
JDL-051 / JDL-052 do not order their checks. Chosen: missing raw columns or
`datetime` first, then a non-raw `price_basis`, then degenerate ratios.

## A-11 Lock before reading in re-adjust and reconcile
JDL-069 says the re-adjustment reads the series "under the series lock"; the
lock is taken before the read, so `adjust` on an absent series leaves the
symbol directory and its `.lock` behind before raising StoreError. Incoming
rows are built (dates parsed, factors validated) before the lock is taken,
so a refusal of the incoming data writes nothing at all (as the import
scenarios require).

## A-12 `differential` argument check before any store read
With neither `--b-csv` nor `--b-symbol`, the refusal is printed before the A
series is read, so it wins over an absent A series.

## A-13 "Set only when unset" for the task size
JDL-147 says JEF_TASK_VCPU / JEF_TASK_MEMORY_GB are set "only when unset".
Implemented as unset-or-empty (`${VAR:-...}`), the bash idiom the rest of the
chain uses for its set-if-unset variables (JEF_RUN_STAMP is "unset or empty").

## A-14 Empty filter lists
`select_legs(..., assets=[], providers=[])` treats an empty list like None
(no filter); the command line never produces an empty list.

## A-15 JDL-132 "`{missed_sessions or -}`" vs the table scenario (contradiction)
Read literally in Python, `0 or "-"` prints `-`, but the status-table
scenario prints `0 missed` for a filled series. The suite wins: `-` (and
`0 row(s)`) is printed only when the field is absent (a never-filled report).

## A-16 Further evidence on A-01 (for the kit owner)
Without a guard the clause of JDL-095 "an empty series with start > end still
sends its request" (and DMN bar_request r3) is unreachable, since the loader
refuses start > end (JDL-019); the decisions.feature bar_request r3 scenario
runs zero_end.toml at 2023-12-25, which makes start > end only under a
previous-UTC-day guard, and asserts a message prefix that hides the `to`
parameter. The rebuild still follows JDL-094 (A-01) and flags this.

## A-17 Traceback module path
refusals.md gives the traceback's last line as `{module path}.{ErrorClass}:
{message}`. The rebuild's errors live in its own modules
(`jef_data_rc.store.StoreError`, `jef_data_rc.adjust.AdjustmentRefused`,
`jef_data_rc.universe.UniverseError`, `jef_data_rc.collectors.base.CollectorError`
...), so that prefix differs from the original's `jef.data...` while the
`{ErrorClass}: {message}` part is identical. Built-in errors (ValueError,
FileNotFoundError, AttributeError) carry no module prefix.

## A-18 Module layout
The package follows uml/component.puml: `cli`, `universe`, `sync`, `health`,
`classification`, `actions`, `adjust`, `store` (also the seam-frame
projection), `contract`, `differential`, `collectors.base` (transports,
fixture identity, rate limiter, retries), `collectors.eodhd`,
`collectors.binance`; `universe.toml` and `classifications.toml` ship as
package data. DeclarationRefused lives in `universe` beside the asset_type
vocabulary it quotes.

## A-19 Pruned year directories
Pruning (overwrite, re-adjustment) deletes stale `data.parquet` files only;
the emptied `year=YYYY/` directory is left behind (readers match
`year=*/data.parquet`, and JDL-058 speaks of files).

## A-20 Validation inside `export`
`export` validates the frame it wrote with the default minimum (1115); it has
no `--min-rows` flag in the parser surface.

## A-21 The B side of `differential --b-csv`
The CSV is read with default `pandas.read_csv` and compared as read: Dates
as text, no load policy, no validation; the six columns are cast to float64
for the comparison (hence `np.float64(5.0)` for an integer CSV volume).

## A-22 Ratio check placement
The split factor itself refuses a non-finite or non-positive ratio, so a
degenerate stored split fails the leg already at volume raw-ization of the
incoming bars, before the lock and before anything is written (the scenario
"A degenerate stored split ratio fails the leg before anything is written").

## A-23 Provider split dates
`/splits/` entry dates are parsed with `date.fromisoformat`; a non-ISO split
date fails the leg with that ValueError. The split string is kept verbatim.

## A-24 The `kind` refusal for a non-string kind
Any value other than the string `eod` is refused with its repr
(`kind 5 is not supported ...`); the kit shows only a string example.

## A-25 Rate limiter clock
The daily budget is keyed by the real UTC date; an injected run clock does
not reach it (like the actions stamp, JDL-043). Replayed collectors have no
limiter at all.

## A-26 Collector lifetime in the hand-run commands
`load` and `sync-actions` close their collector in a `finally`, so it is
closed on errors too; a `load` declaration refusal closes it before printing
`load: ...`.

## A-27 "First" run manifest in the chain
`find DIR -maxdepth 1 -name 'run_manifest*.json' -print -quit` picks the first
one in directory order: the chain may call only the externals chain.md lists
(no `sort`/`head`), so no ordering beyond find's own is applied.

## A-28 Metadata parsing in the chain
The one fetched metadata document is parsed by two one-line `python3 -c`
programs (digest; CPU and memory), each tolerating failure; the digest falls
back to `unknown`, the sizes stay untouched when their parse fails.

## A-29 Classification `last_verified`
Accepted as a TOML date or a `YYYY-MM-DD` string and rendered as
`YYYY-MM-DD` in the verdict suffix.

## A-30 `adjust --symbol` and the actions file
`adjust` reads the splits file of `--symbol` exactly as given (no
normalisation), matching the exchange/symbol pair it re-adjusts.

## A-31 Today-dated bar detection
The newest fetched bar is "dated today" when the first ten characters of its
`date` text equal today's `YYYY-MM-DD` (a time-of-day suffix is ignored).

## A-32 Asset list splitting in the chain
JEF_ASSETS is split on any whitespace, newlines included
(`read -d '' -a`), not only on the first line.

## A-33 Reconcile of zero bars
A reconcile handed zero bars still takes the series lock (creating the symbol
directory and `.lock` on an empty series) and then writes nothing; a first
fill that the provider answers with an empty list therefore leaves only the
lock file behind.

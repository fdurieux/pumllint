# Assumptions

Every point where the kit was silent, ambiguous or contradictory, what was
chosen, and why. One entry each, numbered in the order they were met.

## Naming, packaging, layout

1. **Executable name versus parser name.** The task fixes the console script
   as `jef-data-rc`, while cli.md, refusals.md and cli.feature require the
   parser's usage text to read `usage: jef-data` and errors `jef-data <cmd>:
   error:`. Chosen: console script `jef-data-rc`, argparse `prog="jef-data"`,
   so every printed text is the contract's.
2. **Data command name inside the chain.** The task says "by the name the
   contract says"; chain.md and the chain stubs use `jef-data`. Chosen: the
   chain calls `jef-data` (not `jef-data-rc`).
3. **Distribution name and version.** pins.md says package `jef` 0.6.0; the
   task fixes the package name `jef_data_rc`. Chosen: distribution and import
   package `jef_data_rc`, version kept at 0.6.0.
4. **Module layout.** The component diagram names `cli, universe, sync,
   health, classification, actions, adjust, store, contract, differential,
   collectors.base, collectors.eodhd, collectors.binance`. Chosen: exactly
   those modules under `jef_data_rc/` (collectors as a subpackage), plus
   `__main__.py` for `python -m jef_data_rc`. The seam-frame export lives in
   `store` (the diagram routes "import, export, adjust" to Store).
5. **Traceback module path.** refusals.md says an unwrapped error's last line
   is `{module path}.{ErrorClass}: {message}`; the subject's path is
   `jef.data...`. A rebuild under `jef_data_rc` necessarily prints
   `jef_data_rc.store.StoreError: ...` etc. The class name and message are the
   contract's; only the module prefix differs.
6. **Exception homes.** Not fixed by the kit beyond the class diagram.
   Chosen: UniverseError (universe), SyncError (sync), StoreError (store),
   AdjustmentRefused (adjust), CollectorError, DailyBudgetExhausted,
   TransportConnectionError (collectors.base), ContractError (contract),
   ClassificationError (classification), DeclarationRefused (cli), with the
   base classes of the class diagram.
7. **Editable install.** The venv is a uv venv without pip. Chosen: `uv pip
   install --offline -e OUT` into that venv (setuptools build backend taken
   from uv's local cache, no network); this is the `pip install -e OUT`
   equivalent.
8. **Message text that names the subject's module.** D-03 ends with
   `jef.data.universe.ASSET_TYPE_BY_CLASS`. Kept byte for byte, although the
   rebuild's map lives in `jef_data_rc.universe`.

## Universe

9. **Value check before placement rule.** JDL-012 orders `path`, `start`,
   `end`, then "CSV/collector key rules". Chosen: a present `path` is first
   checked as a non-empty string and a present `start`/`end` as a date for
   every provider; only then does a misplaced key refuse (so a malformed
   `end` on a CSV source refuses as a bad date, not as misplaced).
10. **`kind` values.** Any value other than the string `eod` (including
    non-strings) gets the `kind {value!r} is not supported` refusal; no
    separate type message exists in the kit.
11. **Duplicate store coordinates.** JDL-021 says "two assets declare the
    same coordinate". Chosen: every declared source counts, enabled or not,
    and disabled assets count too (a declaration claims the partition).
12. **Rule 3 versus rule 4 order.** Both are listed after "at most one
    modeled"; they are mutually exclusive, so the order chosen (≥2 enabled
    none modeled, then no enabled source) is unobservable.
13. **TOML local date-times and times for start/end.** A TOML date-time
    (offset or local) is carried as `isoformat()`; a TOML time or any other
    type refuses as "must be an ISO date".
14. **Universe file decoding.** An explicit path is opened in binary and
    decoded as UTF-8 before `tomllib.loads`, so a missing file raises the
    builtin FileNotFoundError naming the path exactly as given.

## Collectors

15. **Non-list `/splits/` and `/div/` answers.** Unspecified. Chosen:
    CollectorError `splits {SYM}: expected a JSON list` /
    `div {SYM}: expected a JSON list`, by analogy with `/eod/`.
16. **Redaction versus truncation order.** "first 200 characters of the body,
    token redacted": chosen `redact(text[:200])` (truncate, then redact).
17. **Bare ticker case.** JDL-031 upper-cases pair symbols only. Chosen: a
    bare ticker gains `.US` with its case untouched; a pair symbol is
    upper-cased before both set tests (so `btc/usdt` → `BTC-USDT.CC`).
18. **Pair symbols with more than one `/`.** Split on the first `/` only.
19. **Binance windows from date-time text.** A universe start/end carried as
    full ISO date-time text is converted to milliseconds from its date part
    (first ten characters) at 00:00 UTC, the rule JDL-037 states for dates;
    an EODHD leg passes the text through verbatim as `from`/`to`.
20. **Pagination message.** "pagination exceeded 100 pages" is rendered from
    the `max_pages` attribute (100), so the text is the contract's at the
    default.
21. **Rate-limit window boundary.** An entry leaves the 60 s window when
    `now - stamp >= 60`; the daily budget refuses the request after 100000
    have been made in the current UTC day.
22. **Retry exhaustion of a connection error.** The network-failure text
    carries the transport's (already redacted) message, redacted again.
23. **Split events' date type.** Stored and compared as calendar dates;
    the provider's `date` must be `YYYY-MM-DD` (anything else fails the leg
    with Python's ValueError text).
24. **Recorder.** Built (`RecordingTransport`) but no command uses it; its
    secret check runs over the serialised fixture text before writing.

## Store

25. **Order of row building and locking.** Rows are built (dates parsed,
    ratios checked, volume raw-ized) before the series lock is taken, so a
    refused write (unparseable dates, degenerate ratio, missing CSV columns)
    leaves no directory or `.lock` behind, matching the scenarios that expect
    an empty store.
26. **Re-adjusting an empty series.** JDL-069 puts the read under the lock,
    so `adjust` on an absent series creates the series directory and `.lock`
    before raising `nothing stored for ...`.
27. **Prune.** A stale year's `data.parquet` is deleted and its now-empty
    `year=` directory removed when possible.
28. **Writing an empty incoming set.** A reconcile or append with zero bars
    writes nothing and takes no lock. An overwrite import of a header-only
    CSV replaces the series literally: it takes the lock, writes no year file
    and prunes every existing year (an empty replacement).
29. **Revision float values.** `stored`/`served` are Python floats of the
    stored and as-would-be-stored cells.
30. **Timestamp derivation.** Implemented literally as the parsed instants'
    integer value divided by 10^6 (`astype(int64) // 10**6`), which under the
    pinned pandas (microsecond parsing) yields Unix seconds.
31. **Export of an empty series.** The seam-frame function raises StoreError
    `nothing stored for {exchange}/{symbol}` (message not given by the kit);
    the command therefore fails with a traceback before opening the file.

## Corporate actions

32. **`sync-actions` file key.** The CLI prints the symbol as given, but the
    files are written under the normalised symbol (the one the collector
    queried), so a later `load`/`adjust` of the canonical symbol finds them.
33. **Stamp without a zone.** A stored stamp lacking `Z`/offset is read as
    UTC.
34. **Split string fallback.** An event without a provider string is stored
    as `{ratio:g}/1`.

## Sync

35. **Collector construction point.** "Only when a non-dry-run leg first
    needs that provider": the collector is obtained at the start of every
    non-dry-run collector leg (before the actions gate), even if the leg then
    fetches nothing; a failed construction is remembered and re-raised for
    each later leg of that provider, so it is attempted once per run.
36. **Today-dated check.** Compares the first ten characters of the newest
    fetched bar's `date` with today's ISO date.
37. **Empty filter lists.** An empty `assets`/`providers` list means no
    filter (same as None).
38. **Collectors closed even on an unexpected abort.** Built collectors are
    closed in a `finally` after the last leg.
39. **Store path rendering.** `{store path!r}` is the repr of the path as a
    string (`'dstore'`), whatever type the caller passed.

## Status

40. **`{missed_sessions or -}`.** The table example prints `0 missed` for a
    zero, so `-` is printed only when the field is absent (never-filled), not
    for a falsy 0; `{rows or 0}` likewise prints 0 only when absent.
41. **Latest session for status.** Taken from the lexicographically last year
    file (JDL-064), the full series loaded for every other check.
42. **Resolution window of 0.** Keeping "the newest 0" leaves nothing, so the
    close fallback applies and then nothing is reported (fewer than 60).
43. **Gap of equal counts.** The earliest pair wins on ties (strictly greater
    replaces); a count of 0 is never a gap.
44. **Jump previous close NaN.** A NaN previous close is not "zero", so the
    move is computed and, being NaN, never exceeds the threshold.
45. **Pair close on the common session.** "The adjusted close of its last
    stored row on that date" within the window rows.
46. **Classification `last_verified` as a TOML date.** Normalised to
    `YYYY-MM-DD` text; a string must already be exactly that form.

## Validation and differential

47. **Unparseable-date count.** Counts every Date that does not parse,
    including empty cells; duplicates are counted among parsed dates only;
    the ascending check is non-strict over parsed dates.
48. **NaN-row count.** A row counts when any of the six numeric columns is
    NaN after coercion or its Date cell is empty.
49. **Empty frames.** A zero-row frame validates as `no parseable dates in
    'Date'`.
50. **Differential alignment with duplicate dates.** Implemented as an inner
    join on Date after sorting each side; `{nC}` is the joined row count.
    With no common date a column reports `within tolerance (max 0.000%)`.
51. **Differential value types.** Every compared column is converted to
    float64 before comparing, so the worst-cell repr is `np.float64(...)`
    even for an int64 Volume (the kit's example shows `np.float64(0.0)` for
    an integral Volume).

## Chain

52. **"Set only if unset".** JEF_TASK_VCPU / JEF_TASK_MEMORY_GB are treated
    as unset when empty too (`${VAR:-}`), matching the digest's
    "empty or unset" wording.
53. **Metadata parsing.** Two single-line `python3 -c` parses of the one
    fetched body (digest, then size); single-line because the chain records
    each call as one line. A digest parse that fails or prints nothing yields
    `unknown`; a size parse that fails leaves both size variables untouched.
54. **First manifest.** "The first `run_manifest*.json` directly inside" is
    `find`'s first match (`-maxdepth 1 ... -print -quit`); a missing output
    directory means no manifest.
55. **Binning stage t0.** STAGE_T0 is set at the stage start (for the TERM
    trap) and each asset's emit carries that asset's own t0.
56. **Arithmetic warnings.** `adjustment_factor` = adjusted_close / close_raw
    is computed with floating-point warnings silenced, so a 0/0 row stores NaN
    without a RuntimeWarning on stderr (pandas-style division warns nothing).

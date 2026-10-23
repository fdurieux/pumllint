# Assumptions

Every point where the kit was silent, ambiguous or contradictory, what was
chosen and why. One entry each, numbered in the order they were taken.

## Packaging and environment

1. **Parser program name.** The console script is `jef-data-rc`, but the
   contracts print usage and parser errors as `jef-data <cmd>: error: ...`
   and the suite greps `usage: jef-data`. Chosen: argparse `prog="jef-data"`
   so usage/error text is byte-identical to the original's, whatever the
   executable's file name.
2. **Package version.** pins.md gives the subject as `jef` 0.6.0; the rebuild
   is a different distribution (`jef_data_rc`). Chosen: version 0.6.0 too.
3. **Installer.** The venv was created by uv and contains no `pip` (the `pip`
   on PATH is the system one and would install outside the venv). Chosen:
   `uv pip install --python <venv>/bin/python --offline -e OUT`, which is the
   venv-local equivalent of `pip install -e OUT`; no package beyond the pins
   was installed.
4. **Build backend.** Not specified. Chosen: setuptools (resolved offline from
   the local uv cache); it is build-time only, not a runtime dependency.
5. **Module layout.** Not specified beyond the package name. Chosen: one module
   per contract (`universe`, `classification`, `collectors`, `adjustment`,
   `actions`, `store`, `seam`, `sync`, `status`, `cli`), plus `__main__`.
6. **Traceback module path.** Unwrapped errors end with
   `{module path}.{ErrorClass}: {message}`; the module path is necessarily
   `jef_data_rc.<module>` here, not the subject's `jef.data.<module>`. The
   class names and messages are kept identical.

## Universe

7. **Non-string enumerated values.** For `asset_class` and `provider` the kit
   lists both a non-empty-string check (U-09) and a vocabulary check
   (U-14/U-15) without ordering them. Chosen: non-empty string first, then
   vocabulary.
8. **`kind` type.** `kind` is not in U-09's string list. Chosen: any value
   other than `"eod"` (including non-strings) gets the U-16 message with its
   repr.
9. **`path` on a collector source.** The path step comes before start/end and
   the CSV/collector rule after them. Chosen: a present `path` is first
   checked as a non-empty string (any provider), the "path applies to
   yahoo-csv sources only" refusal comes in the later CSV/collector step.
10. **Duplicate store coordinates and disabled entries.** Not said whether
    disabled assets/sources take part in the U-26 check. Chosen: every
    declared source of every asset counts (the rule is about partitions that
    could ever be written).
11. **TOML local date-time / time.** A TOML local date-time (no offset) is
    carried as its `isoformat()` text like an offset one; a TOML local time is
    refused as not an ISO date.

## Collectors and fixtures

12. **Replay walk order across subdirectories.** fixtures.md fixes file order
    inside a directory (sorted) and says `os.walk` order; directory order is
    unspecified. Chosen: subdirectories sorted too, for determinism.
13. **Error-body redaction vs truncation.** "first 200 characters of the
    body, token redacted" does not order the two. Chosen: truncate to 200
    then redact (`redact(text[:200])`).
14. **Non-list `/splits/` and `/div/` answers.** Only `/eod/` and klines have
    a stated non-list refusal. Chosen: the same pattern, CollectorError
    `splits {SYM}: expected a JSON list` / `div {SYM}: expected a JSON list`.
15. **Dividend with a null date.** "a missing date sorts as the empty
    string". Chosen: a null date sorts as the empty string as well.
16. **Binance window from a date-time text.** A universe TOML date-time is
    carried as full ISO text, but startTime/endTime are defined from a date.
    Chosen: the first 10 characters (the calendar date) are used. EODHD
    `from`/`to` carry the text verbatim.
17. **Null `adjusted_close`.** A bar carrying `adjusted_close: null` — chosen:
    stored as NaN ("a NaN value stays NaN").
18. **Constructing an EODHD collector with `api_key=""`.** Treated as no key
    (falls back to the environment, then refuses).
19. **Search endpoint.** Listed as "not used by any command"; implemented as
    `search(query, exchange)` with label `search {query}` for completeness.
20. **Fixture recorder.** Optional in the kit; implemented as a transport
    wrapper writing `{slug}_{digest}.json` and refusing secret material.
21. **Rate-limiter day rollover.** The day budget resets when the UTC date of
    the limiter clock changes; the sliding window drops entries 60 s or older.

## Store and adjustment

22. **Checks inside the adjustment pass.** JDL-051/052 do not order the
    price-basis, missing-column and degenerate-ratio refusals. Chosen:
    price_basis, then missing raw columns, then ratios (all events validated
    up front, first offender in stored order).
23. **Reconcile/append with zero served bars.** store.md §2 says every writer
    takes the series lock first (creating the directory and `.lock`), while the
    layout says `.lock` is "created by the first write". Chosen (revised after
    run 1, which did not exercise it): the writer operation always takes the
    lock, so a sync leg handed zero bars for an empty series leaves a `.lock`
    and no year file; nothing is written when nothing is new.
24. **Validation before locking.** Date parsing, ratio validation and the CSV
    column check happen before the series lock is taken, so a refused import
    leaves no `.lock` file (the store-layout scenarios require an empty store
    after a refused import).
25. **Re-adjusting an empty series.** JDL-069 says "under the series lock,
    read ... ; an empty series shall raise". Chosen: the lock is taken first
    (creating the series directory and `.lock`), then the empty check raises.
26. **"Any value changed" for re-adjustment.** Chosen: compared over the
    derived columns open, high, low, close, volume, cumulative_split_factor,
    NaN equal to NaN.
27. **Duplicate timestamps among served bars.** Collectors already dedupe;
    any remaining duplicate is resolved by keeping the first after a stable
    sort.
28. **Pruned year directories.** After deleting a stale `data.parquet` the
    then-empty `year=YYYY` directory is removed as well.
29. **Lock file mode** is requested as 0644 at creation; the process umask
    may narrow it.

## Seam, validation, differential

30. **Exporting an empty series.** The failing exception is unnamed. Chosen:
    `StoreError: nothing stored for {exchange}/{symbol}` raised by `export`
    before any file is opened; `export_frame` itself returns an empty frame
    (JDL-072 speaks of the non-empty case).
31. **"Ascending" dates.** Chosen: non-decreasing (pandas
    `is_monotonic_increasing`) over the parsed dates; duplicates alone do not
    trigger the "not sorted" note.
32. **NaN-row count.** "NaN in any required column" — chosen: the six
    numeric columns after coercion, or a missing (NaN) Date cell; an
    unparseable but present Date string is not a NaN.
33. **pandas parser warnings.** Date inference warnings are suppressed so
    they never reach stderr.
34. **Differential unmatched-date list.** "comma-separated" — chosen `", "`.
35. **Differential with no common dates.** The `max` of an empty set of
    relative differences is reported as 0.000%.
36. **Differential alignment with duplicate dates.** Chosen: an inner merge on
    Date (duplicates pair up as a merge would); the counts of unmatched dates
    are distinct dates.

## Sync

37. **When the collector is constructed.** "only when a non-dry-run leg first
    needs that provider". Chosen: at the start of every eodhd/binance leg
    (before the actions gate), so a key-less run fails every EODHD leg even if
    its window would fetch nothing.
38. **A failed construction.** Its exception is remembered and re-raised for
    each later leg of that provider (the provider is not retried).
39. **Universe before tail.** `sync --tail 0` with a broken universe reports
    the universe refusal: the universe is loaded before `run_sync` checks the
    tail.
40. **Today-dated check.** Compared on the first 10 characters of the newest
    fetched bar's date.
41. **Re-adjust gate.** "whenever the series has at least one stored row" is
    read from the store after the reconcile (latest session present).

## Hand-run commands

42. **`sync-actions` file symbol.** The symbol is normalised (as the requests
    are) and the files are written under the normalised symbol, so `load`
    (which stores under the normalised symbol) finds them; the printed line
    uses the symbol as given.
43. **`load` start.** "the day after the latest stored session" computed as a
    calendar day; with zero incoming bars nothing is written, and a raw series
    that already had rows is still re-adjusted.
44. **`--from`/`--to` metavar.** Usage text is unspecified; `YYYY-MM-DD` is
    shown, as in cli.md's synopsis.

## Status

45. **Classification file errors.** The packaged evidence is valid; the
    grammar's refusals are implemented as ClassificationError but never
    reachable from the CLI.
46. **`last_verified` given as a TOML date.** Rendered as `YYYY-MM-DD`.

## Chain

47. **"The first run_manifest*.json".** Chosen: the first one `find -maxdepth
    1 -print -quit` reports (find is among the chain's listed commands; sort
    is not).
48. **JEF_TASK_* "only when unset".** Chosen: strictly unset (`${VAR+x}`); an
    exported empty value is kept.
49. **Splitting JEF_ASSETS.** "split on whitespace" — chosen `read -d ''`,
    which splits on spaces, tabs and newlines without pathname expansion.
50. **Digest text when the metadata parse prints nothing.** Falls back to
    `unknown`.

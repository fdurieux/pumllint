# Assumptions

Every point where the kit was silent, ambiguous or contradictory, what was
chosen, and why. One entry each, numbered in the order they were met.

1. **Program name in usage and help.** The console script is `jef-data-rc`, but
   cli.md fixes `prog` explicitly as `jef-data` "so it does not depend on how the
   program is launched", and every recorded usage/help text reads `jef-data`.
   Chosen: `prog="jef-data"` (and `jef-data` in every message, e.g. `run jef-data
   sync`), whatever the executable is called.

2. **Command the chain invokes.** The chain contract names `jef-data` (and the
   chain scenarios stub exactly that name). Chosen: `daily-rc.sh` calls
   `jef-data`, not `jef-data-rc`; on a venue the rebuild's script would need a
   `jef-data` alias.

3. **Installing without network.** `pip install -e` with build isolation would
   fetch setuptools from an index. Chosen: `pip install --no-build-isolation
   --no-deps --no-index -e out/` against the venv's existing setuptools; the
   declared runtime dependencies are exactly the four pins.

4. **Package version.** pins.md gives `jef` 0.6.0; the task renames the package
   to `jef_data_rc`. Chosen: version 0.6.0 under the new name.

5. **Where the transports live.** The component diagram lists HttpTransport,
   ReplayTransport (and the data model RecordingTransport, RateLimiter) without
   naming a module. Chosen: all in `collectors/base.py` beside BaseCollector;
   SplitEvent and split-string parsing live in `actions.py` (the store of the
   events), exception classes beside the module that raises them
   (UniverseError/universe, SyncError/sync, StoreError/store,
   AdjustmentRefused/adjust, CollectorError/collectors.base,
   DeclarationRefused/cli, ContractError/contract,
   ClassificationError/classification).

6. **Price division in the adjustment.** "float32 division" could mean
   float32(raw/F) or float32(raw)/float32(F). Checked against every row of the
   expected frames: only float32(raw)/float32(F) reproduces all 476 price cells
   (the other variant misses 40). Chosen: cast both operands to float32, divide in
   float32, widen to float64.

7. **Timestamp unit.** JDL-060 describes the stored `timestamp` as the parsed
   datetime's integer value // 10^6 (seconds for the microsecond resolution the
   pinned pandas infers for date strings). Chosen: exactly that expression on
   whatever unit `pd.to_datetime(..., utc=True)` infers, so a nanosecond-precision
   string would store milliseconds, as the original would.

8. **Zero-row read-back frame.** JDL-159/JDL-163 require that exporting an absent
   series fails inside pandas' `.dt` accessor. Chosen: an absent series reads as
   `pd.DataFrame(columns=COLUMNS)` (object dtype columns), so the export projection
   raises pandas' own AttributeError, unwrapped.

9. **Error body truncation order.** "first 200 characters of the body, token
   redacted" does not say whether redaction precedes truncation. Chosen: redact
   the whole body, then keep 200 characters, so a token straddling the cut can
   never leak a fragment.

10. **Non-list splits/div answers.** The kit specifies the non-list error only for
    `/eod/` and klines. Chosen: `/splits/` and `/div/` answering a non-list raise
    `CollectorError: splits {SYM}: expected a JSON list` (resp. `div {SYM}`) by
    analogy.

11. **Replay walk order across directories.** fixtures.md says `os.walk` order
    with files sorted inside a directory, but leaves subdirectory order to the
    file system. Chosen: subdirectories also visited in sorted order, so a later
    equal key replaces an earlier one deterministically.

12. **Status table, `missed_sessions` of 0 (kit disagreement).** JDL-132 writes
    the source line as `{missed_sessions or -} missed, {rows or 0} row(s)`, which
    in Python would print `-` for a measured 0; status.feature (the higher
    authority) expects `last 2099-03-11, 0 missed`. Chosen: `-` only when the field
    is absent (never-filled report), the number otherwise; `rows` likewise.
    Reported as a defect in the requirement's wording.

13. **Transport shape (kit disagreement).** collectors.md and JDL-023 (revised
    2026-10-24) say `request()` returns a TransportResponse object; the glossary
    and uml/component.puml still say `-> (status, text)`. Chosen: the object
    (status, text, json()), per the precedence rule and CHANGES F-008.

14. **Traceback module path.** refusals.md says the last traceback line is
    `{module path}.{ErrorClass}: {message}`. The rebuild's module path is
    `jef_data_rc.<module>` (e.g. `jef_data_rc.store.StoreError: ...`) where the
    original's is under `jef.data`; the class name and message are identical.

15. **Binance start/end given as date-time text.** The universe carries a TOML
    date-time as full ISO text (`2024-01-01T10:00:00+00:00`), but the Binance
    collector converts "a date" to 00:00 UTC milliseconds. Chosen: the first ten
    characters are taken as that date, so a date-time start pages from its UTC
    calendar day rather than failing the leg.

16. **Differential with no common date.** The kit does not say what `max` is over
    an empty set. Chosen: such a column prints `within tolerance (max 0.000%)`.

17. **Differential unmatched-date list separator.** "first 5 sorted,
    comma-separated" - chosen `", "` (comma and space).

18. **Differential refusal order.** Chosen: the "pass --b-csv or --b-symbol"
    refusal is checked before the A series is read, so it wins over an absent A
    series.

19. **Row building before the lock.** Dates are parsed and split ratios checked
    before the series lock is taken, so a refused import or a failed leg
    (unparseable dates, degenerate ratio) leaves no `.lock` file or directory
    behind; store.feature's "store holds exactly the files" for a refused import
    requires this for the CSV path.

20. **`adjust` on an absent series.** Chosen: the StoreError is raised from a
    read-only check before the lock is taken (no directories created for a symbol
    the store never held); the message is the one of JDL-069.

21. **Re-adjust change detection.** "only when any value changed" - chosen:
    compare the columns the adjustment derives (open, high, low, close, volume,
    cumulative_split_factor) cell for cell, NaN equal to NaN.

22. **Reconcile writes.** A touched year file is rewritten with the full merged
    content of that year (stored rows, replacements, appended rows, sorted by
    timestamp); untouched years are not rewritten and nothing is pruned.

23. **Newest-n sessions.** Chosen exactly as store.md §5 reads: year files are
    read newest first until at least n rows are in hand, then the n most recent
    distinct UTC dates are returned ascending.

24. **Failed EODHD construction.** A missing key is not cached as a failure: each
    eodhd leg attempts construction again and fails with the same ValueError; a
    successful construction is reused for the rest of the run.

25. **`sync-actions --symbol` spelling.** Chosen: the actions files are saved
    under the symbol as given; the collector normalises it only for the request
    path (for a dotted symbol both are the same).

26. **Validation NaN rows.** "NaN in any required column" - chosen: NaN in any
    numeric column after coercion, or an empty Date cell; unparseable but
    non-empty dates are counted by the date note, not here.

27. **Validation warnings.** pandas' "Could not infer format ... dateutil"
    UserWarning (e.g. on `no_dates.csv`) is left to reach stderr; the original's
    validate calls the same pandas function and is assumed not to silence it.

28. **Numpy division warnings.** Divisions that can meet 0/0 on legal input (the
    adjustment_factor of a zero-close CSV row, resolution ticks, jump moves) are
    done under `np.errstate(ignore)`: pandas' own Series arithmetic, which the
    original is assumed to use, emits no RuntimeWarning there.

29. **Export Volume int32.** The int32 cast is applied whenever every volume is
    finite and integral, without an overflow guard (the kit states int32 only).

30. **Resolution fallback.** When no traded positive `close_raw` remains, the
    `close` column is taken through the same filters (traded, non-NaN, positive,
    newest window).

31. **Pair close.** Each side's close is the last row dated on the common
    session inside that side's newest `--window` rows.

32. **Universe: path missing on yahoo-csv.** Reported at the `path` step of the
    JDL-012 order (`missing required key 'path'`), before start/end are read.

33. **Universe: duplicate store coordinates.** Checked across every declared
    source, enabled or not, of every asset, enabled or not.

34. **Universe: `kind` of a non-string type.** Any value other than `"eod"`
    (including a non-string) gets the "is not supported" refusal with its repr.

35. **Universe file decoding.** An explicit file is read as bytes and decoded as
    UTF-8 before `tomllib.loads`, so the TOML error text is tomllib's own.

36. **Chain: task size set-if-unset.** "only when unset" read literally: an
    exported but empty JEF_TASK_VCPU / JEF_TASK_MEMORY_GB is kept as it is.

37. **Chain: metadata parsing.** Two one-line `python3 -c` programs read the
    metadata JSON on stdin, one for the digest (ImageDigest, else ImageID, else
    `unknown`, also on any failure) and one for `CPU` and `Memory / 1024`; the
    size is applied only when the second succeeds.

38. **Chain: which manifest is "first".** `find DIR -maxdepth 1 -name
    'run_manifest*.json' -print -quit` (directory order), as the contract lists
    `find` among the chain's commands.

39. **Chain: filters.** `--store` is written as `${STORE}` (= `data`); the
    command lines are byte-identical to the contract's.

40. **Leg containment.** `except Exception` (not BaseException): a
    KeyboardInterrupt still stops the run.

41. **Multi-line leg detail in the log.** A FAILED detail that spans lines (the
    no-fixture listing) is emitted as one log string containing newlines, i.e. one
    `out(...)` call per leg line.

42. **Rate limiter order.** The daily budget is checked before the sliding
    window, and the budget counter resets when the UTC date changes.

43. **classifications.toml `last_verified`.** Accepted as a TOML date or a
    10-character `YYYY-MM-DD` string; anything else would raise
    ClassificationError (unreachable with the packaged file).

44. **Prune.** A stale year file is deleted and its then-empty `year=` directory
    removed; the `.lock` file is never removed.

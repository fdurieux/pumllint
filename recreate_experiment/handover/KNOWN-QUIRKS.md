# Known quirks: reproduce, do not fix

Each of these looks like a defect. Each is the specified behaviour, pinned
by a requirement and a scenario, because the downstream consumers and the
acceptance suite depend on it. A build that "fixes" one fails the suite.
If you believe one should change, record it in `ASSUMPTIONS.md` and build
the specified behaviour anyway; the change is the specification owner's.

| quirk | what to build | requirement · scenario |
|---|---|---|
| The stored `timestamp` column holds Unix **seconds**, although the column is documented upstream as milliseconds (`2024-01-02` → `1704153600`). | Parse the bar date with the format inferred from the first bar; integer-divide the microsecond count by 10⁶. | JDL-060 · adjustment.feature "A two-split equity is stored raw and adjusted around both effective dates" |
| `export` of a series the store does not hold ends in pandas' own unhandled `AttributeError: Can only use .dt accessor with datetimelike values. Did you mean: 'at'?`, exit 1, no file written. Not a wrapped refusal. | Apply the export projection to the zero-row frame without a guard. | JDL-159 · cli.feature "Exporting a series the store does not hold ends in pandas' own AttributeError" |
| `differential` with an absent A side, or an absent B series named by `--b-symbol`, ends the same way. | Same: no guard. | JDL-163 · decisions.feature "The store commands on an absent series" |
| `import-csv` reports the number of CSV rows read, duplicates included, while only the first row of a duplicate date is stored (5 rows reported, 4 stored for the small fixture). | Count rows read; store first-of-duplicates. | JDL-070 · decisions.feature "A CSV leg overwrites whatever is there" |
| The corporate-actions stamp is always the real wall clock, even when a clock is injected through the adapter; so a second run on an earlier injected day finds the actions "fresh". | `now` reaches the window, the end-guard, the actions gate and the today-dated check; never the stamp. | JDL-043, JDL-088 · actions.feature "A later run on an earlier injected day finds the real-clock stamp fresh unless forced" |
| A filled series whose declared `end` predates its tail sends no request and the leg stays **green**, with a detail line saying the fix is the declaration. | Zero bars, `ok`, the exact detail text. | JDL-095 · sync.feature "A series with rows past its declared end fetches nothing and stays green" |
| An empty series with the same inverted window still sends its request. | Only the filled case short-circuits. | JDL-095 · decisions.feature "An empty series sends its request even when the end-guard falls before the declared start" |
| `--staleness` is a flag; the corporate-actions freshness threshold (2 refresh sessions) is not, and `actions_missed_k` is documented but not exposed. | Fixed constant. | JDL-125 · status.feature "Corporate-actions freshness counts the refresh sessions missed since the stamp" |
| A phantom-split jump is excused by a same-day split only for actions-eligible legs; a crypto leg with the same bars alerts. | Read splits only when eligible. | JDL-124, JDL-086 · status.feature "A same-day split excuses a jump only where splits are read" |
| The declared asset class decides basis, actions and the end-guard; the symbol suffix never does. A `.CC` symbol declared stock is raw basis and actions-eligible. | Resolve from `asset_class`, not from the ticker. | JDL-086, JDL-053 · adjustment.feature "The declared class, never the .CC suffix, decides basis, actions and guard" |
| `sync --tail 0` is refused before any selection or store access, even when `--asset` names an unknown asset. | Check `tail` first. | JDL-087 · sync.feature "Selection refusals of sync and status" |
| Parse errors print the failing parser's usage and are reported by the **top-level** parser for arguments no parser recognises, even after a valid subcommand. | Plain `argparse`, declared exactly as `cli.md` "Parser surface" says. | JDL-161 · cli.feature "Parser errors print the failing parser's usage and one error line" |

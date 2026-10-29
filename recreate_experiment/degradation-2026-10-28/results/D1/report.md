The rebuild passes the kit's acceptance suite in full: **258/258 on run 1 and 258/258 on run 2**. I made no code change between the two runs and did not use run 3. Both runs are recorded in `RUNS.md`.

**Module layout.** It follows `uml/component.puml`. The package `jef_data_rc` holds `cli`, `universe`, `sync`, `health` (the status checks), `classification`, `actions`, `adjust`, `store`, `contract` (validation) and `differential`, plus `collectors/` (`base`, `eodhd`, `binance`, and `transport` for the live, replay and recording transports). The two packaged TOML files are byte-identical copies from the kit. The console script is `jef-data-rc`, but the parser's prog is fixed to `jef-data`, so every `--help` block and parser error matches byte for byte. The pyproject declares only the four pinned runtime dependencies.

**How I tested.** Before the first suite run I checked my own scripts against the kit's expected frames, messages, help texts and the chain stub. The suite runs used `-p no:cacheprovider` and `PYTHONDONTWRITEBYTECODE=1`, so nothing was written into the kit; `sha256sum -c MANIFEST.sha256` still passes.

**Two things that differ from a plain reading of the brief:**
- **Install command:** a plain `pip install -e out` would try to fetch setuptools from the network. I installed with `pip install --no-build-isolation -e out` instead (assumption A-04).
- **Command name in the chain:** `daily-rc.sh` calls `jef-data`, as the chain contract says. A real deployment of this rebuild therefore needs `jef-data-rc` exposed under that name (A-03).

**Assumptions:** 28 entries in `ASSUMPTIONS.md` (A-01 to A-28). A-28 lists small kit inconsistencies for the kit's owner: the README's reading order numbered 1, 2, 5, 3, 4; refusal X-11 listed before X-10; and the glossary and component diagram still showing the old `(status, text)` transport return.

**Five hardest judgement calls:**
1. **Lock timing:** I parse dates, raw-ize volume and check split ratios before taking the store lock. That is the only way a refused import leaves zero files, which the suite checks. The re-adjustment still takes the lock first, as the store contract says, so `adjust` on an absent series leaves a `.lock` behind (A-11).
2. **Absent-series export:** I deliberately apply the export projection without a guard. pandas' own `.dt` AttributeError, with CPython's "Did you mean: 'at'?" suggestion, then becomes the exact last line the kit requires.
3. **Timestamps:** I store Unix seconds by integer-dividing the microsecond count by 10^6, even though the store contract calls the column milliseconds. The requirement and every fixture use seconds (A-28).
4. **Differential details the kit leaves open:** the missing-B-side refusal is checked before either series is read; duplicate dates are compared on the first row per date; and with no common dates the line prints `max 0.000%` (A-15).
5. **Chain details:** empty task-size variables are treated as unset, the first manifest is found with `find -print -quit`, and the metadata parsers are single-line `python3 -c` programs so the stubbed call log stays one record per call (A-17, A-18).

Files are in `/tmp/claude-0/-home-user/2202db69-14ed-511e-bcae-bbd1469c53f1/scratchpad/rb-8a26f756/out/`:
- `pyproject.toml`
- `jef_data_rc/`
- `daily-rc.sh`
- `adapter_rc.py`
- `ASSUMPTIONS.md`
- `READ.log` (210 paths)
- `RUNS.md`
- `events.sh` and `dashboard.sh` (the given externals, unchanged)
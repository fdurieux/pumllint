# The plant bundle

Hidden until grading (PREREGISTRATION.md §4); its hash was pushed before the first rebuild.

| path | what |
|---|---|
| `walk.md` | the selection walk: every candidate, its tests T1-T4, the conventions C1-C7, the selection |
| `plant.md` | the plant: per-arm edits, the conventions P1-P5, the D2 repair, the V results, the gate readouts |
| `order_top60.txt` | the first 60 ids of the pre-registered order (`tools/order.py` regenerates it) |
| `patches/<arm>.patch` | each degraded kit against the pristine kit (`patch -p1 -E` in a kit copy reproduces it) |
| `mutants/<id>.patch` | every mutant against J-F `8f6d6b0` (`src/jef/data`, and `deploy/` for chain mutants) |
| `observing/<id>.json` | each mutant's observing set and the members outside the K2-identical 146 |
| `suites/<label>.txt` | failures and totals of every suite run: `calib-<id>` the pristine kit on a mutant, `V*` the checks |
| `gates/<arm>.txt` | G1-G5 on each kit (`ref` the pristine kit) |
| `scripts/` | `edit.py` and the per-arm edit specs, the expected-frame formatter, the table editor, `v1.py` |
| `regen/` | D3's data regeneration: the glue instrumentation, the dumped frames and cells |
| `tools/` | the lab tools (mutant copy, observe, suite runner, order) |

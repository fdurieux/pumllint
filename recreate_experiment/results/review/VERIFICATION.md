# Spot-check of the post-hoc review (this session, 2026-10-23)

The review (`REVIEW.md`) is a fresh Opus 5 agent's reading of the kit's
eight diagrams and J-F's existing nine against the source tree. Four of
its verdicts were checked here:

| Row | Reviewer | Check | Outcome |
|---|---|---|---|
| `basis_and_adjustment`: "timestamp in Unix seconds" is wrong, it is milliseconds | A defect | **Executed**: the reference run's stored TLT series has `timestamp` 1583107200 for 2020-03-02, which is seconds (ms would be 1583107200000) | **Overturned.** The kit is right; the reviewer read the schema comment, as the source's own comment is wrong. A defects 13 → 12 |
| `data_contract_model` puts `select_legs` on `Universe` | B defect | Read: `class Universe <<config>>` lists `+select_legs(assets, providers)`; the function is `sync.select_legs` | **Confirmed** |
| `daily_chain` (kit): no status gate | A defect | Read: the diagram calls `status` and tees its JSON but draws no branch on its exit before binning; `daily.sh` exits on a non-zero status | **Confirmed** (the gate is implemented and verified by the kit's scenarios; the diagram does not draw it) |
| `ops_daily_chain` (existing): a failed sync carries on | B defect | Not independently read in full; the reviewer cites the diagram's alt structure and `daily.sh:140` | **Taken as the reviewer's** |

Adjusted counts: 33 disagreements; kit right 19 (+1 after the
overturn: 20), existing right 8 (−1: 7); A defects 12, B defects 25;
blind spots unchanged (A misses 15, B misses 16). Every other row is the
reviewer's reading, cited to the source, and unverified here.

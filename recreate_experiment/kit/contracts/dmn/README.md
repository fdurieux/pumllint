# Decision tables (revision 2026-10-23 (wave 2))

Standard DMN 1.3 XML, one `decision` per table, hit policy UNIQUE, every
rule carrying a `description` that cites the requirement or contract line
it encodes. Written by `harness/dmn_build.py` through `harness/dmn_write.py`
(edit the build script, not the XML); checked by `harness/dmn_check.py`
(gaps, overlaps, untyped outputs); joined to `features/decisions.feature`
by `harness/dmn_coverage.py`.

| file | tables | decides |
|---|---|---|
| `basis.dmn` | `price_basis_resolution`, `volume_raw_source` | provider × declared asset_type → price basis, split events applied, actions eligibility; what `volume_raw` holds |
| `command_store_state.dmn` | `command_by_store_state` | each store-touching command × absent / filled series → outcome and message (the wave-2 differential rows measured on the original) |
| `sync_window.dmn` | `fetch_start`, `fetch_end`, `bar_request` | the leg's window and whether a bar request is sent |
| `actions_gate.dmn` | `actions_gate` | eligibility × force × stamp → refresh / fresh / none |
| `status_verdicts.dmn` | `staleness_check`, `actions_freshness_check`, `phantom_jump_check`, `cross_venue_spread_check`, `status_exit_and_flag` | the status findings and the exit code |
| `refusal_routing.dmn` | `refusal_routing` | where an error is raised → wrapped / leg failed / traceback / usage, exit code, stderr form |

Numeric inputs that are counts carry `typeRef="integer"` and an
`inputValues` constraint (`>= 0`); thresholds are encoded at the program's
defaults and say so in the table's description.

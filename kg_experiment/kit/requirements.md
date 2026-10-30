# CargoQuote requirements (authored 2026-10-30 for kg_experiment)

Each requirement quotes one acceptance criterion or normative rule of
`../../stack_experiment/cargo_quote/contract/spec.md` and
`contract/decision_table.md` verbatim and gives it an id. The ids are
this experiment's; the kit itself carries none. Numbers live only in
the decision tables, as the kit's design rule says.

| id | requirement (verbatim source in brackets) |
|---|---|
| REQ-01 | valid request, accept-band risk index → `quoted`, priced per DT-P, stored, quote document sent [spec.md criterion 1] |
| REQ-02 | valid request, review-band risk index → `review_hold`, stored, **no** price, **no** notification [spec.md criterion 2] |
| REQ-03 | valid request, refuse-band risk index → `refused_screening`, stored, **no** price, refusal notice sent [spec.md criterion 3] |
| REQ-04 | any DT-V violation → `rejected: invalid_request`, nothing else runs [spec.md criterion 4] |
| REQ-05 | storage failure → `error: store_unavailable`, nothing else runs [spec.md criterion 5] |
| REQ-06 | screening outage → `held_unscreened` with price and `hold: true`, **no** notification [spec.md criterion 6] |
| REQ-07 | notification delivery failure → outcome and response unchanged [spec.md criterion 7] |
| REQ-08 | long-haul multiplier: if `distance_km >= 4912`, multiply the running total by `1.19` — applied **after** P2 [decision_table.md DT-P P3; "the order is normative"] |

`screening_decision.dmn` mirrors DT-S as a DMN 1.3 decision table;
`decision_table.md` remains the normative text. `quote_process.bpmn`
draws the flow order of spec.md as a BPMN 2.0 process.

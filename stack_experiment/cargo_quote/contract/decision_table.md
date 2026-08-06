# CargoQuote decision tables

The normative decision semantics of CargoQuote. Where any diagram is
silent or qualitative, these tables are the authority. All boundaries
are inclusive exactly as written. The values are deliberately
**non-canonical** (see stack_experiment/README.md): no industry
convention or model prior produces them — an implementation can only
get them from this document.

## DT-V — request validation (checked before anything else)

A request is **valid** iff every row holds:

| # | Field | Rule |
|---|---|---|
| V1 | `shipper_id` | present and non-empty |
| V2 | `weight_kg` | number, `3 <= weight_kg <= 19400` |
| V3 | `distance_km` | number, `25 <= distance_km <= 7150` |
| V4 | `declared_value` | number, `50 <= declared_value <= 83000` |

An invalid request is rejected immediately with status
`rejected: invalid_request`. No draft is stored, no screening is
performed, no price is computed, and no notification is sent.

## DT-S — screening decision (risk banding)

`risk_index` is the integer returned by the Screening Service; higher
is worse. Symbolic names used by the diagrams: `ACCEPT_MAX = 41`,
`REVIEW_MIN = 42`, `REVIEW_MAX = 66`, `REFUSE_MIN = 67`.

| Row | Condition | Decision | Priced? | Notified? | Status |
|---|---|---|---|---|---|
| accept | `risk_index <= 41` | quote issued | yes | yes (quote document) | `quoted` |
| review | `42 <= risk_index <= 66` | held for manual review | **no** | **no** | `review_hold` |
| refuse | `risk_index >= 67` | refused | **no** | **yes** (refusal notice) | `refused_screening` |

Boundary readings, spelled out: 41 is accepted; 42 is review; 66 is
review; 67 is refused.

Notes (normative):

1. A review hold is not a final outcome: no price is computed and no
   notification is sent on the review path.
2. A refusal **is** notified (refusal notice), and pricing never runs
   on a refused quote.
3. On storage failure nothing else runs: no screening call, no
   pricing, no notification; status `error: store_unavailable`.
4. Notification is fire-and-forget: a delivery failure never changes
   the stored quote or the response.
5. A screening outage does **not** fail the quote: the quote is still
   priced, stored with status `held_unscreened`, and **not** notified
   until screening completes (out of scope here). The response carries
   the price and `hold: true`.

## DT-P — pricing (only on DT-S rows accept and screening-outage hold)

| Step | Rule |
|---|---|
| P1 | `base = 0.87 * weight_kg + 1.13 * distance_km` |
| P2 | heavy surcharge: if `weight_kg > 1244`, add `316.00` (flat) |
| P3 | long-haul multiplier: if `distance_km >= 4912`, multiply the running total by `1.19` — applied **after** P2 |
| P4 | `price = round(result, 2)` |

Worked example (both surcharges): `weight_kg = 1500`,
`distance_km = 5000` → base `1305.00 + 5650.00 = 6955.00` → +316 →
`7271.00` → ×1.19 → **`8652.49`**. (Applying P3 before P2 gives the
wrong `8592.45` — the order is normative.)

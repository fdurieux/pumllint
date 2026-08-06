# CargoQuote — companion specification (instant freight quotation)

Supplementary structured specification accompanying the CargoQuote
diagrams. The diagrams define structure and flow shape; this document
plus [decision_table.md](decision_table.md) pin the decision
semantics, validation rules, error policy, and API contract. Where a
diagram is silent or qualitative, these documents are the authority.
All numeric rules live in the decision tables (DT-V, DT-S, DT-P) —
this document never restates a number, so the two cannot drift.

## Glossary

- **Quote request**: one request for a freight price — `shipper_id`,
  `weight_kg` (chargeable weight, kg), `distance_km` (routed road
  distance), `declared_value` (EUR, for liability).
- **Risk index**: integer returned by the Screening Service for a
  shipper; **higher is worse**.
- **Quote outcome**: exactly one of `quoted`, `review_hold`,
  `refused_screening`, `held_unscreened` (screening outage), plus the
  rejection/error statuses in the API contract below.
- **Quote document / refusal notice**: messages delivered to the
  shipper via the Notification Service, only on the DT-S rows that
  say so.

## Flow order and error policy

1. Validate the request (DT-V). Invalid → reject, stop.
2. Store the draft quote in the Quote Store with status `draft`.
   If storage fails: return `error: store_unavailable`; do not call
   screening; do not price; do not notify (DT-S note 3).
3. Request the shipper's risk index from the Screening Service.
   If screening is unavailable: price anyway (DT-P), update the
   stored quote to `held_unscreened`, do **not** notify, and return
   the price with `hold: true` (DT-S note 5).
4. Apply the screening decision (DT-S) to the risk index. Update the
   stored quote to the resulting status.
5. Price the quote (DT-P) — only on the rows DT-S marks priced.
6. Notify the shipper — only on the rows DT-S marks notified;
   fire-and-forget (DT-S note 4).
7. Return the response.

## API contract

Request (JSON object): `shipper_id` (string, required), `weight_kg`
(number, required), `distance_km` (number, required),
`declared_value` (number, required). Bounds: DT-V.

Response (JSON object): `status` is exactly one of

- `"quoted"` | `"review_hold"` | `"refused_screening"` |
  `"held_unscreened"`
- `"rejected: invalid_request"`
- `"error: store_unavailable"`

plus `quote_id` (string) whenever a draft was stored, `price`
(number) exactly on the priced rows (DT-S), and `hold: true` exactly
on `held_unscreened`.

Machine-readable request/response shapes: [openapi.yaml](openapi.yaml).

## Acceptance criteria (qualitative — see tests_input/ for scenarios)

| # | Given | Then |
|---|---|---|
| 1 | valid request, accept-band risk index | `quoted`, priced per DT-P, stored, quote document sent |
| 2 | valid request, review-band risk index | `review_hold`, stored, **no** price, **no** notification |
| 3 | valid request, refuse-band risk index | `refused_screening`, stored, **no** price, refusal notice sent |
| 4 | any DT-V violation | `rejected: invalid_request`, nothing else runs |
| 5 | storage failure | `error: store_unavailable`, nothing else runs |
| 6 | screening outage | `held_unscreened` with price and `hold: true`, **no** notification |
| 7 | notification delivery failure | outcome and response unchanged |

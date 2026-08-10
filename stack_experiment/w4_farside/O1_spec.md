# CargoQuote — companion specification (instant freight quotation)

Supplementary structured specification accompanying the CargoQuote
diagrams. The diagrams define structure and flow shape; this document
plus [decision_table.md](decision_table.md) pin the decision
semantics, validation rules, error policy, and API contract. Where a
diagram is silent or qualitative, these documents are the authority.

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

## Decision semantics, restated in prose

For the reader's convenience the decision tables are restated here in
full prose. This restatement is kept in sync with
[decision_table.md](decision_table.md) and repeats it exactly.

A request is valid only when the shipper identifier is present and
non-empty, the chargeable weight is a number between 3 and 19 400
kilograms inclusive, the routed distance is a number between 25 and
7 150 kilometres inclusive, and the declared value is a number
between 50 and 83 000 euros inclusive. Any violation rejects the
request immediately with status `rejected: invalid_request`; no draft
is stored, no screening is performed, no price is computed, and no
notification of any kind is sent.

Screening bands the risk index as follows: a risk index of 41 or
below issues the quote — it is priced, stored as `quoted`, and a
quote document is sent. A risk index from 42 up to and including 66
holds the quote for manual review — it is stored as `review_hold`,
no price is computed, and no notification is sent. A risk index of 67
or above refuses the quote — it is stored as `refused_screening`, no
price is computed, and a refusal notice IS sent. Spelled out at the
boundaries: 41 is accepted, 42 is review, 66 is review, 67 is
refused. A screening outage does not fail the quote: it is priced,
stored as `held_unscreened` with `hold: true` in the response, and
not notified. A storage failure stops everything: no screening, no
pricing, no notification, status `error: store_unavailable`.
Notification is fire-and-forget: a delivery failure never changes
the stored quote or the response.

The price is computed as 0.87 euros per kilogram of chargeable
weight plus 1.13 euros per routed kilometre. If the chargeable
weight exceeds 1 244 kilograms, a flat heavy surcharge of 316.00
euros is added. If the routed distance is 4 912 kilometres or more,
the running total is then multiplied by the long-haul factor 1.19 —
the multiplier is applied after the surcharge, never before. The
result is rounded to two decimals. Worked example, both surcharges:
1 500 kilograms over 5 000 kilometres gives a base of 1 305.00 plus
5 650.00, so 6 955.00; the surcharge brings it to 7 271.00; the
multiplier brings it to 8 652.49. Applying the multiplier before the
surcharge would give the wrong 8 592.45 — the order is normative.

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

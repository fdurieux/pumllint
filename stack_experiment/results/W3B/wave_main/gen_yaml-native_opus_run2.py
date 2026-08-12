_notes:
  screening_thresholds: see DT-S for ACCEPT_MAX, REVIEW band, REFUSE_MIN
  pricing_inputs: price depends only on weightKg and distanceKm, never on declaredValue


--- FILE: spec/cargoquote.md ---
# CargoQuote — quotation behraviour spec

This companion describes the quotation flow the code must implement. It
refers to decision tables DT-V (validation) and DT-S (screening).

## Actors and collaborators

- **Shipper** — submits the quote request, receives the outcome.
- **Quote API** — orchestrates the flow.
- **Tariff Engine** — computes price from weight and distance.
- **Screening Service** (external) — returns a shipper *risk index*.
- **Notification Service** (external) — delivers documents/notices.
- **Quote Store** — persists quote records and status.

## Request shape

A quote request carries:

- `shipperId` — non-empty identifier of the shipper.
- `weightKg` — chargeable weight in kilograms.
- `distanceKm` — haul distance in kilometres.
- `declaredValue` — declared consignment value; recorded for audit but
  **not** an input to the price.

## Validation — decision table DT-V

DT-V governs `requestQuote` acceptance. All bounds are inclusive.

| rule | condition                          | outcome                        |
|------|------------------------------------|--------------------------------|
| V1   | shipperId missing/empty            | reject — invalidShipper        |
| V2   | weightKg <= 0                      | reject — invalidWeight         |
| V3   | weightKg > 26000                   | reject — weightExceedsMax      |
| V4   | distanceKm <= 0                    | reject — invalidDistance       |
| V5   | distanceKm > 3000                  | reject — distanceExceedsMax    |
| V6   | declaredValue < 0                  | reject — invalidDeclaredValue  |
| V7   | all bounds satisfied               | accept — proceed to storeDraft |

The maxima reflect a single full trailer: 26 t payload and a 3000 km
national haul limit.

## Pricing

The price is computed by the Tariff Engine from `weightKg` and
`distanceKm` only. `declaredValue` must not influence the price.

## Screening decision — decision table DT-S

DT-S governs the screening decision using the `riskIndex` returned by
the Screening Service. Thresholds are inclusive.

| rule | condition                    | status              | priced | notified            | terminal response         |
|------|------------------------------|---------------------|--------|---------------------|---------------------------|
| S1   | riskIndex <= 20              | quoted              | yes    | quote document      | quotedResponse            |
| S2   | 21 <= riskIndex <= 60        | review-hold         | no     | none                | reviewHoldResponse        |
| S3   | riskIndex >= 61              | refused-screening   | no     | refusal notice      | refusedScreeningResponse  |
| S4   | screening service unavailable| held-unscreened     | yes    | none                | heldUnscreenedResponse    |

Notes:
1. **Review hold is not final** — S2 performs no pricing and sends no
   notification; the consignment waits for the compliance team.
2. **Refusal is notified** — S3 sends a refusal notice but never prices.
3. **Storage failure stops everything** — if `storeDraft` fails, there
   is no screening, no pricing and no notification.
4. **Notifications are fire-and-forget** — a notification failure never
   changes the response the shipper receives (applies to S1 and S3).
5. **Screening outage is not fatal** — S4 still prices the consignment
   and stores it on hold, but sends no notification.

## Status vocabulary

`draft`, `quoted`, `review-hold`, `refused-screening`,
`held-unscreened`.


--- FILE: acceptance/quote.feature ---
Feature: CargoQuote instant freight quotation

  Background:
    Given the tariff and screening thresholds are configured

  Scenario: Clean shipper gets an instant quote
    Given a shipper "ACME-001" with a valid consignment
    And the screening service returns risk index 10
    When the shipper requests a quote
    Then the quote is priced by the tariff engine
    And the quote document is sent to the shipper
    And the response status is "quoted"

  Scenario: Mid-risk shipper is held for manual review
    Given a shipper "ACME-014" with a valid consignment
    And the screening service returns risk index 45
    When the shipper requests a quote
    Then no price is computed
    And no notification is sent
    And the response status is "review-hold"

  Scenario: Denied party is refused and notified
    Given a shipper "BADCO-9" with a valid consignment
    And the screening service returns risk index 88
    When the shipper requests a quote
    Then no price is computed
    And a refusal notice is sent to the shipper
    And the response status is "refused-screening"

  Scenario: Screening outage holds the quote unscreened
    Given a shipper "ACME-020" with a valid consignment
    And the screening service is unavailable
    When the shipper requests a quote
    Then the quote is priced by the tariff engine
    And the quote is stored as held unscreened
    And the response status is "held-unscreened"

  Scenario: Overweight consignment is rejected at validation
    Given a shipper "ACME-050" with a consignment of 26001 kg over 100 km
    When the shipper requests a quote
    Then the request is rejected before screening
    And the response status is "invalid"

  Scenario: Storage outage stops the flow
    Given a shipper "ACME-777" with a valid consignment
    And the quote store is unavailable
    When the shipper requests a quote
    Then no screening is performed
    And the response status is "error"
```

Output ONLY Python code. No markdown fences, no prose.
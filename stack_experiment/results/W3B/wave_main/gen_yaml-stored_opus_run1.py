--- FILE: spec/quotation.md ---
# CargoQuote quotation — companion spec

This document pins down the decision tables, bounds and status vocabulary
the diagrams reference.

## Request validation — decision table DT-V

All bounds are inclusive. A request is **valid** only if every row passes.

| field         | rule                          | on failure                     |
|---------------|-------------------------------|--------------------------------|
| shipperId     | non-empty string              | reject: invalid_shipper        |
| weightKg      | 1 ≤ weightKg ≤ 26000          | reject: invalid_weight         |
| distanceKm    | 1 ≤ distanceKm ≤ 3000         | reject: invalid_distance       |
| declaredValue | 0 ≤ declaredValue ≤ 1000000   | reject: invalid_value          |

The checks are ordered: shipperId, then weightKg, then distanceKm, then
declaredValue. The first failing row determines the rejection reason.

## Screening decision — decision table DT-S

The screening provider returns a **risk index** in [0, 100]. Bounds are
inclusive:

| row    | condition             | price? | store status            | notify?         | response                  |
|--------|-----------------------|--------|-------------------------|-----------------|---------------------------|
| accept | riskIndex ≤ 29        | yes    | quoted                  | quote document  | quoted                    |
| review | 30 ≤ riskIndex ≤ 69   | no     | review_hold             | no              | review_hold               |
| refuse | riskIndex ≥ 70        | yes*   | refused_screening       | refusal notice  | refused_screening         |

\* Refuse never prices: the "yes\*" marks the historical trap; pricing
does not run on refuse. See note 2.

Notes:
1. **review** is a non-final hold: no pricing, no notification.
2. **refuse** notifies a refusal notice but never prices.
3. On **storeDraft** failure nothing else runs.
4. Notification is fire-and-forget; delivery failure never changes the response.
5. **Screening outage** does not fail the quote: price it, store `held_unscreened`, do not notify.

## Price computation

`price = base + perKg × weightKg + perKm × distanceKm`, rounded to 2 decimals.
Constants: `base = 25.00`, `perKg = 0.35`, `perKm = 0.12`.

## Status vocabulary

`draft`, `quoted`, `review_hold`, `refused_screening`, `held_unscreened`.

## Screening thresholds

`ACCEPT_MAX = 29`, `REVIEW_MIN = 30`, `REVIEW_MAX = 69`, `REFUSE_MIN = 70`.


--- FILE: features/quotation.feature ---
Feature: CargoQuote instant freight quotation
  Shippers submit consignment details and receive an immediate
  quotation outcome: a priced quote, a manual-review hold, or a
  screening refusal.

  Background:
    Given the tariff constants base=25.00, perKg=0.35, perKm=0.12
    And the screening thresholds ACCEPT_MAX=29, REVIEW_MIN=30, REVIEW_MAX=69, REFUSE_MIN=70

  Scenario: Clean shipper gets an instant quote
    Given a shipper "ACME-001" with a valid consignment
    And the screening service returns risk index 10
    When the shipper requests a quote for weight 1000 kg over 250 km declaring 5000 value
    Then the quote is priced at 405.00
    And the quote status is "quoted"
    And a quote document is sent to the shipper

  Scenario: Mid-risk shipper is held for manual review
    Given a shipper "ACME-002" with a valid consignment
    And the screening service returns risk index 50
    When the shipper requests a quote
    Then no price is computed
    And the quote status is "review_hold"
    And no notification is sent

  Scenario: High-risk shipper is refused
    Given a shipper "ACME-003" with a valid consignment
    And the screening service returns risk index 85
    When the shipper requests a quote
    Then the quote status is "refused_screening"
    And a refusal notice is sent to the shipper
    And no price is computed

  Scenario: Screening outage holds the quote unscreened
    Given a shipper "ACME-004" with a valid consignment
    And the screening service is unavailable
    When the shipper requests a quote for weight 2000 kg over 100 km declaring 8000 value
    Then the quote is priced at 737.00
    And the quote status is "held_unscreened"
    And no notification is sent

  Scenario: Invalid request is rejected before screening
    Given a shipper "ACME-005"
    When the shipper requests a quote for weight 0 kg over 250 km declaring 5000 value
    Then the request is rejected with reason "invalid_weight"
    And nothing is stored
    And no screening call is made
@enduml

Let me implement this.
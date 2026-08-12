--- FILE: spec/cargo_quote.md ---
# CargoQuote — quotation flow specification

This document specifies the **synchronous quotation flow**: from a
shipper's quote request to the outcome (quoted, held for review, held
unscreened, refused, or rejected). It is the companion to the container
diagram and the `quote_flow.yaml` behaviour bundle.

## Participants

| Role | Element | Responsibility |
|------|---------|----------------|
| Orchestrator | `QuoteAPI` | Validates the request, coordinates screening and pricing, persists lifecycle state, returns the outcome |
| Pricing | `TariffEngine` | Computes the freight price from weight and distance |
| Screening | `ScreeningService` (ext) | Returns a shipper risk index |
| Notification | `NotificationService` (ext) | Delivers quote documents and refusal notices |
| Persistence | `QuoteStore` | Stores quote records and lifecycle status |

## Lifecycle states

A quote record moves through these statuses:

- `DRAFT` — request accepted and stored, screening not yet done
- `QUOTED` — priced and offered to the shipper
- `REVIEW_HOLD` — screening flagged the shipper for manual compliance review
- `HELD_UNSCREENED` — screening provider was unavailable; priced but withheld pending screening
- `REFUSED_SCREENING` — screening refused the shipper; no price offered

## Screening thresholds

The shipper risk index is a number from 0 to 100. Thresholds:

- `ACCEPT_MAX = 39` — index at or below this is accepted and quoted
- `REVIEW_MIN = 40`, `REVIEW_MAX = 69` — index in this band is held for review
- `REFUSE_MIN = 70` — index at or above this is refused

## Decision tables

### DT-V — request validation

All conditions must hold for the request to be valid. Bounds are inclusive.

| # | Condition | Rule |
|---|-----------|------|
| 1 | `shipperId` present and non-empty | required |
| 2 | `weightKg` present, numeric, `1 <= weightKg <= 26000` | required |
| 3 | `distanceKm` present, numeric, `1 <= distanceKm <= 4000` | required |
| 4 | `declaredValue` present, numeric, `declaredValue >= 0` | required |

If any condition fails, the request is rejected with `rejectedInvalidRequest`
and nothing is stored.

### DT-S — screening outcome

| Risk index band | Status | Priced? | Notified? | Response |
|-----------------|--------|---------|-----------|----------|
| `<= 39` (accept) | `QUOTED` | yes | quote document | `quotedResponse` |
| `40..69` (review) | `REVIEW_HOLD` | no | no | `reviewHoldResponse` |
| `>= 70` (refuse) | `REFUSED_SCREENING` | no | refusal notice | `refusedScreeningResponse` |
| screening unavailable | `HELD_UNSCREENED` | yes | no | `heldUnscreenedResponse` |

Notes:
1. Review hold is not final — no pricing and no notification on that path.
2. Refusal is notified but never priced.
3. On storage failure nothing else runs.
4. Notification is fire-and-forget: delivery failure never changes the response.
5. Screening outage does not fail the quote: price it, hold it unscreened, don't notify.

## Tariff (informative)

The Tariff Engine computes price from weight and distance. A simple
published formula: `price = base + perKg * weightKg + perKmPerTonne *
distanceKm * (weightKg / 1000)`, with `base = 25.00`, `perKg = 0.35`,
`perKmPerTonne = 0.012`. Rounded to 2 decimals. The exact constants are
informative; treat pricing as a single collaborator call that returns a
price.

## Acceptance scenarios

See `acceptance/quote.feature`.


--- FILE: acceptance/quote.feature ---
Feature: CargoQuote instant freight quotation

  Background:
    Given the tariff engine is configured
    And the screening service is reachable unless stated otherwise

  Scenario: Low-risk shipper is quoted immediately
    Given a shipper "ACME-01" with a valid consignment
    And the screening service returns risk index 12
    When the shipper requests a quote
    Then the quote status is "QUOTED"
    And a price is computed from weight and distance
    And a quote document is sent to the shipper
    And the response is "quotedResponse"

  Scenario: Mid-risk shipper is held for manual review
    Given a shipper "ACME-02" with a valid consignment
    And the screening service returns risk index 55
    When the shipper requests a quote
    Then the quote status is "REVIEW_HOLD"
    And no price is computed
    And no notification is sent
    And the response is "reviewHoldResponse"

  Scenario: High-risk shipper is refused
    Given a shipper "ACME-03" with a valid consignment
    And the screening service returns risk index 88
    When the shipper requests a quote
    Then the quote status is "REFUSED_SCREENING"
    And no price is computed
    And a refusal notice is sent to the shipper
    And the response is "refusedScreeningResponse"

  Scenario: Screening provider is unavailable
    Given a shipper "ACME-04" with a valid consignment
    And the screening service is unavailable
    When the shipper requests a quote
    Then the quote status is "HELD_UNSCREENED"
    And a price is computed from weight and distance
    And no notification is sent
    And the response is "heldUnscreenedResponse"

  Scenario: Invalid request is rejected up front
    Given a shipper "ACME-05" with a consignment weighing 0 kg
    And the screening service is reachable
    When the shipper requests a quote
    Then the quote status is "rejected"
    And nothing is stored
    And no screening call is made
    And the response is "rejectedInvalidRequest"

  Scenario: Storage is unavailable
    Given a shipper "ACME-06" with a valid consignment
    And the quote store is unavailable
    When the shipper requests a quote
    Then the response is "storeUnavailableError"
    And no screening call is made
    And no price is computed
    And no notification is sent
@enduml
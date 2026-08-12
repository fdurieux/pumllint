--- FILE: behavior/screening.md ---
# Screening decision — companion spec

The **risk index** returned by the screening provider is an integer on
a 0–100 scale.

## Decision table DT-S (screening outcome)

| Row    | Condition (riskIndex r)   | Price? | Store status              | Notify?           | Response                    |
|--------|---------------------------|--------|---------------------------|-------------------|-----------------------------|
| accept | `r <= 29`                 | yes    | `QUOTED`                  | quote document    | `quotedResponse`            |
| review | `30 <= r <= 69`           | no     | `REVIEW_HOLD`             | none              | `reviewHoldResponse`        |
| refuse | `r >= 70`                 | no     | `REFUSED_SCREENING`       | refusal notice    | `refusedScreeningResponse`  |
| outage | screening call failed     | yes    | `HELD_UNSCREENED`         | none              | `heldUnscreenedResponse`    |

Boundary notes: `ACCEPT_MAX = 29`, `REVIEW_MIN = 30`, `REVIEW_MAX = 69`,
`REFUSE_MIN = 70`. The three live-score bands are contiguous and cover
the whole 0–100 range; there is no gap or overlap at the boundaries.

Notes:
1. **review** is a non-final hold: no pricing and no notification.
2. **refuse** is notified but never priced.
3. On **storeDraft** failure nothing else runs.
4. On **accept**, notification is fire-and-forget: delivery failure
   never changes the response.
5. On **outage**, the quote is priced and stored as `HELD_UNSCREENED`
   but not notified; the shipper still gets a concrete response.

--- FILE: behavior/validation.md ---
# Request validation — companion spec

Validation runs first, before any screening or pricing. A request that
fails validation is rejected immediately and nothing is stored.

## Decision table DT-V (request validation)

| Rule | Condition                                  | Outcome                       |
|------|--------------------------------------------|-------------------------------|
| V1   | `shipperId` missing or empty               | `rejectedInvalidRequest`      |
| V2   | `weightKg <= 0` or `weightKg > 26000`      | `rejectedInvalidRequest`      |
| V3   | `distanceKm <= 0` or `distanceKm > 3000`   | `rejectedInvalidRequest`      |
| V4   | `declaredValue < 0`                        | `rejectedInvalidRequest`      |
| V5   | all bounds satisfied                       | proceed to screening          |

All four field checks are independent; any single failure rejects the
whole request. Bounds are inclusive where shown (`weightKg` up to and
including 26000 kg is valid; `distanceKm` up to and including 3000 km is
valid).

## Tariff (for reference by the pricing step)

Price = base + per-kg component + per-km component, computed by the
Tariff Engine from `weightKg` and `distanceKm`. Declared value does not
affect the price in this release (it is recorded for screening and
audit only).


--- FILE: acceptance/quote.feature ---
Feature: CargoQuote instant freight quotation

  Scenario: Clean shipper gets an instant quote
    Given a valid quote request from a low-risk shipper
    When the shipper requests a quote
    Then the quote is priced and stored as QUOTED
    And a quote document is sent
    And the response is quotedResponse

  Scenario: Mid-risk shipper is held for manual review
    Given a valid quote request from a mid-risk shipper
    When the shipper requests a quote
    Then no price is computed
    And the quote is stored as REVIEW_HOLD
    And no notification is sent
    And the response is reviewHoldResponse

  Scenario: High-risk shipper is refused
    Given a valid quote request from a high-risk shipper
    When the shipper requests a quote
    Then no price is computed
    And the quote is stored as REFUSED_SCREENING
    And a refusal notice is sent
    And the response is refusedScreeningResponse

  Scenario: Screening outage holds the quote unscreened
    Given a valid quote request from any shipper
    And the screening service is unavailable
    When the shipper requests a quote
    Then the quote is priced
    And the quote is stored as HELD_UNSCREENED
    And a quote document is not sent
    And the response is heldUnscreenedResponse

  Scenario: Invalid request is rejected up front
    Given a quote request with non-positive weight
    When the shipper requests a quote
    Then the request is rejected as invalid
    And nothing is stored
    And the response is rejectedInvalidRequest

  Scenario: Storage outage aborts the quote
    Given a valid quote request
    And the quote store is unavailable
    When the shipper requests a quote
    Then no screening is performed
    And the response is storeUnavailableError


Let me implement this.
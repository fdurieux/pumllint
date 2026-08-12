_notes:
  ACCEPT_MAX: 29
  REVIEW_MIN: 30
  REVIEW_MAX: 69
  REFUSE_MIN: 70


--- FILE: spec/quote_rules.md ---
# CargoQuote — quotation rules companion

This companion pins down the numeric bounds and precedence the
prose leaves loose. Where the brief and this file disagree, this file wins.

## Validained request (DT-V)

A request is well-formed when **all** of these hold. Any failing check
refuses the request with a validation error and stops (no draft is stored,
nothing downstream runs).

| check | rule                              |
|-------|-----------------------------------|
| DT-V1 | `shipperId` is present/non-empty  |
| DT-V2 | `weightKg` is a number in `1 .. 26000` (inclusive) |
| DT-V3 | `distanceKm` is a number in `1 .. 3000` (inclusive) |
| DT-V4 | `declaredValue` is a number in `0 .. 2000000` (inclusive) |

The order of checks does not matter; any single failure is enough.

## Screening decision (DT-S)

The screening provider returns a **risk index** from 0 to 100. The
decision uses these bands:

| row     | condition               | status           | priced? | notified?     | terminal? |
|---------|-------------------------|------------------|---------|---------------|-----------|
| accept  | `riskIndex <= 29`       | QUOTED           | yes     | quote doc     | yes       |
| review  | `30 <= riskIndex <= 69` | REVIEW_HOLD      | no      | none          | yes (hold)|
| refuse  | `riskIndex >= 70`       | REFUSED_SCREENING| no      | refusal notice| yes       |

Notes:
1. **Review hold is not final** in the business sense, but it IS a terminal
   response of the quotation flow — the manual review workflow is out of scope.
2. **Refusal is notified**; pricing never runs for a refused quote.
3. **Storage-first:** if the draft cannot be stored, nothing downstream runs.
4. **Notification is fire-and-forget:** a delivery failure never changes the
   response the shipper sees.
5. **Screening outage is not a refusal:** if the screening provider is
   unavailable, the quote is priced and stored as HELD_UNSCREENED, and no
   notification is sent.

## Precedence

1. Validation (DT-V) comes first; an invalid request is refused before any
   draft is stored.
2. Then storage; if storage fails nothing downstream runs.
3. Then screening; screening determines pricing/notification per DT-S.


--- FILE: acceptance/quote.feature ---
Feature: CargoQuote instant freight quotation

  Background:
    Given the CargoQuote quotation service is available

  Scenario: Clean shipper gets an instant quote
    Given a shipper "ACME-001" with a well-formed request
    And the screening service returns risk index 10
    When the shipper requests a freight quote
    Then a draft quote is stored
    And the tariff engine prices the consignment
    And the quote record is updated to "QUOTED"
    And a quote document is sent to the shipper
    And the response status is "QUOTED"

  Scenario: Mid-risk shipper is held for manual review
    Given a shipper "ACME-002" with a well-formed request
    And the screening service returns risk index 45
    When the shipper requests a freight quote
    Then the quote record is updated to "REVIEW_HOLD"
    And no price is computed
    And no notification is sent
    And the response status is "REVIEW_HOLD"

  Scenario: High-risk shipper is refused
    Given a shipper "ACME-003" with a well-formed request
    And the screening service returns risk index 88
    When the shipper requests a freight quote
    Then the quote record is updated to "REFUSED_SCREENING"
    And a refusal notice is sent to the shipper
    And no price is computed
    And the response status is "REFUSED_SCREENING"

  Scenario: Invalid request is refused up front
    Given a shipper "ACME-004" with a weight of 0 kg
    When the shipper requests a freight quote
    Then the request is refused with a validation error
    And no draft quote is stored
    And the response status is "REJECTED_INVALID"

  Scenario: Screening outage holds the quote unscreened
    Given a shipper "ACME-005" with a well-formed request
    And the screening service is unavailable
    When the shipper requests a freight quote
    Then the tariff engine prices the consignment
    And the quote record is updated to "HELD_UNSCREENED"
    And no notification is sent
    And the response status is "HELD_UNSCREENED"
@enduml
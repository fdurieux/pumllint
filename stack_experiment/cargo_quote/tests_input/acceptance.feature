Feature: CargoQuote instant freight quotation
  Acceptance examples for the quotation flow. Declarative style: each
  scenario states observable outcomes, not implementation steps. This
  file is a GENERATION-INPUT artifact (the W1 tests-as-input rung) —
  it is not executed by any harness. Its declared relationship to the
  frozen grading suite is in oracle_overlap.md and is part of the W1
  pre-registration.

  Background:
    Given the tariff and screening rules of decision_table.md are in force

  Scenario: G1 - clean shipment is quoted and the document is sent
    Given a valid quote request with shipper "ACME-77", weight 620 kg, distance 1400 km, declared value 20000
    And the screening service returns risk index 12
    When the quote request is submitted
    Then the response status is "quoted"
    And the response price is 2121.40
    And a quote document is delivered to the shipper

  Scenario: G2 - underweight request is rejected before anything runs
    Given a quote request with weight 2 kg and otherwise valid fields
    When the quote request is submitted
    Then the response status is "rejected: invalid_request"
    And the shipper is never screened
    And no notification of any kind is sent

  Scenario: G3 - high-risk shipper is refused and told so
    Given a valid quote request
    And the screening service returns risk index 90
    When the quote request is submitted
    Then the response status is "refused_screening"
    And no price is computed
    And a refusal notice is delivered to the shipper

  Scenario: G4 - screening outage holds the quote instead of failing it
    Given a valid quote request with weight 400 kg and distance 900 km
    And the screening service is unavailable
    When the quote request is submitted
    Then the response status is "held_unscreened"
    And the response carries a price and hold set to true
    And no notification of any kind is sent

  Scenario: G5 - price follows the tariff exactly
    Given a valid quote request with weight 600 kg, distance 1200 km, declared value 5000
    And the screening service returns risk index 5
    When the quote request is submitted
    Then the response status is "quoted"
    And the response price is 1878.00

  Scenario: G6 - review-band shipper is held without a price
    Given a valid quote request
    And the screening service returns risk index 50
    When the quote request is submitted
    Then the response status is "review_hold"
    And no price is computed
    And no notification of any kind is sent

  Scenario: G7 - notification failure never changes the outcome
    Given a valid quote request
    And the screening service returns risk index 12
    And the notification provider fails to deliver
    When the quote request is submitted
    Then the response status is "quoted"
    And the response carries the computed price

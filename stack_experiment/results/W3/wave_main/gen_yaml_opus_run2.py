:
  ACCEPT_MAX: 30
  REVIEW_MIN: 31
  REVIEW_MAX: 70
  REFUSE_MIN: 71
  risk_index_range: [0, 100]

--- FILE: spec/decision_tables.md ---
# CargoQuote — decision tables

These tables define the outcome rules for the quotation flow. Thresholds
are inclusive; see `behavior/quote_flow.yaml` for the numeric constants
(ACCEPT_MAX = 30, REVIEW_MIN = 31, REVIEW_MAX = 70, REFUSE_MIN = 71).

## DT-V — Request validation (checked in order; first failing row wins)

| # | Condition                              | Outcome                        |
|---|----------------------------------------|--------------------------------|
| 1 | shipperId missing/blank                | reject: shipper required       |
| 2 | weightKg <= 0                          | reject: weight out of range    |
| 3 | weightKg > 26000                       | reject: weight out of range    |
| 4 | distanceKm <= 0                        | reject: distance out of range  |
| 5 | distanceKm > 3000                      | reject: distance out of range  |
| 6 | declaredValue < 0                      | reject: value out of range     |
| 7 | otherwise                              | accept: proceed to storage     |

Weight is in kilograms; a standard road load caps at 26 tonnes. Distance
is a single-country road haul capped at 3000 km. Declared value may be
zero (some samples ship at nil declared value) but never negative.

## DT-S — Screening outcome (evaluated after a draft is stored)

| # | Condition (riskIndex from Screening Service) | Status            | Priced? | Notified?        | Response                |
|---|----------------------------------------------|-------------------|---------|------------------|-------------------------|
| 1 | riskIndex <= 30                              | QUOTED            | yes     | yes (document)   | quotedResponse          |
| 2 | 31 <= riskIndex <= 70                        | REVIEW_HOLD       | no      | no               | reviewHoldResponse      |
| 3 | riskIndex >= 71                              | REFUSED_SCREENING | no      | yes (refusal)    | refusedScreeningResponse|
| 4 | screening service unavailable                | HELD_UNSCREENED   | yes     | no               | heldUnscreenedResponse  |

Notes:
1. REVIEW_HOLD is a non-final hold: no price is computed and nothing is
   sent to the shipper's notification channel on this row.
2. A refusal (row 3) IS notified: the shipper receives a refusal notice,
   but pricing never runs for a refused quote.
3. If draft storage fails, none of these rows run: no screening, no
   pricing, no notification (see DT-S note in the flow).
4. Notification on rows 1 and 3 is fire-and-forget: a delivery failure
   never changes the response the shipper receives.
5. On screening-service failure (row 4) the quote is still priced and
   stored as HELD_UNSCREENED, but no notification is sent.

## Response status summary

| Response                 | Meaning                                        |
|--------------------------|------------------------------------------------|
| rejectedInvalidRequest   | Request failed validation (DT-V)               |
| storeUnavailableError    | Draft could not be persisted                   |
| quotedResponse           | Quote issued with a price                       |
| reviewHoldResponse       | Held for manual compliance review              |
| refusedScreeningResponse | Refused because of screening risk              |
| heldUnscreenedResponse   | Priced but held because screening was down     |

--- FILE: spec/openapi.yaml ---
openapi: 3.0.3
info:
  title: CargoQuote Quotation API
  version: "1.0"
  description: >
    Synchronous freight quotation API. A shipper submits a consignment
    and receives an immediate quotation outcome: quoted, held for
    review, refused, or held because screening was unavailable.
paths:
  /quotes:
    post:
      summary: Submit a quote request and receive an immediate outcome
      operationId: requestQuote
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/QuoteRequest"
      responses:
        "200":
          description: >
            Quotation processed. The body's status field carries the
            outcome: QUOTED, REVIEW_HOLD, REFUSED_SCREENING, or
            HELD_UNSCREENED.
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/QuoteOutcome"
        "400":
          description: Request failed validation (DT-V).
        "503":
          description: Draft storage unavailable; no quote was created.
      x-notes: >
        Notification of quote documents and refusal notices is
        fire-and-forget and does not affect this response.

components:
  schemas:
    QuoteRequest:
      type: object
      required: [shipperId, weightKg, distanceKm, declaredValue]
      properties:
        shipperId:
          type: string
          description: Identifier of the shipper to be screened.
        weightKg:
          type: number
          description: Gross cargo weight in kilograms: 0 < weightKg <= 26000.
        distanceKm:
          type: number
          description: Road haul distance in kilometers: 0 < distanceKm <= 3000.
        declaredValue:
          type: number
          description: Declared consignment value; may be zero, never negative.
    QuoteOutcome:
      type: object
      properties:
        quoteId:
          type: string
        status:
          type: string
          enum: [QUOTED, REVIEW_HOLD, REFUSED_SCREENING, HELD_UNSCREENED]
        price:
          type: number
          nullable: true
          description: Present only when a price was computed.


--- FILE: features/quote.feature ---
Feature: CargoQuote instant freight quotation
  Shippers submit consignments and receive an immediate quotation
  outcome. Screening decides whether a quote is issued, held for review,
  or refused; pricing runs only where the rules allow.

  Background:
    Given the tariff, screening, notification and storage services are available
    And the following tariff applies:
      | base | per_kg | per_km |
      | 25.0 | 0.10   | 0.05   |

  Scenario: Clean shipper receives an instant quote
    When shipper "SHP-1000" requests a quote for 1200 kg over 300 km declaring 5000 value
    And the screening service returns a risk index of 10
    Then the response status is "QUOTED"
    And the quote is priced at 160.0
    And a quote document is sent to the shipper
    And the quote record is stored with status "QUOTED"

  Scenario: Mid-risk shipper is held for manual review
    When shipper "SHP-2000" requests a quote for 800 kg over 150 km declaring 2000 value
    And the screening service returns a risk index of 55
    Then the response status is "REVIEW_HOLD"
    And no price is computed
    And nothing is sent to the shipper
    And the quote record is stored with status "REVIEW_HOLD"

  Scenario: High-risk shipper is refused and notified
    When shipper "SHP-3000" requests a quote for 500 kg over 100 km declaring 1000 value
    And the screening service returns a risk index of 90
    Then the response status is "REFUSED_SCREENING"
    And no price is computed
    And a refusal notice is sent to the shipper
    And the quote record is stored with status "REFUSED_SCREENING"

  Scenario: Screening outage holds the quote but still prices it
    When shipper "SHP-4000" requests a quote for 1000 kg over 200 km declaring 3000 value
    And the screening service is unavailable
    Then the response status is "HELD_UNSCREENED"
    And the quote is priced at 135.0
    And nothing is sent to the shipper
    And the quote record is stored with status "HELD_UNSCREENED"

  Scenario: Overweight consignment is rejected before screening
    When shipper "SHP-5000" requests a quote for 26001 kg over 100 km declaring 1000 value
    Then the response status is "rejectedInvalidRequest"
    And no screening call is made
    And no quote record is created

  Scenario Outline: Declared value boundaries
    When shipper "SHP-6000" requests a quote for 1000 kg over 100 km declaring <value> value
    Then the response status is "<status>"

    Examples:
      | value | status                 |
      | 0     | QUOTED                 |
      | -1    | rejectedInvalidRequest |

Let me analyze the specification and implement it.
_end: true

--- FILE: behavior/decisions.md ---
# CargoQuote — decision tables (quotation scope)

These tables are the normative source for the validation bounds and the
screening decision. Thresholds are expressed against a shipper risk
index in the range 0–100 inclusive.

## DT-V — request validation

A request is valid only if **every** condition holds. On any violation
the quote is rejected with a validation error and nothing is stored,
screened, priced, or notified.

| # | Condition            | Rule                                  |
|---|----------------------|---------------------------------------|
| 1 | shipperId present     | non-empty string                     |
| 2 | weightKg bounds       | 0 < weightKg <= 26000                 |
| 3 | distanceKm bounds     | 0 < distanceKm <= 3000                |
| 4 | declaredValue bounds  | 0 <= declaredValue <= 1000000         |

Notes:
1. Weight is in kilograms; the ceiling is a full road trailer (26 t).
2. Distance is a one-way domestic haul; the ceiling is 3000 km.
3. Declared value is in whole currency units and may be zero.


## DT-S — screening decision

Evaluated after a draft is stored, using the risk index returned by the
screening provider. Exactly one row fires; rows are mutually exclusive
and ordered by risk.

| # | Condition (risk index) | Decision | Price? | Store status        | Notify?          |
|---|------------------------|----------|--------|---------------------|------------------|
| 1 | 0 <= risk <= 29        | accept   | yes    | QUOTED              | quote document   |
| 2 | 30 <= risk <= 69       | review   | no     | REVIEW_HOLD         | none             |
| 3 | 70 <= risk <= 100      | refuse   | no     | REFUSED_SCREENING   | refusal notice   |

Thresholds (named constants):

- `ACCEPT_MAX = 29`
- `REVIEW_MIN = 30`
- `REVIEW_MAX = 69`
- `REFUSE_MIN = 70`

Notes:
1. **review** is a non-final hold: it is *not* priced and *not*
   notified; it only records a hold for the compliance team.
2. **refuse** *is* notified (refusal notice) but *never* priced.
3. If the draft cannot be stored, the screening step never runs
   (see DT-S/flow): no screening, no pricing, no notification.
4. On **accept**, notification is fire-and-forget: a notification
   failure does not change the quoted outcome.
5. If the screening provider is unavailable, the quote is *not* failed:
   it is priced and stored with status `HELD_UNSCREENED` and returned
   as held; no notification is sent.


--- FILE: behavior/quote_lifecycle.puml ---
@startuml quote_lifecycle
[*] --> Draft : requestQuote / validated & stored

Draft --> Quoted : screening accept (risk <= ACCEPT_MAX) / price & notify
Draft --> ReviewHold : screening review (REVIEW_MIN..REVIEW_MAX)
Draft --> RefusedScreening : screening refuse (risk >= REFUSE_MIN) / notify
Draft --> HeldUnscreened : screening unavailable / price, no notify

Quoted --> [*]
ReviewHold --> [*]
RefusedScreening --> [*]
HeldUnscreened --> [*]

@enduml


--- FILE: api/quote.openapi.yaml ---
openapi: 3.0.3
info:
  title: CargoQuote Quotation API
  version: "1.0.0"
  description: >
    Synchronous freight quotation API. A shipper submits a consignment
    and receives an immediate outcome: quoted, held for review, refused,
    or held unscreened. Booking and payment are out of scope.
paths:
  /quotes:
    post:
      summary: Request a freight quote for a consignment
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
            Quotation processed. The body's `status` names the outcome:
            quoted, review_hold, refused_screening, or held_unscreened.
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/QuoteResult"
        "400":
          description: Validation error: the request violates DT-V bounds.
        "503":
          description: >
            Draft could not be stored (storage unavailable); nothing was
            screened, priced, or notified.
components:
  schemas:
    QuoteRequest:
      type: object
      required: [shipperId, weightKg, distanceKm, declaredValue]
      properties:
        shipperId:
          type: string
          description: Identifier of the shipper to be screened.
          example: "shipper-4417"
        weightKg:
          type: number
          description: Consignment weight in kilograms: 0 < weightKg <= 26000.
          example: 8200
        distanceKm:
          type: number
          description: One-way haul distance in km: 0 < distanceKm <= 3000.
          example: 640
        declaredValue:
          type: number
          description: Declared cargo value: 0 <= declaredValue <= 1000000.
          example: 42000
    QuoteResult:
      type: object
      required: [quoteId, status]
      properties:
        quoteId:
          type: string
          example: "quote-90b3c2"
        status:
          type: string
          enum: [quoted, review_hold, refused_screening, held_unscreened]
        price:
          type: number
          description: Present only when status is quoted or held_unscreened.
          nullable: true
          example: 1287.50


--- FILE: acceptance/quote.feature ---
Feature: CargoQuote instant freight quotation
  Shippers submit consignments and get an immediate quotation outcome:
  quoted, held for review, refused, or held unscreened. Validation,
  screening thresholds, pricing and notification follow the decision
  tables in behavior/decisions.md.

  Background:
    Given the tariff and screening thresholds from the decision tables

  Scenario: Low-risk shipper is quoted immediately
    Given a valid quote request for shipper "shipper-1001"
    And the screening service returns risk index 12
    When the shipper requests a quote
    Then the draft is stored before screening
    And the tariff engine prices the consignment
    And the quote status is "quoted"
    And a quote document is sent to the shipper

  Scenario: Mid-risk shipper is held for manual review
    Given a valid quote request for shipper "shipper-1002"
    And the screening service returns risk index 45
    When the shipper requests a quote
    Then the quote status is "review_hold"
    And the tariff engine is not called
    And no notification is sent

  Scenario: High-risk shipper is refused
    Given a valid quote request for shipper "shipper-1003"
    And the screening service returns risk index 88
    When the shipper requests a quote
    Then the quote status is "refused_screening"
    And the tariff engine is not called
    And a refusal notice is sent to the shipper

  Scenario: Screening provider outage holds the quote unscreened
    Given a valid quote request for shipper "shipper-1004"
    And the screening service is unavailable
    When the shipper requests a quote
    Then the consignment is priced
    And the quote status is "held_unscreened"
    And the quote is stored with status "held_unscreened"
    And no notification is sent

  Scenario: Oversized consignment is rejected by validation
    Given a quote request for shipper "shipper-1005" with weightKg 26001
    When the shipper requests a quote
    Then the request is rejected with a validation error
    And nothing is screened, priced, or notified

  Scenario: Missing shipper id is rejected by validation
    Given a quote request with an empty shipper id
    When the shipper requests a quote
    Then the request is rejected with a validation error
    And nothing is screened, priced, or notified
```

Implement this now.
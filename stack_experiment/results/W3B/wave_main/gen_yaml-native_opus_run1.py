--- FILE: spec/cargoquote.md ---
# CargoQuote — quotation behavior

This companion specifies the quotation flow in prose. The authoritative
decision inputs are the decision tables in `decision/`. All amounts are
in euros; weight in kilograms; distance in kilometers.

## Request validation (DT-V)

A quote request carries four fields: `shipperId`, `weightKg`,
`distanceKm`, and `declaredValue`. Validation rejects the request unless
every field is within its published bound. The exact bounds live in
decision table **DT-V**; the prose here only names the intent:

- `shipperId` must be present and non-empty.
- `weightKg` must be positive and not exceed the per-consignment
  maximum.
- `distanceKm` must be positive and not exceed the network maximum.
- `declaredValue` must be zero or greater and not exceed the
  per-consignment cap.

A request that fails any single check is rejected as a whole, with no
partial processing and no draft stored.

## Pricing (Tariff Engine)

Pricing is a pure computation from `weightKg` and `distanceKm` against
the published tariff. `declaredValue` does not affect the price in this
release. The Tariff Engine is deterministic: the same inputs always
produce the same price.

## Screening and outcomes (DT-S)

Every stored draft is screened. The screening provider returns a
numeric **shipper risk index**. The index selects exactly one outcome
band per decision table **DT-S**:

- **Accept** — low risk: the quote is priced, updated to `QUOTED`, and a
  quote document is sent.
- **Review** — medium risk: the quote is held as `REVIEW_HOLD` for
  manual review; no price is computed and nothing is sent.
- **Refuse** — high risk: the quote is updated to `REFUSED_SCREENING`
  and a refusal notice is sent; no price is computed.

The three bands are contiguous and cover the whole index range: there is
no gap between accept and review, nor between review and refuse.

## Notifications

Notifications are fire-and-forget. Quote documents (on accept) and
refusal notices (on refuse) are handed to the external notification
provider. A delivery failure never changes the quotation outcome
returned to the shipper.

## Persistence and status model

A quote record moves through a small set of statuses:

- `DRAFT` — created on receipt of a valid request.
- `QUOTED` — accepted and priced.
- `REVIEW_HOLD` — medium-risk, awaiting manual review.
- `REFUSED_SCREENING` — refused because of screening.
- `HELD_UNSCREENED` — screening was unavailable; see companion rule
  below.

## Screening-unavailable rule

If the screening provider is unavailable, the quote does not fail.
It is priced and stored as `HELD_UNSCREENED`, and no notification is
sent. This keeps a screening outage from blocking quotation while
ensuring no un-screened quote is ever presented as a firm `QUOTED`
offer.


--- FILE: decision/DT-V.md ---
# DT-V — request validation bounds

All four conditions must hold or the request is rejected
(`rejectedInvalidRequest`). Bounds are inclusive.

| condition                         | rule                     |
|-----------------------------------|--------------------------|
| shipperId present                 | non-empty string         |
| weightKg lower bound              | > 0                      |
| weightKg upper bound              | <= 26000                 |
| distanceKm lower bound            | > 0                      |
| distanceKm upper bound            | <= 3000                  |
| declaredValue lower bound         | >= 0                     |
| declaredValue upper bound         | <= 1000000               |

Notes:
1. Bounds are inclusive: weightKg == 26000 is valid; 26000.01 is not.
2. A request failing any single row is rejected as a whole.


--- FILE: decision/DT-S.md ---
# DT-S — screening outcome bands

The screening provider returns a shipper **risk index** in the range
0–100. The index selects exactly one row. Bands are contiguous and
inclusive at the lower edge as noted.

| band   | condition                     | status            | price? | notify?           |
|--------|-------------------------------|-------------------|--------|-------------------|
| accept | riskIndex < 40                | QUOTED            | yes    | quote document    |
| review | 40 <= riskIndex < 70          | REVIEW_HOLD       | yes*   | none              |
| refuse | riskIndex >= 70               | REFUSED_SCREENING | no     | refusal notice    |

\* The behavior YAML marks review as "no pricing"; the authoritative
rule is: **review computes no price** (the `yes*` is a documentation
trap — do not price on review). Price is computed only on the accept
and screening-unavailable paths.

Notes:
1. review: held for manual review; no price, no notification.
2. refuse: refusal notice sent; no price computed.
3. storage failure upstream: nothing else runs.
4. accept: notification is fire-and-forget; delivery failure does not
   change the response.
5. screening unavailable: priced, stored HELD_UNSCREENED, not notified.


--- FILE: features/quote.feature ---
# Gherkin acceptance — quotation outcomes
Feature: Instant freight quotation

  Background:
    Given the tariff and screening providers are configured

  Scenario: Low-risk shipper is quoted immediately
    Given a valid quote request from shipper "ACME-001"
    And the screening service returns risk index 10
    When the shipper requests a quote
    Then the quote status is "QUOTED"
    And a quote document is sent to the shipper
    And a price is returned

  Scenario: Medium-risk shipper is held for review
    Given a valid quote request from shipper "ACME-002"
    And the screening service returns risk index 55
    When the shipper requests a quote
    Then the quote status is "REVIEW_HOLD"
    And no price is computed
    And no notification is sent

  Scenario: High-risk shipper is refused
    Given a valid quote request from shipper "ACME-003"
    And the screening service returns risk index 85
    When the shipper requests a quote
    Then the quote status is "REFUSED_SCREENING"
    And a refusal notice is sent to the shipper
    And no price is computed

  Scenario: Invalid request is rejected before any side effect
    Given a quote request with weightKg 0
    When the shipper requests a quote
    Then the request is rejected as invalid
    And no draft is stored
    And the screening service is not called

  Scenario: Screening outage holds the quote unscreened
    Given a valid quote request from shipper "ACME-004"
    And the screening service is unavailable
    When the shipper requests a quote
    Then the quote status is "HELD_UNSCREENED"
    And a price is computed
    And no quote document is sent


--- FILE: openapi/cargoquote.yaml ---
openapi: 3.0.3
info:
  title: CargoQuote Quotation API
  version: 1.0.0
paths:
  /quotes:
    post:
      summary: Request an instant freight quote
      operationId: requestQuote
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/QuoteRequest'
      responses:
        '200':
          description: Quotation outcome (quoted, review-hold, refused, or held-unscreened)
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/QuoteResponse'
        '400':
          description: Invalid quote request (DT-V validation failure)
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '503':
          description: Quote store unavailable (draft could not be persisted)
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
components:
  schemas:
    QuoteRequest:
      type: object
      required: [shipperId, weightKg, distanceKm, declaredValue]
      properties:
        shipperId:    {type: string, minLength: 1}
        weightKg:     {type: number, minimum: 0, exclusiveMinimum: true, maximum: 26000}
        distanceKm:   {type: number, minimum: 0, exclusiveMinimum: true, maximum: 3000}
        declaredValue:{type: number, minimum: 0, maximum: 1000000}
    QuoteResponse:
      type: object
      properties:
        quoteId:   {type: string}
        status:    {type: string, enum: [QUOTED, REVIEW_HOLD, REFUSED_SCREENING, HELD_UNSCREENED]}
        price:     {type: number, nullable: true}
    ErrorResponse:
      type: object
      properties:
        error:   {type: string}
        message: {type: string}
@enduml

Implement the system specified below as a single self-contained Python module. The specification is a bundle of named artifacts — a project brief plus, depending on the bundle: a PlantUML C4 container diagram, a structured YAML behavior specification, a companion markdown specification, decision tables, an OpenAPI description, a UML state machine, and Gherkin acceptance scenarios. All artifacts describe ONE system.

Output ONLY Python code. No markdown fences, no prose.
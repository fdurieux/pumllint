# LoanCheck — companion specification (credit check for a personal loan)

Supplementary structured specification accompanying the C4 diagrams of the
LoanCheck Personal Loan Origination System. The diagrams define structure
and flow shape; this document pins the decision semantics, the validation
rules, the error policy, and the API contract. Where a diagram is silent,
this document is the authority.

## Glossary

- **Application**: one request for a personal loan — `customer_id`,
  `amount` (requested principal, EUR), `term_months` (repayment term).
- **Credit score**: integer risk score for the applicant returned by the
  Credit Bureau; higher is better.
- **Decision**: outcome of the credit check — exactly one of `approved`,
  `declined`, `review` (manual review by an underwriter).
- **Decision notification**: message to the applicant via the Notification
  Service, sent only when a decision was actually made.

## Validation rules (checked before anything else)

An application is **valid** iff all of:

- `customer_id` present and non-empty;
- `amount` is a number with `1 <= amount <= 100000`;
- `term_months` is a number with `6 <= term_months <= 120`.

An invalid application is rejected immediately with status
`rejected: invalid_application`. No credit report is pulled and no
notification is sent for an invalid application.

## Decision policy (applies only to valid applications)

| Credit score s | Decision |
|---|---|
| s >= 700 | `approved` |
| 620 <= s <= 699 | `review` |
| s < 620 | `declined` |

The thresholds are inclusive exactly as written: a score of exactly 700 is
approved; a score of exactly 620 is review; 619 is declined.

## Flow order and error policy

1. Validate the application (rules above). Invalid → reject, stop.
2. Store the application in the Application Store with status `pending`.
   If storage fails: return status `error: storage_unavailable`; do not
   pull a credit report; do not send any notification.
3. Request the decision from the Decision Engine, which pulls the credit
   score from the Credit Bureau. If the bureau is unavailable or errors:
   return status `error: bureau_unavailable`; the application stays
   `pending`; do not send any notification.
4. Apply the decision policy to the score. Update the stored application
   to the decision (`approved` / `declined` / `review`).
5. Send the decision notification to the applicant via the Notification
   Service (for all three decisions).
6. Return the response to the applicant.

## API contract

Request (JSON object):

- `customer_id`: string, required.
- `amount`: number, required.
- `term_months`: number, required.

Response (JSON object): `status` is exactly one of:

- `"approved"` | `"declined"` | `"review"`
- `"rejected: invalid_application"`
- `"error: bureau_unavailable"`
- `"error: storage_unavailable"`

plus `application_id` (string) when the application was stored.

## Acceptance criteria

| # | Given | Then |
|---|---|---|
| 1 | valid application, score 760 | status `approved`; stored; approval notification sent |
| 2 | valid application, score exactly 700 | status `approved` |
| 3 | valid application, score 540 | status `declined`; decline notification sent |
| 4 | valid application, score 660 | status `review`; stored; not auto-approved, not auto-declined |
| 5 | `amount` = 0 | status `rejected: invalid_application`; no bureau call |
| 6 | `amount` = 250000 | status `rejected: invalid_application`; no bureau call |
| 7 | bureau unavailable | status `error: bureau_unavailable`; no notification |
| 8 | storage unavailable | status `error: storage_unavailable`; no notification |

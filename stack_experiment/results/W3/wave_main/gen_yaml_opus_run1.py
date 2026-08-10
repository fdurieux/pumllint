_response:
  quotedResponse: {status: quoted, fields: [quoteId, priceAmount]}
  reviewHoldResponse: {status: review_hold, fields: [quoteId]}
  refusedScreeningResponse: {status: refused_screening, fields: [quoteId]}
  heldUnscreenedResponse: {status: held_unscreened, fields: [quoteId, priceAmount]}
  rejectedInvalidRequest: {status: rejected_invalid, error: validationError}
  storeUnavailableError: {status: error_store_unavailable}

--- FILE: spec/tariff_and_screening.md ---
# CargoQuote — quotation rules (companion spec)

These rules refine the container and sequence artifacts. Where a
decision table assigns a status, that status is authoritative.

## Screening bands — decision table DT-S

The screening provider returns a **risk index** — an integer from 0 to
100. The band boundaries:

| Row    | Condition             | Status            | Priced? | Notified?        | Stored status         |
|--------|-----------------------|-------------------|---------|------------------|-----------------------|
| accept | riskIndex 0–39        | quoted            | yes     | quote document   | QUOTED                |
| review | riskIndex 40–69       | review_hold       | no      | none             | REVIEW_HOLD           |
| refuse | riskIndex 70–100      | refused_screening | no      | refusal notice   | REFUSED_SCREENING     |

Notes:
1. Review hold is not final — pricing waits until compliance clears the
   shipper; no notification on this path.
2. A refused quote is never priced, but the shipper *is* notified with a
   refusal notice.
3. On storage failure nothing else runs — no screening, pricing, or
   notification.
4. Notification is fire-and-forget — a delivery failure never changes
   the response returned to the shipper.
5. If screening itself is unavailable, the quote does not fail: it is
   priced and stored with status HELD_UNSCREENED, and not notified.

## Boundary constants

    ACCEPT_MAX = 39
    REVIEW_MIN = 40
    REVIEW_MAX = 69
    REFUSE_MIN = 70

## Request validation — decision table DT-V

All bounds inclusive unless stated. A request failing any row is
rejected with `rejected_invalid` and never stored.

| Field         | Rule                                  |
|---------------|---------------------------------------|
| shipperId     | non-empty string                      |
| weightKg      | number, 1 … 26000                     |
| distanceKm    | number, 1 … 3000                      |
| declaredValue | number, ≥ 0                           |

## Tariff formula (Tariff Engine)

For a valid, accepted quote:

    price = base + perKg * weightKg + perKm * distanceKm

    base   = 25.00
    perKg  =  0.12
    perKm  =  0.05

Rounded to 2 decimals. Declared value does not affect price in this
release (reserved for future insurance surcharge).


--- FILE: acceptance/quote.feature ---
Feature: CargoQuote instant freight quotation

  Background:
    Given the tariff is base 25.00, perKg 0.12, perKm 0.05
    And screening bands accept 0-39, review 40-69, refuse 70-100

  Scenario: Accepted low-risk quote is priced and issued
    Given a shipper "ACME-01" with risk index 10
    And a consignment of 1000 kg over 200 km declared value 5000
    When the shipper requests a quote
    Then the response status is "quoted"
    And the price is 155.00
    And a quote document is sent
    And the quote is stored with status "QUOTED"

  Scenario: Mid-risk shipper is held for manual review
    Given a shipper "ACME-02" with risk index 55
    And a consignment of 500 kg over 100 km declared value 2000
    When the shipper requests a quote
    Then the response status is "review_hold"
    And no price is computed
    And no notification is sent
    And the quote is stored with status "REVIEW_HOLD"

  Scenario: High-risk shipper is refused and notified
    Given a shipper "BADCO-09" with risk index 88
    And a consignment of 800 kg over 150 km declared value 3000
    When the shipper requests a quote
    Then the response status is "refused_screening"
    And no price is computed
    And a refusal notice is sent
    And the quote is stored with status "REFUSED_SCREENING"

  Scenario: Screening outage holds the quote unscreened but priced
    Given a shipper "ACME-03" and the screening service is unavailable
    And a consignment of 1200 kg over 300 km declared value 4000
    When the shipper requests a quote
    Then the response status is "held_unscreened"
    And the price is 184.00
    And the quote is stored with status "HELD_UNSCREENED"
    And no notification is sent

  Scenario: Invalid request is rejected before storage
    Given a shipper "ACME-04"
    And a consignment of 0 kg over 200 km declared value 1000
    When the shipper requests a quote
    Then the response status is "rejected_invalid"
    And the quote is not stored

  Scenario: Storage outage returns a store error
    Given a shipper "ACME-05" with risk index 10
    And a consignment of 1000 kg over 200 km declared value 5000
    And the quote store is unavailable
    When the shipper requests a quote
    Then the response status is "rejected_invalid" or "error_store_unavailable"
    And no quote document is sent
```

Output ONLY Python code.

# CargoQuote — Instant Freight Quotation System
# Single self-contained module implementing the specified system.

# Boundary constants (from companion spec)
ACCEPT_MAX = 39
REVIEW_MIN = 40
REVIEW_MAX = 69
REFUSE_MIN = 70

# Tariff constants
BASE = 25.00
PER_KG = 0.12
PER_KM = 0.05

# Validation bounds
WEIGHT_MIN, WEIGHT_MAX = 1, 26000
DISTANCE_MIN, DISTANCE_MAX = 1, 3000


class ScreeningError(Exception):
    """Raised when the external screening provider is unavailable."""


class StoreError(Exception):
    """Raised when the quote store is unavailable."""


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff."""

    def price(self, weight_kg, distance_km):
        amount = BASE + PER_KG * weight_kg + PER_KM * distance_km
        return round(amount, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._counter = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value,
                    available=True):
        if not available:
            raise StoreError("storage unavailable")
        self._counter += 1
        quote_id = "Q-%04d" % self._counter
        self._records[quote_id] = {
            "quoteId": quote_id,
            "shipperId": shipper_id,
            "weightKg": weight_kg,
            "distanceKm": distance_km,
            "declaredValue": declared_value,
            "status": "DRAFT",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price=None):
        rec = self._records.get(quote_id)
        if rec is None:
            raise StoreError("quote not found")
        rec["status"] = status
        if price is not None:
            rec["price"] = price
        return quote_id


class ScreeningService:
    """External denied-party screening provider returning a risk index."""

    def screen(self, shipper_id, risk_index=0, available=True):
        if not available:
            raise ScreeningError("screening service unavailable")
        return int(risk_index)


class NotificationService:
    """External messaging provider delivering quote documents and notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        # fire-and-forget; delivery failure never changes the response
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening/pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service,
                 notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or not shipper_id.strip():
            return False
        if not isinstance(weight_kg, (int, float)) or isinstance(weight_kg, bool):
            return False
        if not isinstance(distance_km, (int, float)) or isinstance(distance_km, bool):
            return False
        if not isinstance(declared_value, (int, float)) or isinstance(declared_value, bool):
            return False
        if not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            return False
        if not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            return False
        if declared_value < 0:
            return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value,
                      *, risk_index=0, screening_available=True,
                      store_available=True):
        # Step 1: validation (DT-V)
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected_invalid", "error": "validationError"}

        # Step 2: store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value,
                available=store_available)
        except StoreError:
            return {"status": "error_store_unavailable"}

        # Step 3: screening
        try:
            index = self.screening_service.screen(
                shipper_id, risk_index=risk_index, available=screening_available)
        except ScreeningError:
            # DT-S note 5: outage does not fail the quote — priced, held, not notified
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "HELD_UNSCREENED", price_amount)
            return {"status": "held_unscreened",
                    "quoteId": quote_id, "priceAmount": price_amount}

        # Step 4: screening decision (DT-S)
        if index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "QUOTED", price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount)
            return {"status": "quoted",
                    "quoteId": quote_id, "priceAmount": price_amount}
        elif REVIEW_MIN <= index <= REVIEW_MAX:
            # DT-S note 1: no pricing, no notification
            self.quote_store.update_quote(quote_id, "REVIEW_HOLD")
            return {"status": "review_hold", "quoteId": quote_id}
        else:  # index >= REFUSE_MIN
            # DT-S note 2: never priced, but notified with a refusal notice
            self.quote_store.update_quote(quote_id, "REFUSED_SCREENING")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused_screening", "quoteId": quote_id}


def _build_api():
    return QuoteApi(
        tariff_engine=TariffEngine(),
        quote_store=QuoteStore(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )


def _truthy_word(value, positive_words, negative_words):
    if isinstance(value, str):
        return value.strip().lower() in positive_words
    return bool(value)


def handle(request: dict) -> dict:
    """Run one end-to-end quotation flow."""
    api = _build_api()

    shipper_id = request.get("shipperId", request.get("shipper_id", ""))
    weight_kg = request.get("weightKg", request.get("weight_kg", 0))
    distance_km = request.get("distanceKm", request.get("distance_km", 0))
    declared_value = request.get("declaredValue", request.get("declared_value", 0))

    # Screening availability / risk index
    screening_available = True
    risk_index = 0

    screen_status = request.get("screening_status", request.get("screening_result"))
    if screen_status is not None:
        if isinstance(screen_status, str):
            word = screen_status.strip().lower()
            if word in ("error", "unavailable", "down", "outage", "timeout"):
                screening_available = False
            else:
                try:
                    risk_index = int(word)
                except ValueError:
                    risk_index = 0
        else:
            risk_index = int(screen_status)

    if "risk_index" in request:
        risk_index = int(request["risk_index"])
    if "riskIndex" in request:
        risk_index = int(request["riskIndex"])

    if request.get("screening_available") is False:
        screening_available = False

    # Store availability
    store_available = True
    store_status = request.get("store_status", request.get("store_result"))
    if isinstance(store_status, str):
        if store_status.strip().lower() in ("error", "unavailable", "down", "outage"):
            store_available = False
    if request.get("store_available") is False:
        store_available = False
    if request.get("quote_store_available") is False:
        store_available = False

    try:
        return api.request_quote(
            shipper_id, weight_kg, distance_km, declared_value,
            risk_index=risk_index,
            screening_available=screening_available,
            store_available=store_available,
        )
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "error: %s" % exc}
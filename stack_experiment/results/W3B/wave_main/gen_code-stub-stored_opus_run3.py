from enum import Enum


# ---------------------------------------------------------------------------
# Screening decision thresholds (decision table DT-S) and validation bounds
# (decision table DT-V). Risk index modelled on a 0..100 scale.
# ---------------------------------------------------------------------------

ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

WEIGHT_MIN = 1
WEIGHT_MAX = 26000        # kg, full road trailer payload
DISTANCE_MIN = 1
DISTANCE_MAX = 3000       # km
VALUE_MIN = 1
VALUE_MAX = 10_000_000    # declared value ceiling


# ---------------------------------------------------------------------------
# Lifecycle status labels
# ---------------------------------------------------------------------------

STATUS_QUOTED = "QUOTED"
STATUS_REVIEW_HOLD = "REVIEW_HOLD"
STATUS_REFUSED_SCREENING = "REFUSED_SCREENING"
STATUS_HELD_UNSCREENED = "HELD_UNSCREENED"


# ---------------------------------------------------------------------------
# Domain exceptions (failure paths)
# ---------------------------------------------------------------------------

class ValidationError(Exception):
    """DT-V: request outside accepted bounds."""


class ScreeningUnavailableError(Exception):
    """Screening provider outage."""


class StoreUnavailableError(Exception):
    """Quote store outage."""


# ---------------------------------------------------------------------------
# Tariff Engine (internal container)
# ---------------------------------------------------------------------------

class TariffEngine:
    BASE_FEE = 25.0
    RATE_PER_KG_KM = 0.00035

    def price(self, weight_kg, distance_km):
        """Compute a single price amount for a validated request."""
        amount = self.BASE_FEE + (weight_kg * distance_km * self.RATE_PER_KG_KM)
        return round(amount, 2)


# ---------------------------------------------------------------------------
# Screening Service (external)
# ---------------------------------------------------------------------------

class ScreeningService:
    def __init__(self, config=None):
        self._config = config or {}

    def screen(self, shipper_id):
        """Return a single riskIndex, or raise on provider outage."""
        outcome = self._config.get("screening_result",
                                   self._config.get("screening_status"))

        if outcome is None:
            return 10  # default: clean shipper

        # Numeric score passes straight through as the risk index.
        if isinstance(outcome, (int, float)):
            return outcome

        word = str(outcome).strip().lower()
        if word in ("error", "unavailable", "timeout", "failed"):
            raise ScreeningUnavailableError("screening service unavailable")
        if word in ("approved", "accept", "accepted", "clear", "clean"):
            return 10
        if word in ("review", "hold", "manual"):
            return 50
        if word in ("declined", "refuse", "refused", "denied", "hit"):
            return 90
        if word in ("assessed",):
            return 10
        # Unknown word -> treat as clean.
        return 10


# ---------------------------------------------------------------------------
# Notification Service (external) — fire-and-forget
# ---------------------------------------------------------------------------

class NotificationService:
    def send_quote_document(self, shipper_id, quote_id, price_amount):
        # Fire-and-forget: delivery failures never change the response.
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        # Fire-and-forget: delivery failures never change the response.
        return "sent"


# ---------------------------------------------------------------------------
# Quote Store (internal database)
# ---------------------------------------------------------------------------

class QuoteStore:
    def __init__(self, config=None):
        self._config = config or {}
        self._seq = 0
        self._records = {}

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        """Store the draft; return a single quoteId, or raise on outage."""
        outcome = self._config.get("store_result",
                                   self._config.get("store_status"))
        if outcome is not None:
            word = str(outcome).strip().lower()
            if word in ("error", "unavailable", "timeout", "failed"):
                raise StoreUnavailableError("quote storage unavailable")

        self._seq += 1
        quote_id = "Q-{:06d}".format(self._seq)
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "DRAFT",
            "price_amount": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        """Update status (and price if given); return the updated quote."""
        record = self._records.get(quote_id, {})
        record["status"] = status
        if price_amount is not None:
            record["price_amount"] = price_amount
        self._records[quote_id] = record
        return dict(record, quote_id=quote_id)


# ---------------------------------------------------------------------------
# Quote API (internal container) — the orchestrating entry participant
# ---------------------------------------------------------------------------

class QuoteAPI:
    def __init__(self, tariff_engine, screening_service,
                 notification_service, quote_store):
        self._tariff_engine = tariff_engine
        self._screening_service = screening_service
        self._notification_service = notification_service
        self._quote_store = quote_store

    # -- validation (DT-V) --------------------------------------------------

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if shipper_id is None or str(shipper_id).strip() == "":
            raise ValidationError("missing shipper id")
        if not isinstance(weight_kg, (int, float)) or \
                not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            raise ValidationError("weight out of bounds")
        if not isinstance(distance_km, (int, float)) or \
                not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            raise ValidationError("distance out of bounds")
        if not isinstance(declared_value, (int, float)) or \
                not (VALUE_MIN <= declared_value <= VALUE_MAX):
            raise ValidationError("declared value out of bounds")

    # -- main flow ----------------------------------------------------------

    def request_quote(self, shipper_id, weight_kg, distance_km,
                      declared_value):
        # Step 1: validate (DT-V).
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as exc:
            return {"status": "rejected: invalid_request",
                    "reason": str(exc)}

        # Step 1b: store draft. On storage failure nothing else runs.
        try:
            quote_id = self._quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError as exc:
            return {"status": "error: storage_unavailable",
                    "reason": str(exc)}

        # Step 2: screen the shipper.
        try:
            risk_index = self._screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # DT-S note 5: screening outage does not fail the quote.
            price_amount = self._tariff_engine.price(weight_kg, distance_km)
            self._quote_store.update_quote(
                quote_id, STATUS_HELD_UNSCREENED, price_amount)
            return {"status": "held_unscreened",
                    "quote_id": quote_id,
                    "price_amount": price_amount}

        # Step 3: apply the screening decision (DT-S).
        if risk_index <= ACCEPT_MAX:
            price_amount = self._tariff_engine.price(weight_kg, distance_km)
            self._quote_store.update_quote(
                quote_id, STATUS_QUOTED, price_amount)
            self._notification_service.send_quote_document(
                shipper_id, quote_id, price_amount)
            return {"status": "confirmed",
                    "quote_id": quote_id,
                    "price_amount": price_amount}

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # DT-S note 1: review hold is not final; no pricing, no notice.
            self._quote_store.update_quote(quote_id, STATUS_REVIEW_HOLD)
            return {"status": "review_hold",
                    "quote_id": quote_id}

        if risk_index >= REFUSE_MIN:
            # DT-S note 2: refusal IS notified; pricing never runs.
            self._quote_store.update_quote(
                quote_id, STATUS_REFUSED_SCREENING)
            self._notification_service.send_refusal_notice(
                shipper_id, quote_id)
            return {"status": "rejected_screening",
                    "quote_id": quote_id}

        # Defensive fallback (should be unreachable given the bands above).
        self._quote_store.update_quote(quote_id, STATUS_REVIEW_HOLD)
        return {"status": "review_hold", "quote_id": quote_id}


# ---------------------------------------------------------------------------
# Module-level end-to-end entry point
# ---------------------------------------------------------------------------

def handle(request: dict) -> dict:
    request = request or {}

    shipper_id = request.get("shipper_id", request.get("shipper", "SH-1"))

    # Existence flags — an absent/unknown shipper is an invalid request.
    for key in ("shipper_exists", "shipper_found"):
        if key in request and not request[key]:
            return {"status": "rejected: invalid_request",
                    "reason": "shipper not found"}

    weight_kg = request.get("weight_kg", 100)
    distance_km = request.get("distance_km", 100)
    declared_value = request.get("declared_value", 1000)

    tariff_engine = TariffEngine()
    screening_service = ScreeningService(request)
    notification_service = NotificationService()
    quote_store = QuoteStore(request)

    api = QuoteAPI(tariff_engine, screening_service,
                   notification_service, quote_store)

    try:
        return api.request_quote(shipper_id, weight_kg,
                                 distance_km, declared_value)
    except Exception as exc:  # pragma: no cover - final safety net
        return {"status": "error: {}".format(exc)}
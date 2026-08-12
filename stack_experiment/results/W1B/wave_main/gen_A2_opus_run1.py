from dataclasses import dataclass


# ---- Configuration constants (decision table DT-S thresholds) ----
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

# Validation bounds (decision table DT-V)
WEIGHT_MIN, WEIGHT_MAX = 1, 30000
DISTANCE_MIN, DISTANCE_MAX = 1, 5000
VALUE_MIN, VALUE_MAX = 1, 1_000_000

# Tariff rates
RATE_PER_KG = 0.5
RATE_PER_KM = 0.1


# ---- Exceptions ----
class ValidationError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


# ---- External system: Screening Service ----
class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, configured_result=None):
        self._configured = configured_result

    def screen(self, shipper_id):
        result = self._configured
        if result is None:
            return 10  # default: low risk
        if isinstance(result, (int, float)):
            return result
        word = str(result).strip().lower()
        if word in ("error", "unavailable", "down", "timeout"):
            raise ScreeningUnavailableError("screening service unavailable")
        if word in ("approved", "accept", "clear", "pass", "active"):
            return 10
        if word in ("review", "hold", "manual"):
            return 50
        if word in ("declined", "refuse", "refused", "denied", "deny"):
            return 90
        # numeric string
        try:
            return float(word)
        except ValueError:
            return 10


# ---- External system: Notification Service ----
class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        # Fire-and-forget: failures never change the response.
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


# ---- Tariff Engine ----
class TariffEngine:
    """Computes the freight price from weight and distance per tariff rules."""

    def price(self, weight_kg, distance_km):
        return round(weight_kg * RATE_PER_KG + distance_km * RATE_PER_KM, 2)


# ---- Quote Store ----
class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available=True):
        self._available = available
        self._records = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._available:
            raise StoreUnavailableError("quote store unavailable")
        self._seq += 1
        quote_id = f"Q{self._seq:06d}"
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        rec = self._records.get(quote_id)
        if rec is None:
            raise StoreUnavailableError("quote record not found")
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        return quote_id


# ---- Quote API (orchestrator) ----
class QuoteApi:
    def __init__(self, quote_store, screening_service, tariff_engine,
                 notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            raise ValidationError("missing shipper_id")
        for name, value in (("weight_kg", weight_kg),
                            ("distance_km", distance_km),
                            ("declared_value", declared_value)):
            if not isinstance(value, (int, float)):
                raise ValidationError(f"invalid {name}")
        if not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            raise ValidationError("weight_kg out of bounds")
        if not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            raise ValidationError("distance_km out of bounds")
        if not (VALUE_MIN <= declared_value <= VALUE_MAX):
            raise ValidationError("declared_value out of bounds")

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Validation (DT-V)
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as exc:
            return {"status": "rejected", "reason": str(exc)}

        # Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError as exc:
            # On storage failure nothing else runs (DT-S note 3)
            return {"status": "error: store_unavailable", "reason": str(exc)}

        # Screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage does not fail the quote (DT-S note 5)
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, "held_unscreened", price_amount)
            return {"status": "held_unscreened",
                    "quote_id": quote_id, "price": price_amount}

        # Decision table DT-S
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount)
            return {"status": "quoted",
                    "quote_id": quote_id, "price": price_amount}

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # Review hold: no pricing, no notification (DT-S note 1)
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # riskIndex >= REFUSE_MIN
        self.quote_store.update_quote(quote_id, "refused_screening")
        self.notification_service.send_refusal_notice(shipper_id, quote_id)
        return {"status": "refused", "quote_id": quote_id}


# ---- Module-level end-to-end entry point ----
def handle(request: dict) -> dict:
    request = request or {}

    shipper_id = request.get("shipper_id", request.get("shipperId", "SHIP-1"))
    weight_kg = request.get("weight_kg", request.get("weightKg", 100))
    distance_km = request.get("distance_km", request.get("distanceKm", 100))
    declared_value = request.get(
        "declared_value", request.get("declaredValue", 1000))

    # Determine store availability from request flags
    store_result = (request.get("store_result")
                    or request.get("store_status")
                    or request.get("quote_store_result")
                    or request.get("quote_store_status"))
    store_available = True
    if store_result is not None:
        word = str(store_result).strip().lower()
        if word in ("error", "unavailable", "down"):
            store_available = False
    if request.get("store_exists") is False or request.get("store_found") is False:
        store_available = False

    # Determine screening configured result
    screening_result = (request.get("screening_result")
                        or request.get("screening_status")
                        or request.get("screening_service_result")
                        or request.get("screening_service_status"))

    quote_store = QuoteStore(available=store_available)
    screening_service = ScreeningService(configured_result=screening_result)
    tariff_engine = TariffEngine()
    notification_service = NotificationService()

    api = QuoteApi(quote_store, screening_service, tariff_engine,
                   notification_service)

    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
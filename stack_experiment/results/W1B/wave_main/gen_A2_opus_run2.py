import math


ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 69
REFUSE_MIN = 70

WEIGHT_MIN, WEIGHT_MAX = 1, 30000
DISTANCE_MIN, DISTANCE_MAX = 1, 3000
VALUE_MIN, VALUE_MAX = 0, 10_000_000


class ValidationError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, outcome=None):
        if outcome in ("error", "unavailable", "down"):
            raise ScreeningUnavailableError("screening service unavailable")
        if isinstance(outcome, (int, float)):
            return float(outcome)
        try:
            return float(outcome)
        except (TypeError, ValueError):
            pass
        mapping = {
            "approved": 10.0,
            "accept": 10.0,
            "clear": 10.0,
            "review": 50.0,
            "assessed": 50.0,
            "hold": 50.0,
            "declined": 90.0,
            "refuse": 90.0,
            "refused": 90.0,
            "denied": 90.0,
        }
        return mapping.get(outcome, 10.0)


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        # fire-and-forget; delivery failure never changes the response
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class TariffEngine:
    """Computes the freight price from weight and distance per published tariff rules."""

    BASE_FEE = 25.0
    RATE_PER_KG = 0.15
    RATE_PER_KM = 0.30

    def price(self, weight_kg, distance_km):
        amount = (
            self.BASE_FEE
            + self.RATE_PER_KG * float(weight_kg)
            + self.RATE_PER_KM * float(distance_km)
        )
        return round(amount, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, outcome=None):
        if outcome in ("error", "unavailable", "down"):
            raise StoreUnavailableError("quote store unavailable")
        self._seq += 1
        quote_id = "Q%05d" % self._seq
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
        record = self._records.get(quote_id)
        if record is None:
            raise StoreUnavailableError("quote record not found")
        record["status"] = status
        if price_amount is not None:
            record["price"] = price_amount
        return quote_id


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value, shipper_exists):
        if not shipper_id or not shipper_exists:
            raise ValidationError("unknown shipper")
        for name, value in (
            ("weightKg", weight_kg),
            ("distanceKm", distance_km),
            ("declaredValue", declared_value),
        ):
            if value is None or not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValidationError("missing or non-numeric %s" % name)
            if math.isnan(value) or math.isinf(value):
                raise ValidationError("invalid %s" % name)
        if not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            raise ValidationError("weightKg out of bounds")
        if not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            raise ValidationError("distanceKm out of bounds")
        if not (VALUE_MIN <= declared_value <= VALUE_MAX):
            raise ValidationError("declaredValue out of bounds")

    def request_quote(self, request):
        shipper_id = request.get("shipper_id") or request.get("shipperId")
        weight_kg = request.get("weight_kg", request.get("weightKg"))
        distance_km = request.get("distance_km", request.get("distanceKm"))
        declared_value = request.get("declared_value", request.get("declaredValue"))
        shipper_exists = request.get("shipper_exists", request.get("shipper_found", True))

        store_outcome = request.get("store_result", request.get("store_status"))
        screening_outcome = request.get(
            "screening_result", request.get("screening_status")
        )

        # Validation (DT-V)
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value, shipper_exists)
        except ValidationError as exc:
            return {"status": "rejected: invalid request", "reason": str(exc)}

        # Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value, store_outcome
            )
        except StoreUnavailableError as exc:
            # Nothing else runs on storage failure (DT-S note 3).
            return {"status": "error: store unavailable", "reason": str(exc)}

        # Screening
        try:
            risk_index = self.screening_service.screen(shipper_id, screening_outcome)
        except ScreeningUnavailableError:
            # Screening outage does not fail the quote (DT-S note 5).
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
            }

        # Screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {
                "status": "confirmed",
                "quote_id": quote_id,
                "price": price_amount,
                "risk_index": risk_index,
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # Review hold: no pricing, no notification (DT-S note 1).
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "rejected: screening",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }


def handle(request: dict) -> dict:
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    api = QuoteApi(quote_store, screening_service, tariff_engine, notification_service)
    try:
        return api.request_quote(request)
    except Exception as exc:  # pragma: no cover - safety net
        return {"status": "error: %s" % exc}
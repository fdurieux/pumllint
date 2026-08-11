import math


# ---- Decision thresholds (DT-S) ---------------------------------------
ACCEPT_MAX = 30.0
REVIEW_MIN = 31.0
REVIEW_MAX = 69.0
REFUSE_MIN = 70.0

# ---- Validation bounds (DT-V) -----------------------------------------
WEIGHT_MIN, WEIGHT_MAX = 1.0, 26000.0
DISTANCE_MIN, DISTANCE_MAX = 1.0, 3000.0
VALUE_MIN, VALUE_MAX = 0.0, 10_000_000.0


# ---- Exceptions -------------------------------------------------------
class ValidationError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


# ---- External system: Screening Service -------------------------------
class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, context=None):
        context = context or {}
        status = str(context.get("screening_status", "")).lower()
        if status in ("error", "unavailable", "down", "timeout"):
            raise ScreeningUnavailableError("screening service unavailable")

        result = context.get("screening_result", context.get("screening_score"))
        if result is None:
            return 10.0  # default low risk
        word = str(result).lower()
        if word in ("error", "unavailable"):
            raise ScreeningUnavailableError("screening service unavailable")
        mapping = {
            "approved": 10.0,
            "accept": 10.0,
            "clear": 10.0,
            "review": 50.0,
            "hold": 50.0,
            "declined": 90.0,
            "refuse": 90.0,
            "denied": 90.0,
        }
        if word in mapping:
            return mapping[word]
        try:
            return float(result)
        except (TypeError, ValueError):
            return 10.0


# ---- External system: Notification Service ----------------------------
class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "queued"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "queued"


# ---- Container DB: Quote Store ----------------------------------------
class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._seq = 0
        self._records = {}

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, context=None):
        context = context or {}
        status = str(context.get("store_status", context.get("store_result", ""))).lower()
        if status in ("error", "unavailable", "down"):
            raise StoreUnavailableError("quote store unavailable")
        self._seq += 1
        quote_id = "Q-%04d" % self._seq
        self._records[quote_id] = {
            "shipperId": shipper_id,
            "weightKg": weight_kg,
            "distanceKm": distance_km,
            "declaredValue": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        rec = self._records.get(quote_id)
        if rec is not None:
            rec["status"] = status
            if price_amount is not None:
                rec["price"] = price_amount
        return "updated"


# ---- Container: Tariff Engine -----------------------------------------
class TariffEngine:
    """Computes the freight price from weight and distance per the tariff rules."""

    BASE_FEE = 25.0
    RATE_PER_KG = 0.15
    RATE_PER_KM = 0.40
    RATE_PER_KG_KM = 0.0005

    def price(self, weight_kg, distance_km):
        amount = (
            self.BASE_FEE
            + self.RATE_PER_KG * weight_kg
            + self.RATE_PER_KM * distance_km
            + self.RATE_PER_KG_KM * weight_kg * distance_km
        )
        return round(amount, 2)


# ---- Container: Quote API (orchestrator) ------------------------------
class QuoteApi:
    def __init__(self, tariff_engine=None, quote_store=None,
                 screening_service=None, notification_service=None):
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    # DT-V validation
    def _validate(self, shipper_id, weight_kg, distance_km, declared_value, context):
        if not shipper_id:
            raise ValidationError("missing shipperId")
        if context.get("shipper_exists") is False or context.get("shipper_found") is False:
            raise ValidationError("shipper not found")
        for name, val, lo, hi in (
            ("weightKg", weight_kg, WEIGHT_MIN, WEIGHT_MAX),
            ("distanceKm", distance_km, DISTANCE_MIN, DISTANCE_MAX),
            ("declaredValue", declared_value, VALUE_MIN, VALUE_MAX),
        ):
            if val is None:
                raise ValidationError("missing %s" % name)
            try:
                num = float(val)
            except (TypeError, ValueError):
                raise ValidationError("non-numeric %s" % name)
            if math.isnan(num) or num < lo or num > hi:
                raise ValidationError("out-of-bounds %s" % name)
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value, context=None):
        context = context or {}

        # --- validation (DT-V) ---
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value, context)
        except ValidationError as exc:
            return {"status": "rejected: invalid request", "reason": str(exc)}

        weight_kg = float(weight_kg)
        distance_km = float(distance_km)
        declared_value = float(declared_value)

        # --- store draft ---
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value, context
            )
        except StoreUnavailableError as exc:
            # DT-S note 3: nothing else runs on storage failure
            return {"status": "error: store unavailable", "reason": str(exc)}

        # --- screening (DT-S) ---
        try:
            risk_index = self.screening_service.screen(shipper_id, context)
        except ScreeningUnavailableError:
            # DT-S note 5: screening outage does not fail the quote
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quoteId": quote_id,
                "price": price_amount,
            }

        if risk_index <= ACCEPT_MAX:
            # accept -> price, quote, notify
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quoteId": quote_id,
                "price": price_amount,
                "riskIndex": risk_index,
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # review hold -> no pricing, no notification
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quoteId": quote_id,
                "riskIndex": risk_index,
            }
        elif risk_index >= REFUSE_MIN:
            # refuse -> notify, no pricing
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused",
                "quoteId": quote_id,
                "riskIndex": risk_index,
            }
        else:
            # gap between ACCEPT_MAX and REVIEW_MIN -> treat as review hold
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quoteId": quote_id,
                "riskIndex": risk_index,
            }


# ---- Module-level entry point -----------------------------------------
def _first(request, *keys, default=None):
    for k in keys:
        if k in request and request[k] is not None:
            return request[k]
    return default


def handle(request: dict) -> dict:
    request = request or {}

    shipper_id = _first(request, "shipperId", "shipper_id", "shipper", default=None)
    weight_kg = _first(request, "weightKg", "weight_kg", "weight")
    distance_km = _first(request, "distanceKm", "distance_km", "distance")
    declared_value = _first(request, "declaredValue", "declared_value", "value")

    api = QuoteApi()
    try:
        return api.request_quote(shipper_id, weight_kg, distance_km, declared_value, request)
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "error: %s" % exc}
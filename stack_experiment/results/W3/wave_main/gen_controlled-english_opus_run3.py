MAX_WEIGHT_KG = 30000.0
MAX_DISTANCE_KM = 5000.0
MAX_DECLARED_VALUE = 10_000_000.0

ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

STATUS_QUOTED = "quoted"
STATUS_REVIEW_HOLD = "review_hold"
STATUS_REFUSED_SCREENING = "refused_screening"
STATUS_HELD_UNSCREENED = "held_unscreened"


class ValidationError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, context=None):
        context = context or {}
        status = str(context.get("screening_status", context.get("screening_result", ""))).lower()
        if status in ("error", "unavailable", "down", "timeout"):
            raise ScreeningUnavailableError("screening service unavailable")

        result = context.get("screening_result", context.get("screening_status"))
        if isinstance(result, (int, float)):
            return float(result)
        result = str(result).lower()
        mapping = {
            "approved": 10.0,
            "clear": 10.0,
            "accept": 10.0,
            "low": 10.0,
            "review": 50.0,
            "hold": 50.0,
            "medium": 50.0,
            "declined": 90.0,
            "refuse": 90.0,
            "denied": 90.0,
            "high": 90.0,
            "assessed": 10.0,
        }
        return mapping.get(result, 10.0)


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        return "sent"

    def sendRefusalNotice(self, shipper_id, quote_id):
        return "sent"


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff rules."""

    BASE_FEE = 25.0
    RATE_PER_KG = 0.15
    RATE_PER_KM = 0.40

    def price(self, weight_kg, distance_km):
        return round(
            self.BASE_FEE
            + self.RATE_PER_KG * float(weight_kg)
            + self.RATE_PER_KM * float(distance_km),
            2,
        )


class QuoteStore:
    """Stores quote requests and their lifecycle status (PostgreSQL)."""

    def __init__(self):
        self._records = {}
        self._counter = 0

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value, context=None):
        context = context or {}
        status = str(context.get("store_status", context.get("store_result", ""))).lower()
        if status in ("error", "unavailable", "down"):
            raise StoreUnavailableError("quote store unavailable")
        self._counter += 1
        quote_id = "Q%05d" % self._counter
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def updateQuote(self, quote_id, status, price_amount=None):
        record = self._records.get(quote_id)
        if record is not None:
            record["status"] = status
            if price_amount is not None:
                record["price"] = price_amount
        return quote_id


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, store, screening, tariff, notification):
        self.store = store
        self.screening = screening
        self.tariff = tariff
        self.notification = notification

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value, context):
        if context.get("shipper_exists") is False or context.get("shipper_found") is False:
            raise ValidationError("unknown shipper")
        if not shipper_id:
            raise ValidationError("missing shipper id")
        try:
            weight_kg = float(weight_kg)
            distance_km = float(distance_km)
            declared_value = float(declared_value)
        except (TypeError, ValueError):
            raise ValidationError("non-numeric field")
        if not (0 < weight_kg <= MAX_WEIGHT_KG):
            raise ValidationError("weight out of bounds")
        if not (0 < distance_km <= MAX_DISTANCE_KM):
            raise ValidationError("distance out of bounds")
        if not (0 < declared_value <= MAX_DECLARED_VALUE):
            raise ValidationError("declared value out of bounds")

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value, context=None):
        context = context or {}

        # Step 2: validate
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value, context)
        except ValidationError as e:
            return {"status": "rejected", "reason": "invalid_request", "detail": str(e)}

        # Step 2/3: store draft
        try:
            quote_id = self.store.storeDraft(
                shipper_id, weight_kg, distance_km, declared_value, context
            )
        except StoreUnavailableError as e:
            return {"status": "error: store_unavailable", "detail": str(e)}

        # Step 3: screening
        try:
            risk_index = self.screening.screen(shipper_id, context)
        except ScreeningUnavailableError:
            # Case d: screening outage -> price, hold unscreened, no notification
            price_amount = self.tariff.price(weight_kg, distance_km)
            self.store.updateQuote(quote_id, STATUS_HELD_UNSCREENED, price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
            }

        # Step 4: apply screening decision
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff.price(weight_kg, distance_km)
            self.store.updateQuote(quote_id, STATUS_QUOTED, price_amount)
            self._notify_quote(shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount,
                "risk_index": risk_index,
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.store.updateQuote(quote_id, STATUS_REVIEW_HOLD)
            return {
                "status": "review_hold",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }
        else:  # risk_index >= REFUSE_MIN
            self.store.updateQuote(quote_id, STATUS_REFUSED_SCREENING)
            self._notify_refusal(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }

    def _notify_quote(self, shipper_id, quote_id, price_amount):
        # fire-and-forget: delivery failures never change the response
        try:
            self.notification.sendQuoteDocument(shipper_id, quote_id, price_amount)
        except Exception:
            pass

    def _notify_refusal(self, shipper_id, quote_id):
        try:
            self.notification.sendRefusalNotice(shipper_id, quote_id)
        except Exception:
            pass


def handle(request: dict) -> dict:
    request = request or {}
    store = QuoteStore()
    screening = ScreeningService()
    tariff = TariffEngine()
    notification = NotificationService()
    api = QuoteApi(store, screening, tariff, notification)

    shipper_id = request.get("shipper_id", request.get("shipperId"))
    weight_kg = request.get("weight_kg", request.get("weightKg"))
    distance_km = request.get("distance_km", request.get("distanceKm"))
    declared_value = request.get("declared_value", request.get("declaredValue"))

    return api.requestQuote(shipper_id, weight_kg, distance_km, declared_value, request)
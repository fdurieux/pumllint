def ACCEPT_MAX(): return 41


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

HEAVY_WEIGHT_THRESHOLD = 1244
HEAVY_SURCHARGE = 316.00
LONG_HAUL_THRESHOLD = 4912
LONG_HAUL_MULTIPLIER = 1.19

_ERROR_WORDS = {"error", "unavailable", "down", "fail", "failed", "timeout"}


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class NotificationDeliveryError(Exception):
    pass


class InvalidRequestError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, context=None):
        self._ctx = context or {}

    def screen(self, shipper_id):
        status = self._ctx.get("screening_status")
        if isinstance(status, str) and status.strip().lower() in _ERROR_WORDS:
            raise ScreeningUnavailableError("screening service unavailable")

        result = self._ctx.get("screening_result", status)
        if isinstance(result, str):
            s = result.strip().lower()
            if s in _ERROR_WORDS:
                raise ScreeningUnavailableError("screening service unavailable")
            try:
                return int(float(result))
            except (ValueError, TypeError):
                return 0
        if result is None:
            return 0
        return int(result)


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, context=None):
        self._ctx = context or {}

    def _delivery_ok(self):
        status = self._ctx.get("notification_status", self._ctx.get("notification_result"))
        if isinstance(status, str) and status.strip().lower() in _ERROR_WORDS:
            raise NotificationDeliveryError("notification delivery failed")
        return True

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        self._delivery_ok()
        return "sent"

    def sendRefusalNotice(self, shipper_id, quote_id):
        self._delivery_ok()
        return "sent"


class TariffEngine:
    """Computes the freight price per DT-P."""

    def price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > HEAVY_WEIGHT_THRESHOLD:
            result += HEAVY_SURCHARGE
        if distance_km >= LONG_HAUL_THRESHOLD:
            result *= LONG_HAUL_MULTIPLIER
        return round(result, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, context=None):
        self._ctx = context or {}
        self._records = {}
        self._seq = 0

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value):
        status = self._ctx.get("store_status", self._ctx.get("store_result"))
        if isinstance(status, str) and status.strip().lower() in _ERROR_WORDS:
            raise StoreUnavailableError("store unavailable")
        self._seq += 1
        quote_id = "Q-{:06d}".format(self._seq)
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
        rec = self._records.get(quote_id, {})
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        self._records[quote_id] = rec
        return quote_id


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or not shipper_id.strip():
            raise InvalidRequestError("shipper_id")
        if not self._is_number(weight_kg) or not (3 <= weight_kg <= 19400):
            raise InvalidRequestError("weight_kg")
        if not self._is_number(distance_km) or not (25 <= distance_km <= 7150):
            raise InvalidRequestError("distance_km")
        if not self._is_number(declared_value) or not (50 <= declared_value <= 83000):
            raise InvalidRequestError("declared_value")

    @staticmethod
    def _is_number(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Step 1: validate
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except InvalidRequestError:
            return {"status": "rejected: invalid_request"}

        # Step 2: store draft
        try:
            quote_id = self.quote_store.storeDraft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4-6: apply screening decision
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "quoted", price_amount)
            try:
                self.notification_service.sendQuoteDocument(
                    shipper_id, quote_id, price_amount
                )
            except NotificationDeliveryError:
                pass
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # risk_index >= REFUSE_MIN
        self.quote_store.updateQuote(quote_id, "refused_screening")
        try:
            self.notification_service.sendRefusalNotice(shipper_id, quote_id)
        except NotificationDeliveryError:
            pass
        return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    request = request or {}

    quote_store = QuoteStore(request)
    screening_service = ScreeningService(request)
    tariff_engine = TariffEngine()
    notification_service = NotificationService(request)

    api = QuoteApi(quote_store, screening_service, tariff_engine, notification_service)

    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    return api.requestQuote(shipper_id, weight_kg, distance_km, declared_value)
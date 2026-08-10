def price_quote(weight_kg, distance_km):
    result = 0.87 * weight_kg + 1.13 * distance_km
    if weight_kg > 1244:
        result += 316.00
    if distance_km >= 4912:
        result *= 1.19
    return round(result, 2)


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class TariffEngine:
    """Computes freight price from weight and distance per DT-P."""

    def price(self, weight_kg, distance_km):
        return price_quote(weight_kg, distance_km)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._counter = 0

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value, store_status="stored"):
        if store_status in ("error", "unavailable", "store_unavailable"):
            raise StoreUnavailableError("store_unavailable")
        self._counter += 1
        quote_id = "Q-%04d" % self._counter
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def updateQuote(self, quote_id, status, price=None):
        rec = self._records.get(quote_id)
        if rec is not None:
            rec["status"] = status
            if price is not None:
                rec["price"] = price
        return quote_id


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, screening_result=None):
        if screening_result in ("error", "unavailable", "screening_unavailable"):
            raise ScreeningUnavailableError("screening_unavailable")
        if screening_result is None:
            return 0
        try:
            return int(screening_result)
        except (TypeError, ValueError):
            raise ScreeningUnavailableError("screening_unavailable")


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount, notification_result=None):
        if notification_result in ("error", "unavailable", "failed"):
            return "delivery_failed"
        return "delivered"

    def sendRefusalNotice(self, shipper_id, quote_id, notification_result=None):
        if notification_result in ("error", "unavailable", "failed"):
            return "delivery_failed"
        return "delivered"


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and
    pricing, and returns the quotation outcome."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or not shipper_id.strip():
            return False
        if not self._is_number(weight_kg) or not (3 <= weight_kg <= 19400):
            return False
        if not self._is_number(distance_km) or not (25 <= distance_km <= 7150):
            return False
        if not self._is_number(declared_value) or not (50 <= declared_value <= 83000):
            return False
        return True

    @staticmethod
    def _is_number(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def requestQuote(self, request):
        shipper_id = request.get("shipper_id")
        weight_kg = request.get("weight_kg")
        distance_km = request.get("distance_km")
        declared_value = request.get("declared_value")

        # Step 1: validate (DT-V)
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        # Step 2: store draft
        store_status = request.get("store_result", request.get("store_status", "stored"))
        try:
            quote_id = self.quote_store.storeDraft(
                shipper_id, weight_kg, distance_km, declared_value, store_status
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        screening_result = request.get("screening_result", request.get("screening_status"))
        try:
            risk_index = self.screening_service.screen(shipper_id, screening_result)
        except ScreeningUnavailableError:
            # Screening outage: price anyway, hold, no notification
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4-6: apply DT-S decision
        notification_result = request.get("notification_result", request.get("notification_status"))

        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "quoted", price_amount)
            self.notification_service.sendQuoteDocument(
                shipper_id, quote_id, price_amount, notification_result
            )
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}

        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        else:  # risk_index >= REFUSE_MIN
            self.quote_store.updateQuote(quote_id, "refused_screening")
            self.notification_service.sendRefusalNotice(
                shipper_id, quote_id, notification_result
            )
            return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)
    try:
        return api.requestQuote(request)
    except Exception as exc:
        return {"status": "error: %s" % exc}
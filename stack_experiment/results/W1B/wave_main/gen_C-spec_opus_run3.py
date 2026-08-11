from typing import Optional


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, risk_result=None):
        if risk_result == "error":
            raise ScreeningUnavailableError("screening service unavailable")
        if risk_result is None:
            return 0
        if isinstance(risk_result, (int, float)):
            return int(risk_result)
        # map words to bands
        mapping = {
            "approved": 10,
            "accept": 10,
            "active": 10,
            "review": 50,
            "assessed": 50,
            "declined": 90,
            "refuse": 90,
            "lapsed": 90,
        }
        return mapping.get(str(risk_result), 0)


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        return "sent"

    def sendRefusalNotice(self, shipper_id, quote_id):
        return "sent"


class TariffEngine:
    """Computes the freight price from weight and distance per the published tariff rules."""

    def price(self, weight_kg, distance_km):
        base = 0.87 * weight_kg + 1.13 * distance_km
        total = base
        if weight_kg > 1244:
            total += 316.00
        if distance_km >= 4912:
            total *= 1.19
        return round(total, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._counter = 0

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value, store_result=None):
        if store_result == "error":
            raise StoreUnavailableError("store unavailable")
        self._counter += 1
        quote_id = "Q%04d" % self._counter
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


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class InvalidRequestError(Exception):
    pass


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, tariff_engine=None, quote_store=None,
                 screening_service=None, notification_service=None):
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            raise InvalidRequestError("shipper_id")
        if not isinstance(weight_kg, (int, float)) or not (3 <= weight_kg <= 19400):
            raise InvalidRequestError("weight_kg")
        if not isinstance(distance_km, (int, float)) or not (25 <= distance_km <= 7150):
            raise InvalidRequestError("distance_km")
        if not isinstance(declared_value, (int, float)) or not (50 <= declared_value <= 83000):
            raise InvalidRequestError("declared_value")

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value,
                     store_result=None, risk_result=None):
        # DT-V validation
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except InvalidRequestError:
            return {"status": "rejected: invalid_request"}

        # store draft
        try:
            quote_id = self.quote_store.storeDraft(
                shipper_id, weight_kg, distance_km, declared_value, store_result)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # screening
        try:
            risk_index = self.screening_service.screen(shipper_id, risk_result)
        except ScreeningUnavailableError:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price)
            return {"status": "held_unscreened", "quote_id": quote_id,
                    "price": price, "hold": True}

        # DT-S banding
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "quoted", price)
            self.notification_service.sendQuoteDocument(shipper_id, quote_id, price)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.updateQuote(quote_id, "refused_screening")
            self.notification_service.sendRefusalNotice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    api = QuoteApi()

    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    # store outcome
    store_result = request.get("store_result") or request.get("store_status")
    if request.get("quote_store_exists") is False or request.get("store_found") is False:
        store_result = "error"

    # screening outcome
    risk_result = request.get("screening_result")
    if risk_result is None:
        risk_result = request.get("screening_status")

    return api.requestQuote(shipper_id, weight_kg, distance_km, declared_value,
                            store_result=store_result, risk_result=risk_result)
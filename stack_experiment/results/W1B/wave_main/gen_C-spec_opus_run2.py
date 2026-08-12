from typing import Optional

ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, risk_result=None):
        if risk_result == "error":
            raise ScreeningUnavailableError("screening service unavailable")
        if risk_result is None:
            return 0
        try:
            return int(risk_result)
        except (TypeError, ValueError):
            return 0


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        return "sent"

    def sendRefusalNotice(self, shipper_id, quote_id):
        return "sent"


class TariffEngine:
    """Computes the freight price per DT-P."""

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
        self._seq = 0
        self._records = {}

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value, store_result=None):
        if store_result == "error":
            raise StoreUnavailableError("quote store unavailable")
        self._seq += 1
        quote_id = "Q%04d" % self._seq
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
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


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, store=None, screening=None, tariff=None, notification=None):
        self.store = store or QuoteStore()
        self.screening = screening or ScreeningService()
        self.tariff = tariff or TariffEngine()
        self.notification = notification or NotificationService()

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not shipper_id:
            raise InvalidRequestError("shipper_id")
        weight = request.get("weight_kg")
        if not self._is_number(weight) or not (3 <= weight <= 19400):
            raise InvalidRequestError("weight_kg")
        distance = request.get("distance_km")
        if not self._is_number(distance) or not (25 <= distance <= 7150):
            raise InvalidRequestError("distance_km")
        value = request.get("declared_value")
        if not self._is_number(value) or not (50 <= value <= 83000):
            raise InvalidRequestError("declared_value")

    @staticmethod
    def _is_number(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def requestQuote(self, request):
        # DT-V validation
        try:
            self._validate(request)
        except InvalidRequestError:
            return {"status": "rejected: invalid_request"}

        shipper_id = request.get("shipper_id")
        weight = request.get("weight_kg")
        distance = request.get("distance_km")
        value = request.get("declared_value")

        # store draft
        try:
            quote_id = self.store.storeDraft(
                shipper_id, weight, distance, value,
                store_result=request.get("store_result"),
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # screening
        try:
            risk_index = self.screening.screen(
                shipper_id, risk_result=request.get("screening_result"),
            )
        except ScreeningUnavailableError:
            price_amount = self.tariff.price(weight, distance)
            self.store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff.price(weight, distance)
            self.store.updateQuote(quote_id, "quoted", price_amount)
            self.notification.sendQuoteDocument(shipper_id, quote_id, price_amount)
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.store.updateQuote(quote_id, "refused_screening")
            self.notification.sendRefusalNotice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    api = QuoteApi()
    return api.requestQuote(request)
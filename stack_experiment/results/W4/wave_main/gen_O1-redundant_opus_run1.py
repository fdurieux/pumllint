import math


class ScreeningUnavailableError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, risk_index=0, available=True):
        self._risk_index = risk_index
        self._available = available

    def screen(self, shipper_id):
        if not self._available:
            raise ScreeningUnavailableError("screening_unavailable")
        return int(self._risk_index)


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, deliverable=True):
        self._deliverable = deliverable

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        # Fire-and-forget: never raises to the caller in a way that changes outcome.
        return "delivered" if self._deliverable else "delivery_failed"

    def sendRefusalNotice(self, shipper_id, quote_id):
        return "delivered" if self._deliverable else "delivery_failed"


class TariffEngine:
    """Computes the freight price from weight and distance per DT-P."""

    WEIGHT_RATE = 0.87
    DISTANCE_RATE = 1.13
    HEAVY_THRESHOLD = 1244
    HEAVY_SURCHARGE = 316.00
    LONGHAUL_THRESHOLD = 4912
    LONGHAUL_FACTOR = 1.19

    def price(self, weight_kg, distance_km):
        total = self.WEIGHT_RATE * weight_kg + self.DISTANCE_RATE * distance_km
        if weight_kg > self.HEAVY_THRESHOLD:
            total += self.HEAVY_SURCHARGE
        if distance_km >= self.LONGHAUL_THRESHOLD:
            total *= self.LONGHAUL_FACTOR
        return round(total, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available=True):
        self._available = available
        self._records = {}
        self._counter = 0

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._available:
            raise StoreUnavailableError("store_unavailable")
        self._counter += 1
        quote_id = "Q-{:06d}".format(self._counter)
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
        if record is None:
            record = {}
            self._records[quote_id] = record
        record["status"] = status
        if price_amount is not None:
            record["price"] = price_amount
        return quote_id


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening/pricing, returns outcome."""

    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

    WEIGHT_MIN = 3
    WEIGHT_MAX = 19400
    DISTANCE_MIN = 25
    DISTANCE_MAX = 7150
    VALUE_MIN = 50
    VALUE_MAX = 83000

    def __init__(self, store, screening, tariff, notification):
        self._store = store
        self._screening = screening
        self._tariff = tariff
        self._notification = notification

    def _is_number(self, value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False
        if not self._is_number(weight_kg) or not (self.WEIGHT_MIN <= weight_kg <= self.WEIGHT_MAX):
            return False
        if not self._is_number(distance_km) or not (self.DISTANCE_MIN <= distance_km <= self.DISTANCE_MAX):
            return False
        if not self._is_number(declared_value) or not (self.VALUE_MIN <= declared_value <= self.VALUE_MAX):
            return False
        return True

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Step 1: validate
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        # Step 2: store draft
        try:
            quote_id = self._store.storeDraft(shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self._screening.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage: price anyway, hold, do not notify.
            price_amount = self._tariff.price(weight_kg, distance_km)
            self._store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4-7: apply screening decision
        if risk_index <= self.ACCEPT_MAX:
            price_amount = self._tariff.price(weight_kg, distance_km)
            self._store.updateQuote(quote_id, "quoted", price_amount)
            self._notification.sendQuoteDocument(shipper_id, quote_id, price_amount)
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}
        elif risk_index <= self.REVIEW_MAX:
            self._store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:
            self._store.updateQuote(quote_id, "refused_screening")
            self._notification.sendRefusalNotice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}


def _screening_unavailable(request):
    for key in ("screening_status", "screening_result", "screening"):
        val = request.get(key)
        if isinstance(val, str) and val.lower() in ("error", "unavailable", "down", "timeout"):
            return True
    return False


def _store_unavailable(request):
    for key in ("store_status", "store_result", "quote_store_status", "quote_store_result"):
        val = request.get(key)
        if isinstance(val, str) and val.lower() in ("error", "unavailable", "down"):
            return True
    if request.get("store_exists") is False or request.get("quote_store_exists") is False:
        return True
    return False


def _risk_index(request):
    for key in ("risk_index", "screening_result", "screening_status", "screening_score"):
        val = request.get(key)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return val
        if isinstance(val, str):
            try:
                return int(val)
            except ValueError:
                continue
    return 0


def _notification_deliverable(request):
    for key in ("notification_status", "notification_result", "notification"):
        val = request.get(key)
        if isinstance(val, str) and val.lower() in ("error", "fail", "failed", "undelivered"):
            return False
    return True


def handle(request: dict) -> dict:
    store = QuoteStore(available=not _store_unavailable(request))
    screening = ScreeningService(
        risk_index=_risk_index(request),
        available=not _screening_unavailable(request),
    )
    tariff = TariffEngine()
    notification = NotificationService(deliverable=_notification_deliverable(request))

    api = QuoteApi(store, screening, tariff, notification)

    return api.requestQuote(
        request.get("shipper_id"),
        request.get("weight_kg"),
        request.get("distance_km"),
        request.get("declared_value"),
    )
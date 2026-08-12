def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, risk_override=None):
        if risk_override is not None:
            return risk_override
        return 0


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        return "sent"

    def sendRefusalNotice(self, shipper_id, quote_id):
        return "sent"


class TariffEngine:
    """Computes the freight price from weight and distance per DT-P."""

    def price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            result += 316.00
        if distance_km >= 4912:
            result *= 1.19
        return round(result, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._seq = 0
        self._records = {}

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value, available=True):
        if not available:
            raise StoreUnavailableError("store_unavailable")
        self._seq += 1
        quote_id = "Q%d" % self._seq
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


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id or not isinstance(shipper_id, str):
            raise InvalidRequestError("invalid_request")
        if not (_is_number(weight_kg) and 3 <= weight_kg <= 19400):
            raise InvalidRequestError("invalid_request")
        if not (_is_number(distance_km) and 25 <= distance_km <= 7150):
            raise InvalidRequestError("invalid_request")
        if not (_is_number(declared_value) and 50 <= declared_value <= 83000):
            raise InvalidRequestError("invalid_request")

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value,
                     store_available=True, screening_available=True, risk_index=None):
        # DT-V validation
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except InvalidRequestError:
            return {"status": "rejected: invalid_request"}

        # store draft
        try:
            quote_id = self.quote_store.storeDraft(
                shipper_id, weight_kg, distance_km, declared_value, available=store_available)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # screening
        if not screening_available:
            # DT-S note 5: screening outage -> price, hold, no notify
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {"status": "held_unscreened", "quote_id": quote_id,
                    "price": price_amount, "hold": True}

        risk = self.screening_service.screen(shipper_id, risk_override=risk_index)

        if risk <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "quoted", price_amount)
            self.notification_service.sendQuoteDocument(shipper_id, quote_id, price_amount)
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}
        elif REVIEW_MIN <= risk <= REVIEW_MAX:
            self.quote_store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk >= REFUSE_MIN
            self.quote_store.updateQuote(quote_id, "refused_screening")
            self.notification_service.sendRefusalNotice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}


def _screening_available(request):
    for key in ("screening_result", "screening_status"):
        val = request.get(key)
        if isinstance(val, str) and val.lower() in ("error", "unavailable", "down", "outage"):
            return False
    return True


def _store_available(request):
    for key in ("store_result", "store_status", "quote_store_result", "quote_store_status"):
        val = request.get(key)
        if isinstance(val, str) and val.lower() in ("error", "unavailable", "down"):
            return False
    return True


def _risk_index(request):
    for key in ("screening_result", "screening_status", "risk_index"):
        val = request.get(key)
        if _is_number(val):
            return int(val)
        if isinstance(val, str):
            low = val.lower()
            if low in ("error", "unavailable", "down", "outage"):
                return None
            if low in ("approved", "accept", "accepted", "clear", "assessed"):
                return 0
            if low in ("review", "hold"):
                return 50
            if low in ("declined", "refuse", "refused", "denied"):
                return 99
            try:
                return int(low)
            except ValueError:
                pass
    return 0


def handle(request: dict) -> dict:
    api = QuoteApi(TariffEngine(), QuoteStore(), ScreeningService(), NotificationService())
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    store_ok = _store_available(request)
    screening_ok = _screening_available(request)
    risk = _risk_index(request) if screening_ok else None

    return api.requestQuote(
        shipper_id, weight_kg, distance_km, declared_value,
        store_available=store_ok,
        screening_available=screening_ok,
        risk_index=risk,
    )
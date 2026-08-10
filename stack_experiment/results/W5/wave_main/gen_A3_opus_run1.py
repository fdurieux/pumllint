ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

HEAVY_THRESHOLD = 1244
HEAVY_SURCHARGE = 316.00
LONGHAUL_THRESHOLD = 4912
LONGHAUL_MULTIPLIER = 1.19


class ScreeningServiceUnavailable(Exception):
    pass


class StoreUnavailable(Exception):
    pass


class InvalidRequest(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, outcome=None):
        if outcome is None:
            return 0
        if isinstance(outcome, (int, float)) and not isinstance(outcome, bool):
            return int(outcome)
        text = str(outcome).strip().lower()
        if text in ("error", "unavailable", "outage", "down"):
            raise ScreeningServiceUnavailable("screening service unavailable")
        if text in ("approved", "accept", "accepted", "active", "clear"):
            return 0
        if text in ("review", "hold"):
            return REVIEW_MIN
        if text in ("declined", "refuse", "refused", "denied"):
            return REFUSE_MIN
        try:
            return int(float(text))
        except ValueError:
            return 0


class TariffEngine:
    """Computes the freight price from weight and distance per DT-P."""

    def price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > HEAVY_THRESHOLD:
            result += HEAVY_SURCHARGE
        if distance_km >= LONGHAUL_THRESHOLD:
            result *= LONGHAUL_MULTIPLIER
        return round(result, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._counter = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, available=True):
        if not available:
            raise StoreUnavailable("store unavailable")
        self._counter += 1
        quote_id = "Q-%05d" % self._counter
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price=None):
        record = self._records.get(quote_id)
        if record is None:
            record = {}
            self._records[quote_id] = record
        record["status"] = status
        if price is not None:
            record["price"] = price
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine=None, quote_store=None,
                 screening_service=None, notification_service=None):
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False
        if not self._is_number(weight_kg) or not (3 <= weight_kg <= 19400):
            return False
        if not self._is_number(distance_km) or not (25 <= distance_km <= 7150):
            return False
        if not self._is_number(declared_value) or not (50 <= declared_value <= 83000):
            return False
        return True

    @staticmethod
    def _is_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value,
                      store_available=True, screening_outcome=None):
        # Step 1: validate
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        # Step 2: store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value,
                available=store_available)
        except StoreUnavailable:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(shipper_id, screening_outcome)
        except ScreeningServiceUnavailable:
            # outage: price anyway, hold, do not notify
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4/5/6: apply screening decision
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}


def _store_available(request):
    for key in ("store_status", "store_result", "quote_store_status",
                "quote_store_result"):
        if key in request:
            val = str(request[key]).strip().lower()
            if val in ("error", "unavailable", "down", "outage", "fail", "failed"):
                return False
            if val in ("stored", "ok", "available", "up"):
                return True
    if request.get("store_exists") is False or request.get("quote_store_exists") is False:
        return False
    return True


def _screening_outcome(request):
    for key in ("screening_result", "screening_status", "screening_service_result",
                "screening_service_status", "risk_index", "risk"):
        if key in request:
            return request[key]
    return None


def handle(request: dict) -> dict:
    api = QuoteApi()
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    store_available = _store_available(request)
    screening_outcome = _screening_outcome(request)

    return api.request_quote(
        shipper_id, weight_kg, distance_km, declared_value,
        store_available=store_available,
        screening_outcome=screening_outcome,
    )
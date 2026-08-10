import math


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000


class ScreeningUnavailable(Exception):
    pass


class StoreUnavailable(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, risk_index=0, available=True):
        self._risk_index = risk_index
        self._available = available

    def get_risk_index(self, shipper_id):
        if not self._available:
            raise ScreeningUnavailable("screening service unavailable")
        return int(self._risk_index)


class TariffEngine:
    """Computes the freight price per the published tariff rules (DT-P)."""

    def compute_price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            result += 316.00
        if distance_km >= 4912:
            result *= 1.19
        return round(result, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available=True):
        self._available = available
        self._records = {}
        self._counter = 0

    def store_draft(self, quote_request):
        if not self._available:
            raise StoreUnavailable("quote store unavailable")
        self._counter += 1
        quote_id = "Q-%04d" % self._counter
        self._records[quote_id] = dict(quote_request)
        self._records[quote_id]["status"] = "draft"
        return quote_id

    def update_status(self, quote_id, status):
        if quote_id in self._records:
            self._records[quote_id]["status"] = status
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, deliverable=True):
        self._deliverable = deliverable

    def send(self, shipper_id, message):
        if not self._deliverable:
            raise RuntimeError("notification delivery failed")
        return "delivered"


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False
        weight = request.get("weight_kg")
        if not isinstance(weight, (int, float)) or isinstance(weight, bool):
            return False
        if not (WEIGHT_MIN <= weight <= WEIGHT_MAX):
            return False
        distance = request.get("distance_km")
        if not isinstance(distance, (int, float)) or isinstance(distance, bool):
            return False
        if not (DISTANCE_MIN <= distance <= DISTANCE_MAX):
            return False
        value = request.get("declared_value")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False
        if not (VALUE_MIN <= value <= VALUE_MAX):
            return False
        return True

    def request_quote(self, request):
        # Step 1: validate (DT-V)
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight = request["weight_kg"]
        distance = request["distance_km"]

        # Step 2: store draft
        try:
            quote_id = self.quote_store.store_draft(request)
        except StoreUnavailable:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.get_risk_index(shipper_id)
        except ScreeningUnavailable:
            price = self.tariff_engine.compute_price(weight, distance)
            self.quote_store.update_status(quote_id, "held_unscreened")
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4/5/6: apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            self.quote_store.update_status(quote_id, "quoted")
            price = self.tariff_engine.compute_price(weight, distance)
            self._notify(shipper_id, "quote_document")
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif risk_index <= REVIEW_MAX:
            self.quote_store.update_status(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:
            self.quote_store.update_status(quote_id, "refused_screening")
            self._notify(shipper_id, "refusal_notice")
            return {"status": "refused_screening", "quote_id": quote_id}

    def _notify(self, shipper_id, message):
        # fire-and-forget: delivery failure never changes outcome
        try:
            self.notification_service.send(shipper_id, message)
        except Exception:
            pass


def _resolve_risk_index(request):
    for key in ("screening_result", "screening_status", "risk_index"):
        if key in request:
            val = request[key]
            if isinstance(val, bool):
                continue
            if isinstance(val, (int, float)):
                return int(val), True
            if isinstance(val, str):
                s = val.strip().lower()
                if s in ("error", "unavailable", "outage", "down"):
                    return None, False
                try:
                    return int(float(s)), True
                except ValueError:
                    if s == "approved":
                        return 0, True
                    if s == "declined":
                        return 99, True
    return 0, True


def handle(request: dict) -> dict:
    # Configure store availability
    store_status = str(request.get("store_status", request.get("store_result", "stored"))).lower()
    store_available = store_status not in ("error", "unavailable", "down", "failed")

    # Configure screening
    risk_index, screening_available = _resolve_risk_index(request)

    # Configure notification
    notif_status = str(request.get("notification_status", request.get("notification_result", "ok"))).lower()
    notif_deliverable = notif_status not in ("error", "failed", "undelivered", "down")

    quote_store = QuoteStore(available=store_available)
    screening_service = ScreeningService(
        risk_index=risk_index if risk_index is not None else 0,
        available=screening_available,
    )
    tariff_engine = TariffEngine()
    notification_service = NotificationService(deliverable=notif_deliverable)

    api = QuoteApi(quote_store, screening_service, tariff_engine, notification_service)
    return api.request_quote(request)
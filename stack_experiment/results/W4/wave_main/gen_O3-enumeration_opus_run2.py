ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class ScreeningError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, risk_index=0, available=True):
        if not available:
            raise ScreeningError("screening_unavailable")
        return int(risk_index)


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount, deliverable=True):
        # fire-and-forget: delivery outcome never affects the response
        return "delivered" if deliverable else "delivery_failed"

    def send_refusal_notice(self, shipper_id, quote_id, deliverable=True):
        return "delivered" if deliverable else "delivery_failed"


class TariffEngine:
    """Computes the freight price per DT-P."""

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
        self._records = {}
        self._counter = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, available=True):
        if not available:
            raise StoreUnavailableError("store_unavailable")
        self._counter += 1
        quote_id = "Q{:06d}".format(self._counter)
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
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
        return quote_id


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, tariff_engine=None, quote_store=None,
                 screening_service=None, notification_service=None):
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or shipper_id == "":
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

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value,
                      risk_index=0, screening_available=True, store_available=True,
                      notification_deliverable=True):
        # Step 1: validate
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        # Step 2: store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value,
                available=store_available)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            index = self.screening_service.screen(
                shipper_id, risk_index=risk_index, available=screening_available)
        except ScreeningError:
            # Screening outage: price anyway, hold, no notification
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4-6: apply DT-S
        if index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount,
                deliverable=notification_deliverable)
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}
        elif REVIEW_MIN <= index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # index >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(
                shipper_id, quote_id, deliverable=notification_deliverable)
            return {"status": "refused_screening", "quote_id": quote_id}


_STORE = QuoteStore()
_API = QuoteApi(quote_store=_STORE)


def _truthy_outage(value):
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in ("error", "unavailable", "down", "outage", "lapsed", "false"):
        return False
    if s in ("active", "ok", "up", "available", "assessed", "true", "stored"):
        return True
    return None


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", request.get("shipper", ""))
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    # Store availability
    store_available = True
    for key in ("store_result", "store_status"):
        flag = _truthy_outage(request.get(key))
        if flag is False:
            store_available = False
    if request.get("quote_store_exists") is False:
        store_available = False

    # Screening availability + risk index
    screening_available = True
    risk_index = 0
    for key in ("screening_result", "screening_status"):
        val = request.get(key)
        if val is None:
            continue
        if isinstance(val, bool):
            continue
        if isinstance(val, (int, float)):
            risk_index = int(val)
            continue
        s = str(val).strip().lower()
        if s in ("error", "unavailable", "down", "outage"):
            screening_available = False
        elif s.lstrip("-").isdigit():
            risk_index = int(s)
    if "risk_index" in request and request["risk_index"] is not None:
        try:
            risk_index = int(request["risk_index"])
        except (TypeError, ValueError):
            pass

    # Notification deliverability
    notification_deliverable = True
    for key in ("notification_result", "notification_status"):
        flag = _truthy_outage(request.get(key))
        if flag is False:
            notification_deliverable = False

    return _API.request_quote(
        shipper_id, weight_kg, distance_km, declared_value,
        risk_index=risk_index,
        screening_available=screening_available,
        store_available=store_available,
        notification_deliverable=notification_deliverable,
    )
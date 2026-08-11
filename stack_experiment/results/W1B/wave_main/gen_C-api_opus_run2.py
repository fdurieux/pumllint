from typing import Optional


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, risk_index=None, status=None):
        if status in ("error", "unavailable", "outage"):
            raise ScreeningUnavailable("screening_unavailable")
        if risk_index is not None:
            return int(risk_index)
        # plausible default: accept band
        return 10


class TariffEngine:
    """Computes the freight price from weight and distance per DT-P."""

    def price(self, weight_kg, distance_km):
        base = 0.87 * weight_kg + 1.13 * distance_km  # P1
        result = base
        if weight_kg > 1244:  # P2
            result += 316.00
        if distance_km >= 4912:  # P3
            result *= 1.19
        return round(result, 2)  # P4


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._counter = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, available=True):
        if not available:
            raise StoreUnavailable("store_unavailable")
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

    def update_quote(self, quote_id, status, price=None):
        rec = self._records.get(quote_id)
        if rec is None:
            raise StoreUnavailable("quote_not_found")
        rec["status"] = status
        if price is not None:
            rec["price"] = price
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        # fire-and-forget
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        # fire-and-forget
        return "sent"


class StoreUnavailable(Exception):
    pass


class ScreeningUnavailable(Exception):
    pass


class InvalidRequest(Exception):
    pass


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
            raise InvalidRequest("V1")
        if not _is_number(weight_kg) or not (3 <= weight_kg <= 19400):
            raise InvalidRequest("V2")
        if not _is_number(distance_km) or not (25 <= distance_km <= 7150):
            raise InvalidRequest("V3")
        if not _is_number(declared_value) or not (50 <= declared_value <= 83000):
            raise InvalidRequest("V4")

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value,
                      store_available=True, screening_status=None, risk_index=None):
        # Step 1: validate
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except InvalidRequest:
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
            risk = self.screening_service.screen(
                shipper_id, risk_index=risk_index, status=screening_status)
        except ScreeningUnavailable:
            # screening outage: price anyway, hold
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4-6: apply screening decision
        if risk <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self._notify_quote(shipper_id, quote_id, price_amount)
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}
        elif REVIEW_MIN <= risk <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, "refused_screening")
            self._notify_refusal(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}

    def _notify_quote(self, shipper_id, quote_id, price_amount):
        try:
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
        except Exception:
            pass  # fire-and-forget

    def _notify_refusal(self, shipper_id, quote_id):
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            pass  # fire-and-forget


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _parse_risk(request):
    for key in ("screening_result", "screening_status", "screening_score", "risk_index"):
        if key in request:
            val = request[key]
            if val in ("error", "unavailable", "outage"):
                return None, "error"
            try:
                return int(val), None
            except (TypeError, ValueError):
                return None, None
    return None, None


def handle(request: dict) -> dict:
    api = QuoteApi()

    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    # storage availability
    store_available = True
    if request.get("store_result") in ("error", "unavailable") or \
       request.get("store_status") in ("error", "unavailable"):
        store_available = False
    if request.get("quote_store_exists") is False or request.get("store_available") is False:
        store_available = False

    risk_index, screening_status = _parse_risk(request)

    return api.request_quote(
        shipper_id, weight_kg, distance_km, declared_value,
        store_available=store_available,
        screening_status=screening_status,
        risk_index=risk_index,
    )
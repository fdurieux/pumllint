def ACCEPT_MAX(): return 41


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000

RATE_PER_KG = 0.87
RATE_PER_KM = 1.13
HEAVY_THRESHOLD = 1244
HEAVY_SURCHARGE = 316.00
LONGHAUL_THRESHOLD = 4912
LONGHAUL_FACTOR = 1.19


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, context=None):
        context = context or {}
        status = str(context.get("screening_status", context.get("screening_result", ""))).lower()
        if status in ("error", "unavailable", "down", "outage", "timeout"):
            raise ScreeningUnavailableError("screening service unavailable")
        for key in ("risk_index", "screening_result", "screening_score", "screening_status"):
            if key in context:
                val = context[key]
                try:
                    return int(val)
                except (TypeError, ValueError):
                    continue
        return 0


class TariffEngine:
    """Computes the freight price from weight and distance per DT-P."""

    def price(self, weight_kg, distance_km):
        total = RATE_PER_KG * weight_kg + RATE_PER_KM * distance_km
        if weight_kg > HEAVY_THRESHOLD:
            total += HEAVY_SURCHARGE
        if distance_km >= LONGHAUL_THRESHOLD:
            total *= LONGHAUL_FACTOR
        return round(total, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._quotes = {}
        self._counter = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, context=None):
        context = context or {}
        status = str(context.get("store_status", context.get("store_result", ""))).lower()
        if status in ("error", "unavailable", "down", "fail", "failed"):
            raise StoreUnavailableError("store unavailable")
        self._counter += 1
        quote_id = "Q-{:06d}".format(self._counter)
        self._quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price=None):
        rec = self._quotes.get(quote_id)
        if rec is not None:
            rec["status"] = status
            if price is not None:
                rec["price"] = price
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price, context=None):
        context = context or {}
        status = str(context.get("notification_status", context.get("notification_result", ""))).lower()
        if status in ("error", "fail", "failed", "undelivered"):
            return "failed"
        return "delivered"

    def send_refusal_notice(self, shipper_id, quote_id, context=None):
        context = context or {}
        status = str(context.get("notification_status", context.get("notification_result", ""))).lower()
        if status in ("error", "fail", "failed", "undelivered"):
            return "failed"
        return "delivered"


class QuoteApi:
    """Receives quote requests, orchestrates screening and pricing, returns outcome."""

    def __init__(self, tariff_engine=None, quote_store=None,
                 screening_service=None, notification_service=None):
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    def _is_number(self, v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def _validate(self, req):
        shipper_id = req.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False
        weight = req.get("weight_kg")
        if not self._is_number(weight) or not (WEIGHT_MIN <= weight <= WEIGHT_MAX):
            return False
        distance = req.get("distance_km")
        if not self._is_number(distance) or not (DISTANCE_MIN <= distance <= DISTANCE_MAX):
            return False
        value = req.get("declared_value")
        if not self._is_number(value) or not (VALUE_MIN <= value <= VALUE_MAX):
            return False
        return True

    def request_quote(self, req):
        # Step 1: validate
        if not self._validate(req):
            return {"status": "rejected: invalid_request"}

        shipper_id = req.get("shipper_id")
        weight = req.get("weight_kg")
        distance = req.get("distance_km")
        value = req.get("declared_value")

        # Step 2: store draft
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight, distance, value, req)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(shipper_id, req)
        except ScreeningUnavailableError:
            price = self.tariff_engine.price(weight, distance)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4-6: apply screening decision
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight, distance)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price, req)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id, req)
            return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    api = QuoteApi()
    return api.request_quote(request or {})
def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


class ScreeningServiceUnavailable(Exception):
    pass


class StoreUnavailable(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def request_risk_index(self, request):
        status = str(request.get("screening_status", "")).lower()
        result = request.get("screening_result", request.get("risk_index"))
        if status in ("error", "unavailable", "outage", "down"):
            raise ScreeningServiceUnavailable("screening unavailable")
        if isinstance(result, str) and result.lower() in ("error", "unavailable", "outage", "down"):
            raise ScreeningServiceUnavailable("screening unavailable")
        if _is_number(result):
            return int(result)
        if isinstance(result, str):
            try:
                return int(float(result))
            except ValueError:
                pass
        # default: an accept-band risk index
        return 12


class TariffEngine:
    """Computes the freight price from weight and distance per DT-P."""

    def compute_price(self, request):
        weight = request["weight_kg"]
        distance = request["distance_km"]
        result = 0.87 * weight + 1.13 * distance
        if weight > 1244:
            result += 316.00
        if distance >= 4912:
            result *= 1.19
        return round(result, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._counter = 0

    def store_draft(self, request):
        status = str(request.get("store_status", request.get("store_result", ""))).lower()
        if status in ("error", "unavailable", "fail", "failed"):
            raise StoreUnavailable("store unavailable")
        self._counter += 1
        quote_id = "Q-{:06d}".format(self._counter)
        self._records[quote_id] = {"request": dict(request), "status": "draft"}
        return quote_id

    def update_status(self, quote_id, status, price=None):
        rec = self._records.get(quote_id)
        if rec is not None:
            rec["status"] = status
            if price is not None:
                rec["price"] = price
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send(self, request, quote_id, message_type):
        status = str(request.get("notification_status", request.get("notification_result", ""))).lower()
        if status in ("error", "unavailable", "fail", "failed"):
            return "failed"
        return "delivered"


# Screening bands (DT-S)
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

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False
        weight = request.get("weight_kg")
        if not _is_number(weight) or not (3 <= weight <= 19400):
            return False
        distance = request.get("distance_km")
        if not _is_number(distance) or not (25 <= distance <= 7150):
            return False
        value = request.get("declared_value")
        if not _is_number(value) or not (50 <= value <= 83000):
            return False
        return True

    def request_quote(self, request):
        # Step 1: validate
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        # Step 2: store draft
        try:
            quote_id = self.quote_store.store_draft(request)
        except StoreUnavailable:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.request_risk_index(request)
        except ScreeningServiceUnavailable:
            # outage: price anyway, hold, do not notify
            price = self.tariff_engine.compute_price(request)
            self.quote_store.update_status(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4-6: apply screening decision
        if risk_index <= ACCEPT_MAX:
            self.quote_store.update_status(quote_id, "quoted")
            price = self.tariff_engine.compute_price(request)
            self.quote_store.update_status(quote_id, "quoted", price)
            self.notification_service.send(request, quote_id, "quote_document")
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_status(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # refuse
        self.quote_store.update_status(quote_id, "refused_screening")
        self.notification_service.send(request, quote_id, "refusal_notice")
        return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    api = QuoteApi()
    return api.request_quote(dict(request))
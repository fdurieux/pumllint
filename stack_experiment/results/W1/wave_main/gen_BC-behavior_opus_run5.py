def _round2(x):
    return round(x + 1e-9, 2)


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def risk_index(self, shipper_id, outcome):
        if outcome is None:
            return 0
        if isinstance(outcome, (int, float)) and not isinstance(outcome, bool):
            return int(outcome)
        text = str(outcome).strip().lower()
        if text in ("error", "unavailable", "outage", "down", "timeout"):
            raise ScreeningUnavailable("screening service unavailable")
        try:
            return int(float(text))
        except ValueError:
            return 0


class ScreeningUnavailable(Exception):
    pass


class StoreUnavailable(Exception):
    pass


class TariffEngine:
    """Computes the freight price from weight and distance per DT-P."""

    def price(self, weight_kg, distance_km, declared_value):
        result = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            result += 316.00
        if distance_km >= 4912:
            result *= 1.19
        return _round2(result)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._counter = 0

    def store_draft(self, request, outcome):
        if outcome is not None:
            text = str(outcome).strip().lower()
            if text in ("error", "unavailable", "down", "fail", "failed"):
                raise StoreUnavailable("store unavailable")
        self._counter += 1
        quote_id = "Q-{:06d}".format(self._counter)
        self._records[quote_id] = dict(request, status="draft")
        return quote_id

    def update_status(self, quote_id, status, price=None):
        rec = self._records.get(quote_id, {})
        rec["status"] = status
        if price is not None:
            rec["price"] = price
        self._records[quote_id] = rec
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send(self, shipper_id, message, outcome):
        if outcome is not None:
            text = str(outcome).strip().lower()
            if text in ("error", "unavailable", "fail", "failed", "down"):
                return "failed"
        return "delivered"


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening
    and pricing, and returns the quotation outcome."""

    def __init__(self, screening_service, tariff_engine, quote_store,
                 notification_service):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not shipper_id or not str(shipper_id).strip():
            return False
        weight = request.get("weight_kg")
        distance = request.get("distance_km")
        value = request.get("declared_value")
        if not self._is_number(weight) or not (3 <= weight <= 19400):
            return False
        if not self._is_number(distance) or not (25 <= distance <= 7150):
            return False
        if not self._is_number(value) or not (50 <= value <= 83000):
            return False
        return True

    @staticmethod
    def _is_number(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def request_quote(self, request):
        # 1. Validate
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        # 2. Store draft
        try:
            quote_id = self.quote_store.store_draft(
                request, request.get("store_result", request.get("store_status")))
        except StoreUnavailable:
            return {"status": "error: store_unavailable"}

        shipper_id = request.get("shipper_id")
        weight = request.get("weight_kg")
        distance = request.get("distance_km")
        value = request.get("declared_value")

        # 3. Screening
        screening_outcome = request.get("screening_result",
                                        request.get("screening_status"))
        try:
            risk_index = self.screening_service.risk_index(
                shipper_id, screening_outcome)
        except ScreeningUnavailable:
            price = self.tariff_engine.price(weight, distance, value)
            self.quote_store.update_status(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        notif_outcome = request.get("notification_result",
                                    request.get("notification_status"))

        # 4/5/6. Apply screening decision
        if risk_index <= ACCEPT_MAX:
            self.quote_store.update_status(quote_id, "quoted")
            price = self.tariff_engine.price(weight, distance, value)
            self.quote_store.update_status(quote_id, "quoted", price)
            self.notification_service.send(shipper_id, "quote_document",
                                           notif_outcome)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }
        elif risk_index <= REVIEW_MAX:
            self.quote_store.update_status(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }
        else:
            self.quote_store.update_status(quote_id, "refused_screening")
            self.notification_service.send(shipper_id, "refusal_notice",
                                           notif_outcome)
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }


def handle(request: dict) -> dict:
    api = QuoteApi(
        screening_service=ScreeningService(),
        tariff_engine=TariffEngine(),
        quote_store=QuoteStore(),
        notification_service=NotificationService(),
    )
    return api.request_quote(request)
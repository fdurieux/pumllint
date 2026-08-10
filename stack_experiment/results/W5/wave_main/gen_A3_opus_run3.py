ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, request):
        status = str(
            request.get("screening_status", request.get("screening_result", ""))
        ).lower()
        if status in ("error", "unavailable", "down", "outage", "timeout"):
            raise ScreeningUnavailableError("screening_unavailable")
        for key in ("risk_index", "screening_result", "screening_status"):
            if key in request:
                val = request[key]
                try:
                    return int(val)
                except (TypeError, ValueError):
                    continue
        return 0


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
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

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, request):
        status = str(
            request.get("store_status", request.get("store_result", ""))
        ).lower()
        if status in ("error", "unavailable", "down", "fail", "failed"):
            raise StoreUnavailableError("store_unavailable")
        self._seq += 1
        quote_id = "Q{:06d}".format(self._seq)
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
        return "updated"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _valid(self, request):
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False
        weight = request.get("weight_kg")
        if not self._is_number(weight) or not (3 <= weight <= 19400):
            return False
        distance = request.get("distance_km")
        if not self._is_number(distance) or not (25 <= distance <= 7150):
            return False
        value = request.get("declared_value")
        if not self._is_number(value) or not (50 <= value <= 83000):
            return False
        return True

    @staticmethod
    def _is_number(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def request_quote(self, request):
        # 1. Validate (DT-V)
        if not self._valid(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]

        # 2. Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value, request
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # 3. Screening
        try:
            risk_index = self.screening_service.screen(shipper_id, request)
        except ScreeningUnavailableError:
            # Screening outage: price anyway, hold, no notification.
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # 4/5/6. Apply screening decision
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self._notify_quote(shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount,
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, "refused_screening")
            self._notify_refusal(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}

    def _notify_quote(self, shipper_id, quote_id, price_amount):
        try:
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
        except Exception:
            pass

    def _notify_refusal(self, shipper_id, quote_id):
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            pass


def handle(request: dict) -> dict:
    api = QuoteApi(
        TariffEngine(),
        QuoteStore(),
        ScreeningService(),
        NotificationService(),
    )
    return api.request_quote(request)
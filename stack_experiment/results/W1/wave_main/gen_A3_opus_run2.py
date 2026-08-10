ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class ScreeningUnavailableError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, risk_index=None, status=None):
        if status in ("error", "unavailable", "down", "outage"):
            raise ScreeningUnavailableError("screening_unavailable")
        if risk_index is not None:
            return int(risk_index)
        # plausible default risk index
        return 10


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class TariffEngine:
    """Computes the freight price for a validated request per DT-P."""

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

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value,
                    status=None):
        if status in ("error", "unavailable", "down"):
            raise StoreUnavailableError("store_unavailable")
        self._counter += 1
        quote_id = "Q{:06d}".format(self._counter)
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
        }
        return quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        record = self._records.get(quote_id, {})
        record["status"] = status
        if price_amount is not None:
            record["price"] = price_amount
        self._records[quote_id] = record
        return "updated"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine=None, quote_store=None,
                 screening_service=None, notification_service=None):
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    def _valid(self, request):
        shipper_id = request.get("shipper_id")
        if not shipper_id or not isinstance(shipper_id, str):
            return False
        weight = request.get("weight_kg")
        if not isinstance(weight, (int, float)) or isinstance(weight, bool):
            return False
        if not (3 <= weight <= 19400):
            return False
        distance = request.get("distance_km")
        if not isinstance(distance, (int, float)) or isinstance(distance, bool):
            return False
        if not (25 <= distance <= 7150):
            return False
        value = request.get("declared_value")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False
        if not (50 <= value <= 83000):
            return False
        return True

    def request_quote(self, request):
        # Step 1: validate
        if not self._valid(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request.get("shipper_id")
        weight_kg = request.get("weight_kg")
        distance_km = request.get("distance_km")
        declared_value = request.get("declared_value")

        # Step 2: store draft
        store_status = request.get("quote_store_result",
                                   request.get("store_result",
                                               request.get("store_status")))
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value,
                status=store_status)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        screening_status = request.get("screening_status",
                                       request.get("screening_service_status"))
        risk_index = request.get("screening_result",
                                 request.get("screening_service_result",
                                             request.get("risk_index")))
        if isinstance(screening_status, str) and screening_status not in (
                "error", "unavailable", "down", "outage"):
            screening_status = None
        try:
            risk = self.screening_service.screen(
                shipper_id, risk_index=risk_index, status=screening_status)
        except ScreeningUnavailableError:
            # Screening outage: price anyway, hold, no notify
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened",
                                          price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4/5/6: apply screening decision
        if risk <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount,
            }
        elif REVIEW_MIN <= risk <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }
        else:  # risk >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }


def handle(request: dict) -> dict:
    api = QuoteApi()
    return api.request_quote(request)
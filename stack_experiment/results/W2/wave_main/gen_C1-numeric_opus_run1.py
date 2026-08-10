import numbers


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

    def __init__(self, request=None):
        self._request = request or {}

    def screen(self, shipper_id):
        status = str(self._request.get("screening_status", "")).lower()
        result = self._request.get("screening_result", None)
        if status in ("error", "unavailable", "down", "timeout"):
            raise ScreeningUnavailableError("screening_unavailable")
        if isinstance(result, str) and result.lower() in (
            "error",
            "unavailable",
            "down",
            "timeout",
        ):
            raise ScreeningUnavailableError("screening_unavailable")
        if isinstance(result, bool):
            result = None
        if isinstance(result, numbers.Number):
            return int(result)
        if isinstance(result, str):
            try:
                return int(float(result))
            except ValueError:
                pass
        # default: a clean, accept-band shipper
        return 12


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, request=None):
        self._request = request or {}

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        # fire-and-forget: never affects the response
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        # fire-and-forget: never affects the response
        return "sent"


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, request=None):
        self._request = request or {}
        self._records = {}
        self._counter = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        status = str(self._request.get("store_status", "")).lower()
        result = str(self._request.get("store_result", "")).lower()
        if status in ("error", "unavailable", "down") or result in (
            "error",
            "unavailable",
            "down",
        ):
            raise StoreUnavailableError("store_unavailable")
        self._counter += 1
        quote_id = "Q-{:06d}".format(self._counter)
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
        record = self._records.get(quote_id, {})
        record["status"] = status
        if price_amount is not None:
            record["price"] = price_amount
        self._records[quote_id] = record
        return "updated"


class TariffEngine:
    """Computes the freight price per DT-P."""

    def price(self, weight_kg, distance_km):
        total = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            total += 316.00
        if distance_km >= 4912:
            total *= 1.19
        return round(total, 2)


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and
    pricing, and returns the quotation outcome."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    @staticmethod
    def _is_number(value):
        return isinstance(value, numbers.Number) and not isinstance(value, bool)

    def _validate(self, request):
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

    def request_quote(self, request):
        # Step 1: validate
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]

        # Step 2: store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # screening outage: price anyway, hold, no notification
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4-7: apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount
            )
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
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    request = request or {}
    screening_service = ScreeningService(request)
    notification_service = NotificationService(request)
    quote_store = QuoteStore(request)
    tariff_engine = TariffEngine()
    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)
    return api.request_quote(request)
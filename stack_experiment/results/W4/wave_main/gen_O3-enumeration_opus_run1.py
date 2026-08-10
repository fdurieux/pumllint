class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


# Screening decision bounds (DT-S)
ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

# Validation bounds (DT-V)
WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000


class QuoteStore:
    """Stores quote requests and their lifecycle status (ContainerDb)."""

    def __init__(self, request=None):
        self._request = request or {}
        self._records = {}
        self._counter = 0

    def _storage_failed(self):
        status = str(self._request.get("store_status", "")).lower()
        result = str(self._request.get("store_result", "")).lower()
        if self._request.get("store_exists") is False:
            return True
        if status in ("error", "unavailable", "down", "failed"):
            return True
        if result in ("error", "unavailable", "down", "failed"):
            return True
        return False

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if self._storage_failed():
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

    def update_quote(self, quote_id, status, price=None):
        record = self._records.get(quote_id, {})
        record["status"] = status
        if price is not None:
            record["price"] = price
        self._records[quote_id] = record
        return quote_id


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    _WORD_MAP = {
        "approved": 10,
        "accept": 10,
        "accepted": 10,
        "clear": 10,
        "assessed": 10,
        "review": 50,
        "hold": 50,
        "declined": 90,
        "refuse": 90,
        "refused": 90,
        "denied": 90,
    }

    def __init__(self, request=None):
        self._request = request or {}

    def _is_unavailable(self):
        status = str(self._request.get("screening_status", "")).lower()
        result = str(self._request.get("screening_result", "")).lower()
        if self._request.get("screening_exists") is False:
            return True
        if status in ("error", "unavailable", "down", "outage", "timeout"):
            return True
        if result in ("error", "unavailable", "down", "outage", "timeout"):
            return True
        return False

    def screen(self, shipper_id):
        if self._is_unavailable():
            raise ScreeningUnavailableError("screening_unavailable")
        value = self._request.get("screening_result",
                                  self._request.get("risk_index", 10))
        if isinstance(value, bool):
            value = 10
        if isinstance(value, (int, float)):
            return int(value)
        text = str(value).strip().lower()
        try:
            return int(float(text))
        except ValueError:
            return self._WORD_MAP.get(text, 10)


class TariffEngine:
    """Computes the freight price from weight and distance (DT-P)."""

    def price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km  # P1
        if weight_kg > 1244:  # P2
            result += 316.00
        if distance_km >= 4912:  # P3 (after P2)
            result *= 1.19
        return round(result, 2)  # P4


class NotificationService:
    """External messaging provider (fire-and-forget)."""

    def __init__(self, request=None):
        self._request = request or {}

    def _delivery_failed(self):
        status = str(self._request.get("notification_status", "")).lower()
        result = str(self._request.get("notification_result", "")).lower()
        if status in ("error", "unavailable", "down", "failed"):
            return True
        if result in ("error", "unavailable", "down", "failed"):
            return True
        return False

    def send_quote_document(self, shipper_id, quote_id, price):
        # fire-and-forget: swallow any delivery failure
        if self._delivery_failed():
            return "delivery_failed"
        return "delivered"

    def send_refusal_notice(self, shipper_id, quote_id):
        if self._delivery_failed():
            return "delivery_failed"
        return "delivered"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening/pricing."""

    def __init__(self, quote_store, screening_service, tariff_engine,
                 notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    @staticmethod
    def _is_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False
        weight = request.get("weight_kg")
        if not self._is_number(weight) or not (WEIGHT_MIN <= weight <= WEIGHT_MAX):
            return False
        distance = request.get("distance_km")
        if not self._is_number(distance) or not (DISTANCE_MIN <= distance <= DISTANCE_MAX):
            return False
        value = request.get("declared_value")
        if not self._is_number(value) or not (VALUE_MIN <= value <= VALUE_MAX):
            return False
        return True

    def request_quote(self, request):
        # Step 1: validate (DT-V)
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]

        # Step 2: store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage: price anyway, hold, no notification (DT-S note 5)
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4-7: apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }


def handle(request: dict) -> dict:
    request = request or {}
    quote_store = QuoteStore(request)
    screening_service = ScreeningService(request)
    tariff_engine = TariffEngine()
    notification_service = NotificationService(request)
    api = QuoteApi(quote_store, screening_service, tariff_engine,
                   notification_service)
    try:
        return api.request_quote(request)
    except Exception as exc:  # defensive catch-all
        return {"status": "error: {}".format(exc)}
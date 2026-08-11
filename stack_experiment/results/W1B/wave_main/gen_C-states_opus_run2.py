class InvalidRequestError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


# Symbolic bounds (DT-S)
ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

# Validation bounds (DT-V)
WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, config=None):
        self._config = config or {}

    def screen(self, shipper_id):
        status = str(self._config.get("screening_status", "")).lower()
        result = self._config.get("screening_result",
                                  self._config.get("risk_index"))
        if status in ("error", "unavailable", "down", "outage"):
            raise ScreeningUnavailableError("screening_unavailable")
        if isinstance(result, str) and result.lower() in (
                "error", "unavailable", "down", "outage"):
            raise ScreeningUnavailableError("screening_unavailable")
        if result is None:
            return 0
        return int(result)


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

    def __init__(self, config=None):
        self._config = config or {}
        self._records = {}
        self._counter = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        status = str(self._config.get("store_status",
                     self._config.get("store_result", ""))).lower()
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

    def update_quote(self, quote_id, status, price=None):
        rec = self._records.get(quote_id, {})
        rec["status"] = status
        if price is not None:
            rec["price"] = price
        self._records[quote_id] = rec
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, config=None):
        self._config = config or {}

    def send_quote_document(self, shipper_id, quote_id, price):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, quote_store, screening_service, tariff_engine,
                 notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or not shipper_id.strip():
            raise InvalidRequestError("V1")
        for name, val, lo, hi in (
                ("weight_kg", weight_kg, WEIGHT_MIN, WEIGHT_MAX),
                ("distance_km", distance_km, DISTANCE_MIN, DISTANCE_MAX),
                ("declared_value", declared_value, VALUE_MIN, VALUE_MAX)):
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise InvalidRequestError(name)
            if val < lo or val > hi:
                raise InvalidRequestError(name)

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Step 1: validate
        self._validate(shipper_id, weight_kg, distance_km, declared_value)

        # Step 2: store draft
        quote_id = self.quote_store.store_draft(
            shipper_id, weight_kg, distance_km, declared_value)

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4-7: apply screening decision
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self._notify_quote(shipper_id, quote_id, price)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:
            self.quote_store.update_quote(quote_id, "refused_screening")
            self._notify_refusal(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}

    def _notify_quote(self, shipper_id, quote_id, price):
        try:
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price)
        except Exception:
            pass  # fire-and-forget

    def _notify_refusal(self, shipper_id, quote_id):
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            pass  # fire-and-forget


def handle(request: dict) -> dict:
    request = request or {}

    store = QuoteStore(request)
    screening = ScreeningService(request)
    tariff = TariffEngine()
    notification = NotificationService(request)
    api = QuoteApi(store, screening, tariff, notification)

    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    try:
        return api.request_quote(
            shipper_id, weight_kg, distance_km, declared_value)
    except InvalidRequestError:
        return {"status": "rejected: invalid_request"}
    except StoreUnavailableError:
        return {"status": "error: store_unavailable"}
    except Exception as exc:
        return {"status": "error: " + str(exc)}
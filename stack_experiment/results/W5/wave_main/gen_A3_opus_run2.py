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

    def __init__(self, config=None):
        self._config = config or {}

    def screen(self, shipper_id):
        result = self._config.get("screening_result",
                                  self._config.get("screening_status"))
        if result is None and "risk_index" in self._config:
            result = self._config["risk_index"]
        if isinstance(result, str):
            token = result.strip().lower()
            if token in ("error", "unavailable", "outage", "down", "timeout"):
                raise ScreeningUnavailableError("screening_unavailable")
            if token in ("approved", "accept", "accepted", "clear"):
                return 10
            if token in ("review", "hold", "assessed"):
                return 50
            if token in ("declined", "refuse", "refused", "denied"):
                return 90
            try:
                return int(float(token))
            except ValueError:
                return 10
        if isinstance(result, (int, float)):
            return int(result)
        return 10


class TariffEngine:
    """Computes the freight price from weight and distance per DT-P."""

    def price(self, weight_kg, distance_km):
        base = 0.87 * weight_kg + 1.13 * distance_km
        total = base
        if weight_kg > 1244:
            total += 316.00
        if distance_km >= 4912:
            total *= 1.19
        return round(total, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, config=None):
        self._config = config or {}
        self._counter = 0
        self._records = {}

    def _unavailable(self):
        result = self._config.get("quote_store_result",
                                  self._config.get("quote_store_status"))
        if isinstance(result, str):
            return result.strip().lower() in (
                "error", "unavailable", "down", "outage", "fail", "failure")
        return False

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if self._unavailable():
            raise StoreUnavailableError("store_unavailable")
        self._counter += 1
        quote_id = "Q-%04d" % self._counter
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
        }
        return quote_id

    def update_quote(self, quote_id, status, price=None):
        record = self._records.get(quote_id, {})
        record["status"] = status
        if price is not None:
            record["price"] = price
        self._records[quote_id] = record
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, config=None):
        self._config = config or {}

    def _delivers(self):
        result = self._config.get("notification_result",
                                  self._config.get("notification_status"))
        if isinstance(result, str):
            return result.strip().lower() not in (
                "error", "unavailable", "fail", "failure", "down")
        return True

    def send_quote_document(self, shipper_id, quote_id, price):
        # fire-and-forget: never affects the response
        return self._delivers()

    def send_refusal_notice(self, shipper_id, quote_id):
        # fire-and-forget: never affects the response
        return self._delivers()


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service,
                 notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False
        weight_kg = request.get("weight_kg")
        if not isinstance(weight_kg, (int, float)) or isinstance(weight_kg, bool):
            return False
        if not (3 <= weight_kg <= 19400):
            return False
        distance_km = request.get("distance_km")
        if not isinstance(distance_km, (int, float)) or isinstance(distance_km, bool):
            return False
        if not (25 <= distance_km <= 7150):
            return False
        declared_value = request.get("declared_value")
        if not isinstance(declared_value, (int, float)) or isinstance(declared_value, bool):
            return False
        if not (50 <= declared_value <= 83000):
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
            # Screening outage: price anyway, hold, no notification.
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4/5/6: apply screening decision (DT-S)
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
    config = dict(request) if isinstance(request, dict) else {}
    tariff_engine = TariffEngine()
    quote_store = QuoteStore(config)
    screening_service = ScreeningService(config)
    notification_service = NotificationService(config)
    api = QuoteApi(tariff_engine, quote_store, screening_service,
                   notification_service)
    return api.request_quote(request)
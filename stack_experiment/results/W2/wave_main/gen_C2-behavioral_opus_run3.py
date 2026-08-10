ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

HEAVY_THRESHOLD = 1244
HEAVY_SURCHARGE = 316.00
LONGHAUL_THRESHOLD = 4912
LONGHAUL_MULTIPLIER = 1.19


class ValidationError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, request=None):
        self._request = request or {}

    def screen(self, shipper_id):
        raw = None
        for key in ("screening_result", "screening_status", "risk_index",
                    "riskIndex", "screening"):
            if key in self._request and self._request[key] is not None:
                raw = self._request[key]
                break
        if raw is None:
            return 0
        if isinstance(raw, bool):
            raise ScreeningUnavailableError("screening_unavailable")
        if isinstance(raw, (int, float)):
            return int(raw)
        text = str(raw).strip().lower()
        if text in ("error", "unavailable", "down", "outage", "timeout"):
            raise ScreeningUnavailableError("screening_unavailable")
        if text in ("approved", "accept", "clear", "pass"):
            return 0
        if text in ("review", "manual"):
            return REVIEW_MIN
        if text in ("declined", "refuse", "refused", "denied", "reject"):
            return REFUSE_MIN
        try:
            return int(float(text))
        except ValueError:
            return 0


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, request=None):
        self._request = request or {}

    def _fails(self):
        for key in ("notification_result", "notification_status", "notify_status"):
            if key in self._request:
                text = str(self._request[key]).strip().lower()
                if text in ("error", "fail", "failed", "unavailable", "down"):
                    return True
        return False

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        # Fire-and-forget: delivery failure never changes the response.
        if self._fails():
            return "delivery_failed"
        return "delivered"

    def send_refusal_notice(self, shipper_id, quote_id):
        if self._fails():
            return "delivery_failed"
        return "delivered"


class TariffEngine:
    """Computes the freight price for a validated request per DT-P."""

    def price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > HEAVY_THRESHOLD:
            result += HEAVY_SURCHARGE
        if distance_km >= LONGHAUL_THRESHOLD:
            result *= LONGHAUL_MULTIPLIER
        return round(result, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, request=None):
        self._request = request or {}
        self._seq = 0
        self._records = {}

    def _store_fails(self):
        for key in ("quote_store_result", "quote_store_status", "store_result",
                    "store_status"):
            if key in self._request:
                text = str(self._request[key]).strip().lower()
                if text in ("error", "unavailable", "down", "fail", "failed"):
                    return True
        return False

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if self._store_fails():
            raise StoreUnavailableError("store_unavailable")
        self._seq += 1
        quote_id = "Q-{:06d}".format(self._seq)
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
        return quote_id


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and
    pricing, and returns the quotation outcome."""

    def __init__(self, tariff_engine, quote_store, screening_service,
                 notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    @staticmethod
    def _is_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            raise ValidationError("shipper_id")
        if not self._is_number(weight_kg) or not (3 <= weight_kg <= 19400):
            raise ValidationError("weight_kg")
        if not self._is_number(distance_km) or not (25 <= distance_km <= 7150):
            raise ValidationError("distance_km")
        if not self._is_number(declared_value) or not (50 <= declared_value <= 83000):
            raise ValidationError("declared_value")

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Step 1: validate
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError:
            return {"status": "rejected: invalid_request"}

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
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4-6: apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount,
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

    tariff_engine = TariffEngine()
    quote_store = QuoteStore(request)
    screening_service = ScreeningService(request)
    notification_service = NotificationService(request)

    api = QuoteApi(tariff_engine, quote_store, screening_service,
                   notification_service)

    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
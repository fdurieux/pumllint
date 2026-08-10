ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 69
REFUSE_MIN = 70

WEIGHT_MIN = 1
WEIGHT_MAX = 24000
DISTANCE_MIN = 1
DISTANCE_MAX = 3000
VALUE_MIN = 1
VALUE_MAX = 10_000_000


class ScreeningUnavailableError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, request=None):
        request = request or {}
        status = request.get("screening_result", request.get("screening_status"))
        if status in ("error", "unavailable", "down"):
            raise ScreeningUnavailableError("screening service unavailable")
        try:
            return float(status)
        except (TypeError, ValueError):
            pass
        mapping = {
            "approved": 10.0,
            "clear": 10.0,
            "active": 10.0,
            "declined": 90.0,
            "denied": 90.0,
            "refused": 90.0,
            "review": 50.0,
            "hold": 50.0,
        }
        return mapping.get(status, 10.0)


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff rules."""

    BASE_FEE = 20.0
    PER_KG = 0.10
    PER_KG_KM = 0.0005

    def price(self, weight_kg, distance_km):
        return round(
            self.BASE_FEE
            + weight_kg * self.PER_KG
            + weight_kg * distance_km * self.PER_KG_KM,
            2,
        )


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, request=None):
        request = request or {}
        status = request.get("store_result", request.get("store_status"))
        if status in ("error", "unavailable", "down"):
            raise StoreUnavailableError("quote store unavailable")
        self._seq += 1
        return "Q-{}-{}".format(shipper_id, self._seq)

    def update_quote(self, quote_id, status, price_amount=None):
        return {"quote_id": quote_id, "status": status, "price": price_amount}


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening/pricing, returns outcome."""

    def __init__(self, tariff_engine=None, quote_store=None,
                 screening_service=None, notification_service=None):
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value, request):
        if request.get("shipper_exists") is False or request.get("shipper_found") is False:
            return "unknown shipper"
        if not shipper_id:
            return "missing shipper"
        try:
            w = float(weight_kg)
            d = float(distance_km)
            v = float(declared_value)
        except (TypeError, ValueError):
            return "non-numeric input"
        if not (WEIGHT_MIN <= w <= WEIGHT_MAX):
            return "weight out of bounds"
        if not (DISTANCE_MIN <= d <= DISTANCE_MAX):
            return "distance out of bounds"
        if not (VALUE_MIN <= v <= VALUE_MAX):
            return "declared value out of bounds"
        return None

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value, request=None):
        request = request or {}

        # Validation (DT-V)
        error = self._validate(shipper_id, weight_kg, distance_km, declared_value, request)
        if error is not None:
            return {"status": "rejected: invalid request", "reason": error}

        # Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value, request
            )
        except StoreUnavailableError:
            return {"status": "error: store unavailable"}

        # Screening (DT-S)
        try:
            risk_index = self.screening_service.screen(shipper_id, request)
        except ScreeningUnavailableError:
            # DT-S note 5: outage does not fail the quote; price + hold, no notify
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
            }

        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {
                "status": "confirmed",
                "quote_id": quote_id,
                "price": price_amount,
                "risk_index": risk_index,
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # DT-S note 1: no pricing, no notification
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }
        else:  # risk_index >= REFUSE_MIN
            # DT-S note 2: refusal is notified; pricing never runs
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "rejected",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }


class Shipper:
    """A logistics customer requesting a price quote for palletized road cargo."""

    def __init__(self, quote_api=None):
        self.quote_api = quote_api or QuoteApi()

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value, request=None):
        return self.quote_api.request_quote(
            shipper_id, weight_kg, distance_km, declared_value, request
        )


def handle(request: dict) -> dict:
    request = request or {}
    shipper_id = request.get("shipper_id", request.get("shipperId", "S1"))
    weight_kg = request.get("weightKg", request.get("weight_kg", request.get("weight", 0)))
    distance_km = request.get("distanceKm", request.get("distance_km", request.get("distance", 0)))
    declared_value = request.get(
        "declaredValue", request.get("declared_value", request.get("value", 0))
    )

    shipper = Shipper()
    try:
        return shipper.request_quote(
            shipper_id, weight_kg, distance_km, declared_value, request
        )
    except Exception as exc:  # pragma: no cover
        return {"status": "error: {}".format(exc)}
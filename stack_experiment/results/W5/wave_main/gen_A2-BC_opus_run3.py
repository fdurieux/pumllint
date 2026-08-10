import uuid


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen_shipper(self, shipper_id, override=None):
        if override is not None:
            if isinstance(override, (int, float)):
                return float(override)
            mapping = {
                "approved": 10.0,
                "clear": 5.0,
                "review": 55.0,
                "hold": 55.0,
                "declined": 95.0,
                "denied": 95.0,
                "error": -1.0,
            }
            return mapping.get(str(override).lower(), 10.0)
        return 10.0


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send(self, shipper_id, document_type, payload):
        return "sent"


class TariffEngine:
    """Computes the freight price for a validated request from weight and
    distance per the published tariff rules."""

    BASE_FEE = 25.0
    PER_KG = 0.35
    PER_KM = 0.12

    def compute_price(self, weight_kg, distance_km):
        price = (
            self.BASE_FEE
            + self.PER_KG * float(weight_kg)
            + self.PER_KM * float(distance_km)
        )
        return round(price, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}

    def save_quote(self, record):
        quote_id = record.get("quote_id") or str(uuid.uuid4())
        self._records[quote_id] = dict(record)
        self._records[quote_id]["quote_id"] = quote_id
        return quote_id

    def update_status(self, quote_id, status):
        if quote_id not in self._records:
            return "missing"
        self._records[quote_id]["status"] = status
        return "updated"


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and
    pricing, and returns the quotation outcome."""

    LOW_RISK_MAX = 30.0
    HIGH_RISK_MIN = 70.0

    def __init__(self, screening=None, tariff=None, store=None, notifier=None):
        self.screening = screening or ScreeningService()
        self.tariff = tariff or TariffEngine()
        self.store = store or QuoteStore()
        self.notifier = notifier or NotificationService()

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not shipper_id:
            return "missing_shipper"
        if request.get("shipper_exists") is False or request.get("shipper_found") is False:
            return "unknown_shipper"
        try:
            weight = float(request.get("weight_kg", 0))
            distance = float(request.get("distance_km", 0))
            value = float(request.get("declared_value", 0))
        except (TypeError, ValueError):
            return "invalid_numbers"
        if weight <= 0:
            return "invalid_weight"
        if distance <= 0:
            return "invalid_distance"
        if value < 0:
            return "invalid_value"
        return None

    def request_quote(self, request):
        error = self._validate(request)
        if error:
            return {"status": "error: " + error}

        shipper_id = request.get("shipper_id")
        weight = float(request.get("weight_kg", 0))
        distance = float(request.get("distance_km", 0))
        value = float(request.get("declared_value", 0))

        quote_id = self.store.save_quote(
            {
                "shipper_id": shipper_id,
                "weight_kg": weight,
                "distance_km": distance,
                "declared_value": value,
                "status": "received",
            }
        )

        screening_override = request.get("screening_result", request.get("screening_status"))
        risk_index = self.screening.screen_shipper(shipper_id, screening_override)

        if risk_index is None or risk_index < 0:
            self.store.update_status(quote_id, "screening_error")
            return {"status": "error: screening_failed", "quote_id": quote_id}

        if risk_index >= self.HIGH_RISK_MIN:
            self.store.update_status(quote_id, "refused")
            self.notifier.send(shipper_id, "refusal_notice", {"quote_id": quote_id})
            return {
                "status": "rejected",
                "quote_id": quote_id,
            }

        price = self.tariff.compute_price(weight, distance)

        if risk_index > self.LOW_RISK_MAX:
            self.store.update_status(quote_id, "held_for_review")
            return {
                "status": "held",
                "quote_id": quote_id,
                "price": price,
            }

        self.store.update_status(quote_id, "issued")
        self.notifier.send(
            shipper_id, "quote_document", {"quote_id": quote_id, "price": price}
        )
        return {
            "status": "confirmed",
            "quote_id": quote_id,
            "price": price,
        }


class Shipper:
    """A logistics customer requesting a price quote."""

    def __init__(self, api=None):
        self.api = api or QuoteApi()

    def request_freight_quote(self, request):
        return self.api.request_quote(request)


def handle(request: dict) -> dict:
    api = QuoteApi()
    shipper = Shipper(api)
    try:
        return shipper.request_freight_quote(request)
    except Exception as exc:
        return {"status": "error: " + str(exc)}
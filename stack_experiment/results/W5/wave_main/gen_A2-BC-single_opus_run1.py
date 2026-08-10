class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, request):
        result = request.get("screening_result") or request.get("screening_status")
        if result == "error":
            raise RuntimeError("screening provider unavailable")
        score = request.get("screening_score")
        if score is not None:
            return float(score)
        if result == "declined":
            return 90.0
        if result == "review":
            return 50.0
        if result in ("approved", "assessed", None, ""):
            return 10.0
        return 10.0


class TariffEngine:
    """Computes the freight price from weight and distance per tariff rules."""

    BASE_FEE = 25.0
    RATE_PER_KG_KM = 0.0002
    VALUE_SURCHARGE_RATE = 0.01

    def price(self, request):
        result = request.get("tariff_result") or request.get("tariff_status")
        if result == "error":
            raise RuntimeError("tariff engine unavailable")
        weight = float(request.get("weight_kg", 0) or 0)
        distance = float(request.get("distance_km", 0) or 0)
        value = float(request.get("declared_value", 0) or 0)
        if weight <= 0 or distance <= 0:
            raise ValueError("invalid consignment dimensions")
        amount = (
            self.BASE_FEE
            + weight * distance * self.RATE_PER_KG_KM
            + value * self.VALUE_SURCHARGE_RATE
        )
        return round(amount, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}

    def store(self, quote_id, record):
        result = record.get("quote_store_result") or record.get("quote_store_status")
        if result == "error":
            raise RuntimeError("quote store unavailable")
        self._records[quote_id] = dict(record)
        return quote_id

    def update_status(self, quote_id, status):
        if quote_id in self._records:
            self._records[quote_id]["status"] = status
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send(self, shipper_id, document_type, payload):
        if payload.get("notification_result") == "error":
            raise RuntimeError("notification provider unavailable")
        return "delivered"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    LOW_RISK_THRESHOLD = 30.0
    HIGH_RISK_THRESHOLD = 70.0

    def __init__(self, screening_service=None, tariff_engine=None,
                 quote_store=None, notification_service=None):
        self.screening_service = screening_service or ScreeningService()
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.notification_service = notification_service or NotificationService()
        self._counter = 0

    def _next_id(self):
        self._counter += 1
        return "Q%05d" % self._counter

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not shipper_id:
            raise ValueError("missing shipper")
        if not request.get("shipper_exists", True) or not request.get("shipper_found", True):
            raise ValueError("unknown shipper")
        weight = request.get("weight_kg")
        distance = request.get("distance_km")
        if weight is None or float(weight) <= 0:
            raise ValueError("invalid weight")
        if distance is None or float(distance) <= 0:
            raise ValueError("invalid distance")
        value = request.get("declared_value", 0)
        if value is not None and float(value) < 0:
            raise ValueError("invalid declared value")

    def request_quote(self, request):
        # 1. Validate
        self._validate(request)

        shipper_id = request.get("shipper_id")
        quote_id = self._next_id()

        # 2. Record the request
        record = dict(request)
        record["status"] = "recorded"
        self.quote_store.store(quote_id, record)

        # 3. Screen the shipper
        risk_index = self.screening_service.screen(shipper_id, request)

        # 4. Decide by risk
        if risk_index >= self.HIGH_RISK_THRESHOLD:
            self.quote_store.update_status(quote_id, "refused")
            self.notification_service.send(shipper_id, "refusal_notice", request)
            return {
                "status": "rejected",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }

        if risk_index >= self.LOW_RISK_THRESHOLD:
            self.quote_store.update_status(quote_id, "held_for_review")
            return {
                "status": "held",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }

        # 5. Price and issue
        price = self.tariff_engine.price(request)
        self.quote_store.update_status(quote_id, "quoted")
        self.notification_service.send(shipper_id, "quote_document", request)
        return {
            "status": "confirmed",
            "quote_id": quote_id,
            "price": price,
            "risk_index": risk_index,
        }


def handle(request: dict) -> dict:
    api = QuoteApi()
    try:
        return api.request_quote(request)
    except ValueError as exc:
        return {"status": "error: %s" % exc}
    except RuntimeError as exc:
        return {"status": "error: %s" % exc}
    except Exception as exc:  # pragma: no cover
        return {"status": "error: %s" % exc}
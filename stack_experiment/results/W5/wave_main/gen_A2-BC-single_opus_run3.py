class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, declared_value, result_hint=None):
        if result_hint is not None:
            if isinstance(result_hint, (int, float)):
                return float(result_hint)
            hint = str(result_hint).lower()
            if hint in ("approved", "clear", "low"):
                return 10.0
            if hint in ("review", "hold", "assessed", "medium"):
                return 55.0
            if hint in ("declined", "denied", "refused", "high"):
                return 95.0
            if hint in ("error", "unavailable"):
                raise RuntimeError("screening service error")
        return 10.0


class TariffEngine:
    """Computes the freight price from weight and distance per tariff rules."""

    BASE_FEE = 25.0
    RATE_PER_KG_KM = 0.0005

    def price(self, weight_kg, distance_km, declared_value):
        if weight_kg <= 0 or distance_km <= 0:
            raise ValueError("invalid consignment dimensions")
        freight = self.BASE_FEE + (weight_kg * distance_km * self.RATE_PER_KG_KM)
        insurance = declared_value * 0.01
        return round(freight + insurance, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._seq = 0

    def save(self, quote_record):
        self._seq += 1
        quote_id = quote_record.get("quote_id") or f"Q{self._seq:06d}"
        record = dict(quote_record)
        record["quote_id"] = quote_id
        self._records[quote_id] = record
        return quote_id

    def update_status(self, quote_id, status):
        if quote_id not in self._records:
            raise KeyError("quote not found")
        self._records[quote_id]["status"] = status
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send(self, shipper_id, document_type, payload):
        return "sent"


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and
    pricing, and returns the quotation outcome."""

    LOW_RISK_THRESHOLD = 40.0
    HIGH_RISK_THRESHOLD = 80.0

    def __init__(self, quote_store=None, screening_service=None,
                 tariff_engine=None, notification_service=None):
        self.quote_store = quote_store or QuoteStore()
        self.screening_service = screening_service or ScreeningService()
        self.tariff_engine = tariff_engine or TariffEngine()
        self.notification_service = notification_service or NotificationService()

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not shipper_id:
            raise ValueError("missing shipper_id")
        if request.get("shipper_exists") is False or request.get("shipper_found") is False:
            raise ValueError("unknown shipper")
        try:
            weight = float(request.get("weight_kg", 0))
            distance = float(request.get("distance_km", 0))
            declared_value = float(request.get("declared_value", 0))
        except (TypeError, ValueError):
            raise ValueError("invalid numeric fields")
        if weight <= 0:
            raise ValueError("invalid weight")
        if distance <= 0:
            raise ValueError("invalid distance")
        if declared_value < 0:
            raise ValueError("invalid declared_value")
        return shipper_id, weight, distance, declared_value

    def request_quote(self, request):
        shipper_id, weight, distance, declared_value = self._validate(request)

        quote_id = self.quote_store.save({
            "shipper_id": shipper_id,
            "weight_kg": weight,
            "distance_km": distance,
            "declared_value": declared_value,
            "status": "received",
        })

        screening_hint = request.get("screening_result",
                                     request.get("screening_status"))
        try:
            risk_index = self.screening_service.screen(
                shipper_id, declared_value, screening_hint)
        except Exception as exc:
            self.quote_store.update_status(quote_id, "screening_error")
            return {"status": "error: screening_unavailable",
                    "quote_id": quote_id, "detail": str(exc)}

        if risk_index >= self.HIGH_RISK_THRESHOLD:
            self.quote_store.update_status(quote_id, "refused")
            self.notification_service.send(shipper_id, "refusal_notice",
                                           {"quote_id": quote_id,
                                            "risk_index": risk_index})
            return {"status": "rejected", "quote_id": quote_id,
                    "risk_index": risk_index}

        if risk_index >= self.LOW_RISK_THRESHOLD:
            self.quote_store.update_status(quote_id, "held_for_review")
            return {"status": "held", "quote_id": quote_id,
                    "risk_index": risk_index}

        try:
            price = self.tariff_engine.price(weight, distance, declared_value)
        except Exception as exc:
            self.quote_store.update_status(quote_id, "pricing_error")
            return {"status": "error: pricing_failed",
                    "quote_id": quote_id, "detail": str(exc)}

        self.quote_store.update_status(quote_id, "issued")
        self.notification_service.send(shipper_id, "quote_document",
                                       {"quote_id": quote_id, "price": price})
        return {"status": "confirmed", "quote_id": quote_id,
                "price": price, "risk_index": risk_index}


def handle(request: dict) -> dict:
    api = QuoteApi()
    try:
        return api.request_quote(request)
    except ValueError as exc:
        return {"status": f"error: {exc}"}
    except Exception as exc:
        return {"status": f"error: {exc}"}
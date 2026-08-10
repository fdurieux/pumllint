class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, declared_value, override=None):
        if override is not None:
            if isinstance(override, (int, float)):
                return float(override)
            word = str(override).lower()
            mapping = {
                "approved": 10.0,
                "clear": 10.0,
                "assessed": 50.0,
                "review": 50.0,
                "declined": 90.0,
                "denied": 90.0,
                "error": -1.0,
            }
            if word == "error":
                raise RuntimeError("screening provider error")
            return mapping.get(word, 10.0)
        # Plausible default risk index.
        return 10.0


class TariffEngine:
    """Computes the freight price from weight and distance per tariff rules."""

    BASE_FEE = 25.0
    RATE_PER_KG_KM = 0.0005

    def price(self, weight, distance, declared_value, override=None):
        if override is not None:
            if isinstance(override, (int, float)):
                return float(override)
            if str(override).lower() == "error":
                raise RuntimeError("tariff engine error")
        freight = self.BASE_FEE + (weight * distance * self.RATE_PER_KG_KM)
        insurance = declared_value * 0.01
        return round(freight + insurance, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status (PostgreSQL)."""

    def __init__(self):
        self._records = {}
        self._seq = 0

    def save(self, record, override=None):
        if override is not None and str(override).lower() == "error":
            raise RuntimeError("quote store error")
        self._seq += 1
        quote_id = "Q%05d" % self._seq
        stored = dict(record)
        stored["quote_id"] = quote_id
        self._records[quote_id] = stored
        return quote_id

    def update_status(self, quote_id, status):
        if quote_id in self._records:
            self._records[quote_id]["status"] = status
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send(self, shipper_id, document_type, payload, override=None):
        if override is not None and str(override).lower() == "error":
            raise RuntimeError("notification provider error")
        return "sent"


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and
    pricing, and returns the quotation outcome."""

    LOW_RISK_THRESHOLD = 30.0
    HIGH_RISK_THRESHOLD = 70.0

    def __init__(self, quote_store=None, screening_service=None,
                 tariff_engine=None, notification_service=None):
        self.quote_store = quote_store or QuoteStore()
        self.screening_service = screening_service or ScreeningService()
        self.tariff_engine = tariff_engine or TariffEngine()
        self.notification_service = notification_service or NotificationService()

    def _validate(self, request):
        if not request.get("shipper_exists", request.get("shipper_found", True)):
            raise ValueError("unknown shipper")
        if not request.get("shipper_id"):
            raise ValueError("missing shipper id")
        weight = request.get("weight")
        distance = request.get("distance")
        declared_value = request.get("declared_value")
        for name, value in (("weight", weight), ("distance", distance),
                            ("declared_value", declared_value)):
            if value is None:
                raise ValueError("missing %s" % name)
            if not isinstance(value, (int, float)) or value < 0:
                raise ValueError("invalid %s" % name)
        if weight <= 0:
            raise ValueError("invalid weight")
        if distance <= 0:
            raise ValueError("invalid distance")

    def request_quote(self, request):
        # 1. Validate the request.
        self._validate(request)

        shipper_id = request.get("shipper_id")
        weight = request.get("weight")
        distance = request.get("distance")
        declared_value = request.get("declared_value", 0.0)

        # 2. Record the quote request.
        quote_id = self.quote_store.save(
            {
                "shipper_id": shipper_id,
                "weight": weight,
                "distance": distance,
                "declared_value": declared_value,
                "status": "received",
            },
            override=request.get("store_result", request.get("store_status")),
        )

        # 3. Screen the shipper.
        risk_index = self.screening_service.screen(
            shipper_id,
            declared_value,
            override=request.get("screening_result",
                                 request.get("screening_status")),
        )

        # 4. Branch on screening outcome.
        if risk_index >= self.HIGH_RISK_THRESHOLD:
            self.quote_store.update_status(quote_id, "refused")
            self.notification_service.send(
                shipper_id, "refusal_notice",
                {"quote_id": quote_id, "reason": "screening"},
                override=request.get("notification_result",
                                     request.get("notification_status")),
            )
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

        # 5. Price the consignment.
        price = self.tariff_engine.price(
            weight, distance, declared_value,
            override=request.get("tariff_result", request.get("tariff_status")),
        )

        # 6. Issue the quote and notify the shipper.
        self.quote_store.update_status(quote_id, "issued")
        self.notification_service.send(
            shipper_id, "quote_document",
            {"quote_id": quote_id, "price": price},
            override=request.get("notification_result",
                                 request.get("notification_status")),
        )

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
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "error: %s" % exc}
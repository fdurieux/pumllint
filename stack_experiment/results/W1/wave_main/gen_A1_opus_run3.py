def _to_camel(alias):
    return "".join(p.capitalize() for p in alias.split("_"))


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def request_risk_index(self, shipper_id, request):
        result = request.get("screening_result", request.get("screening_status"))
        if result is None:
            return 10.0
        if isinstance(result, (int, float)):
            return float(result)
        word = str(result).strip().lower()
        mapping = {
            "approved": 10.0,
            "clear": 10.0,
            "active": 10.0,
            "assessed": 50.0,
            "review": 50.0,
            "declined": 90.0,
            "denied": 90.0,
            "blocked": 90.0,
        }
        if word == "error":
            raise RuntimeError("screening_provider_error")
        try:
            return float(word)
        except ValueError:
            return mapping.get(word, 10.0)


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff rules."""

    BASE_FEE = 25.0
    WEIGHT_RATE = 0.5
    DISTANCE_RATE = 0.1
    VALUE_RATE = 0.01

    def compute_price(self, weight, distance, declared_value):
        price = (
            self.BASE_FEE
            + weight * self.WEIGHT_RATE
            + distance * self.DISTANCE_RATE
            + declared_value * self.VALUE_RATE
        )
        return round(price, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._seq = 0

    def save_request(self, record):
        self._seq += 1
        quote_id = "Q{:06d}".format(self._seq)
        stored = dict(record)
        stored["quote_id"] = quote_id
        self._records[quote_id] = stored
        return quote_id

    def update_status(self, quote_id, status, extra=None):
        record = self._records.get(quote_id)
        if record is None:
            raise KeyError("quote_not_found")
        record["status"] = status
        if extra:
            record.update(extra)
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send(self, recipient, document):
        return "delivered"


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    LOW_RISK_MAX = 30.0
    HIGH_RISK_MIN = 70.0

    def __init__(self, screening_service, tariff_engine, quote_store,
                 notification_service):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service

    def _validate(self, request):
        if not request.get("shipper_id"):
            raise ValueError("missing_shipper_id")
        if request.get("shipper_exists") is False or \
                request.get("shipper_found") is False:
            raise ValueError("unknown_shipper")
        for field in ("weight", "distance", "declared_value"):
            value = request.get(field)
            if value is None:
                raise ValueError("missing_" + field)
            if not isinstance(value, (int, float)):
                raise ValueError("invalid_" + field)
            if value < 0:
                raise ValueError("invalid_" + field)

    def request_quote(self, request):
        # 1. Validate
        try:
            self._validate(request)
        except ValueError as exc:
            return {"status": "error: " + str(exc)}

        shipper_id = request["shipper_id"]

        # 2. Record the request
        quote_id = self.quote_store.save_request({
            "shipper_id": shipper_id,
            "weight": request["weight"],
            "distance": request["distance"],
            "declared_value": request["declared_value"],
            "status": "received",
        })

        # 3. Screen the shipper
        try:
            risk_index = self.screening_service.request_risk_index(
                shipper_id, request)
        except RuntimeError as exc:
            self.quote_store.update_status(quote_id, "screening_error")
            return {"status": "error: " + str(exc), "quote_id": quote_id}

        # 4. Decide based on screening
        if risk_index >= self.HIGH_RISK_MIN:
            self.quote_store.update_status(quote_id, "refused",
                                           {"risk_index": risk_index})
            self.notification_service.send(shipper_id, {
                "type": "refusal_notice",
                "quote_id": quote_id,
            })
            return {
                "status": "rejected",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }

        if risk_index > self.LOW_RISK_MAX:
            self.quote_store.update_status(quote_id, "held_for_review",
                                           {"risk_index": risk_index})
            return {
                "status": "held",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }

        # 5. Price the consignment
        price = self.tariff_engine.compute_price(
            request["weight"], request["distance"], request["declared_value"])

        # 6. Store and notify
        self.quote_store.update_status(quote_id, "quoted", {
            "risk_index": risk_index,
            "price": price,
        })
        self.notification_service.send(shipper_id, {
            "type": "quote_document",
            "quote_id": quote_id,
            "price": price,
        })

        return {
            "status": "confirmed",
            "quote_id": quote_id,
            "price": price,
            "risk_index": risk_index,
        }


def handle(request: dict) -> dict:
    api = QuoteApi(
        screening_service=ScreeningService(),
        tariff_engine=TariffEngine(),
        quote_store=QuoteStore(),
        notification_service=NotificationService(),
    )
    try:
        return api.request_quote(request)
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "error: " + str(exc)}
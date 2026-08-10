class ScreeningProvider:
    """External denied-party screening provider (outside system boundary)."""

    def screen(self, shipper_id, request=None):
        request = request or {}
        if "screening_result" in request:
            val = request["screening_result"]
        elif "screening_status" in request:
            val = request["screening_status"]
        else:
            val = "approved"
        # A numeric risk index may be supplied directly.
        if isinstance(val, (int, float)):
            return float(val)
        text = str(val).strip().lower()
        mapping = {
            "approved": 10.0,
            "clear": 10.0,
            "active": 10.0,
            "review": 50.0,
            "assessed": 50.0,
            "hold": 50.0,
            "declined": 90.0,
            "denied": 90.0,
            "rejected": 90.0,
        }
        if text in mapping:
            return mapping[text]
        try:
            return float(text)
        except ValueError:
            return 10.0


class TariffEngine:
    """Prices a consignment against the company tariff."""

    BASE_FEE = 25.0
    RATE_PER_KG_KM = 0.0005
    VALUE_SURCHARGE = 0.001

    def price(self, consignment):
        weight = float(consignment.get("weight", 0.0))
        distance = float(consignment.get("distance", 0.0))
        value = float(consignment.get("value", 0.0))
        price = (
            self.BASE_FEE
            + weight * distance * self.RATE_PER_KG_KM
            + value * self.VALUE_SURCHARGE
        )
        return round(price, 2)


class QuoteStore:
    """Persists quote requests and issued quotes."""

    def __init__(self):
        self._records = {}
        self._counter = 0

    def save(self, quote):
        if quote.get("store_result") == "error":
            return "error"
        self._counter += 1
        quote_id = "Q%05d" % self._counter
        self._records[quote_id] = dict(quote)
        return quote_id


class NotificationProvider:
    """External notification provider (outside system boundary)."""

    def notify(self, shipper_id, document):
        return "delivered"


class QuoteService:
    """Orchestrates the synchronous quotation flow."""

    REVIEW_THRESHOLD = 30.0
    REFUSE_THRESHOLD = 70.0

    def __init__(self, screening=None, tariff=None, store=None, notifier=None):
        self.screening = screening or ScreeningProvider()
        self.tariff = tariff or TariffEngine()
        self.store = store or QuoteStore()
        self.notifier = notifier or NotificationProvider()

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not shipper_id:
            return "missing_shipper"
        exists = request.get("shipper_exists", request.get("shipper_found", True))
        if not exists:
            return "unknown_shipper"
        try:
            weight = float(request.get("weight", 0))
            distance = float(request.get("distance", 0))
            value = float(request.get("value", 0))
        except (TypeError, ValueError):
            return "invalid_amounts"
        if weight <= 0:
            return "invalid_weight"
        if distance <= 0:
            return "invalid_distance"
        if value < 0:
            return "invalid_value"
        return None

    def quote(self, request):
        # 1. Validate the request.
        problem = self._validate(request)
        if problem:
            return {"status": "error: " + problem}

        shipper_id = request.get("shipper_id")

        # 2. Record the incoming request.
        request_record = {
            "shipper_id": shipper_id,
            "weight": request.get("weight"),
            "distance": request.get("distance"),
            "value": request.get("value"),
            "kind": "request",
            "store_result": request.get("store_result"),
        }
        request_ref = self.store.save(request_record)
        if request_ref == "error":
            return {"status": "error: store_unavailable"}

        # 3. Screen the shipper.
        risk_index = self.screening.screen(shipper_id, request)

        # 4. Decide the outcome based on screening.
        if risk_index >= self.REFUSE_THRESHOLD:
            refusal = {
                "shipper_id": shipper_id,
                "kind": "refusal",
                "risk_index": risk_index,
                "store_result": request.get("store_result"),
            }
            ref = self.store.save(refusal)
            if ref == "error":
                return {"status": "error: store_unavailable"}
            self.notifier.notify(shipper_id, refusal)
            return {
                "status": "rejected",
                "reason": "screening_declined",
                "risk_index": risk_index,
                "quote_ref": ref,
            }

        # 5. Price the consignment.
        price = self.tariff.price(request)

        if risk_index >= self.REVIEW_THRESHOLD:
            held = {
                "shipper_id": shipper_id,
                "kind": "held_for_review",
                "risk_index": risk_index,
                "price": price,
                "store_result": request.get("store_result"),
            }
            ref = self.store.save(held)
            if ref == "error":
                return {"status": "error: store_unavailable"}
            return {
                "status": "review",
                "reason": "manual_review_required",
                "risk_index": risk_index,
                "price": price,
                "quote_ref": ref,
            }

        # 6. Issue the quote.
        quote_doc = {
            "shipper_id": shipper_id,
            "kind": "quote",
            "risk_index": risk_index,
            "price": price,
            "store_result": request.get("store_result"),
        }
        quote_ref = self.store.save(quote_doc)
        if quote_ref == "error":
            return {"status": "error: store_unavailable"}

        # 7. Deliver the quote document to the shipper.
        self.notifier.notify(shipper_id, quote_doc)

        return {
            "status": "confirmed",
            "price": price,
            "risk_index": risk_index,
            "quote_ref": quote_ref,
        }


def handle(request: dict) -> dict:
    request = request or {}
    try:
        service = QuoteService()
        return service.quote(request)
    except Exception as exc:  # noqa: BLE001
        return {"status": "error: " + str(exc)}
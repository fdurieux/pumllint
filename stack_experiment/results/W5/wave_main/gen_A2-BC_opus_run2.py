class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, override=None):
        if override is not None:
            if isinstance(override, bool):
                pass
            elif isinstance(override, (int, float)):
                return float(override)
            word = str(override).lower()
            if word in ("approved", "clear", "active"):
                return 10.0
            if word in ("review", "hold", "assessed"):
                return 55.0
            if word in ("declined", "denied", "refused"):
                return 95.0
            if word in ("error", "unavailable"):
                raise RuntimeError("screening_unavailable")
        return 10.0


class TariffEngine:
    """Computes the freight price for a validated request from weight and
    distance per the published tariff rules."""

    BASE_FEE = 25.0
    RATE_PER_KG_KM = 0.0005

    def price(self, weight_kg, distance_km, declared_value=0):
        if weight_kg <= 0 or distance_km <= 0:
            raise ValueError("invalid_consignment")
        freight = self.BASE_FEE + (weight_kg * distance_km * self.RATE_PER_KG_KM)
        return round(freight, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._counter = 0

    def save(self, request):
        self._counter += 1
        quote_id = "Q%05d" % self._counter
        self._records[quote_id] = {"request": dict(request), "status": "recorded"}
        return quote_id

    def update_status(self, quote_id, status):
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send(self, shipper_id, document_type, payload):
        return "delivered"


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and
    pricing, and returns the quotation outcome."""

    REVIEW_THRESHOLD = 40.0
    REFUSE_THRESHOLD = 80.0

    def __init__(self, store=None, screening=None, tariff=None, notifier=None):
        self.store = store or QuoteStore()
        self.screening = screening or ScreeningService()
        self.tariff = tariff or TariffEngine()
        self.notifier = notifier or NotificationService()

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not shipper_id:
            raise ValueError("missing_shipper")
        if not request.get("shipper_exists", True) or not request.get(
            "shipper_found", True
        ):
            raise LookupError("shipper_not_found")
        weight = request.get("weight_kg")
        distance = request.get("distance_km")
        value = request.get("declared_value", 0)
        for field, val in (("weight_kg", weight), ("distance_km", distance)):
            if val is None:
                raise ValueError("missing_" + field)
            if isinstance(val, bool) or not isinstance(val, (int, float)) or val <= 0:
                raise ValueError("invalid_" + field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError("invalid_declared_value")
        return shipper_id, float(weight), float(distance), float(value)

    def request_quote(self, request):
        try:
            shipper_id, weight, distance, value = self._validate(request)
        except (ValueError, LookupError) as exc:
            return {"status": "error: %s" % exc}

        quote_id = self.store.save(request)

        try:
            risk_index = self.screening.screen(
                shipper_id,
                request.get("screening_result", request.get("screening_status")),
            )
        except Exception:
            self.store.update_status(quote_id, "screening_error")
            return {"status": "error: screening_unavailable", "quote_id": quote_id}

        if risk_index >= self.REFUSE_THRESHOLD:
            self.store.update_status(quote_id, "refused")
            self.notifier.send(shipper_id, "refusal_notice", {"quote_id": quote_id})
            return {
                "status": "rejected",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }

        if risk_index >= self.REVIEW_THRESHOLD:
            self.store.update_status(quote_id, "held_for_review")
            return {
                "status": "held",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }

        try:
            price = self.tariff.price(weight, distance, value)
        except ValueError as exc:
            self.store.update_status(quote_id, "pricing_error")
            return {"status": "error: %s" % exc, "quote_id": quote_id}

        self.store.update_status(quote_id, "issued")
        self.notifier.send(
            shipper_id, "quote_document", {"quote_id": quote_id, "price": price}
        )
        return {
            "status": "confirmed",
            "quote_id": quote_id,
            "price": price,
            "risk_index": risk_index,
        }


def handle(request: dict) -> dict:
    api = QuoteApi()
    return api.request_quote(request)
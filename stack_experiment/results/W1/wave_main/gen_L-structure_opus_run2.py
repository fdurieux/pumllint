def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


class ScreeningUnavailable(Exception):
    pass


class StoreUnavailable(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider (outside system boundary)."""

    def screen(self, shipper_id, request=None):
        request = request or {}
        status = str(request.get("screening_status", request.get("screening_result", ""))).lower()
        if status in ("error", "unavailable", "down", "outage", "timeout"):
            raise ScreeningUnavailable("screening service unavailable")
        for key in ("risk_index", "screening_result", "screening_status", "screening_score"):
            val = request.get(key)
            if _is_number(val):
                return int(val)
            if isinstance(val, str):
                try:
                    return int(val)
                except ValueError:
                    continue
        # default plausible low-risk index
        return 0


class TariffEngine:
    """Company tariff pricing computation (DT-P)."""

    def price(self, weight_kg, distance_km):
        base = 0.87 * weight_kg + 1.13 * distance_km
        total = base
        if weight_kg > 1244:
            total += 316.00
        if distance_km >= 4912:
            total *= 1.19
        return round(total, 2)


class QuoteStore:
    """Quote persistence (ContainerDb)."""

    def __init__(self):
        self._seq = 0
        self._quotes = {}

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value, request=None):
        request = request or {}
        status = str(request.get("store_status", request.get("store_result", ""))).lower()
        if status in ("error", "unavailable", "down", "fail", "failed"):
            raise StoreUnavailable("store unavailable")
        self._seq += 1
        quote_id = "Q-{:06d}".format(self._seq)
        self._quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
        }
        return quote_id

    def updateQuote(self, quote_id, status, price=None):
        record = self._quotes.get(quote_id, {})
        record["status"] = status
        if price is not None:
            record["price"] = price
        self._quotes[quote_id] = record
        return quote_id


class NotificationService:
    """External notification provider (fire-and-forget)."""

    def sendQuoteDocument(self, shipper_id, quote_id, price, request=None):
        request = request or {}
        status = str(request.get("notification_status", request.get("notification_result", ""))).lower()
        return status not in ("error", "unavailable", "fail", "failed")

    def sendRefusalNotice(self, shipper_id, quote_id, request=None):
        request = request or {}
        status = str(request.get("notification_status", request.get("notification_result", ""))).lower()
        return status not in ("error", "unavailable", "fail", "failed")


class QuoteAPI:
    """Synchronous quotation orchestrator (QuoteAPI service)."""

    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

    def __init__(self, tariff_engine, screening_service, notification_service, quote_store):
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.notification_service = notification_service
        self.quote_store = quote_store

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False
        weight_kg = request.get("weight_kg")
        if not _is_number(weight_kg) or not (3 <= weight_kg <= 19400):
            return False
        distance_km = request.get("distance_km")
        if not _is_number(distance_km) or not (25 <= distance_km <= 7150):
            return False
        declared_value = request.get("declared_value")
        if not _is_number(declared_value) or not (50 <= declared_value <= 83000):
            return False
        return True

    def requestQuote(self, request):
        # Step 1 — validate (DT-V)
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]

        # Step 2 — store draft
        try:
            quote_id = self.quote_store.storeDraft(
                shipper_id, weight_kg, distance_km, declared_value, request
            )
        except StoreUnavailable:
            return {"status": "error: store_unavailable"}

        # Step 3 — screening
        try:
            risk_index = self.screening_service.screen(shipper_id, request)
        except ScreeningUnavailable:
            # Screening outage: price anyway, hold, do not notify (DT-S note 5)
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4/5/6 — apply screening decision (DT-S)
        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "quoted", price)
            self.notification_service.sendQuoteDocument(shipper_id, quote_id, price, request)
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        if self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # risk_index >= REFUSE_MIN
        self.quote_store.updateQuote(quote_id, "refused_screening")
        self.notification_service.sendRefusalNotice(shipper_id, quote_id, request)
        return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    tariff_engine = TariffEngine()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    quote_store = QuoteStore()
    api = QuoteAPI(tariff_engine, screening_service, notification_service, quote_store)
    return api.requestQuote(request or {})
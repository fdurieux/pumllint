SCREENING_ACCEPT_MAX = 30
SCREENING_REVIEW_MIN = 31
SCREENING_REVIEW_MAX = 69
SCREENING_REFUSE_MIN = 70

WEIGHT_MIN = 1
WEIGHT_MAX = 26000
DISTANCE_MIN = 1
DISTANCE_MAX = 3000
VALUE_MIN = 1
VALUE_MAX = 1000000


class ScreeningError(Exception):
    pass


class StoreError(Exception):
    pass


class Shipper:
    """Person: a logistics customer requesting a quote."""

    def __init__(self, quote_api):
        self.quote_api = quote_api

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        return self.quote_api.request_quote(
            shipper_id, weight_kg, distance_km, declared_value
        )


class TariffEngine:
    """Computes freight price from weight and distance."""

    BASE_RATE = 5.0
    PER_KG = 0.15
    PER_KM = 0.08

    def price(self, weight_kg, distance_km):
        return round(
            self.BASE_RATE + self.PER_KG * weight_kg + self.PER_KM * distance_km, 2
        )


class QuoteStore:
    """Stores quote records and their lifecycle status."""

    def __init__(self, store_status="stored"):
        self.store_status = store_status
        self._seq = 0
        self.records = {}

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if self.store_status in ("error", "unavailable", "down"):
            raise StoreError("storeUnavailableError")
        self._seq += 1
        quote_id = "Q{:06d}".format(self._seq)
        self.records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "Draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price=None):
        rec = self.records.get(quote_id, {})
        rec["status"] = status
        if price is not None:
            rec["price"] = price
        self.records[quote_id] = rec
        return quote_id


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, risk_index=10, available=True):
        self.risk_index = risk_index
        self.available = available

    def screen(self, shipper_id):
        if not self.available:
            raise ScreeningError("screeningUnavailableError")
        return self.risk_index


class NotificationService:
    """External messaging provider delivering documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            return False
        try:
            w = float(weight_kg)
            d = float(distance_km)
            v = float(declared_value)
        except (TypeError, ValueError):
            return False
        if not (WEIGHT_MIN <= w <= WEIGHT_MAX):
            return False
        if not (DISTANCE_MIN <= d <= DISTANCE_MAX):
            return False
        if not (VALUE_MIN <= v <= VALUE_MAX):
            return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Validation per DT-V
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected_invalid_request"}

        # Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreError:
            # On storage failure nothing else runs (DT-S note 3)
            return {"status": "error: store_unavailable"}

        # Screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            # Screening outage: price, hold, do not notify (DT-S note 5)
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "HeldUnscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
            }

        if risk_index <= SCREENING_ACCEPT_MAX:
            # Accept: price and notify
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "Quoted", price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount
            )
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount,
            }
        elif SCREENING_REVIEW_MIN <= risk_index <= SCREENING_REVIEW_MAX:
            # Review hold: no pricing, no notification (DT-S note 1)
            self.quote_store.update_quote(quote_id, "ReviewHold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:
            # Refuse: notify, no pricing (DT-S note 2)
            self.quote_store.update_quote(quote_id, "RefusedScreening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}


def _risk_from_request(request):
    """Derive the screening risk index / availability from the request."""
    status = request.get("screening_status")
    result = request.get("screening_result")

    if status in ("error", "unavailable", "down") or result in (
        "error",
        "unavailable",
        "down",
    ):
        return None  # signals unavailable

    for candidate in (result, request.get("risk_index"), status):
        if candidate is None:
            continue
        if isinstance(candidate, (int, float)):
            return candidate
        try:
            return float(candidate)
        except (TypeError, ValueError):
            pass
        word = str(candidate).lower()
        if word in ("approved", "accept", "accepted", "clear", "active"):
            return 10
        if word in ("review", "hold", "assessed"):
            return 50
        if word in ("declined", "refused", "denied", "reject", "rejected"):
            return 90
    return 10  # default: low risk


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id") or request.get("shipperId")
    if request.get("shipper_exists") is False or request.get("shipper_found") is False:
        shipper_id = None

    weight_kg = request.get("weight_kg", request.get("weightKg"))
    distance_km = request.get("distance_km", request.get("distanceKm"))
    declared_value = request.get("declared_value", request.get("declaredValue"))

    store_status = request.get("store_status") or request.get("store_result") or "stored"

    risk = _risk_from_request(request)
    if risk is None:
        screening = ScreeningService(available=False)
    else:
        screening = ScreeningService(risk_index=risk, available=True)

    quote_store = QuoteStore(store_status=store_status)
    tariff_engine = TariffEngine()
    notification_service = NotificationService()

    quote_api = QuoteApi(
        quote_store, screening, tariff_engine, notification_service
    )
    shipper = Shipper(quote_api)

    return shipper.request_quote(shipper_id, weight_kg, distance_km, declared_value)
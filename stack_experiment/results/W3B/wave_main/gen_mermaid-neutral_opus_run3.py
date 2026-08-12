def _to_camel(alias):
    return "".join(part.capitalize() for part in alias.split("_"))


# ---- Screening thresholds (decision table DT-S) ----
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 69
REFUSE_MIN = 70

# ---- Validation bounds (decision table DT-V) ----
WEIGHT_MIN, WEIGHT_MAX = 1, 26000
DISTANCE_MIN, DISTANCE_MAX = 1, 3000
VALUE_MIN, VALUE_MAX = 1, 10_000_000


class ScreeningUnavailableError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, result=None, status=None):
        self._result = result
        self._status = status

    def screen(self, shipper_id):
        if self._status == "error":
            raise ScreeningUnavailableError("screening service unavailable")
        if isinstance(self._result, (int, float)):
            return self._result
        mapping = {
            "approved": 10,
            "accept": 10,
            "active": 10,
            "review": 50,
            "assessed": 50,
            "declined": 90,
            "refused": 90,
        }
        if self._status in mapping:
            return mapping[self._status]
        if self._result in mapping:
            return mapping[self._result]
        return 10


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, status=None):
        self._status = status

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        if self._status == "error":
            return "delivery_failed"
        return "delivered"

    def send_refusal_notice(self, shipper_id, quote_id):
        if self._status == "error":
            return "delivery_failed"
        return "delivered"


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, status=None):
        self._status = status
        self._records = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if self._status == "error":
            raise StoreUnavailableError("quote store unavailable")
        self._seq += 1
        quote_id = "Q%04d" % self._seq
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        rec = self._records.get(quote_id)
        if rec is None:
            rec = {}
            self._records[quote_id] = rec
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        return "updated:%s" % quote_id


class TariffEngine:
    """Computes the freight price from weight and distance per published tariff rules."""

    BASE_FEE = 25.0
    RATE_PER_KG = 0.15
    RATE_PER_KM = 0.40

    def price(self, weight_kg, distance_km):
        return round(
            self.BASE_FEE + weight_kg * self.RATE_PER_KG + distance_km * self.RATE_PER_KM,
            2,
        )


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate(self, weight_kg, distance_km, declared_value):
        if not isinstance(weight_kg, (int, float)) or not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            return False
        if not isinstance(distance_km, (int, float)) or not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            return False
        if not isinstance(declared_value, (int, float)) or not (VALUE_MIN <= declared_value <= VALUE_MAX):
            return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Validation (DT-V)
        if not self._validate(weight_kg, distance_km, declared_value):
            return {"status": "rejected", "reason": "invalid_request"}

        # Store draft (DT-S note 3: on storage failure nothing else runs)
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # DT-S note 5: outage does not fail the quote; price and hold, no notification
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
            }

        # Accept path
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            try:
                self.notification_service.send_quote_document(
                    shipper_id, quote_id, price_amount
                )
            except Exception:
                pass  # fire-and-forget (DT-S note 4)
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}

        # Review path
        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # Refuse path
        if risk_index >= REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass
            return {"status": "refused", "quote_id": quote_id}

        # Fallback (should not occur)
        self.quote_store.update_quote(quote_id, "review_hold")
        return {"status": "review_hold", "quote_id": quote_id}


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "unknown")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    screening_result = request.get("screening_result", request.get("screening_score"))
    screening_status = request.get("screening_status")
    store_status = request.get("store_status", request.get("store_result"))
    if store_status == "stored":
        store_status = None
    notification_status = request.get("notification_status", request.get("notification_result"))

    screening_service = ScreeningService(result=screening_result, status=screening_status)
    quote_store = QuoteStore(status=store_status if store_status == "error" else None)
    notification_service = NotificationService(status=notification_status)
    tariff_engine = TariffEngine()

    api = QuoteApi(quote_store, screening_service, tariff_engine, notification_service)
    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
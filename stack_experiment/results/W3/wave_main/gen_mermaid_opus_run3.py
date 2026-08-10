import math


# --- Exceptions -------------------------------------------------------------

class ValidationError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


# --- External system: Screening Service ------------------------------------

class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, status=None, result=None):
        self._status = status
        self._result = result

    def screen(self, shipper_id):
        raw = self._result if self._result is not None else self._status
        if isinstance(raw, str):
            word = raw.strip().lower()
            if word == "error":
                raise ScreeningUnavailableError("screening service unavailable")
            mapping = {
                "approved": 10,
                "clear": 10,
                "active": 10,
                "assessed": 50,
                "review": 50,
                "declined": 90,
                "denied": 90,
            }
            if word in mapping:
                return mapping[word]
            try:
                return float(word)
            except ValueError:
                return 10.0
        if isinstance(raw, (int, float)):
            return float(raw)
        # default: low-risk clear result
        return 10.0


# --- External system: Notification Service ----------------------------------

class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "queued"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "queued"


# --- Container DB: Quote Store ----------------------------------------------

class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, status=None, result=None):
        self._status = status
        self._result = result
        self._seq = 0
        self._records = {}

    def _unavailable(self):
        raw = self._result if self._result is not None else self._status
        if isinstance(raw, str) and raw.strip().lower() == "error":
            return True
        return False

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if self._unavailable():
            raise StoreUnavailableError("quote store unavailable")
        self._seq += 1
        quote_id = "Q-{:06d}".format(self._seq)
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
        rec = self._records.get(quote_id, {})
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        self._records[quote_id] = rec
        return "updated"


# --- Container: Tariff Engine -----------------------------------------------

class TariffEngine:
    """Computes the freight price from weight and distance per published tariff."""

    BASE_FEE = 25.0
    RATE_PER_KG = 0.50
    RATE_PER_KM = 0.80

    def price(self, weight_kg, distance_km):
        amount = (
            self.BASE_FEE
            + self.RATE_PER_KG * float(weight_kg)
            + self.RATE_PER_KM * float(distance_km)
        )
        return round(amount, 2)


# --- Container: Quote API ---------------------------------------------------

class QuoteApi:
    """Receives quote requests, validates, orchestrates screening/pricing."""

    # DT-V validation bounds
    WEIGHT_MIN = 0.0
    WEIGHT_MAX = 26000.0
    DISTANCE_MIN = 0.0
    DISTANCE_MAX = 5000.0
    VALUE_MIN = 0.0

    # DT-S screening thresholds
    ACCEPT_MAX = 30.0
    REVIEW_MAX = 70.0
    REFUSE_MIN = 71.0

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    # --- validation (DT-V) ---
    def _validate(self, shipper_id, weight_kg, distance_km, declared_value, request):
        if not shipper_id:
            raise ValidationError("missing_shipper_id")
        if request.get("shipper_exists") is False or request.get("shipper_found") is False:
            raise ValidationError("shipper_not_found")
        try:
            w = float(weight_kg)
            d = float(distance_km)
            v = float(declared_value)
        except (TypeError, ValueError):
            raise ValidationError("non_numeric_field")
        if not (self.WEIGHT_MIN < w <= self.WEIGHT_MAX):
            raise ValidationError("weight_out_of_bounds")
        if not (self.DISTANCE_MIN < d <= self.DISTANCE_MAX):
            raise ValidationError("distance_out_of_bounds")
        if v < self.VALUE_MIN:
            raise ValidationError("declared_value_out_of_bounds")
        return w, d, v

    def request_quote(self, request):
        shipper_id = request.get("shipper_id") or request.get("shipperId")
        weight_kg = request.get("weight_kg", request.get("weightKg"))
        distance_km = request.get("distance_km", request.get("distanceKm"))
        declared_value = request.get("declared_value", request.get("declaredValue"))

        # 1. Validate (DT-V)
        try:
            w, d, v = self._validate(
                shipper_id, weight_kg, distance_km, declared_value, request
            )
        except ValidationError as e:
            return {"status": "rejected", "reason": str(e)}

        # 2. Store draft
        try:
            quote_id = self.quote_store.store_draft(shipper_id, w, d, v)
        except StoreUnavailableError:
            # On storage failure nothing else runs (DT-S note 3).
            return {"status": "error: store_unavailable"}

        # 3. Screen the shipper
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage does NOT fail the quote (DT-S note 5):
            # price it, store on hold, do not notify.
            price_amount = self.tariff_engine.price(w, d)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
            }

        # 4. Decide by risk index (DT-S)
        if risk_index <= self.ACCEPT_MAX:
            price_amount = self.tariff_engine.price(w, d)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            # fire-and-forget notification (DT-S note 4)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount
            )
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount,
                "risk_index": risk_index,
            }
        elif risk_index <= self.REVIEW_MAX:
            # Review hold: no pricing, no notification (DT-S note 1).
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }
        else:  # risk_index >= REFUSE_MIN
            # Refusal IS notified; pricing never runs (DT-S note 2).
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }


# --- Module-level entry point -----------------------------------------------

def handle(request: dict) -> dict:
    request = request or {}

    screening_service = ScreeningService(
        status=request.get("screening_status"),
        result=request.get("screening_result"),
    )
    quote_store = QuoteStore(
        status=request.get("store_status"),
        result=request.get("store_result"),
    )
    tariff_engine = TariffEngine()
    notification_service = NotificationService()

    api = QuoteApi(
        tariff_engine=tariff_engine,
        quote_store=quote_store,
        screening_service=screening_service,
        notification_service=notification_service,
    )

    try:
        return api.request_quote(request)
    except Exception as e:  # pragma: no cover - defensive catch-all
        return {"status": "error: {}".format(e)}
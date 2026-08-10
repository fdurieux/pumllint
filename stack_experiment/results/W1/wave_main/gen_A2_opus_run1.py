import copy


class ScreeningUnavailableError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ValidationError(Exception):
    pass


# Screening decision thresholds (decision table DT-S)
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 69
REFUSE_MIN = 70

# Validation bounds (decision table DT-V)
WEIGHT_MIN, WEIGHT_MAX = 1, 26000
DISTANCE_MIN, DISTANCE_MAX = 1, 3000
VALUE_MIN, VALUE_MAX = 1, 1_000_000


class Shipper:
    """Person: A logistics customer requesting a price quote."""

    def __init__(self, quote_api):
        self.quote_api = quote_api

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        return self.quote_api.request_quote(
            shipper_id, weight_kg, distance_km, declared_value
        )


class TariffEngine:
    """Computes the freight price from weight and distance per tariff rules."""

    BASE_FEE = 25.0
    RATE_PER_KG = 0.12
    RATE_PER_KM = 0.85

    def price(self, weight_kg, distance_km):
        return round(
            self.BASE_FEE
            + self.RATE_PER_KG * float(weight_kg)
            + self.RATE_PER_KM * float(distance_km),
            2,
        )


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, request=None):
        self._request = request or {}
        self._records = {}
        self._seq = 0

    def _store_ok(self):
        status = str(
            self._request.get("store_result")
            or self._request.get("store_status")
            or self._request.get("quote_store_result")
            or self._request.get("quote_store_status")
            or "stored"
        ).lower()
        if status in ("error", "unavailable", "down", "failed"):
            return False
        return True

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._store_ok():
            raise StoreUnavailableError("store unavailable")
        self._seq += 1
        quote_id = "Q%04d" % self._seq
        self._records[quote_id] = {
            "quote_id": quote_id,
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
            raise StoreUnavailableError("unknown quote")
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        return copy.deepcopy(rec)


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, request=None):
        self._request = request or {}

    def screen(self, shipper_id):
        raw = self._request.get("screening_result")
        if raw is None:
            raw = self._request.get("screening_status")
        if raw is None:
            # default: benign shipper
            return 10.0

        if isinstance(raw, (int, float)):
            return float(raw)

        word = str(raw).lower()
        if word in ("error", "unavailable", "down", "timeout", "failed"):
            raise ScreeningUnavailableError("screening service unavailable")
        mapping = {
            "approved": 10.0,
            "accept": 10.0,
            "accepted": 10.0,
            "clear": 10.0,
            "low": 10.0,
            "review": 50.0,
            "assessed": 50.0,
            "hold": 50.0,
            "medium": 50.0,
            "declined": 90.0,
            "refuse": 90.0,
            "refused": 90.0,
            "denied": 90.0,
            "high": 90.0,
        }
        if word in mapping:
            return mapping[word]
        try:
            return float(word)
        except ValueError:
            return 10.0


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, request=None):
        self._request = request or {}

    def _deliver(self):
        # Fire-and-forget: failures are the provider's retry problem.
        status = str(
            self._request.get("notification_result")
            or self._request.get("notification_status")
            or "sent"
        ).lower()
        return status

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return self._deliver()

    def send_refusal_notice(self, shipper_id, quote_id):
        return self._deliver()


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if shipper_id is None or str(shipper_id).strip() == "":
            raise ValidationError("missing shipper id")
        try:
            weight = float(weight_kg)
            distance = float(distance_km)
            value = float(declared_value)
        except (TypeError, ValueError):
            raise ValidationError("non-numeric field")
        if not (WEIGHT_MIN <= weight <= WEIGHT_MAX):
            raise ValidationError("weight out of bounds")
        if not (DISTANCE_MIN <= distance <= DISTANCE_MAX):
            raise ValidationError("distance out of bounds")
        if not (VALUE_MIN <= value <= VALUE_MAX):
            raise ValidationError("declared value out of bounds")

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Validation (DT-V)
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as exc:
            return {"status": "rejected", "reason": str(exc)}

        # Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError:
            # DT-S note 3: nothing else runs on storage failure
            return {"status": "error: store_unavailable"}

        # Screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # DT-S note 5: outage does not fail the quote; priced & held.
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, "held_unscreened", price_amount
            )
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
            }

        # Decision table DT-S
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount
            )
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount,
                "risk_index": risk_index,
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # DT-S note 1: no pricing, no notification
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }
        else:  # risk_index >= REFUSE_MIN
            # DT-S note 2: refusal is notified; pricing never runs
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }


def handle(request: dict) -> dict:
    request = request or {}

    quote_store = QuoteStore(request)
    screening_service = ScreeningService(request)
    tariff_engine = TariffEngine()
    notification_service = NotificationService(request)
    quote_api = QuoteApi(
        quote_store, screening_service, tariff_engine, notification_service
    )
    shipper = Shipper(quote_api)

    shipper_id = (
        request.get("shipper_id")
        or request.get("shipperId")
        or request.get("shipper")
    )
    weight_kg = request.get("weight_kg", request.get("weightKg"))
    distance_km = request.get("distance_km", request.get("distanceKm"))
    declared_value = request.get("declared_value", request.get("declaredValue"))

    # Existence flag handling
    if request.get("shipper_exists") is False or request.get("shipper_found") is False:
        return {"status": "rejected", "reason": "shipper not found"}

    try:
        return shipper.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "error: %s" % type(exc).__name__}
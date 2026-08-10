from __future__ import annotations


# --- Exceptions for failure paths -------------------------------------------

class StoreUnavailableError(Exception):
    """Raised when the quote store cannot accept a write."""


class ScreeningUnavailableError(Exception):
    """Raised when the external screening provider is unreachable."""


class InvalidRequestError(Exception):
    """Raised when a quote request fails validation (DT-V)."""


# --- External systems (outside the system boundary) -------------------------

class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, outcome=None):
        self.outcome = outcome

    def screen(self, shipper_id):
        outcome = self.outcome
        if outcome is None:
            return 10
        if isinstance(outcome, bool):
            return 10 if outcome else 90
        if isinstance(outcome, (int, float)):
            return outcome
        word = str(outcome).strip().lower()
        try:
            return float(word)
        except ValueError:
            pass
        if word in ("error", "unavailable", "down", "timeout", "outage"):
            raise ScreeningUnavailableError("screening service unavailable")
        accept = {"approved", "accept", "active", "clear", "assessed", "ok", "pass"}
        review = {"review", "hold", "manual", "pending"}
        refuse = {"declined", "refuse", "refused", "denied", "deny", "lapsed", "blocked"}
        if word in accept:
            return 10
        if word in review:
            return 50
        if word in refuse:
            return 90
        return 10


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


# --- Internal containers ----------------------------------------------------

class TariffEngine:
    """Computes the freight price from weight and distance per the tariff rules."""

    BASE_FEE = 25.0
    RATE_PER_KG_KM = 0.0001

    def price(self, weight_kg, distance_km):
        amount = self.BASE_FEE + float(weight_kg) * float(distance_km) * self.RATE_PER_KG_KM
        return round(amount, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available=True):
        self.available = available
        self._records = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self.available:
            raise StoreUnavailableError("quote store unavailable")
        self._seq += 1
        quote_id = "Q{}".format(self._seq)
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
        if not self.available:
            raise StoreUnavailableError("quote store unavailable")
        record = self._records.get(quote_id)
        if record is None:
            record = {"shipper_id": None, "status": None, "price": None}
            self._records[quote_id] = record
        record["status"] = status
        if price_amount is not None:
            record["price"] = price_amount
        return quote_id


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and
    pricing, and returns the quotation outcome."""

    # DT-S thresholds
    ACCEPT_MAX = 30
    REVIEW_MIN = 31
    REVIEW_MAX = 70
    REFUSE_MIN = 71

    # DT-V bounds
    WEIGHT_MIN = 1.0
    WEIGHT_MAX = 26000.0
    DISTANCE_MIN = 1.0
    DISTANCE_MAX = 3000.0
    VALUE_MIN = 0.01
    VALUE_MAX = 10_000_000.0

    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            raise InvalidRequestError("missing shipper id")
        for name, value in (
            ("weight", weight_kg),
            ("distance", distance_km),
            ("declared_value", declared_value),
        ):
            if value is None:
                raise InvalidRequestError("missing {}".format(name))
            try:
                float(value)
            except (TypeError, ValueError):
                raise InvalidRequestError("non-numeric {}".format(name))
        w = float(weight_kg)
        d = float(distance_km)
        v = float(declared_value)
        if not (self.WEIGHT_MIN <= w <= self.WEIGHT_MAX):
            raise InvalidRequestError("weight out of bounds")
        if not (self.DISTANCE_MIN <= d <= self.DISTANCE_MAX):
            raise InvalidRequestError("distance out of bounds")
        if not (self.VALUE_MIN <= v <= self.VALUE_MAX):
            raise InvalidRequestError("declared value out of bounds")

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # DT-V validation
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except InvalidRequestError as exc:
            return {"status": "rejected: invalid request", "reason": str(exc)}

        # Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError as exc:
            # DT-S note 3: nothing else runs on storage failure
            return {"status": "error: store unavailable", "reason": str(exc)}

        # Screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # DT-S note 5: outage does not fail the quote — price, hold, no notify
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
            }

        # DT-S decision on risk index
        if risk_index <= self.ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            # DT-S note 4: notification is fire-and-forget
            try:
                self.notification_service.send_quote_document(
                    shipper_id, quote_id, price_amount
                )
            except Exception:
                pass
            return {
                "status": "confirmed",
                "quote_id": quote_id,
                "price": price_amount,
            }

        if risk_index <= self.REVIEW_MAX:
            # DT-S note 1: no pricing, no notification on review hold
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # refuse (risk_index >= REFUSE_MIN)
        self.quote_store.update_quote(quote_id, "refused_screening")
        # DT-S note 2: refusal IS notified; pricing never runs
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            pass
        return {"status": "refused", "quote_id": quote_id}


# --- Module-level end-to-end entry point ------------------------------------

def _lookup(request, *keys, default=None):
    for key in keys:
        if key in request:
            return request[key]
    return default


def handle(request: dict) -> dict:
    request = request or {}

    # Shipper existence check
    if request.get("shipper_exists") is False or request.get("shipper_found") is False:
        return {"status": "rejected: invalid request", "reason": "shipper not found"}

    # Store availability driven by store result/status
    store_status = _lookup(
        request,
        "quote_store_result",
        "quote_store_status",
        "store_result",
        "store_status",
    )
    store_available = True
    if store_status is not None and str(store_status).strip().lower() in (
        "error",
        "unavailable",
        "down",
        "outage",
    ):
        store_available = False

    # Screening outcome
    screening_outcome = _lookup(request, "screening_result", "screening_status")

    quote_store = QuoteStore(available=store_available)
    screening_service = ScreeningService(outcome=screening_outcome)
    tariff_engine = TariffEngine()
    notification_service = NotificationService()

    api = QuoteApi(quote_store, screening_service, tariff_engine, notification_service)

    shipper_id = _lookup(request, "shipper_id", "shipperId", default="unknown")
    weight_kg = _lookup(request, "weight_kg", "weightKg", "weight")
    distance_km = _lookup(request, "distance_km", "distanceKm", "distance")
    declared_value = _lookup(request, "declared_value", "declaredValue", "value")

    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
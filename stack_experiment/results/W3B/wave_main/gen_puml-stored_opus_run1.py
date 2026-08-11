import uuid


# --- Exceptions ---------------------------------------------------------------

class ValidationError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


# --- Validation / screening thresholds (DT-V, DT-S) ---------------------------

WEIGHT_MIN, WEIGHT_MAX = 1, 24000        # kg
DISTANCE_MIN, DISTANCE_MAX = 1, 3000     # km
VALUE_MIN, VALUE_MAX = 1, 1_000_000      # declared value

ACCEPT_MAX = 30
REVIEW_MIN, REVIEW_MAX = 31, 69
REFUSE_MIN = 70


# --- External systems (outside the boundary) ---------------------------------

class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, config=None):
        self.config = config or {}

    def screen(self, shipper_id):
        raw = self.config.get("screening_result",
                              self.config.get("screening_status"))
        if raw is None:
            return 10
        if isinstance(raw, (int, float)):
            return raw
        word = str(raw).strip().lower()
        if word in ("error", "unavailable", "timeout", "down"):
            raise ScreeningUnavailableError("screening service unavailable")
        if word in ("approved", "accept", "clear", "active"):
            return 10
        if word in ("review", "hold", "manual"):
            return 50
        if word in ("declined", "refuse", "refused", "denied", "blocked"):
            return 90
        try:
            return float(word)
        except ValueError:
            return 10


class NotificationService:
    """External messaging provider (fire-and-forget)."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


# --- System containers --------------------------------------------------------

class QuoteStore:
    """Stores quote requests and their lifecycle status (PostgreSQL)."""

    def __init__(self, config=None):
        self.config = config or {}
        self.records = {}

    def _available(self):
        raw = self.config.get("store_result", self.config.get("store_status"))
        if raw is None:
            return True
        word = str(raw).strip().lower()
        return word in ("stored", "ok", "available", "success")

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._available():
            raise StoreUnavailableError("quote store unavailable")
        quote_id = str(uuid.uuid4())
        self.records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        rec = self.records.get(quote_id, {})
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        self.records[quote_id] = rec
        return quote_id


class TariffEngine:
    """Computes the freight price from weight and distance per tariff rules."""

    def price(self, weight_kg, distance_km):
        base = 25.0
        weight_component = weight_kg * 0.05
        distance_component = distance_km * 0.10
        return round(base + weight_component + distance_component, 2)


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service,
                 notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            raise ValidationError("missing shipper id")
        for name, val in (("weight_kg", weight_kg),
                          ("distance_km", distance_km),
                          ("declared_value", declared_value)):
            if val is None or not isinstance(val, (int, float)):
                raise ValidationError("invalid %s" % name)
        if not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            raise ValidationError("weight out of bounds")
        if not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            raise ValidationError("distance out of bounds")
        if not (VALUE_MIN <= declared_value <= VALUE_MAX):
            raise ValidationError("declared value out of bounds")

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Validation (DT-V)
        self._validate(shipper_id, weight_kg, distance_km, declared_value)

        # Store draft (on failure nothing else runs)
        quote_id = self.quote_store.store_draft(
            shipper_id, weight_kg, distance_km, declared_value)

        # Screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # DT-S note 5: outage does not fail the quote; price + hold, no notify
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
            }

        # Accept
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount)  # fire-and-forget
            return {
                "status": "confirmed",
                "quote_id": quote_id,
                "price": price_amount,
            }

        # Review hold (no pricing, no notification)
        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # Refuse (notified, no pricing)
        if risk_index >= REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused", "quote_id": quote_id}

        # Fallback (should not happen with contiguous bands)
        self.quote_store.update_quote(quote_id, "review_hold")
        return {"status": "review_hold", "quote_id": quote_id}


# --- Module-level entry point -------------------------------------------------

def handle(request: dict) -> dict:
    request = request or {}

    shipper_id = request.get("shipper_id", request.get("shipperId"))
    weight_kg = request.get("weight_kg", request.get("weightKg"))
    distance_km = request.get("distance_km", request.get("distanceKm"))
    declared_value = request.get("declared_value", request.get("declaredValue"))

    screening_service = ScreeningService(request)
    quote_store = QuoteStore(request)
    tariff_engine = TariffEngine()
    notification_service = NotificationService()

    api = QuoteApi(tariff_engine, quote_store, screening_service,
                   notification_service)

    try:
        return api.request_quote(shipper_id, weight_kg, distance_km,
                                 declared_value)
    except ValidationError as exc:
        return {"status": "rejected", "reason": str(exc)}
    except StoreUnavailableError as exc:
        return {"status": "error: store_unavailable", "reason": str(exc)}
    except Exception as exc:  # pragma: no cover
        return {"status": "error: %s" % exc}
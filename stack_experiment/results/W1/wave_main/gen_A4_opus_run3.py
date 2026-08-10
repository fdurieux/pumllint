import math


# --- Decision table constants (DT-S) ---
ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

# --- DT-V validation bounds ---
WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000

# --- DT-P pricing constants ---
WEIGHT_RATE = 0.87
DISTANCE_RATE = 1.13
HEAVY_THRESHOLD = 1244
HEAVY_SURCHARGE = 316.00
LONGHAUL_THRESHOLD = 4912
LONGHAUL_MULTIPLIER = 1.19


class StoreUnavailableError(Exception):
    """Raised when the Quote Store cannot persist a record."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service is unavailable."""


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, context=None):
        self._context = context or {}

    def screen(self, shipper_id):
        status = str(self._context.get("screening_status", "")).lower()
        result = self._context.get("screening_result", None)

        if status in ("error", "unavailable", "outage", "down"):
            raise ScreeningUnavailableError("screening service unavailable")
        if isinstance(result, str) and result.lower() in (
            "error",
            "unavailable",
            "outage",
            "down",
        ):
            raise ScreeningUnavailableError("screening service unavailable")

        if result is None:
            result = self._context.get("risk_index", 0)
        try:
            return int(result)
        except (TypeError, ValueError):
            raise ScreeningUnavailableError("screening service returned no index")


class TariffEngine:
    """Computes the freight price for a validated request per DT-P."""

    def price(self, weight_kg, distance_km):
        result = WEIGHT_RATE * weight_kg + DISTANCE_RATE * distance_km  # P1
        if weight_kg > HEAVY_THRESHOLD:  # P2
            result += HEAVY_SURCHARGE
        if distance_km >= LONGHAUL_THRESHOLD:  # P3 (after P2)
            result *= LONGHAUL_MULTIPLIER
        return round(result, 2)  # P4


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, context=None):
        self._context = context or {}
        self._records = {}
        self._counter = 0

    def _store_available(self):
        status = str(self._context.get("store_status", "")).lower()
        result = str(self._context.get("store_result", "")).lower()
        if status in ("error", "unavailable", "down"):
            return False
        if result in ("error", "unavailable", "down"):
            return False
        return True

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._store_available():
            raise StoreUnavailableError("quote store unavailable")
        self._counter += 1
        quote_id = "Q-{:06d}".format(self._counter)
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
        }
        return quote_id

    def update_quote(self, quote_id, status, price=None):
        record = self._records.get(quote_id, {})
        record["status"] = status
        if price is not None:
            record["price"] = price
        self._records[quote_id] = record
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, context=None):
        self._context = context or {}

    def _delivers(self):
        status = str(self._context.get("notification_status", "")).lower()
        result = str(self._context.get("notification_result", "")).lower()
        if status in ("error", "fail", "failed", "unavailable"):
            return False
        if result in ("error", "fail", "failed", "unavailable"):
            return False
        return True

    def send_quote_document(self, shipper_id, quote_id, price):
        if not self._delivers():
            raise Exception("delivery failed")
        return "delivered"

    def send_refusal_notice(self, shipper_id, quote_id):
        if not self._delivers():
            raise Exception("delivery failed")
        return "delivered"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self._tariff_engine = tariff_engine
        self._quote_store = quote_store
        self._screening_service = screening_service
        self._notification_service = notification_service

    # --- DT-V validation ---
    @staticmethod
    def _is_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False
        if not self._is_number(weight_kg) or not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            return False
        if not self._is_number(distance_km) or not (
            DISTANCE_MIN <= distance_km <= DISTANCE_MAX
        ):
            return False
        if not self._is_number(declared_value) or not (
            VALUE_MIN <= declared_value <= VALUE_MAX
        ):
            return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Step 1: validate (DT-V)
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        # Step 2: store draft
        try:
            quote_id = self._quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self._screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage (DT-S note 5): price, hold, do not notify
            price = self._tariff_engine.price(weight_kg, distance_km)
            self._quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4-6: apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            # accept row: priced + notified
            price = self._tariff_engine.price(weight_kg, distance_km)
            self._quote_store.update_quote(quote_id, "quoted", price)
            self._fire_and_forget(
                self._notification_service.send_quote_document,
                shipper_id,
                quote_id,
                price,
            )
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # review row: no price, no notification
            self._quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # refuse row (risk_index >= REFUSE_MIN): no price, notified
        self._quote_store.update_quote(quote_id, "refused_screening")
        self._fire_and_forget(
            self._notification_service.send_refusal_notice, shipper_id, quote_id
        )
        return {"status": "refused_screening", "quote_id": quote_id}

    @staticmethod
    def _fire_and_forget(func, *args):
        # DT-S note 4: notification is fire-and-forget; failures never change outcome.
        try:
            func(*args)
        except Exception:
            pass


def handle(request: dict) -> dict:
    context = dict(request or {})

    tariff_engine = TariffEngine()
    quote_store = QuoteStore(context)
    screening_service = ScreeningService(context)
    notification_service = NotificationService(context)

    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)

    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    try:
        return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    except Exception as exc:  # defensive catch-all
        return {"status": "error: {}".format(exc)}
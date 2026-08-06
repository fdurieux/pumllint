"""Hand-written reference implementation of CargoQuote.

SMOKE-TEST ORACLE ONLY. This file exists so the acceptance suite
(tools/acceptance/cargo_quote_suite.py) can be exercised end-to-end
through the sandboxed runner before any API spend — the deterministic
half of the house calibration protocol. It is NEVER a generation
input, never part of any W1 condition, and must never appear in a
generation or repair prompt. Implements exactly the normative
semantics of contract/decision_table.md (DT-V, DT-S, DT-P) and
contract/spec.md.
"""

ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000

HEAVY_LIMIT_KG = 1244
HEAVY_SURCHARGE = 316.0
LONGHAUL_MIN_KM = 4912
LONGHAUL_FACTOR = 1.19


class ScreeningUnavailableError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class QuoteStore:
    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        return {"quote_id": "Q-1", "status": "stored"}

    def update_quote(self, quote_id, status, price=None):
        return {"quote_id": quote_id, "status": status, "price": price}


class TariffEngine:
    def price(self, weight_kg, distance_km):
        total = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > HEAVY_LIMIT_KG:
            total += HEAVY_SURCHARGE
        if distance_km >= LONGHAUL_MIN_KM:
            total *= LONGHAUL_FACTOR
        return round(total, 2)


class ScreeningService:
    def screen(self, shipper_id):
        return 8


class NotificationService:
    def send_quote_document(self, shipper_id, quote_id, price):
        return {"status": "sent"}

    def send_refusal_notice(self, shipper_id, quote_id):
        return {"status": "sent"}


def _quote_id_of(stored):
    if isinstance(stored, dict):
        return stored.get("quote_id") or "Q-1"
    return getattr(stored, "quote_id", None) or "Q-1"


class QuoteAPI:
    def __init__(self, quote_store=None, tariff_engine=None,
                 screening_service=None, notification_service=None):
        self.store = quote_store or QuoteStore()
        self.engine = tariff_engine or TariffEngine()
        self.screening = screening_service or ScreeningService()
        self.notifier = notification_service or NotificationService()

    def handle(self, request):
        shipper_id = request.get("shipper_id")
        weight = request.get("weight_kg")
        distance = request.get("distance_km")
        value = request.get("declared_value")

        reason = self._validate(shipper_id, weight, distance, value)
        if reason:
            return {"status": "rejected: invalid_request", "reason": reason}

        try:
            stored = self.store.store_draft(shipper_id, weight, distance, value)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}
        quote_id = _quote_id_of(stored)

        try:
            risk_index = self.screening.screen(shipper_id)
        except ScreeningUnavailableError:
            price = self.engine.price(weight, distance)
            self.store.update_quote(quote_id, "held_unscreened", price)
            return {"status": "held_unscreened", "price": price,
                    "hold": True, "quote_id": quote_id}

        if risk_index <= ACCEPT_MAX:
            price = self.engine.price(weight, distance)
            self.store.update_quote(quote_id, "quoted", price)
            try:
                self.notifier.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                pass  # DT-S note 4: delivery failure never changes the response
            return {"status": "quoted", "price": price, "quote_id": quote_id}

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        self.store.update_quote(quote_id, "refused_screening")
        try:
            self.notifier.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            pass
        return {"status": "refused_screening", "quote_id": quote_id}

    def _validate(self, shipper_id, weight, distance, value):
        if not shipper_id:
            return "shipper_id missing"
        if not isinstance(weight, (int, float)) or \
                not (WEIGHT_MIN <= weight <= WEIGHT_MAX):
            return "weight_kg out of bounds"
        if not isinstance(distance, (int, float)) or \
                not (DISTANCE_MIN <= distance <= DISTANCE_MAX):
            return "distance_km out of bounds"
        if not isinstance(value, (int, float)) or \
                not (VALUE_MIN <= value <= VALUE_MAX):
            return "declared_value out of bounds"
        return None


def handle(request):
    return QuoteAPI().handle(request)

from __future__ import annotations


class ScreeningError(Exception):
    """Raised when the external screening provider is unavailable."""


class StoreError(Exception):
    """Raised when the quote store is unavailable."""


class ScreeningService:
    """External denied-party screening provider (outside the system boundary)."""

    def __init__(self, risk_index: float = 0.0, available: bool = True):
        self._risk_index = risk_index
        self._available = available

    def screen(self, shipper_id):
        if not self._available:
            raise ScreeningError("screening_unavailable")
        return self._risk_index


class NotificationService:
    """External messaging provider (outside the system boundary)."""

    def __init__(self, deliver: bool = True):
        self._deliver = deliver

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        # Fire-and-forget: return a single confirmation value.
        return bool(self._deliver)

    def send_refusal_notice(self, shipper_id, quote_id):
        return bool(self._deliver)


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff."""

    BASE = 336.0
    PER_KG = 0.17
    PER_KM = 1.2

    def price(self, weight_kg, distance_km):
        amount = self.BASE + self.PER_KG * float(weight_kg) + self.PER_KM * float(distance_km)
        return round(amount, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available: bool = True):
        self._available = available
        self._seq = 0
        self._records = {}

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._available:
            raise StoreError("store_unavailable")
        self._seq += 1
        quote_id = f"Q-{self._seq}"
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
        record = self._records.get(quote_id)
        if record is not None:
            record["status"] = status
            record["price"] = price_amount
        return quote_id


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    # Screening thresholds (decision table DT-S)
    ACCEPT_MAX = 30
    REFUSE_MIN = 70

    # Validation bounds (decision table DT-V)
    MIN_WEIGHT = 50
    MAX_WEIGHT = 26000
    MIN_DISTANCE = 1
    MAX_DISTANCE = 3000

    def __init__(self, store: QuoteStore, screening: ScreeningService,
                 tariff: TariffEngine, notification: NotificationService):
        self._store = store
        self._screening = screening
        self._tariff = tariff
        self._notification = notification

    def _valid(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            return False
        try:
            w = float(weight_kg)
            d = float(distance_km)
            v = float(declared_value)
        except (TypeError, ValueError):
            return False
        if not (self.MIN_WEIGHT <= w <= self.MAX_WEIGHT):
            return False
        if not (self.MIN_DISTANCE <= d <= self.MAX_DISTANCE):
            return False
        if v <= 0:
            return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Validation (DT-V)
        if not self._valid(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        # Store draft
        try:
            quote_id = self._store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StoreError:
            return {"status": "error: store_unavailable"}

        # Screening
        try:
            risk_index = self._screening.screen(shipper_id)
        except ScreeningError:
            # Screening outage: price, hold, no notification (DT-S note 5)
            price_amount = self._tariff.price(weight_kg, distance_km)
            self._store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "price": price_amount,
                "hold": True,
                "quote_id": quote_id,
            }

        # Accept band
        if risk_index <= self.ACCEPT_MAX:
            price_amount = self._tariff.price(weight_kg, distance_km)
            self._store.update_quote(quote_id, "quoted", price_amount)
            self._notification.send_quote_document(shipper_id, quote_id, price_amount)
            return {"status": "quoted", "price": price_amount, "quote_id": quote_id}

        # Refuse band
        if risk_index >= self.REFUSE_MIN:
            self._store.update_quote(quote_id, "refused_screening")
            self._notification.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}

        # Review band (no pricing, no notification — DT-S note 1)
        self._store.update_quote(quote_id, "review_hold")
        return {"status": "review_hold", "quote_id": quote_id}


def _resolve_risk(request):
    """Return (available, risk_index) from request screening outcome keys."""
    status = request.get("screening_status")
    if isinstance(status, str) and status.lower() in ("error", "unavailable", "down", "timeout"):
        return False, 0.0

    raw = request.get("screening_result")
    if raw is None:
        raw = request.get("risk_index")

    if raw is None:
        return True, 0.0

    if isinstance(raw, (int, float)):
        return True, float(raw)

    if isinstance(raw, str):
        text = raw.strip().lower()
        if text in ("error", "unavailable", "down", "timeout"):
            return False, 0.0
        try:
            return True, float(text)
        except ValueError:
            pass
        mapping = {
            "approved": 10.0,
            "clear": 10.0,
            "active": 10.0,
            "accept": 10.0,
            "assessed": 50.0,
            "review": 50.0,
            "hold": 50.0,
            "declined": 90.0,
            "denied": 90.0,
            "refuse": 90.0,
            "refused": 90.0,
        }
        return True, mapping.get(text, 0.0)

    return True, 0.0


def handle(request: dict) -> dict:
    request = request or {}

    shipper_id = (request.get("shipper_id") or request.get("shipperId")
                  or request.get("shipper") or "SHIPPER-1")

    # Existence flags
    if request.get("shipper_exists") is False or request.get("shipper_found") is False:
        return {"status": "rejected: invalid_request"}

    def pick(*keys, default=None):
        for k in keys:
            if k in request and request[k] is not None:
                return request[k]
        return default

    weight_kg = pick("weight_kg", "weightKg", "weight", default=600)
    distance_km = pick("distance_km", "distanceKm", "distance", default=1200)
    declared_value = pick("declared_value", "declaredValue", "value", default=5000)

    # Store availability
    store_status = request.get("store_status") or request.get("store_result")
    store_available = not (isinstance(store_status, str)
                           and store_status.lower() in ("error", "unavailable", "down"))

    # Screening outcome
    screening_available, risk_index = _resolve_risk(request)

    # Notification outcome
    notif_status = request.get("notification_status") or request.get("notification_result")
    deliver = not (isinstance(notif_status, str)
                   and notif_status.lower() in ("error", "failed", "fail", "unavailable"))

    store = QuoteStore(available=store_available)
    screening = ScreeningService(risk_index=risk_index, available=screening_available)
    tariff = TariffEngine()
    notification = NotificationService(deliver=deliver)

    api = QuoteApi(store, screening, tariff, notification)

    try:
        return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": f"error: {exc}"}
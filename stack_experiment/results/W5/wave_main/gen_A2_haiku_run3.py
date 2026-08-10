from enum import Enum
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import uuid


class ValidationError(Exception):
    """Raised when quote request validation fails."""
    pass


class StorageError(Exception):
    """Raised when quote store operation fails."""
    pass


class ScreeningError(Exception):
    """Raised when screening service is unavailable."""
    pass


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price_amount: Optional[float] = None
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()


class QuoteStore:
    """Stores and retrieves quote records."""

    def __init__(self):
        self._quotes = {}
        self._available = True

    def set_availability(self, available: bool):
        """Control whether store is available (for testing/simulation)."""
        self._available = available

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its ID."""
        if not self._available:
            raise StorageError("Quote store unavailable")

        quote_id = str(uuid.uuid4())
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT
        )
        self._quotes[quote_id] = quote
        return quote_id

    def update_quote(self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None) -> Quote:
        """Update quote status and optionally price, returning updated quote."""
        if not self._available:
            raise StorageError("Quote store unavailable")

        if quote_id not in self._quotes:
            raise StorageError(f"Quote {quote_id} not found")

        quote = self._quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        quote.updated_at = datetime.utcnow()
        return quote

    def get_quote(self, quote_id: str) -> Optional[Quote]:
        """Retrieve a quote by ID."""
        return self._quotes.get(quote_id)


class TariffEngine:
    """Computes freight price from weight and distance."""

    def __init__(self):
        self._base_rate_per_kg_km = 0.05
        self._available = True

    def set_availability(self, available: bool):
        """Control whether engine is available (for testing/simulation)."""
        self._available = available

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute price for given weight and distance."""
        if not self._available:
            raise Exception("Tariff engine unavailable")

        base_price = weight_kg * distance_km * self._base_rate_per_kg_km
        minimum_charge = 50.0
        return max(base_price, minimum_charge)


class ScreeningService:
    """External denied-party screening provider."""

    def __init__(self):
        self._available = True
        self._risk_indices = {}

    def set_availability(self, available: bool):
        """Control whether service is available (for testing/simulation)."""
        self._available = available

    def set_risk_index(self, shipper_id: str, risk_index: float):
        """Set the risk index for a shipper (for testing/simulation)."""
        self._risk_indices[shipper_id] = risk_index

    def screen(self, shipper_id: str) -> float:
        """Return shipper risk index (0-100 scale)."""
        if not self._available:
            raise ScreeningError("Screening service unavailable")

        if shipper_id in self._risk_indices:
            return self._risk_indices[shipper_id]

        return 25.0


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def __init__(self):
        self._available = True
        self._sent_notifications = []

    def set_availability(self, available: bool):
        """Control whether service is available (for testing/simulation)."""
        self._available = available

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        """Send quote document to shipper (fire-and-forget, returns confirmation ID)."""
        if self._available:
            notification_id = str(uuid.uuid4())
            self._sent_notifications.append({
                "type": "quote_document",
                "shipper_id": shipper_id,
                "quote_id": quote_id,
                "price_amount": price_amount,
                "notification_id": notification_id
            })
            return notification_id
        return ""

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Send refusal notice to shipper (fire-and-forget, returns confirmation ID)."""
        if self._available:
            notification_id = str(uuid.uuid4())
            self._sent_notifications.append({
                "type": "refusal_notice",
                "shipper_id": shipper_id,
                "quote_id": quote_id,
                "notification_id": notification_id
            })
            return notification_id
        return ""

    def get_sent_notifications(self):
        """Retrieve sent notifications (for testing/simulation)."""
        return self._sent_notifications


class QuoteAPI:
    """Orchestrates quote request validation, screening, pricing, and storage."""

    ACCEPT_MAX = 30.0
    REVIEW_MIN = 31.0
    REVIEW_MAX = 69.0
    REFUSE_MIN = 70.0

    def __init__(self, quote_store: QuoteStore, tariff_engine: TariffEngine,
                 screening_service: ScreeningService, notification_service: NotificationService):
        self.quote_store = quote_store
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> bool:
        """Validate quote request bounds per decision table DT-V."""
        if shipper_id is None or not str(shipper_id).strip():
            return False
        try:
            w = float(weight_kg)
            d = float(distance_km)
            v = float(declared_value)
        except (TypeError, ValueError):
            return False
        
        if w <= 0 or w > 50000:
            return False
        if d <= 0 or d > 10000:
            return False
        if v < 0 or v > 1000000:
            return False
        return True

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        """Main quote request handler."""
        try:
            if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
                return {"status": "rejected_invalid_request"}

            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)

            try:
                risk_index = self.screening_service.screen(shipper_id)
            except ScreeningError:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
                return {"status": "held_unscreened", "quote_id": quote_id, "price": price_amount}

            if risk_index <= self.ACCEPT_MAX:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
                self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
                return {"status": "quoted", "quote_id": quote_id, "price": price_amount}

            elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
                return {"status": "review_hold", "quote_id": quote_id}

            elif risk_index >= self.REFUSE_MIN:
                self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
                return {"status": "refused_screening", "quote_id": quote_id}

        except StorageError as e:
            return {"status": f"error: {str(e)}"}
        except Exception as e:
            return {"status": f"error: {str(e)}"}

        return {"status": "error: unknown"}


_quote_store = QuoteStore()
_tariff_engine = TariffEngine()
_screening_service = ScreeningService()
_notification_service = NotificationService()
_quote_api = QuoteAPI(_quote_store, _tariff_engine, _screening_service, _notification_service)


def handle(request: dict) -> dict:
    """
    Main entry point for quote request handling.
    
    Expected request keys:
    - shipper_id: str
    - weight_kg: float
    - distance_km: float
    - declared_value: float
    - (optional) store_exists: bool (controls store availability)
    - (optional) tariff_engine_exists: bool (controls engine availability)
    - (optional) screening_service_result: float (overrides risk index)
    - (optional) screening_service_status: "error" (simulates service unavailability)
    - (optional) notification_service_exists: bool (controls notification availability)
    
    Returns dict with "status" key and optional "quote_id" and "price" keys.
    """
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    if "store_exists" in request:
        _quote_store.set_availability(request["store_exists"])
    else:
        _quote_store.set_availability(True)

    if "tariff_engine_exists" in request:
        _tariff_engine.set_availability(request["tariff_engine_exists"])
    else:
        _tariff_engine.set_availability(True)

    if "notification_service_exists" in request:
        _notification_service.set_availability(request["notification_service_exists"])
    else:
        _notification_service.set_availability(True)

    if request.get("screening_service_status") == "error":
        _screening_service.set_availability(False)
    else:
        _screening_service.set_availability(True)

    if "screening_service_result" in request:
        _screening_service.set_risk_index(shipper_id, request["screening_service_result"])

    result = _quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    return result
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime
import uuid


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
    pass


@dataclass
class QuoteRecord:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price: Optional[float] = None
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow().isoformat()


class QuoteStore:
    """PostgreSQL 16 quote storage."""

    def __init__(self):
        self._quotes: dict[str, QuoteRecord] = {}
        self._available = True

    def set_available(self, available: bool):
        """Control availability for testing."""
        self._available = available

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        """Store a draft quote. Returns quote_id or raises StorageError."""
        if not self._available:
            raise StorageError("store_unavailable")

        quote_id = str(uuid.uuid4())
        record = QuoteRecord(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT,
        )
        self._quotes[quote_id] = record
        return quote_id

    def update_quote(
        self, quote_id: str, status: QuoteStatus, price: Optional[float] = None
    ) -> QuoteRecord:
        """Update quote status and optionally price. Returns updated record."""
        if quote_id not in self._quotes:
            raise StorageError(f"quote_not_found: {quote_id}")

        record = self._quotes[quote_id]
        record.status = status
        if price is not None:
            record.price = price
        record.updated_at = datetime.utcnow().isoformat()
        return record

    def get_quote(self, quote_id: str) -> Optional[QuoteRecord]:
        """Retrieve a quote record."""
        return self._quotes.get(quote_id)


class ScreeningService:
    """External denied-party screening provider."""

    def __init__(self):
        self._available = True
        self._risk_index = 30

    def set_available(self, available: bool):
        """Control availability for testing."""
        self._available = available

    def set_risk_index(self, risk_index: int):
        """Set the risk index to return for testing."""
        self._risk_index = risk_index

    def screen(self, shipper_id: str) -> int:
        """Return shipper risk index. Higher is worse. Raises ScreeningError on unavailability."""
        if not self._available:
            raise ScreeningError("screening_unavailable")
        return self._risk_index


class TariffEngine:
    """Pricing computation against the tariff."""

    def __init__(self):
        self._available = True

    def set_available(self, available: bool):
        """Control availability for testing."""
        self._available = available

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute freight price from weight and distance. Returns price in EUR."""
        if not self._available:
            raise Exception("tariff_engine_unavailable")

        base_rate = 50.0
        weight_rate = 2.5
        distance_rate = 0.8

        price = base_rate + (weight_kg * weight_rate) + (distance_km * distance_rate)
        return round(price, 2)


class NotificationService:
    """External messaging provider."""

    def __init__(self):
        self._available = True
        self._last_notification = None

    def set_available(self, available: bool):
        """Control availability for testing."""
        self._available = available

    def get_last_notification(self) -> Optional[dict]:
        """Get the last notification sent (for testing)."""
        return self._last_notification

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        """Send quote document. Fire-and-forget; returns 'sent' or 'failed'."""
        if not self._available:
            result = "failed"
        else:
            result = "sent"

        self._last_notification = {
            "type": "quote_document",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
            "price": price,
            "result": result,
        }
        return result

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Send refusal notice. Fire-and-forget; returns 'sent' or 'failed'."""
        if not self._available:
            result = "failed"
        else:
            result = "sent"

        self._last_notification = {
            "type": "refusal_notice",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
            "result": result,
        }
        return result


class QuoteAPI:
    """Quote API: validates, orchestrates screening and pricing, returns outcome."""

    VALIDATION_MIN_WEIGHT = 1.0
    VALIDATION_MAX_WEIGHT = 24000.0
    VALIDATION_MIN_DISTANCE = 1.0
    VALIDATION_MAX_DISTANCE = 2000.0
    VALIDATION_MIN_VALUE = 1.0
    VALIDATION_MAX_VALUE = 500000.0

    SCREENING_ACCEPT_MAX = 49
    SCREENING_REVIEW_MIN = 50
    SCREENING_REVIEW_MAX = 74
    SCREENING_REFUSE_MIN = 75

    def __init__(
        self,
        quote_store: QuoteStore,
        screening_service: ScreeningService,
        tariff_engine: TariffEngine,
        notification_service: NotificationService,
    ):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate_request(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> bool:
        """Validate request against DT-V bounds."""
        if not shipper_id or not isinstance(shipper_id, str):
            return False
        if not isinstance(weight_kg, (int, float)) or weight_kg < self.VALIDATION_MIN_WEIGHT or weight_kg > self.VALIDATION_MAX_WEIGHT:
            return False
        if not isinstance(distance_km, (int, float)) or distance_km < self.VALIDATION_MIN_DISTANCE or distance_km > self.VALIDATION_MAX_DISTANCE:
            return False
        if not isinstance(declared_value, (int, float)) or declared_value < self.VALIDATION_MIN_VALUE or declared_value > self.VALIDATION_MAX_VALUE:
            return False
        return True

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        """Process a quote request. Returns response dict with status and optionally quote_id, price, hold."""

        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StorageError:
            return {"status": "error: store_unavailable"}

        risk_index = None
        screening_failed = False

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            screening_failed = True

        price = None
        notify = False
        final_status = None

        if screening_failed:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, QuoteStatus.HELD_UNSCREENED, price
            )
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        if risk_index <= self.SCREENING_ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price)
            notify = True
            final_status = "quoted"
        elif self.SCREENING_REVIEW_MIN <= risk_index <= self.SCREENING_REVIEW_MAX:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            final_status = "review_hold"
        elif risk_index >= self.SCREENING_REFUSE_MIN:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            notify = True
            final_status = "refused_screening"

        if notify:
            if final_status == "quoted":
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            elif final_status == "refused_screening":
                self.notification_service.send_refusal_notice(shipper_id, quote_id)

        response = {
            "status": final_status,
            "quote_id": quote_id,
        }
        if price is not None:
            response["price"] = price

        return response


_quote_store = QuoteStore()
_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_notification_service = NotificationService()
_quote_api = QuoteAPI(
    _quote_store, _screening_service, _tariff_engine, _notification_service
)


def handle(request: dict) -> dict:
    """
    Handle a quote request. Process the request dict and return the outcome.

    Request keys:
    - shipper_id, weight_kg, distance_km, declared_value: standard quote fields
    - screening_result: override the screening service result
      (e.g. "approved", "review", "declined", or a number for risk_index)
    - store_result: set quote store availability ("available" or "unavailable")
    - notification_result: set notification service availability
    - tariff_result: set tariff engine availability

    Returns dict with "status" and optionally "quote_id", "price", "hold".
    """
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    if "store_result" in request:
        _quote_store.set_available(request["store_result"] != "unavailable")

    if "screening_result" in request:
        screening_result = request["screening_result"]
        if isinstance(screening_result, int):
            _screening_service.set_risk_index(screening_result)
            _screening_service.set_available(True)
        elif screening_result == "approved":
            _screening_service.set_risk_index(25)
            _screening_service.set_available(True)
        elif screening_result == "review":
            _screening_service.set_risk_index(60)
            _screening_service.set_available(True)
        elif screening_result == "declined":
            _screening_service.set_risk_index(80)
            _screening_service.set_available(True)
        elif screening_result == "error":
            _screening_service.set_available(False)

    if "notification_result" in request:
        _notification_service.set_available(request["notification_result"] != "error")

    if "tariff_result" in request:
        _tariff_engine.set_available(request["tariff_result"] != "error")

    response = _quote_api.request_quote(
        shipper_id, weight_kg, distance_km, declared_value
    )

    _quote_store.set_available(True)
    _screening_service.set_available(True)
    _screening_service.set_risk_index(30)
    _notification_service.set_available(True)
    _tariff_engine.set_available(True)

    return response
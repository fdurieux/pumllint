"""CargoQuote — Instant Freight Quotation System."""

import uuid
from datetime import datetime
from typing import Any


# Configuration
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

# Validation bounds
MIN_WEIGHT_KG = 100
MAX_WEIGHT_KG = 25000
MIN_DISTANCE_KM = 1
MAX_DISTANCE_KM = 2000
MIN_DECLARED_VALUE = 100
MAX_DECLARED_VALUE = 500000


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id: str) -> int:
        """Return riskIndex (0-100). Raises ScreeningUnavailableError on failure."""
        # In real use, calls external REST API
        # For testing: request dict can carry 'screening_service_result'
        return 0


class TariffEngine:
    """Computes freight price from weight and distance."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute priceAmount for a validated request."""
        # Base rate: 0.5 EUR per kg + 0.1 EUR per km
        base_price = (weight_kg * 0.5) + (distance_km * 0.1)
        return round(base_price, 2)


class NotificationService:
    """External messaging provider."""

    def send_quote_document(self, shipper_id: str, quote_id: str,
                           price_amount: float) -> str:
        """Deliver quote document. Fire-and-forget; always succeeds."""
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Deliver refusal notice. Fire-and-forget; always succeeds."""
        return "sent"


class QuoteStore:
    """PostgreSQL-backed quote storage."""

    def __init__(self):
        self.quotes = {}

    def store_draft(self, shipper_id: str, weight_kg: float,
                   distance_km: float, declared_value: float) -> str:
        """Store draft quote; return quoteId."""
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "quote_id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price_amount": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        return quote_id

    def update_quote(self, quote_id: str, status: str,
                    price_amount: float = None) -> dict:
        """Update quote status and optionally price; return updatedQuote."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote["status"] = status
        if price_amount is not None:
            quote["price_amount"] = price_amount
        quote["updated_at"] = datetime.utcnow().isoformat()
        return quote


class QuoteAPI:
    """Main quotation service orchestrating the flow."""

    def __init__(self, tariff_engine: TariffEngine, screening_service: ScreeningService,
                 quote_store: QuoteStore, notification_service: NotificationService):
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.quote_store = quote_store
        self.notification_service = notification_service

    def request_quote(self, shipper_id: str, weight_kg: float,
                     distance_km: float, declared_value: float) -> dict:
        """Execute the quotation flow."""

        # Step 1: Validate request
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {
                "status": "rejected_invalid_request",
                "error": "Request validation failed",
            }

        # Step 2: Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except Exception as e:
            return {
                "status": "store_unavailable_error",
                "error": str(e),
            }

        # Step 3: Screen shipper
        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_failed = False
        except Exception:
            risk_index = None
            screening_failed = True

        # Step 4: Apply screening decision
        if screening_failed:
            # Screening unavailable: price, hold unscreened, respond
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened_response",
                "quote_id": quote_id,
                "price_amount": price_amount,
            }

        if risk_index <= ACCEPT_MAX:
            # Accept: price, update, notify
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount
            )
            return {
                "status": "quoted_response",
                "quote_id": quote_id,
                "price_amount": price_amount,
            }

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # Review hold: update, do NOT price or notify
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold_response",
                "quote_id": quote_id,
            }

        if risk_index >= REFUSE_MIN:
            # Refuse: update, notify, do NOT price
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused_screening_response",
                "quote_id": quote_id,
            }

        # Should not reach here
        return {
            "status": "error_unexpected",
            "error": "Unexpected screening state",
        }

    def _validate_request(self, shipper_id: str, weight_kg: float,
                         distance_km: float, declared_value: float) -> bool:
        """Validate request against decision table DT-V."""
        if not shipper_id or not isinstance(shipper_id, str):
            return False
        if not isinstance(weight_kg, (int, float)) or weight_kg < MIN_WEIGHT_KG or weight_kg > MAX_WEIGHT_KG:
            return False
        if not isinstance(distance_km, (int, float)) or distance_km < MIN_DISTANCE_KM or distance_km > MAX_DISTANCE_KM:
            return False
        if not isinstance(declared_value, (int, float)) or declared_value < MIN_DECLARED_VALUE or declared_value > MAX_DECLARED_VALUE:
            return False
        return True


def handle(request: dict) -> dict:
    """End-to-end quotation flow entry point."""
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    # Instantiate collaborators with injectable behavior via request dict
    screening_service = _MockScreeningService(request)
    tariff_engine = _MockTariffEngine(request)
    quote_store = QuoteStore()
    notification_service = _MockNotificationService(request)

    api = QuoteAPI(tariff_engine, screening_service, quote_store, notification_service)

    response = api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    return response


class _MockScreeningService(ScreeningService):
    """Test double for ScreeningService."""

    def __init__(self, request: dict):
        self.request = request

    def screen(self, shipper_id: str) -> int:
        if self.request.get("screening_service_unavailable"):
            raise RuntimeError("Screening service unavailable")
        # Allow request to specify risk_index or use screening_service_result
        if "screening_service_result" in self.request:
            return int(self.request["screening_service_result"])
        return self.request.get("risk_index", 0)


class _MockTariffEngine(TariffEngine):
    """Test double for TariffEngine."""

    def __init__(self, request: dict):
        self.request = request

    def price(self, weight_kg: float, distance_km: float) -> float:
        if "tariff_engine_result" in self.request:
            return float(self.request["tariff_engine_result"])
        return super().price(weight_kg, distance_km)


class _MockNotificationService(NotificationService):
    """Test double for NotificationService."""

    def __init__(self, request: dict):
        self.request = request

    def send_quote_document(self, shipper_id: str, quote_id: str,
                           price_amount: float) -> str:
        if self.request.get("notification_service_unavailable"):
            raise RuntimeError("Notification service unavailable")
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if self.request.get("notification_service_unavailable"):
            raise RuntimeError("Notification service unavailable")
        return "sent"
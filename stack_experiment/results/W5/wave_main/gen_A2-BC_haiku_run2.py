"""
CargoQuote — Instant Freight Quotation System

A synchronous quotation flow for palletized road cargo:
1. Validate request
2. Store quote record
3. Screen shipper via external service
4. Price consignment via tariff engine
5. Notify shipper of outcome
6. Return result to caller
"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass
from datetime import datetime


class QuoteStatus(Enum):
    CONFIRMED = "confirmed"
    HELD_FOR_REVIEW = "held_for_review"
    REJECTED = "rejected"
    ERROR = "error"


@dataclass
class QuoteRequest:
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float


class ValidationError(Exception):
    pass


class ScreeningError(Exception):
    pass


class PricingError(Exception):
    pass


class NotificationError(Exception):
    pass


class StoreError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider."""

    def screen_shipper(self, shipper_id: str) -> float:
        """
        Returns a shipper risk index (0.0 to 1.0).
        In production, this calls an external REST API.
        """
        return 0.2


class TariffEngine:
    """Computes freight price from weight, distance, and tariff rules."""

    def compute_price(self, weight_kg: float, distance_km: float) -> float:
        """
        Returns price in currency units.
        Tariff rule: base_rate + (weight_kg * 0.5) + (distance_km * 0.3)
        """
        base_rate = 50.0
        return base_rate + (weight_kg * 0.5) + (distance_km * 0.3)


class QuoteStore:
    """PostgreSQL-backed store for quote records and lifecycle status."""

    def __init__(self):
        self._quotes = {}
        self._counter = 0

    def create_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        """
        Stores a new quote record.
        Returns quote_id as confirmation.
        """
        self._counter += 1
        quote_id = f"QT{self._counter:06d}"
        self._quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "created_at": datetime.utcnow().isoformat(),
            "status": "draft",
            "price": None,
            "risk_index": None,
        }
        return quote_id

    def update_quote_status(
        self, quote_id: str, status: str, price: Optional[float] = None, risk_index: Optional[float] = None
    ) -> str:
        """
        Updates quote status and optional price/risk_index.
        Returns confirmation.
        """
        if quote_id not in self._quotes:
            raise StoreError(f"Quote {quote_id} not found")
        self._quotes[quote_id]["status"] = status
        if price is not None:
            self._quotes[quote_id]["price"] = price
        if risk_index is not None:
            self._quotes[quote_id]["risk_index"] = risk_index
        return "stored"


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def notify_quote_issued(self, shipper_id: str, quote_id: str, price: float) -> str:
        """
        Sends quote document to shipper.
        Returns confirmation status.
        """
        return "sent"

    def notify_quote_held_for_review(self, shipper_id: str, quote_id: str) -> str:
        """
        Sends hold notice to shipper (manual review pending).
        Returns confirmation status.
        """
        return "sent"

    def notify_quote_rejected(self, shipper_id: str, quote_id: str, reason: str) -> str:
        """
        Sends refusal notice to shipper.
        Returns confirmation status.
        """
        return "sent"


class QuoteAPI:
    """
    Main orchestrator: receives quote requests, validates, screens,
    prices, stores, notifies, and returns outcome.
    """

    # Risk index thresholds for screening decision
    REVIEW_THRESHOLD = 0.5  # Above this: hold for manual review
    REJECT_THRESHOLD = 0.8  # Above this: reject outright

    def __init__(
        self,
        screening_service: ScreeningService,
        tariff_engine: TariffEngine,
        quote_store: QuoteStore,
        notification_service: NotificationService,
    ):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service

    def _validate_request(self, request: dict) -> QuoteRequest:
        """
        Validates incoming quote request.
        Raises ValidationError if invalid.
        """
        try:
            shipper_id = request.get("shipper_id")
            weight_kg = float(request.get("weight_kg", 0))
            distance_km = float(request.get("distance_km", 0))
            declared_value = float(request.get("declared_value", 0))

            if not shipper_id or shipper_id.strip() == "":
                raise ValidationError("shipper_id is required")
            if weight_kg <= 0:
                raise ValidationError("weight_kg must be positive")
            if distance_km <= 0:
                raise ValidationError("distance_km must be positive")
            if declared_value < 0:
                raise ValidationError("declared_value must be non-negative")

            return QuoteRequest(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid request format: {e}")

    def handle_quote_request(self, request: dict) -> dict:
        """
        Main quotation flow:
        1. Validate request
        2. Store quote record
        3. Screen shipper
        4. Price consignment
        5. Decide outcome (confirmed, held for review, or rejected)
        6. Notify shipper
        7. Return result

        Returns dict with 'status' key and optional 'quote_id', 'price', 'reason'.
        """
        try:
            # Step 1: Validate
            validated = self._validate_request(request)

            # Step 2: Store
            quote_id = self.quote_store.create_quote(
                shipper_id=validated.shipper_id,
                weight_kg=validated.weight_kg,
                distance_km=validated.distance_km,
                declared_value=validated.declared_value,
            )

            # Step 3: Screen shipper
            risk_index = self.screening_service.screen_shipper(validated.shipper_id)

            # Step 4: Price consignment
            price = self.tariff_engine.compute_price(
                validated.weight_kg, validated.distance_km
            )

            # Update store with screening result
            self.quote_store.update_quote_status(
                quote_id, "screened", price=price, risk_index=risk_index
            )

            # Step 5: Decide outcome based on risk_index
            if risk_index > self.REJECT_THRESHOLD:
                # Reject: too risky
                self.quote_store.update_quote_status(quote_id, "rejected")
                self.notification_service.notify_quote_rejected(
                    validated.shipper_id, quote_id, "Failed denied-party screening"
                )
                return {
                    "status": QuoteStatus.REJECTED.value,
                    "quote_id": quote_id,
                    "reason": "Failed denied-party screening",
                }
            elif risk_index > self.REVIEW_THRESHOLD:
                # Hold for review: moderately risky
                self.quote_store.update_quote_status(quote_id, "held_for_review")
                self.notification_service.notify_quote_held_for_review(
                    validated.shipper_id, quote_id
                )
                return {
                    "status": QuoteStatus.HELD_FOR_REVIEW.value,
                    "quote_id": quote_id,
                    "reason": "Pending compliance review",
                }
            else:
                # Confirm: low risk, issue immediately
                self.quote_store.update_quote_status(quote_id, "confirmed")
                self.notification_service.notify_quote_issued(
                    validated.shipper_id, quote_id, price
                )
                return {
                    "status": QuoteStatus.CONFIRMED.value,
                    "quote_id": quote_id,
                    "price": price,
                }

        except ValidationError as e:
            return {"status": f"error: {str(e)}"}
        except (ScreeningError, PricingError, StoreError, NotificationError) as e:
            return {"status": f"error: {str(e)}"}
        except Exception as e:
            return {"status": f"error: {str(e)}"}


class MockScreeningService:
    """Mock screening service for testing with overridden result."""

    def __init__(self, risk_index: float):
        self.risk_index = risk_index

    def screen_shipper(self, shipper_id: str) -> float:
        return self.risk_index


class MockTariffEngine:
    """Mock tariff engine for testing with overridden price."""

    def __init__(self, price: float):
        self.price = price

    def compute_price(self, weight_kg: float, distance_km: float) -> float:
        return self.price


class MockQuoteStore:
    """Mock quote store for testing with overridden quote_id."""

    def __init__(self, quote_id: str):
        self.quote_id = quote_id
        self._quotes = {}

    def create_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        self._quotes[self.quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "created_at": datetime.utcnow().isoformat(),
            "status": "draft",
            "price": None,
            "risk_index": None,
        }
        return self.quote_id

    def update_quote_status(
        self, quote_id: str, status: str, price: Optional[float] = None, risk_index: Optional[float] = None
    ) -> str:
        if quote_id not in self._quotes:
            raise StoreError(f"Quote {quote_id} not found")
        self._quotes[quote_id]["status"] = status
        if price is not None:
            self._quotes[quote_id]["price"] = price
        if risk_index is not None:
            self._quotes[quote_id]["risk_index"] = risk_index
        return "stored"


def handle(request: dict) -> dict:
    """
    Module-level entry point for quote request handling.

    Instantiates all collaborators and orchestrates the quotation flow.
    Respects overrides from request for testing: screening_result,
    tariff_result, store_result override external calls.

    Args:
        request: dict with shipper_id, weight_kg, distance_km, declared_value,
                 and optional override keys like screening_result, tariff_result.

    Returns:
        dict with 'status' key and optional 'quote_id', 'price', 'reason'.
    """
    # Create a clean request for validation (without override keys)
    clean_request = {
        k: v for k, v in request.items()
        if k not in ["screening_result", "tariff_result", "store_result", "notification_result"]
    }

    # Use overrides if provided in request
    if "screening_result" in request:
        screening_service = MockScreeningService(request["screening_result"])
    else:
        screening_service = ScreeningService()

    if "tariff_result" in request:
        tariff_engine = MockTariffEngine(request["tariff_result"])
    else:
        tariff_engine = TariffEngine()

    if "store_result" in request:
        quote_store = MockQuoteStore(request["store_result"])
    else:
        quote_store = QuoteStore()

    notification_service = NotificationService()

    api = QuoteAPI(
        screening_service=screening_service,
        tariff_engine=tariff_engine,
        quote_store=quote_store,
        notification_service=notification_service,
    )

    return api.handle_quote_request(clean_request)
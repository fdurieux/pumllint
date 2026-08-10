import json
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional


class QuoteStatus(Enum):
    PENDING = "pending"
    ISSUED = "issued"
    HELD_FOR_REVIEW = "held_for_review"
    REFUSED = "refused"


@dataclass
class QuoteRequest:
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price: Optional[float] = None
    risk_index: Optional[float] = None


class ScreeningService:
    """External denied-party screening provider."""

    def screen_shipper(self, shipper_id: str) -> float:
        """
        Screen a shipper and return a risk index.
        Returns a float between 0.0 and 1.0 where:
        - 0.0-0.3: low risk
        - 0.3-0.7: medium risk (requires review)
        - 0.7-1.0: high risk (refuse)
        """
        return 0.5


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules."""

    def compute_price(self, weight_kg: float, distance_km: float) -> float:
        """
        Compute price for a consignment.
        Base rate: 0.50 per kg, 0.10 per km.
        """
        base_rate_per_kg = 0.50
        distance_rate_per_km = 0.10
        price = (weight_kg * base_rate_per_kg) + (distance_km * distance_rate_per_km)
        return round(price, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self.quotes = {}
        self.next_quote_id = 1

    def create_quote(self, request: QuoteRequest) -> str:
        """Create and store a new quote, return quote_id."""
        quote_id = f"Q{self.next_quote_id:06d}"
        self.next_quote_id += 1
        quote = Quote(
            quote_id=quote_id,
            shipper_id=request.shipper_id,
            weight_kg=request.weight_kg,
            distance_km=request.distance_km,
            declared_value=request.declared_value,
            status=QuoteStatus.PENDING,
        )
        self.quotes[quote_id] = quote
        return quote_id

    def update_quote(
        self, quote_id: str, status: QuoteStatus, price: Optional[float] = None,
        risk_index: Optional[float] = None
    ) -> str:
        """Update quote status and optional price/risk_index, return confirmation."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price is not None:
            quote.price = price
        if risk_index is not None:
            quote.risk_index = risk_index
        return quote_id

    def get_quote(self, quote_id: str) -> Quote:
        """Retrieve a quote by ID."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        return self.quotes[quote_id]


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        """Send issued quote document to shipper."""
        return f"notification_sent_{quote_id}"

    def send_refusal_notice(self, shipper_id: str, quote_id: str, reason: str) -> str:
        """Send refusal notice to shipper."""
        return f"refusal_sent_{quote_id}"


class QuoteAPI:
    """
    Main API orchestrating quote requests.
    Validates requests, screens shippers, prices consignments, and returns outcomes.
    """

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

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        """
        Process a quote request end-to-end.
        
        Flow:
        1. Validate request
        2. Create quote record
        3. Screen shipper
        4. Price consignment
        5. Determine outcome based on risk
        6. Send notification
        7. Return result
        """
        # Validate request
        if not shipper_id or weight_kg <= 0 or distance_km <= 0 or declared_value <= 0:
            return {
                "status": "error: invalid_request",
                "message": "Missing or invalid shipper_id, weight_kg, distance_km, or declared_value",
            }

        # Create quote record
        request = QuoteRequest(
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
        )
        quote_id = self.quote_store.create_quote(request)

        # Screen shipper
        try:
            risk_index = self.screening_service.screen_shipper(shipper_id)
        except Exception as e:
            self.quote_store.update_quote(
                quote_id, QuoteStatus.REFUSED, risk_index=None
            )
            return {
                "status": "error: screening_failed",
                "message": str(e),
            }

        # Price consignment
        try:
            price = self.tariff_engine.compute_price(weight_kg, distance_km)
        except Exception as e:
            self.quote_store.update_quote(
                quote_id, QuoteStatus.REFUSED, risk_index=risk_index
            )
            return {
                "status": "error: pricing_failed",
                "message": str(e),
            }

        # Determine outcome based on risk index
        if risk_index < 0.3:
            # Low risk: issue immediately
            status = QuoteStatus.ISSUED
            notification_result = self.notification_service.send_quote_document(
                shipper_id, quote_id, price
            )
            self.quote_store.update_quote(
                quote_id, status, price=price, risk_index=risk_index
            )
            return {
                "status": "confirmed",
                "quote_id": quote_id,
                "price": price,
                "message": "Quote issued immediately",
            }
        elif risk_index < 0.7:
            # Medium risk: hold for review
            status = QuoteStatus.HELD_FOR_REVIEW
            self.quote_store.update_quote(
                quote_id, status, price=price, risk_index=risk_index
            )
            return {
                "status": "held_for_review",
                "quote_id": quote_id,
                "price": price,
                "message": "Quote held for compliance review",
            }
        else:
            # High risk: refuse
            status = QuoteStatus.REFUSED
            notification_result = self.notification_service.send_refusal_notice(
                shipper_id, quote_id, "High-risk shipper"
            )
            self.quote_store.update_quote(
                quote_id, status, risk_index=risk_index
            )
            return {
                "status": "rejected",
                "quote_id": quote_id,
                "message": "Quote refused due to shipper risk assessment",
            }


def handle(request: dict) -> dict:
    """
    Handle a quote request end-to-end.
    
    Expected request keys:
    - shipper_id: str
    - weight_kg: float
    - distance_km: float
    - declared_value: float
    - screening_service_result: optional float (overrides service)
    - tariff_engine_result: optional float (overrides service)
    - notification_service_result: optional str (overrides service)
    """
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    # Initialize services
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()

    # Override service results if provided in request
    if "screening_service_result" in request:
        original_screen = screening_service.screen_shipper
        screening_service.screen_shipper = (
            lambda shipper_id: request["screening_service_result"]
        )

    if "tariff_engine_result" in request:
        original_compute = tariff_engine.compute_price
        tariff_engine.compute_price = (
            lambda weight_kg, distance_km: request["tariff_engine_result"]
        )

    if "notification_service_result" in request:
        original_send_doc = notification_service.send_quote_document
        original_send_ref = notification_service.send_refusal_notice
        notification_service.send_quote_document = (
            lambda shipper_id, quote_id, price: request["notification_service_result"]
        )
        notification_service.send_refusal_notice = (
            lambda shipper_id, quote_id, reason: request["notification_service_result"]
        )

    # Create API and process request
    api = QuoteAPI(
        screening_service, tariff_engine, quote_store, notification_service
    )

    result = api.request_quote(shipper_id, weight_kg, distance_km, declared_value)

    return result
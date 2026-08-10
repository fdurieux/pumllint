import json
from datetime import datetime
from typing import Optional
from enum import Enum


class ScreeningRiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class QuoteStatus(Enum):
    CONFIRMED = "confirmed"
    HELD_FOR_REVIEW = "held_for_review"
    REJECTED = "rejected"


class ExternalScreeningProvider:
    """External denied-party screening service."""
    
    def screen_shipper(self, shipper_id: str) -> str:
        """
        Returns risk level as a string: 'low', 'medium', or 'high'.
        """
        return "low"


class TariffEngine:
    """Computes price based on consignment parameters."""
    
    def calculate_price(
        self,
        weight_kg: float,
        distance_km: float,
        declared_value: float
    ) -> float:
        """
        Returns price as a single float value.
        Base rate: 0.5 per km + 0.1 per kg + 1% of declared value.
        """
        base_charge = distance_km * 0.5
        weight_charge = weight_kg * 0.1
        value_charge = declared_value * 0.01
        return base_charge + weight_charge + value_charge


class QuoteStore:
    """Persists quote requests and issued quotes."""
    
    def __init__(self):
        self.quotes = {}
        self.next_id = 1000
    
    def store_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
        price: float,
        status: str
    ) -> str:
        """
        Stores quote and returns confirmation ID.
        """
        quote_id = f"Q{self.next_id}"
        self.next_id += 1
        self.quotes[quote_id] = {
            "id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "price": price,
            "status": status,
            "created_at": datetime.utcnow().isoformat()
        }
        return quote_id


class NotificationProvider:
    """External notification service for sending documents."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        """
        Sends issued quote document. Returns delivery confirmation.
        """
        return "delivered"
    
    def send_refusal_notice(self, shipper_id: str, reason: str) -> str:
        """
        Sends refusal notice. Returns delivery confirmation.
        """
        return "delivered"
    
    def send_review_notice(self, shipper_id: str, quote_id: str) -> str:
        """
        Sends notice that quote is held for manual review.
        Returns delivery confirmation.
        """
        return "delivered"


class QuoteValidator:
    """Validates quote request parameters."""
    
    def validate_request(
        self,
        shipper_id: Optional[str],
        weight_kg: Optional[float],
        distance_km: Optional[float],
        declared_value: Optional[float]
    ) -> None:
        """
        Raises ValueError if validation fails.
        """
        if not shipper_id:
            raise ValueError("shipper_id is required")
        if weight_kg is None or weight_kg <= 0:
            raise ValueError("weight_kg must be positive")
        if distance_km is None or distance_km <= 0:
            raise ValueError("distance_km must be positive")
        if declared_value is None or declared_value < 0:
            raise ValueError("declared_value must be non-negative")


class CargoQuote:
    """Main quotation engine orchestrating the flow."""
    
    def __init__(
        self,
        screening_provider: Optional[ExternalScreeningProvider] = None,
        tariff_engine: Optional[TariffEngine] = None,
        quote_store: Optional[QuoteStore] = None,
        notification_provider: Optional[NotificationProvider] = None,
        validator: Optional[QuoteValidator] = None
    ):
        self.screening_provider = screening_provider or ExternalScreeningProvider()
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.notification_provider = notification_provider or NotificationProvider()
        self.validator = validator or QuoteValidator()
    
    def process_quote_request(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float
    ) -> dict:
        """
        Main flow:
        1. Validate request
        2. Screen shipper (external)
        3. Price consignment (internal)
        4. Apply screening rules
        5. Store quote
        6. Send notification
        7. Return outcome
        """
        try:
            # Step 1: Validate request
            self.validator.validate_request(
                shipper_id,
                weight_kg,
                distance_km,
                declared_value
            )
            
            # Step 2: Screen shipper
            risk_level = self.screening_provider.screen_shipper(shipper_id)
            
            # Step 3: Price consignment
            price = self.tariff_engine.calculate_price(
                weight_kg,
                distance_km,
                declared_value
            )
            
            # Step 4: Apply screening rules to determine quote status
            if risk_level == ScreeningRiskLevel.HIGH.value:
                # High risk: reject immediately
                quote_status = QuoteStatus.REJECTED.value
            elif risk_level == ScreeningRiskLevel.MEDIUM.value:
                # Medium risk: hold for manual review
                quote_status = QuoteStatus.HELD_FOR_REVIEW.value
            else:
                # Low risk: confirm immediately
                quote_status = QuoteStatus.CONFIRMED.value
            
            # Step 5: Store quote
            quote_id = self.quote_store.store_quote(
                shipper_id,
                weight_kg,
                distance_km,
                declared_value,
                price,
                quote_status
            )
            
            # Step 6: Send appropriate notification
            if quote_status == QuoteStatus.CONFIRMED.value:
                self.notification_provider.send_quote_document(
                    shipper_id,
                    quote_id,
                    price
                )
            elif quote_status == QuoteStatus.HELD_FOR_REVIEW.value:
                self.notification_provider.send_review_notice(
                    shipper_id,
                    quote_id
                )
            elif quote_status == QuoteStatus.REJECTED.value:
                self.notification_provider.send_refusal_notice(
                    shipper_id,
                    "Screening result: high risk classification"
                )
            
            # Step 7: Return outcome
            return {
                "status": quote_status,
                "quote_id": quote_id,
                "price": price,
                "risk_level": risk_level
            }
        
        except ValueError as e:
            return {
                "status": "error: validation failed",
                "reason": str(e)
            }
        except Exception as e:
            return {
                "status": "error: system error",
                "reason": str(e)
            }


def handle(request: dict) -> dict:
    """
    Module-level entry point for handling a quote request.
    
    Expected request keys:
      - shipper_id: str
      - weight_kg: float
      - distance_km: float
      - declared_value: float
      - (optional) screening_result: 'low', 'medium', 'high'
      - (optional) pricing_result: float
      - (optional) store_result: str (confirmation ID)
    
    Returns a dict with 'status' key indicating outcome.
    """
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    
    # Create a custom screening provider if override is provided
    screening_provider = ExternalScreeningProvider()
    if "screening_result" in request:
        class OverrideScreeningProvider(ExternalScreeningProvider):
            def screen_shipper(self, shipper_id: str) -> str:
                return request["screening_result"]
        screening_provider = OverrideScreeningProvider()
    
    # Create a custom tariff engine if override is provided
    tariff_engine = TariffEngine()
    if "pricing_result" in request:
        class OverrideTariffEngine(TariffEngine):
            def calculate_price(self, weight_kg: float, distance_km: float, declared_value: float) -> float:
                return request["pricing_result"]
        tariff_engine = OverrideTariffEngine()
    
    # Create quote processor
    processor = CargoQuote(
        screening_provider=screening_provider,
        tariff_engine=tariff_engine
    )
    
    # Process the request
    result = processor.process_quote_request(
        shipper_id,
        weight_kg,
        distance_km,
        declared_value
    )
    
    return result
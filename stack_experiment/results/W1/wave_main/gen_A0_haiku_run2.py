import uuid
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from typing import Optional


class ScreeningRisk(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class QuoteStatus(Enum):
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
    price: float
    status: QuoteStatus
    created_at: datetime


class ExternalScreeningProvider:
    def screen_shipper(self, shipper_id: str) -> ScreeningRisk:
        return ScreeningRisk.LOW


class TariffEngine:
    def calculate_price(self, weight_kg: float, distance_km: float, declared_value: float) -> float:
        base_rate = 0.5
        weight_charge = weight_kg * base_rate
        distance_charge = distance_km * 0.02
        value_charge = declared_value * 0.001
        return round(weight_charge + distance_charge + value_charge, 2)


class QuoteStore:
    def __init__(self):
        self.quotes = {}

    def store_quote(self, quote: Quote) -> str:
        self.quotes[quote.quote_id] = quote
        return quote.quote_id


class NotificationProvider:
    def send_quote_issued(self, shipper_id: str, quote_id: str, price: float) -> bool:
        return True

    def send_refusal_notice(self, shipper_id: str, reason: str) -> bool:
        return True

    def send_review_notice(self, shipper_id: str, quote_id: str) -> bool:
        return True


class CargoQuote:
    def __init__(
        self,
        screening_provider: Optional[ExternalScreeningProvider] = None,
        tariff_engine: Optional[TariffEngine] = None,
        quote_store: Optional[QuoteStore] = None,
        notification_provider: Optional[NotificationProvider] = None,
    ):
        self.screening_provider = screening_provider or ExternalScreeningProvider()
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.notification_provider = notification_provider or NotificationProvider()

    def validate_request(self, request_data: dict) -> QuoteRequest:
        shipper_id = request_data.get("shipper_id")
        weight_kg = request_data.get("weight_kg")
        distance_km = request_data.get("distance_km")
        declared_value = request_data.get("declared_value")

        if not shipper_id:
            raise ValueError("shipper_id is required")
        if weight_kg is None or weight_kg <= 0:
            raise ValueError("weight_kg must be positive")
        if distance_km is None or distance_km <= 0:
            raise ValueError("distance_km must be positive")
        if declared_value is None or declared_value < 0:
            raise ValueError("declared_value must be non-negative")

        return QuoteRequest(
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
        )

    def process_quote_request(self, request_data: dict) -> dict:
        try:
            quote_request = self.validate_request(request_data)
        except ValueError as e:
            return {"status": f"error: {str(e)}"}

        shipper_id = quote_request.shipper_id

        screening_risk = self.screening_provider.screen_shipper(shipper_id)

        if screening_risk == ScreeningRisk.HIGH:
            self.notification_provider.send_refusal_notice(
                shipper_id, "Failed denied-party screening"
            )
            return {"status": "rejected", "reason": "Failed denied-party screening"}

        price = self.tariff_engine.calculate_price(
            quote_request.weight_kg,
            quote_request.distance_km,
            quote_request.declared_value,
        )

        quote_id = str(uuid.uuid4())

        if screening_risk == ScreeningRisk.MEDIUM:
            status = QuoteStatus.HELD_FOR_REVIEW
            quote = Quote(
                quote_id=quote_id,
                shipper_id=shipper_id,
                price=price,
                status=status,
                created_at=datetime.utcnow(),
            )
            self.quote_store.store_quote(quote)
            self.notification_provider.send_review_notice(shipper_id, quote_id)
            return {
                "status": "held_for_review",
                "quote_id": quote_id,
                "price": price,
            }
        else:
            status = QuoteStatus.ISSUED
            quote = Quote(
                quote_id=quote_id,
                shipper_id=shipper_id,
                price=price,
                status=status,
                created_at=datetime.utcnow(),
            )
            self.quote_store.store_quote(quote)
            self.notification_provider.send_quote_issued(shipper_id, quote_id, price)
            return {
                "status": "confirmed",
                "quote_id": quote_id,
                "price": price,
            }


_system = CargoQuote()


def handle(request: dict) -> dict:
    return _system.process_quote_request(request)
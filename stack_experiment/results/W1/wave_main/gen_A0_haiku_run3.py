import dataclasses
from datetime import datetime
from typing import Optional
from enum import Enum


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class QuoteStatus(Enum):
    CONFIRMED = "confirmed"
    HELD_FOR_REVIEW = "held_for_review"
    REJECTED = "rejected"


@dataclasses.dataclass
class QuoteRequest:
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float


@dataclasses.dataclass
class Quote:
    quote_id: str
    shipper_id: str
    price: float
    status: QuoteStatus
    created_at: datetime


class ExternalScreeningProvider:
    def screen_shipper(self, shipper_id: str) -> float:
        return 0.5


class ExternalNotificationProvider:
    def send_quote_issued(self, shipper_id: str, quote_id: str, price: float) -> str:
        return "sent"

    def send_quote_rejected(self, shipper_id: str, reason: str) -> str:
        return "sent"

    def send_quote_held_for_review(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


class TariffEngine:
    def calculate_price(self, weight_kg: float, distance_km: float, declared_value: float) -> float:
        base_rate = 0.5
        distance_multiplier = 1.0 + (distance_km / 1000.0) * 0.1
        weight_multiplier = 1.0 + (weight_kg / 100.0) * 0.15
        value_multiplier = 1.0 + (declared_value / 10000.0) * 0.05
        price = base_rate * weight_kg * distance_multiplier * weight_multiplier * value_multiplier
        return round(price, 2)


class QuoteStore:
    def __init__(self):
        self.quotes = {}
        self.counter = 0

    def store_quote(self, request: QuoteRequest, price: float, status: QuoteStatus) -> str:
        self.counter += 1
        quote_id = f"QUOTE-{self.counter:06d}"
        quote = Quote(
            quote_id=quote_id,
            shipper_id=request.shipper_id,
            price=price,
            status=status,
            created_at=datetime.now()
        )
        self.quotes[quote_id] = quote
        return quote_id


class RequestValidator:
    def validate(self, request_data: dict) -> QuoteRequest:
        if "shipper_id" not in request_data or not request_data["shipper_id"]:
            raise ValueError("shipper_id is required")
        if "weight_kg" not in request_data or request_data["weight_kg"] <= 0:
            raise ValueError("weight_kg must be positive")
        if "distance_km" not in request_data or request_data["distance_km"] <= 0:
            raise ValueError("distance_km must be positive")
        if "declared_value" not in request_data or request_data["declared_value"] < 0:
            raise ValueError("declared_value cannot be negative")

        return QuoteRequest(
            shipper_id=request_data["shipper_id"],
            weight_kg=request_data["weight_kg"],
            distance_km=request_data["distance_km"],
            declared_value=request_data["declared_value"]
        )


class CargoQuoteSystem:
    def __init__(self):
        self.validator = RequestValidator()
        self.screening_provider = ExternalScreeningProvider()
        self.tariff_engine = TariffEngine()
        self.quote_store = QuoteStore()
        self.notification_provider = ExternalNotificationProvider()

    def process_quote_request(self, request_data: dict) -> dict:
        try:
            quote_request = self.validator.validate(request_data)
        except ValueError as e:
            return {"status": f"error: {str(e)}"}

        risk_index = self.screening_provider.screen_shipper(quote_request.shipper_id)

        if risk_index > 0.8:
            self.notification_provider.send_quote_rejected(
                quote_request.shipper_id,
                "Shipper failed denied-party screening"
            )
            return {"status": "rejected"}

        price = self.tariff_engine.calculate_price(
            quote_request.weight_kg,
            quote_request.distance_km,
            quote_request.declared_value
        )

        if 0.5 < risk_index <= 0.8:
            status = QuoteStatus.HELD_FOR_REVIEW
            quote_id = self.quote_store.store_quote(quote_request, price, status)
            self.notification_provider.send_quote_held_for_review(
                quote_request.shipper_id,
                quote_id
            )
            return {
                "status": "held_for_review",
                "quote_id": quote_id,
                "price": price
            }
        else:
            status = QuoteStatus.CONFIRMED
            quote_id = self.quote_store.store_quote(quote_request, price, status)
            self.notification_provider.send_quote_issued(
                quote_request.shipper_id,
                quote_id,
                price
            )
            return {
                "status": "confirmed",
                "quote_id": quote_id,
                "price": price
            }


_system = CargoQuoteSystem()


def handle(request: dict) -> dict:
    return _system.process_quote_request(request)
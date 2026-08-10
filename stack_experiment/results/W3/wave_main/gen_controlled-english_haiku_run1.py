import json
from dataclasses import dataclass
from typing import Any
from enum import Enum


class ValidationResult(Enum):
    VALID = "valid"
    INVALID = "invalid"


class StorageResult(Enum):
    STORED = "stored"
    UNAVAILABLE = "unavailable"


class ScreeningResult(Enum):
    ACCEPTED = "accepted"
    REVIEW = "review"
    REFUSED = "refused"
    UNAVAILABLE = "unavailable"


class NotificationResult(Enum):
    SENT = "sent"
    FAILED = "failed"


ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

WEIGHT_MIN = 0.1
WEIGHT_MAX = 25000
DISTANCE_MIN = 1
DISTANCE_MAX = 2000
DECLARED_VALUE_MIN = 0
DECLARED_VALUE_MAX = 1000000


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: str
    price_amount: float = None


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id: str, risk_index: int = None) -> int:
        """Screen a shipper and return a risk index (0-100)."""
        if risk_index is not None:
            return risk_index
        return 25


class TariffEngine:
    """Computes freight price from weight and distance."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute price based on tariff rules."""
        base_rate = 0.5
        weight_factor = weight_kg * 0.01
        distance_factor = distance_km * 0.15
        return round(base_rate + weight_factor + distance_factor, 2)


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(
        self, shipper_id: str, quote_id: str, price_amount: float
    ) -> str:
        """Send quote document asynchronously (fire-and-forget)."""
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Send refusal notice asynchronously (fire-and-forget)."""
        return "sent"


class QuoteStore:
    """PostgreSQL-backed quote storage."""

    def __init__(self):
        self.quotes = {}
        self.next_id = 1

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        """Store a draft quote and return quote_id."""
        quote_id = f"QT-{self.next_id}"
        self.next_id += 1
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status="draft",
        )
        self.quotes[quote_id] = quote
        return quote_id

    def update_quote(
        self,
        quote_id: str,
        status: str,
        price_amount: float = None,
    ) -> Quote:
        """Update quote status and optionally price."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return quote


class QuoteAPI:
    """Main quotation orchestrator."""

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
    ) -> ValidationResult:
        """Validate quote request against bounds (DT-V)."""
        if not shipper_id or not isinstance(shipper_id, str):
            return ValidationResult.INVALID
        if weight_kg < WEIGHT_MIN or weight_kg > WEIGHT_MAX:
            return ValidationResult.INVALID
        if distance_km < DISTANCE_MIN or distance_km > DISTANCE_MAX:
            return ValidationResult.INVALID
        if declared_value < DECLARED_VALUE_MIN or declared_value > DECLARED_VALUE_MAX:
            return ValidationResult.INVALID
        return ValidationResult.VALID

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        """
        Main quote request entry point.
        Returns outcome dict with 'status' key and supporting details.
        """
        # Step 1: Validate request
        if self._validate_request(shipper_id, weight_kg, distance_km, declared_value) == ValidationResult.INVALID:
            return {"status": "rejected_invalid_request"}

        # Step 2: Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except Exception:
            return {"status": "store_unavailable_error"}

        # Step 3: Screen shipper
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception:
            # Step 4d: Screening unavailable — price, hold, respond
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, "held_unscreened", price_amount
                )
                return {
                    "status": "held_unscreened_response",
                    "quote_id": quote_id,
                    "price": price_amount,
                }
            except Exception:
                return {"status": "error"}

        # Step 4: Apply screening decision
        if risk_index <= ACCEPT_MAX:
            # 4a: Accept — price, store, notify, respond
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, "quoted", price_amount)
                self.notification_service.send_quote_document(
                    shipper_id, quote_id, price_amount
                )
                return {
                    "status": "quoted_response",
                    "quote_id": quote_id,
                    "price": price_amount,
                }
            except Exception:
                return {"status": "error"}

        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # 4b: Review — hold, no pricing, no notification
            try:
                self.quote_store.update_quote(quote_id, "review_hold")
                return {
                    "status": "review_hold_response",
                    "quote_id": quote_id,
                }
            except Exception:
                return {"status": "error"}

        elif risk_index >= REFUSE_MIN:
            # 4c: Refuse — mark refused, notify, respond
            try:
                self.quote_store.update_quote(quote_id, "refused_screening")
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
                return {
                    "status": "refused_screening_response",
                    "quote_id": quote_id,
                }
            except Exception:
                return {"status": "error"}

        return {"status": "error: unknown_screening_outcome"}


def handle(request: dict) -> dict:
    """
    End-to-end quote flow handler.

    Accepts request with keys:
    - shipper_id: string
    - weight_kg: float
    - distance_km: float
    - declared_value: float
    - screening_result (optional): 0-100 risk index, or None/absence for default
    - store_result (optional): "stored" or "unavailable"

    Returns dict with "status" key describing outcome.
    """
    shipper_id = request.get("shipper_id", "SHIPPER-1")
    weight_kg = request.get("weight_kg", 100.0)
    distance_km = request.get("distance_km", 500.0)
    declared_value = request.get("declared_value", 10000.0)

    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    quote_api = QuoteAPI(
        quote_store, screening_service, tariff_engine, notification_service
    )

    # Inject test outcomes if provided
    if "screening_result" in request:
        original_screen = screening_service.screen

        def mocked_screen(shipper_id_arg, risk_index=None):
            return request["screening_result"]

        screening_service.screen = mocked_screen

    if "store_result" in request and request["store_result"] == "unavailable":
        original_store = quote_store.store_draft

        def mocked_store(shipper_id_arg, weight_kg_arg, distance_km_arg, declared_value_arg):
            raise Exception("Store unavailable")

        quote_store.store_draft = mocked_store

    return quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
import json
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


@dataclass
class QuoteRecord:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price: Optional[float] = None


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id: str) -> int:
        """
        Returns a risk index (higher is worse).
        In the test harness, this is controlled via screening_result in the request dict.
        """
        raise NotImplementedError("ScreeningService must be injected or mocked")


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules (DT-P)."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        DT-P pricing rules:
        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: if weight_kg > 1244, add 316.00
        P3: if distance_km >= 4912, multiply by 1.19 (after P2)
        P4: round to 2 decimals
        """
        base = Decimal(str(0.87 * weight_kg + 1.13 * distance_km))

        if weight_kg > 1244:
            base += Decimal("316.00")

        if distance_km >= 4912:
            base *= Decimal("1.19")

        price_val = base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return float(price_val)


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        """Fire-and-forget: returns a delivery status (success/failure does not change response)."""
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Fire-and-forget: returns a delivery status."""
        return "sent"


class QuoteStore:
    """PostgreSQL-backed quote storage (in-memory simulation here)."""

    def __init__(self):
        self.quotes: dict[str, QuoteRecord] = {}

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        """
        Store a draft quote.
        Returns quote_id on success.
        Raises exception if storage fails (simulated via store_status in test harness).
        """
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = QuoteRecord(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT,
        )
        return quote_id

    def update_quote(self, quote_id: str, status: QuoteStatus, price: Optional[float] = None) -> QuoteRecord:
        """
        Update quote status and optionally price.
        Returns the updated record.
        """
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price is not None:
            quote.price = price
        return quote


class QuoteAPI:
    """
    Orchestrator: receives quote requests, validates them, screens the shipper,
    prices the consignment, stores it, and returns the outcome.
    Implements the flow from the sequence diagram with DT-V, DT-S, DT-P logic.
    """

    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

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

    def validate_request(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> tuple[bool, Optional[str]]:
        """
        DT-V validation:
        V1: shipper_id present and non-empty
        V2: weight_kg in [3, 19400]
        V3: distance_km in [25, 7150]
        V4: declared_value in [50, 83000]
        Returns (is_valid, error_message).
        """
        if not shipper_id or not isinstance(shipper_id, str) or len(shipper_id) == 0:
            return False, "invalid shipper_id"
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False, "weight_kg out of bounds [3, 19400]"
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False, "distance_km out of bounds [25, 7150]"
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False, "declared_value out of bounds [50, 83000]"
        return True, None

    def request_quote(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> dict:
        """
        Main quote flow orchestrator.
        Returns a response dict with status and optional quote_id, price, hold flag.
        """

        is_valid, error_msg = self.validate_request(shipper_id, weight_kg, distance_km, declared_value)
        if not is_valid:
            return {"status": "rejected: invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception:
            return {"status": "error: store_unavailable"}

        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_available = True
        except Exception:
            screening_available = False
            risk_index = None

        response = {"quote_id": quote_id}

        if screening_available:
            if risk_index <= self.ACCEPT_MAX:
                price = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price)
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
                response["status"] = "quoted"
                response["price"] = price
            elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
                response["status"] = "review_hold"
            elif risk_index >= self.REFUSE_MIN:
                self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
                response["status"] = "refused_screening"
        else:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price)
            response["status"] = "held_unscreened"
            response["price"] = price
            response["hold"] = True

        return response


def handle(request: dict) -> dict:
    """
    End-to-end handler: receives a request dict, runs the quotation flow,
    and returns a response dict with status and optional fields.

    The request dict carries:
      - shipper_id, weight_kg, distance_km, declared_value (core quote data)
      - screening_result (int): the risk index to return from ScreeningService
      - store_status (str): "ok" or "error" to simulate store success/failure
      - notification_status (str): "ok" or "error" to simulate notification success/failure
      - screening_status (str): "ok" or "error" to simulate screening availability
    """

    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    store_status = request.get("store_status", "ok")
    screening_status = request.get("screening_status", "ok")
    screening_result = request.get("screening_result")
    notification_status = request.get("notification_status", "ok")

    class TestScreeningService(ScreeningService):
        def screen(self, shipper_id: str) -> int:
            if screening_status != "ok":
                raise Exception("Screening unavailable")
            if screening_result is None:
                raise ValueError("screening_result not provided")
            return int(screening_result)

    class TestQuoteStore(QuoteStore):
        def store_draft(
            self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
        ) -> str:
            if store_status != "ok":
                raise Exception("Store unavailable")
            return super().store_draft(shipper_id, weight_kg, distance_km, declared_value)

    class TestNotificationService(NotificationService):
        def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
            if notification_status != "ok":
                return "failed"
            return "sent"

        def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
            if notification_status != "ok":
                return "failed"
            return "sent"

    quote_store = TestQuoteStore()
    screening_service = TestScreeningService()
    tariff_engine = TariffEngine()
    notification_service = TestNotificationService()

    api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)

    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
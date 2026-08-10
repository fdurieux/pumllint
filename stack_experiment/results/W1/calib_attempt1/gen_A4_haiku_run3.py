import json
import uuid
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, asdict
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
    status: str
    price: Optional[float] = None


class ScreeningService:
    """External denied-party screening provider."""

    def __init__(self, risk_index: Optional[int] = None, available: bool = True):
        self.risk_index = risk_index
        self.available = available

    def screen(self, shipper_id: str) -> tuple[Optional[int], bool]:
        """
        Returns (risk_index, success).
        If unavailable, returns (None, False).
        """
        if not self.available:
            return None, False
        return self.risk_index, True


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules (DT-P)."""

    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Pricing rules DT-P:
        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: if weight_kg > 1244, add 316.00
        P3: if distance_km >= 4912, multiply by 1.19 (applied after P2)
        P4: round to 2 decimal places
        """
        base = Decimal(str(0.87 * weight_kg + 1.13 * distance_km))

        if weight_kg > 1244:
            base += Decimal("316.00")

        if distance_km >= 4912:
            base *= Decimal("1.19")

        price = base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return float(price)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available: bool = True):
        self.available = available
        self.quotes: dict[str, QuoteRecord] = {}

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> tuple[Optional[str], bool]:
        """
        Stores a draft quote. Returns (quote_id, success).
        If unavailable, returns (None, False).
        """
        if not self.available:
            return None, False

        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = QuoteRecord(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT.value,
        )
        return quote_id, True

    def update_quote(
        self, quote_id: str, status: str, price: Optional[float] = None
    ) -> tuple[Optional[QuoteRecord], bool]:
        """
        Updates a stored quote with new status and optional price.
        Returns (updated_quote, success).
        """
        if quote_id not in self.quotes:
            return None, False

        quote = self.quotes[quote_id]
        quote.status = status
        if price is not None:
            quote.price = price

        return quote, True


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def __init__(self, available: bool = True):
        self.available = available
        self.sent_documents: list[tuple[str, str, Optional[float]]] = []
        self.sent_refusals: list[tuple[str, str]] = []

    def send_quote_document(
        self, shipper_id: str, quote_id: str, price: float
    ) -> bool:
        """
        Sends a quote document. Fire-and-forget; failure does not
        affect the response. Returns success status.
        """
        if not self.available:
            return False
        self.sent_documents.append((shipper_id, quote_id, price))
        return True

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> bool:
        """
        Sends a refusal notice. Fire-and-forget; failure does not
        affect the response. Returns success status.
        """
        if not self.available:
            return False
        self.sent_refusals.append((shipper_id, quote_id))
        return True


class QuoteAPI:
    """
    Orchestrates the quotation flow: validates, stores, screens,
    prices, notifies, and returns the outcome.
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

    def validate_request(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> tuple[bool, Optional[str]]:
        """
        Validates request per DT-V. Returns (is_valid, error_message).
        """
        if not shipper_id or shipper_id.strip() == "":
            return False, "shipper_id is required and non-empty"
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False, f"weight_kg must be between 3 and 19400, got {weight_kg}"
        if (
            not isinstance(distance_km, (int, float))
            or distance_km < 25
            or distance_km > 7150
        ):
            return False, (
                f"distance_km must be between 25 and 7150, got {distance_km}"
            )
        if (
            not isinstance(declared_value, (int, float))
            or declared_value < 50
            or declared_value > 83000
        ):
            return False, (
                f"declared_value must be between 50 and 83000, got {declared_value}"
            )
        return True, None

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        """
        End-to-end quotation flow orchestrator.
        Returns response dict with status and optional quote_id, price, hold.
        """
        is_valid, error_msg = self.validate_request(
            shipper_id, weight_kg, distance_km, declared_value
        )
        if not is_valid:
            return {"status": "rejected: invalid_request"}

        quote_id, store_ok = self.quote_store.store_draft(
            shipper_id, weight_kg, distance_km, declared_value
        )
        if not store_ok:
            return {"status": "error: store_unavailable"}

        risk_index, screening_ok = self.screening_service.screen(shipper_id)

        if not screening_ok:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, QuoteStatus.HELD_UNSCREENED.value, price
            )
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        if risk_index <= TariffEngine.ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED.value, price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }
        elif risk_index <= TariffEngine.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD.value)
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }
        else:
            self.quote_store.update_quote(
                quote_id, QuoteStatus.REFUSED_SCREENING.value
            )
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }


def handle(request: dict) -> dict:
    """
    Run one end-to-end flow. Request dict carries scenario input:
    entity ids and amounts, existence flags, and external system outcomes.
    """
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)

    screening_available = request.get("screening_service_available", True)
    screening_result = request.get("screening_service_result", None)
    if screening_result is not None:
        if isinstance(screening_result, str):
            if screening_result == "error":
                screening_available = False
            else:
                try:
                    screening_result = int(screening_result)
                except (ValueError, TypeError):
                    screening_available = False
        elif not isinstance(screening_result, int):
            screening_available = False

    quote_store_available = request.get("quote_store_available", True)
    notification_service_available = request.get(
        "notification_service_available", True
    )

    screening_service = ScreeningService(
        risk_index=screening_result if isinstance(screening_result, int) else None,
        available=screening_available,
    )
    tariff_engine = TariffEngine()
    quote_store = QuoteStore(available=quote_store_available)
    notification_service = NotificationService(available=notification_service_available)

    quote_api = QuoteAPI(
        screening_service, tariff_engine, quote_store, notification_service
    )

    response = quote_api.request_quote(
        shipper_id, weight_kg, distance_km, declared_value
    )

    return response
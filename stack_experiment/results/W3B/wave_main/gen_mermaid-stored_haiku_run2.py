import uuid
from typing import Optional
from dataclasses import dataclass, asdict
from enum import Enum


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price_amount: Optional[float] = None


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id: str) -> float:
        """
        Returns a risk index (0.0 to 100.0).
        In production this calls an external REST API.
        """
        if not hasattr(ScreeningService, '_mock_result'):
            return 25.0
        return ScreeningService._mock_result


class TariffEngine:
    """Computes freight price from weight and distance."""

    RATE_PER_KG_KM = 0.5

    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Returns price amount based on weight and distance.
        In test scenarios, mock via _mock_result.
        """
        if not hasattr(TariffEngine, '_mock_result'):
            return weight_kg * distance_km * self.RATE_PER_KG_KM
        return TariffEngine._mock_result


class QuoteStore:
    """PostgreSQL-backed quote persistence."""

    def __init__(self):
        self.quotes = {}

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        """
        Stores a draft quote and returns its ID.
        Raises exception on storage failure.
        """
        if hasattr(QuoteStore, '_mock_store_result'):
            if QuoteStore._mock_store_result == "error":
                raise Exception("storeUnavailableError")

        quote_id = str(uuid.uuid4())
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT,
        )
        self.quotes[quote_id] = quote
        return quote_id

    def update_quote(
        self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None
    ) -> Quote:
        """
        Updates quote status and optionally price; returns updated quote.
        """
        if quote_id not in self.quotes:
            raise Exception(f"Quote {quote_id} not found")

        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount

        return quote


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(
        self, shipper_id: str, quote_id: str, price_amount: float
    ) -> str:
        """
        Sends quote document; returns confirmation.
        Fire-and-forget: failures do not affect the quote response.
        """
        if hasattr(NotificationService, '_mock_result'):
            return NotificationService._mock_result
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """
        Sends refusal notice; returns confirmation.
        Fire-and-forget: failures do not affect the quote response.
        """
        if hasattr(NotificationService, '_mock_result'):
            return NotificationService._mock_result
        return "sent"


class QuoteAPI:
    """
    Orchestrates validation, screening, pricing, storage, and notification
    for freight quote requests.
    """

    ACCEPT_MAX = 30.0
    REVIEW_MIN = 30.0
    REVIEW_MAX = 70.0
    REFUSE_MIN = 70.0

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
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> bool:
        """
        Validates request bounds per decision table DT-V.
        """
        if not shipper_id or shipper_id.strip() == "":
            return False
        if weight_kg <= 0 or weight_kg > 30000:
            return False
        if distance_km <= 0 or distance_km > 2000:
            return False
        if declared_value < 0:
            return False
        return True

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        """
        Main quotation flow per the sequence diagram.
        Returns a response dict with "status" and optional details.
        """

        if not self.validate_request(
            shipper_id, weight_kg, distance_km, declared_value
        ):
            return {"status": "rejected", "reason": "invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except Exception as e:
            error_msg = str(e)
            if "storeUnavailableError" in error_msg:
                return {"status": "error", "reason": "store_unavailable"}
            raise

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception as e:
            risk_index = None
            screening_error = True

        if risk_index is not None:
            screening_error = False

            if risk_index <= self.ACCEPT_MAX:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.QUOTED, price_amount
                )
                self.notification_service.send_quote_document(
                    shipper_id, quote_id, price_amount
                )
                return {
                    "status": "quoted",
                    "quote_id": quote_id,
                    "price": price_amount,
                }

            elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
                return {
                    "status": "review_hold",
                    "quote_id": quote_id,
                    "reason": "screening_review_required",
                }

            elif risk_index >= self.REFUSE_MIN:
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.REFUSED_SCREENING
                )
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
                return {
                    "status": "refused",
                    "quote_id": quote_id,
                    "reason": "screening_failed",
                }

        if screening_error:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, QuoteStatus.HELD_UNSCREENED, price_amount
            )
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "reason": "screening_unavailable",
                "price": price_amount,
            }

        return {"status": "error", "reason": "unexpected_state"}


def handle(request: dict) -> dict:
    """
    Entry point for end-to-end quote request handling.
    
    request keys:
      - shipper_id: str
      - weight_kg: float
      - distance_km: float
      - declared_value: float
      - screening_result: float (optional, mocks screening risk index)
      - tariff_result: float (optional, mocks pricing)
      - quote_store_result: str (optional, "error" to fail storage)
      - notification_result: str (optional, mocks notification outcome)
    
    Returns dict with "status" key naming the outcome.
    """
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0.0)
    distance_km = request.get("distance_km", 0.0)
    declared_value = request.get("declared_value", 0.0)

    if "screening_result" in request:
        ScreeningService._mock_result = request["screening_result"]
    else:
        if hasattr(ScreeningService, '_mock_result'):
            delattr(ScreeningService, '_mock_result')

    if "tariff_result" in request:
        TariffEngine._mock_result = request["tariff_result"]
    else:
        if hasattr(TariffEngine, '_mock_result'):
            delattr(TariffEngine, '_mock_result')

    if "quote_store_result" in request:
        QuoteStore._mock_store_result = request["quote_store_result"]
    else:
        if hasattr(QuoteStore, '_mock_store_result'):
            delattr(QuoteStore, '_mock_store_result')

    if "notification_result" in request:
        NotificationService._mock_result = request["notification_result"]
    else:
        if hasattr(NotificationService, '_mock_result'):
            delattr(NotificationService, '_mock_result')

    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()

    quote_api = QuoteAPI(
        screening_service, tariff_engine, quote_store, notification_service
    )

    return quote_api.request_quote(
        shipper_id, weight_kg, distance_km, declared_value
    )
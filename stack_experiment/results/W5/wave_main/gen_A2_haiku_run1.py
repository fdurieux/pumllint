from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime
import uuid


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
    pass


class PricingError(Exception):
    pass


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price_amount: Optional[float] = None
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow().isoformat()


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id: str) -> float:
        """
        Returns a risk index (0.0 to 100.0).
        In a real system, this would call an external REST API.
        Test injection via request["screening_service_result"] (a number).
        """
        return 0.0


class TariffEngine:
    """Computes freight price from weight and distance."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Computes price based on tariff rules.
        Base rate: 5.0 per 100kg + 0.5 per km.
        Test injection via request["tariff_engine_result"] (a number).
        """
        base_per_100kg = 5.0
        per_km = 0.5
        price = (weight_kg / 100.0) * base_per_100kg + distance_km * per_km
        return round(price, 2)


class QuoteStore:
    """PostgreSQL-backed quote storage."""

    def __init__(self):
        self.quotes: dict[str, Quote] = {}
        self.storage_available = True

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        """
        Stores a draft quote and returns its quote_id.
        Test injection via request["quote_store_exists"] (boolean).
        """
        if not self.storage_available:
            raise StorageError("Quote store unavailable")
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

    def update_quote(self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None) -> Quote:
        """
        Updates a quote's status and optionally price.
        Test injection via request["quote_store_found"] (boolean).
        """
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        quote.updated_at = datetime.utcnow().isoformat()
        return quote


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        """
        Sends a quote document to the shipper.
        Fire-and-forget: failures do not affect the response.
        Test injection via request["notification_service_status"] (e.g., "sent", "failed").
        Returns a confirmation string.
        """
        return f"quote_document_sent_to_{shipper_id}"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """
        Sends a refusal notice to the shipper.
        Test injection via request["notification_service_status"].
        Returns a confirmation string.
        """
        return f"refusal_notice_sent_to_{shipper_id}"


class QuoteAPI:
    """Main quote request orchestrator."""

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
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> bool:
        """
        Validates request bounds (decision table DT-V).
        Returns True if valid; raises ValidationError otherwise.
        """
        if not shipper_id:
            raise ValidationError("shipper_id is required")
        if weight_kg < 0 or weight_kg > 10000:
            raise ValidationError("weight_kg must be >= 0 and <= 10000")
        if distance_km < 0 or distance_km > 1000:
            raise ValidationError("distance_km must be >= 0 and <= 1000")
        if declared_value < 0:
            raise ValidationError("declared_value must be >= 0")
        return True

    def request_quote(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> dict:
        """
        Main quotation flow. Synchronous end-to-end orchestration.
        Returns outcome dict with keys: status, quote_id, price_amount (optional), message.
        """
        try:
            self.validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {"status": "rejected_invalid_request", "message": str(e)}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageError as e:
            return {"status": "store_unavailable_error", "message": str(e)}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError as e:
            risk_index = None

        if risk_index is None:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
                return {
                    "status": "held_unscreened",
                    "quote_id": quote_id,
                    "price_amount": price_amount,
                    "message": "Quote held pending screening completion",
                }
            except Exception as e:
                return {"status": "error", "message": f"Pricing or storage failed: {str(e)}"}

        if risk_index <= self.ACCEPT_MAX:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
                self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
                return {
                    "status": "quoted",
                    "quote_id": quote_id,
                    "price_amount": price_amount,
                    "message": "quote issued and document sent",
                }
            except Exception as e:
                return {"status": "error", "message": f"Pricing or storage failed: {str(e)}"}

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
                return {
                    "status": "review_hold",
                    "quote_id": quote_id,
                    "message": "Quote held for compliance review",
                }
            except Exception as e:
                return {"status": "error", "message": f"Storage failed: {str(e)}"}

        elif risk_index >= self.REFUSE_MIN:
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
                return {
                    "status": "refused_screening",
                    "quote_id": quote_id,
                    "message": "Quote refused due to screening outcome",
                }
            except Exception as e:
                return {"status": "error", "message": f"Storage or notification failed: {str(e)}"}

        return {"status": "error", "message": "Unexpected risk index value"}


def handle(request: dict) -> dict:
    """
    Entry point for end-to-end quote flow.
    request dict keys:
      - shipper_id (str): shipper identifier
      - weight_kg (float): cargo weight
      - distance_km (float): delivery distance
      - declared_value (float): cargo declared value
      - quote_store_exists (bool, optional): whether store is available
      - quote_store_found (bool, optional): whether quote can be updated
      - screening_service_result (float, optional): risk index override
      - tariff_engine_result (float, optional): price override
      - notification_service_status (str, optional): notification outcome
    Returns dict with keys: status, quote_id (optional), price_amount (optional), message.
    """
    screening_svc = ScreeningService()
    tariff_eng = TariffEngine()
    quote_st = QuoteStore()
    notif_svc = NotificationService()

    if "quote_store_exists" in request and not request["quote_store_exists"]:
        quote_st.storage_available = False

    api = QuoteAPI(screening_svc, tariff_eng, quote_st, notif_svc)

    if "screening_service_result" in request:
        screening_svc.screen = lambda shipper_id: request["screening_service_result"]

    if "tariff_engine_result" in request:
        tariff_eng.price = lambda weight_kg, distance_km: request["tariff_engine_result"]

    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0.0)
    distance_km = request.get("distance_km", 0.0)
    declared_value = request.get("declared_value", 0.0)

    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
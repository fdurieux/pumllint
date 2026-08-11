from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ValidationError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class StorageUnavailableError(Exception):
    pass


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


ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71


class QuoteStore:
    """PostgreSQL 16 quote store."""

    def __init__(self):
        self.quotes = {}
        self.counter = 0

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        """Store a draft quote and return its ID."""
        if not hasattr(self, "_available"):
            self._available = True

        if not self._available:
            raise StorageUnavailableError("Quote store unavailable")

        self.counter += 1
        quote_id = f"Q{self.counter:06d}"
        self.quotes[quote_id] = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT,
        )
        return quote_id

    def update_quote(
        self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None
    ) -> Quote:
        """Update quote status and optionally price."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")

        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount

        return quote


class TariffEngine:
    """Rules library for tariff pricing."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute freight price from weight and distance."""
        base_rate = 0.5
        weight_charge = weight_kg * 0.02
        distance_charge = distance_km * 0.03
        return base_rate + weight_charge + distance_charge


class ScreeningService:
    """External denied-party screening provider."""

    def __init__(self):
        self._available = True

    def screen(self, shipper_id: str) -> int:
        """Return shipper risk index (0-100)."""
        if not self._available:
            raise ScreeningUnavailableError("Screening service unavailable")
        return 0


class NotificationService:
    """External messaging provider."""

    def __init__(self):
        self.sent_documents = []
        self.sent_refusals = []

    def send_quote_document(
        self, shipper_id: str, quote_id: str, price_amount: float
    ) -> str:
        """Send quote document to shipper (fire-and-forget)."""
        self.sent_documents.append(
            {"shipper_id": shipper_id, "quote_id": quote_id, "price": price_amount}
        )
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Send refusal notice to shipper (fire-and-forget)."""
        self.sent_refusals.append({"shipper_id": shipper_id, "quote_id": quote_id})
        return "sent"


class QuoteAPI:
    """FastAPI quote request orchestrator."""

    def __init__(
        self,
        quote_store: QuoteStore,
        tariff_engine: TariffEngine,
        screening_service: ScreeningService,
        notification_service: NotificationService,
    ):
        self.quote_store = quote_store
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.notification_service = notification_service

    def validate_request(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> bool:
        """Validate quote request bounds (decision table DT-V)."""
        if not shipper_id or len(shipper_id) == 0:
            return False
        if weight_kg <= 0 or weight_kg > 30000:
            return False
        if distance_km <= 0 or distance_km > 3000:
            return False
        if declared_value < 0 or declared_value > 1000000:
            return False
        return True

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        """Main quote request handler."""
        if not self.validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {
                "status": "rejected: invalid request",
                "reason": "Request validation failed",
            }

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StorageUnavailableError:
            return {
                "status": "error: store unavailable",
                "reason": "Quote store is unavailable",
            }

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, QuoteStatus.HELD_UNSCREENED, price_amount
            )
            return {
                "status": "held: unscreened",
                "quote_id": quote_id,
                "reason": "Screening service unavailable",
            }

        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount
            )
            return {
                "status": "confirmed",
                "quote_id": quote_id,
                "price": price_amount,
            }

        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {
                "status": "held: review",
                "quote_id": quote_id,
                "reason": "Quote held for manual compliance review",
            }

        elif risk_index >= REFUSE_MIN:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused",
                "quote_id": quote_id,
                "reason": "Shipper screening failed",
            }


def handle(request: dict) -> dict:
    """Run one end-to-end quotation flow."""
    quote_store = QuoteStore()
    tariff_engine = TariffEngine()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    quote_api = QuoteAPI(
        quote_store, tariff_engine, screening_service, notification_service
    )

    shipper_id = request.get("shipper_id", "S001")
    weight_kg = request.get("weight_kg", 1000.0)
    distance_km = request.get("distance_km", 500.0)
    declared_value = request.get("declared_value", 50000.0)

    if "quote_store_available" in request:
        quote_store._available = request["quote_store_available"]

    if "screening_service_available" in request:
        screening_service._available = request["screening_service_available"]

    if "screening_result" in request:
        if request["screening_result"] == "error":
            screening_service._available = False
        else:
            risk_map = {
                "accept": 20,
                "review": 50,
                "refuse": 80,
            }
            if isinstance(request["screening_result"], int):
                screening_service.screen = lambda _: request["screening_result"]
            elif request["screening_result"] in risk_map:
                risk_index = risk_map[request["screening_result"]]
                screening_service.screen = lambda _: risk_index

    try:
        result = quote_api.request_quote(
            shipper_id, weight_kg, distance_km, declared_value
        )
        return result
    except Exception as e:
        return {
            "status": f"error: {str(e)}",
            "reason": str(e),
        }
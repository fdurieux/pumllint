import uuid
from datetime import datetime
from typing import Optional


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id: str, screening_result: Optional[int] = None) -> int:
        """
        Request shipper risk index.
        Returns integer risk index; higher is worse.
        """
        if screening_result is not None:
            return screening_result
        return 30


class NotificationService:
    """External messaging provider."""

    def send_quote_document(
        self, shipper_id: str, quote_id: str, price: float, notification_status: Optional[str] = None
    ) -> str:
        """Send quote document to shipper. Fire-and-forget."""
        if notification_status == "error":
            return "failed"
        return "sent"

    def send_refusal_notice(
        self, shipper_id: str, quote_id: str, notification_status: Optional[str] = None
    ) -> str:
        """Send refusal notice to shipper. Fire-and-forget."""
        if notification_status == "error":
            return "failed"
        return "sent"


class QuoteStore:
    """PostgreSQL quote store."""

    def __init__(self):
        self.quotes = {}

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float, store_status: Optional[str] = None
    ) -> str:
        """Store draft quote. Returns quote_id or raises exception."""
        if store_status == "unavailable":
            raise Exception("store_unavailable")
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "quote_id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
            "created_at": datetime.now().isoformat(),
        }
        return quote_id

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        """Update quote status and optionally price. Returns updated quote."""
        if quote_id not in self.quotes:
            raise Exception("quote_not_found")
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        return self.quotes[quote_id]


class TariffEngine:
    """Pricing engine."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute freight price per DT-P."""
        base = 0.87 * weight_kg + 1.13 * distance_km
        result = base

        if weight_kg > 1244:
            result += 316.00

        if distance_km >= 4912:
            result *= 1.19

        return round(result, 2)


class QuoteAPI:
    """Orchestrates quote request flow."""

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

    def _validate_request(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> tuple[bool, Optional[str]]:
        """Validate request per DT-V. Returns (is_valid, error_message)."""
        if not shipper_id or not isinstance(shipper_id, str):
            return False, "invalid_request"
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False, "invalid_request"
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False, "invalid_request"
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False, "invalid_request"
        return True, None

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
        screening_result: Optional[int] = None,
        store_status: Optional[str] = None,
        notification_status: Optional[str] = None,
    ) -> dict:
        """Process quote request. Returns response dict."""
        is_valid, error = self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        if not is_valid:
            return {"status": "rejected: invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value, store_status=store_status
            )
        except Exception as e:
            if "store_unavailable" in str(e):
                return {"status": "error: store_unavailable"}
            raise

        try:
            risk_index = self.screening_service.screen(shipper_id, screening_result=screening_result)
        except Exception:
            risk_index = None

        if risk_index is None:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price=price)
            return {"status": "held_unscreened", "quote_id": quote_id, "price": price, "hold": True}

        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price=price)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price, notification_status=notification_status
            )
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(
                shipper_id, quote_id, notification_status=notification_status
            )
            return {"status": "refused_screening", "quote_id": quote_id}

        return {"status": "error: unknown_screening_outcome"}


def handle(request: dict) -> dict:
    """
    Main entry point. Processes a quote request.
    Request dict keys:
      - shipper_id, weight_kg, distance_km, declared_value (core request fields)
      - screening_result (optional int, mocked screening outcome)
      - store_status (optional, "unavailable" to simulate store failure)
      - notification_status (optional, "error" to simulate notification failure)
    """
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)

    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    screening_result = request.get("screening_result")
    store_status = request.get("store_status")
    notification_status = request.get("notification_status")

    return api.request_quote(
        shipper_id=shipper_id,
        weight_kg=weight_kg,
        distance_km=distance_km,
        declared_value=declared_value,
        screening_result=screening_result,
        store_status=store_status,
        notification_status=notification_status,
    )
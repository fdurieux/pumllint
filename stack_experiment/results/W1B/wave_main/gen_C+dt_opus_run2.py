from dataclasses import dataclass, field
from typing import Any, Optional
import uuid


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id: str, risk_result: Any = None, status: str = "assessed") -> int:
        if status in ("error", "unavailable"):
            raise RuntimeError("screening_unavailable")
        if risk_result is not None:
            try:
                return int(risk_result)
            except (TypeError, ValueError):
                pass
        return 10


class TariffEngine:
    """Computes the freight price from weight and distance per DT-P."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        result = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            result += 316.00
        if distance_km >= 4912:
            result *= 1.19
        return round(result, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self) -> None:
        self._records: dict = {}

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float,
                    declared_value: float, status: str = "stored") -> str:
        if status in ("error", "unavailable"):
            raise RuntimeError("store_unavailable")
        quote_id = str(uuid.uuid4())
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> str:
        rec = self._records.get(quote_id)
        if rec is not None:
            rec["status"] = status
            if price is not None:
                rec["price"] = price
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        return "delivered"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "delivered"


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, tariff_engine: TariffEngine, quote_store: QuoteStore,
                 screening_service: ScreeningService,
                 notification_service: NotificationService) -> None:
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, req: dict) -> None:
        shipper_id = req.get("shipper_id")
        if not shipper_id:
            raise ValueError("invalid_request")
        if not self._in_range(req.get("weight_kg"), 3, 19400):
            raise ValueError("invalid_request")
        if not self._in_range(req.get("distance_km"), 25, 7150):
            raise ValueError("invalid_request")
        if not self._in_range(req.get("declared_value"), 50, 83000):
            raise ValueError("invalid_request")

    @staticmethod
    def _in_range(value: Any, lo: float, hi: float) -> bool:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        return lo <= value <= hi

    def request_quote(self, request: dict) -> dict:
        # DT-V validation
        try:
            self._validate(request)
        except ValueError:
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]

        # Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value,
                status=request.get("quote_store_result", request.get("store_result", "stored")),
            )
        except RuntimeError:
            return {"status": "error: store_unavailable"}

        # Screening
        try:
            risk_index = self.screening_service.screen(
                shipper_id,
                risk_result=request.get("screening_result", request.get("screening_status")),
                status=str(request.get("screening_status", "assessed")),
            )
        except RuntimeError:
            # DT-S note 5: screening outage — priced, held_unscreened, not notified
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # DT-S banding
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    api = QuoteApi(
        tariff_engine=TariffEngine(),
        quote_store=QuoteStore(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.request_quote(request)
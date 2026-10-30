from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the QuoteStore is unavailable for storing or updating quotes."""


class ScreeningUnavailableError(Exception):
    """Raised when the ScreeningService is unavailable (screening outage)."""


class QuoteStore:
    """Persistence layer for quotes.

    Methods are expected to raise StoreUnavailableError on storage failures.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        In a real implementation this would persist with status 'draft'.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None, hold: bool = False) -> None:
        """Update an existing quote's status and optional price/hold flag.

        Raises StoreUnavailableError on failure.
        """

        raise NotImplementedError


class TariffEngine:
    """Implements DT-P pricing rules."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # P1: base calculation
        base = 0.87 * weight_kg + 1.13 * distance_km

        # P2: heavy surcharge
        if weight_kg > 1244:
            base += 316.00

        # P3: long-haul multiplier
        if distance_km >= 4912:
            base *= 1.19

        # P4: round to 2 decimal places
        price = round(base, 2)
        return price


class ScreeningService:
    """External service for risk screening.

    screen() returns an integer risk index on success and raises
    ScreeningUnavailableError on outage.
    """

    def screen(self, shipper_id: str) -> int:
        raise NotImplementedError


class NotificationService:
    """Fire-and-forget notification delivery service."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        raise NotImplementedError


@dataclass
class QuoteRequest:
    shipper_id: Any
    weight_kg: Any
    distance_km: Any
    declared_value: Any


class QuoteAPI:
    def __init__(
        self,
        store: Optional[QuoteStore] = None,
        tariff_engine: Optional[TariffEngine] = None,
        screening_service: Optional[ScreeningService] = None,
        notification_service: Optional[NotificationService] = None,
    ) -> None:
        self.store = store if store is not None else QuoteStore()
        self.tariff_engine = tariff_engine if tariff_engine is not None else TariffEngine()
        self.screening_service = screening_service if screening_service is not None else ScreeningService()
        self.notification_service = notification_service if notification_service is not None else NotificationService()

    # --- Validation (DT-V) ---
    def _validate(self, req: QuoteRequest) -> bool:
        # V1: shipper_id present and non-empty string
        if not isinstance(req.shipper_id, str) or req.shipper_id == "":
            return False

        # V2: weight_kg number, 3 <= weight_kg <= 19400
        if not isinstance(req.weight_kg, (int, float)):
            return False
        if req.weight_kg < 3 or req.weight_kg > 19400:
            return False

        # V3: distance_km number, 25 <= distance_km <= 7150
        if not isinstance(req.distance_km, (int, float)):
            return False
        if req.distance_km < 25 or req.distance_km > 7150:
            return False

        # V4: declared_value number, 50 <= declared_value <= 83000
        if not isinstance(req.declared_value, (int, float)):
            return False
        if req.declared_value < 50 or req.declared_value > 83000:
            return False

        return True

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate the CargoQuote instant quotation flow.

        Implements the flow and error policy specified in spec.md and decision_table.md.
        """

        # Normalize incoming request into QuoteRequest
        req = QuoteRequest(
            shipper_id=request.get("shipper_id"),
            weight_kg=request.get("weight_kg"),
            distance_km=request.get("distance_km"),
            declared_value=request.get("declared_value"),
        )

        # 1. Validate the request (DT-V). Invalid -> reject, stop.
        if not self._validate(req):
            return {"status": "rejected: invalid_request"}

        # 2. Store the draft quote with status 'draft'. Handle storage failure.
        try:
            quote_id = self.store.store_draft(
                req.shipper_id,
                float(req.weight_kg),
                float(req.distance_km),
                float(req.declared_value),
            )
        except StoreUnavailableError:
            # storage failure -> error: store_unavailable, nothing else runs
            return {"status": "error: store_unavailable"}

        # At this point a draft was stored; quote_id must be present in responses.

        # 3. Request the shipper's risk index from Screening Service.
        try:
            risk_index = self.screening_service.screen(req.shipper_id)
            screening_outage = False
        except ScreeningUnavailableError:
            # Screening outage path per DT-S note 5 / spec step 3.
            screening_outage = True
            risk_index = None

        # Handle screening outage first, since it bypasses DT-S rows and has its own semantics.
        if screening_outage:
            # Price anyway (DT-P)
            price = self.tariff_engine.price(float(req.weight_kg), float(req.distance_km))

            # Update stored quote to held_unscreened (status) with price
            self.store.update_quote(quote_id, status="held_unscreened", price=price, hold=True)

            # Do NOT notify; return price and hold: true
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4. Apply the screening decision (DT-S) to the risk index and update stored status.
        assert risk_index is not None

        response: Dict[str, Any] = {"quote_id": quote_id}

        if risk_index <= 41:
            # Accept row: quote issued, priced, notified with quote document.
            status = "quoted"

            # 5. Price the quote (DT-P)
            price = self.tariff_engine.price(float(req.weight_kg), float(req.distance_km))

            # Update stored quote to quoted with price
            self.store.update_quote(quote_id, status=status, price=price)

            # 6. Notify the shipper (fire-and-forget)
            try:
                self.notification_service.send_quote_document(req.shipper_id, quote_id, price)
            except Exception:
                # Fire-and-forget: delivery failure never changes stored quote or response.
                pass

            # 7. Prepare response
            response["status"] = status
            response["price"] = price
            return response

        if 42 <= risk_index <= 66:
            # Review row: held for manual review, no price, no notification.
            status = "review_hold"

            # Update stored quote status
            self.store.update_quote(quote_id, status=status)

            response["status"] = status
            return response

        # risk_index >= 67 -> refused row
        status = "refused_screening"

        # Update stored quote status
        self.store.update_quote(quote_id, status=status)

        # Notify refusal (fire-and-forget)
        try:
            self.notification_service.send_refusal_notice(req.shipper_id, quote_id)
        except Exception:
            # Fire-and-forget semantics
            pass

        response["status"] = status
        return response


# Module-level handle for the grading harness
_api_instance: Optional[QuoteAPI] = None


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    global _api_instance
    if _api_instance is None:
        _api_instance = QuoteAPI()
    return _api_instance.handle(request)

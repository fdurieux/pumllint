from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the Quote Store is unavailable for read/write operations."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service experiences an outage for screening requests."""


class QuoteStore:
    """Persistence layer for quotes.

    In this module, methods are stubs to be overridden or mocked by a test harness.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        May raise StoreUnavailableError on storage failure.
        """
        raise NotImplementedError

    def update_quote(
        self,
        quote_id: str,
        status: str,
        price: Optional[float] = None,
        hold: Optional[bool] = None,
    ) -> None:
        """Update an existing quote record with the final status and optional price/hold.

        May raise StoreUnavailableError on storage failure.
        """
        raise NotImplementedError


class TariffEngine:
    """Tariff calculation engine implementing DT-P pricing rules."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute the freight price according to DT-P.

        DT-P:
          P1: base = 0.87 * weight_kg + 1.13 * distance_km
          P2: if weight_kg > 1244, add 341.00
          P3: if distance_km >= 4912, multiply running total by 1.19 (after P2)
          P4: price = round(result, 2)
        """
        base = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            base += 341.00
        if distance_km >= 4912:
            base *= 1.19
        price = round(base, 2)
        return price


class ScreeningService:
    """External screening provider used to obtain a risk index for a shipper."""

    def screen(self, shipper_id: str) -> int:
        """Return the risk_index for the given shipper.

        May raise ScreeningUnavailableError to indicate a screening outage.
        """
        raise NotImplementedError


class NotificationService:
    """External notification provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send the quote document. Fire-and-forget; failures must not change outcome/response."""
        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send the refusal notice. Fire-and-forget; failures must not change outcome/response."""
        raise NotImplementedError


@dataclass
class QuoteRequest:
    shipper_id: Any
    weight_kg: Any
    distance_km: Any
    declared_value: Any


class QuoteAPI:
    """Orchestrates validation, storage, screening, pricing, and notification."""

    def __init__(self) -> None:
        self.store = QuoteStore()
        self.tariff_engine = TariffEngine()
        self.screening_service = ScreeningService()
        self.notification_service = NotificationService()

    def _validate(self, req: QuoteRequest) -> Optional[Dict[str, Any]]:
        """Validate the incoming request according to DT-V.

        Returns None if valid, or a response dict if invalid.
        """
        # V1: shipper_id present and non-empty
        if not isinstance(req.shipper_id, str) or req.shipper_id.strip() == "":
            return {"status": "rejected: invalid_request"}

        # Helper to check numeric and bounds
        def _is_number(value: Any) -> bool:
            return isinstance(value, (int, float)) and not isinstance(value, bool)

        # V2: weight_kg number, 3 <= weight_kg <= 19400
        if not _is_number(req.weight_kg):
            return {"status": "rejected: invalid_request"}
        if not (3 <= req.weight_kg <= 19400):
            return {"status": "rejected: invalid_request"}

        # V3: distance_km number, 25 <= distance_km <= 7150
        if not _is_number(req.distance_km):
            return {"status": "rejected: invalid_request"}
        if not (25 <= req.distance_km <= 7150):
            return {"status": "rejected: invalid_request"}

        # V4: declared_value number, 50 <= declared_value <= 83000
        if not _is_number(req.declared_value):
            return {"status": "rejected: invalid_request"}
        if not (50 <= req.declared_value <= 83000):
            return {"status": "rejected: invalid_request"}

        return None

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point implementing the CargoQuote flow.

        Expects request dict with keys: shipper_id, weight_kg, distance_km, declared_value.
        Returns a response dict with at least a "status" key, following the spec and decision tables.
        """
        # Extract fields with defaults of None if missing
        quote_req = QuoteRequest(
            shipper_id=request.get("shipper_id"),
            weight_kg=request.get("weight_kg"),
            distance_km=request.get("distance_km"),
            declared_value=request.get("declared_value"),
        )

        # Step 1: Validate (DT-V)
        validation_error = self._validate(quote_req)
        if validation_error is not None:
            # Invalid request: reject immediately, nothing else runs.
            return validation_error

        shipper_id = quote_req.shipper_id
        weight_kg = float(quote_req.weight_kg)
        distance_km = float(quote_req.distance_km)
        declared_value = float(quote_req.declared_value)

        # Step 2: Store draft quote (status draft)
        try:
            quote_id = self.store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            # Storage failure → error: store_unavailable, nothing else runs.
            return {"status": "error: store_unavailable"}

        # Step 3: Request risk index from Screening Service
        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_outage = False
        except ScreeningUnavailableError:
            risk_index = None
            screening_outage = True

        # Screening outage path: price, store as held_unscreened, no notification, hold: true
        if screening_outage:
            price = self.tariff_engine.price(weight_kg=weight_kg, distance_km=distance_km)
            # update stored quote to held_unscreened with price
            self.store.update_quote(quote_id=quote_id, status="held_unscreened", price=price, hold=True)
            return {"status": "held_unscreened", "quote_id": quote_id, "price": price, "hold": True}

        # Step 4: Apply DT-S to risk_index
        # Accept band: risk_index <= 41
        if risk_index <= 41:
            # Step 5: Price (DT-P)
            price = self.tariff_engine.price(weight_kg=weight_kg, distance_km=distance_km)
            # Update stored quote to quoted with price
            self.store.update_quote(quote_id=quote_id, status="quoted", price=price, hold=None)
            # Step 6: Notify (quote document), fire-and-forget
            try:
                self.notification_service.send_quote_document(shipper_id=shipper_id, quote_id=quote_id, price=price)
            except Exception:
                # Notification failures must not change outcome/response
                pass
            # Step 7: Return response
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        # Review band: 42 <= risk_index <= 66
        if 42 <= risk_index <= 66:
            # Update stored quote to review_hold, no pricing, no notification
            self.store.update_quote(quote_id=quote_id, status="review_hold", price=None, hold=None)
            return {"status": "review_hold", "quote_id": quote_id}

        # Refuse band: risk_index >= 67
        if risk_index >= 67:
            # Update stored quote to refused_screening, no pricing
            self.store.update_quote(quote_id=quote_id, status="refused_screening", price=None, hold=None)
            # Notify refusal, fire-and-forget
            try:
                self.notification_service.send_refusal_notice(shipper_id=shipper_id, quote_id=quote_id)
            except Exception:
                # Notification failures must not change outcome/response
                pass
            return {"status": "refused_screening", "quote_id": quote_id}

        # The DT-S table is exhaustive over all integer risk_index values, but if
        # an unexpected value slips through (e.g., non-integer), treat it as invalid
        # screening result and refuse conservatively.
        self.store.update_quote(quote_id=quote_id, status="refused_screening", price=None, hold=None)
        return {"status": "refused_screening", "quote_id": quote_id}


# Module-level function required by the task
_api_instance: Optional[QuoteAPI] = None


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level façade for processing a quote request.

    Delegates to QuoteAPI.handle so that tests can stub collaborators by class name.
    """
    global _api_instance
    if _api_instance is None:
        _api_instance = QuoteAPI()
    return _api_instance.handle(request)

from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the Quote Store is unavailable for storing or updating."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service is unavailable (screening outage)."""


class QuoteStore:
    """Persistence layer for quotes.

    In the real system this would interact with PostgreSQL. Here it's a
    collaborator that can be stubbed in tests.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        May raise StoreUnavailableError on failure.
        """
        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> None:
        """Update an existing quote's status and, optionally, its price.

        May raise StoreUnavailableError on failure.
        """
        raise NotImplementedError


class TariffEngine:
    """Pricing engine implementing DT-P."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # DT-P P1: base = 0.87 * weight_kg + 1.13 * distance_km
        base = 0.87 * weight_kg + 1.13 * distance_km

        # DT-P P2: heavy surcharge if weight_kg > 1244, add 341.00 flat
        if weight_kg > 1244:
            base += 341.00

        # DT-P P3 / REQ-08: long-haul multiplier if distance_km >= 4912,
        # applied AFTER P2
        if distance_km >= 4912:
            base *= 1.19

        # DT-P P4: round to 2 decimal places
        price = round(base, 2)
        return price


class ScreeningService:
    """External denied-party screening provider wrapper."""

    def screen(self, shipper_id: str) -> int:
        """Return the integer risk index for the given shipper.

        May raise ScreeningUnavailableError on outage.
        """
        raise NotImplementedError


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send the quote document. Delivery failure must not affect outcome/response."""
        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send the refusal notice. Delivery failure must not affect outcome/response."""
        raise NotImplementedError


@dataclass
class QuoteRequest:
    shipper_id: Any
    weight_kg: Any
    distance_km: Any
    declared_value: Any


class QuoteAPI:
    """Implements the CargoQuote decision semantics over collaborators."""

    def __init__(self) -> None:
        self.store = QuoteStore()
        self.tariff = TariffEngine()
        self.screening = ScreeningService()
        self.notification = NotificationService()

    # --- Public API ---

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a quote request dict and return a response dict.

        Expected request keys: shipper_id, weight_kg, distance_km, declared_value.
        """
        qr = QuoteRequest(
            shipper_id=request.get("shipper_id"),
            weight_kg=request.get("weight_kg"),
            distance_km=request.get("distance_km"),
            declared_value=request.get("declared_value"),
        )

        # 1. Validate the request (DT-V). Invalid -> reject, stop.
        if not self._is_valid_request(qr):
            return {"status": "rejected: invalid_request"}

        # 2. Store the draft quote with status draft.
        try:
            quote_id = self.store.store_draft(
                shipper_id=str(qr.shipper_id),
                weight_kg=float(qr.weight_kg),
                distance_km=float(qr.distance_km),
                declared_value=float(qr.declared_value),
            )
        except StoreUnavailableError:
            # storage failure -> error: store_unavailable, nothing else runs
            return {"status": "error: store_unavailable"}

        # From here on, the response should carry quote_id on all non-rejection
        # and non-storage-error paths per spec.

        # 3. Request risk index from Screening Service.
        screening_outage = False
        risk_index: Optional[int] = None
        try:
            risk_index = int(self.screening.screen(str(qr.shipper_id)))
        except ScreeningUnavailableError:
            screening_outage = True

        # Handle screening outage separately per DT-S note 5 / REQ-06.
        if screening_outage:
            # Price anyway using DT-P
            price = self.tariff.price(float(qr.weight_kg), float(qr.distance_km))
            try:
                self.store.update_quote(quote_id, status="held_unscreened", price=price)
            except StoreUnavailableError:
                # Spec does not define behavior for update failures; propagate.
                raise

            response: Dict[str, Any] = {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }
            # No notification on outage path.
            return response

        # 4. Apply DT-S to risk_index (accept/review/refuse).
        assert risk_index is not None  # for type checkers; logically ensured above

        status: str
        price: Optional[float] = None

        if risk_index <= 41:
            # Accept row: priced, notified.
            price = self.tariff.price(float(qr.weight_kg), float(qr.distance_km))
            status = "quoted"
            try:
                self.store.update_quote(quote_id, status=status, price=price)
            except StoreUnavailableError:
                # Undefined by spec; propagate.
                raise

            # Fire-and-forget notification. Swallow any delivery failure.
            try:
                self.notification.send_quote_document(str(qr.shipper_id), quote_id, price)
            except Exception:
                # Outcome and response unchanged
                pass

        elif 42 <= risk_index <= 66:
            # Review row: no price, no notification.
            status = "review_hold"
            try:
                self.store.update_quote(quote_id, status=status, price=None)
            except StoreUnavailableError:
                # Undefined by spec; propagate.
                raise

        else:  # risk_index >= 67 (refuse row)
            status = "refused_screening"
            try:
                self.store.update_quote(quote_id, status=status, price=None)
            except StoreUnavailableError:
                # Undefined by spec; propagate.
                raise

            # Fire-and-forget refusal notice.
            try:
                self.notification.send_refusal_notice(str(qr.shipper_id), quote_id)
            except Exception:
                # Outcome and response unchanged
                pass

        # 7. Build and return the response.
        response = {"status": status, "quote_id": quote_id}
        if price is not None and status in ("quoted", "held_unscreened"):
            response["price"] = price
        if status == "held_unscreened":
            response["hold"] = True
        return response

    # --- Internal helpers ---

    def _is_valid_request(self, qr: QuoteRequest) -> bool:
        """Check DT-V validation rules on the request.

        Any violation yields an invalid request.
        """
        # V1 shipper_id present and non-empty
        if qr.shipper_id is None:
            return False
        if not isinstance(qr.shipper_id, str):
            return False
        if qr.shipper_id.strip() == "":
            return False

        # For numeric fields, ensure they are numbers and within bounds.
        # Accept int or float, reject other types.
        for value in (qr.weight_kg, qr.distance_km, qr.declared_value):
            if not isinstance(value, (int, float)):
                return False

        weight = float(qr.weight_kg)
        distance = float(qr.distance_km)
        declared = float(qr.declared_value)

        # V2: 3 <= weight_kg <= 19400
        if not (3 <= weight <= 19400):
            return False

        # V3: 25 <= distance_km <= 7150
        if not (25 <= distance <= 7150):
            return False

        # V4: 50 <= declared_value <= 83000
        if not (50 <= declared <= 83000):
            return False

        return True


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point delegating to QuoteAPI.handle."""
    api = QuoteAPI()
    return api.handle(request)

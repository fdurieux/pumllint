from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable for an operation."""


class ScreeningUnavailableError(Exception):
    """Raised when the screening service is unavailable or times out."""


class QuoteStore:
    """Persistence adapter for quote drafts and their lifecycle status.

    Methods raise StoreUnavailableError when storage is unavailable.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a new draft quote and return its quote_id.

        In a real implementation this would talk to a database. Here it is a
        stub meant to be overridden or monkeypatched by tests.
        """

        raise StoreUnavailableError("QuoteStore.store_draft not implemented")

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> None:
        """Update an existing quote's status (and optionally its price)."""

        raise StoreUnavailableError("QuoteStore.update_quote not implemented")


class TariffEngine:
    """Tariff calculation engine implementing DT-P pricing rules."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute the freight price according to DT-P.

        Steps (normative, in order):
        - P1: base = 0.87 * weight_kg + 1.13 * distance_km
        - P2: if weight_kg > 1244, add 316.00
        - P3: if distance_km >= 4912, multiply running total by 1.19
        - P4: price = round(result, 2)
        """

        base = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            base += 316.00
        if distance_km >= 4912:
            base *= 1.19
        return round(base, 2)


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id: str) -> int:
        """Return an integer risk index for the given shipper.

        May raise ScreeningUnavailableError on outage or timeout.
        """

        raise ScreeningUnavailableError("ScreeningService.screen not implemented")


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send the quote document to the shipper (fire-and-forget)."""

        # In the real world this would call an external service.
        return None

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send a refusal notice to the shipper (fire-and-forget)."""

        # In the real world this would call an external service.
        return None


@dataclass
class QuoteRequest:
    shipper_id: Any
    weight_kg: Any
    distance_km: Any
    declared_value: Any


class QuoteAPI:
    """Orchestrates the CargoQuote instant freight quotation flow."""

    def __init__(
        self,
        quote_store: Optional[QuoteStore] = None,
        tariff_engine: Optional[TariffEngine] = None,
        screening_service: Optional[ScreeningService] = None,
        notification_service: Optional[NotificationService] = None,
    ) -> None:
        self.quote_store = quote_store or QuoteStore()
        self.tariff_engine = tariff_engine or TariffEngine()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    # --- Public entrypoint ---

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a quotation request and return the outcome response dict.

        The request dict must contain: shipper_id, weight_kg, distance_km,
        declared_value. The response dict always contains a "status" key and
        includes "quote_id" whenever a draft was stored, and "price" only on
        priced (accept-band) outcomes.
        """

        # 1. Validate the request (DT-V). Invalid → reject, stop.
        validation_error = self._validate(request)
        if validation_error is not None:
            # Per DT-V: invalid → rejected: invalid_request, nothing else runs.
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # 2. Store the draft quote with status draft.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            # Per spec: return error: store_unavailable; nothing else runs.
            return {"status": "error: store_unavailable"}

        # From here on, a draft exists, so responses must include quote_id.
        response: Dict[str, Any] = {"quote_id": quote_id}

        # 3. Request the shipper's risk index from the Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Assumed policy (OD-1 resolution): treat outage as refused screening
            # so that no price reaches an unscreened shipper.
            status = "refused_screening"
            self.quote_store.update_quote(quote_id, status=status)
            response["status"] = status
            # Notify as a refusal, fire-and-forget: swallow any delivery errors.
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass
            return response

        # 4. Apply the screening decision (DT-S) to the risk index.
        if risk_index <= 41:
            status = "quoted"
            priced = True
            notified = "quote"
        elif 42 <= risk_index <= 66:
            status = "review_hold"
            priced = False
            notified = "none"
        else:  # risk_index >= 67
            status = "refused_screening"
            priced = False
            notified = "refusal"

        # 5. Price the quote (DT-P) — only on priced rows.
        price: Optional[float] = None
        if priced:
            price = self.tariff_engine.price(weight_kg, distance_km)

        # 4 (continued). Update the stored quote to the resulting status (and price).
        if price is not None:
            self.quote_store.update_quote(quote_id, status=status, price=price)
        else:
            self.quote_store.update_quote(quote_id, status=status)

        # 6. Notify the shipper — only on the rows DT-S marks notified.
        # Fire-and-forget: swallow any delivery failures.
        if notified == "quote":
            try:
                # price is not None in this branch by construction.
                self.notification_service.send_quote_document(shipper_id, quote_id, price)  # type: ignore[arg-type]
            except Exception:
                pass
        elif notified == "refusal":
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass

        # 7. Return the response.
        response["status"] = status
        if price is not None:
            response["price"] = price
        return response

    # --- Internal helpers ---

    def _validate(self, request: Dict[str, Any]) -> Optional[str]:
        """Validate the request against DT-V.

        Returns an error message string if invalid, or None if valid. The
        message content is not used by callers, which only inspect validity.
        """

        # Presence and basic type/emptiness checks
        required_fields = ["shipper_id", "weight_kg", "distance_km", "declared_value"]
        for field in required_fields:
            if field not in request:
                return f"missing field: {field}"

        shipper_id = request["shipper_id"]
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return "invalid shipper_id"

        # Numeric bounds per DT-V
        try:
            weight_kg = float(request["weight_kg"])
            distance_km = float(request["distance_km"])
            declared_value = float(request["declared_value"])
        except (TypeError, ValueError):
            return "non-numeric field in numeric input"

        if not (3 <= weight_kg <= 19400):
            return "weight_kg out of bounds"
        if not (25 <= distance_km <= 7150):
            return "distance_km out of bounds"
        if not (50 <= declared_value <= 83000):
            return "declared_value out of bounds"

        return None


# Module-level handle function required by the harness.

def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    api = QuoteAPI()
    return api.handle(request)

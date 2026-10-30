from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the QuoteStore cannot persist or update data."""


class ScreeningUnavailableError(Exception):
    """Raised when the ScreeningService cannot provide a risk index (outage)."""


class QuoteStore:
    """Persistence layer for quotes.

    In this implementation, methods are stubs meant to be overridden or
    monkeypatched in tests. The required behaviour (raising
    StoreUnavailableError on failure) is modelled but not concretely
    implemented.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        On storage failure, this method must raise StoreUnavailableError.
        """
        # Placeholder implementation; real storage should override this.
        raise NotImplementedError("QuoteStore.store_draft must be implemented by the environment")

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> None:
        """Update an existing quote's status and optional price.

        On storage failure, this method must raise StoreUnavailableError.
        """
        # Placeholder implementation; real storage should override this.
        raise NotImplementedError("QuoteStore.update_quote must be implemented by the environment")


class TariffEngine:
    """Tariff engine implementing DT-P pricing rules."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute price according to DT-P.

        Steps (DT-P):
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
        price = round(base, 2)
        return price


class ScreeningService:
    """External service returning a risk index for a shipper."""

    def screen(self, shipper_id: str) -> int:
        """Return an integer risk index for the given shipper.

        On outage, this method must raise ScreeningUnavailableError.
        """
        # Placeholder implementation; real screening should override this.
        raise NotImplementedError("ScreeningService.screen must be implemented by the environment")


class NotificationService:
    """External notification service for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send a quote document to the shipper.

        Any delivery failure must not change the stored quote or response; thus
        callers should treat this as fire-and-forget and ignore failures.
        """
        # Placeholder implementation; real notification should override this.
        raise NotImplementedError("NotificationService.send_quote_document must be implemented by the environment")

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send a refusal notice to the shipper.

        Any delivery failure must not change the stored quote or response; thus
        callers should treat this as fire-and-forget and ignore failures.
        """
        # Placeholder implementation; real notification should override this.
        raise NotImplementedError("NotificationService.send_refusal_notice must be implemented by the environment")


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    def _validate(self, request: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Validate the request according to DT-V.

        Returns a dict with parsed values on success, or None if invalid.
        """
        required_fields = ["shipper_id", "weight_kg", "distance_km", "declared_value"]
        for field in required_fields:
            if field not in request:
                return None

        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return None

        def _as_number(value: Any) -> Optional[float]:
            if isinstance(value, (int, float)):
                return float(value)
            return None

        weight_kg_raw = request.get("weight_kg")
        distance_km_raw = request.get("distance_km")
        declared_value_raw = request.get("declared_value")

        weight_kg = _as_number(weight_kg_raw)
        distance_km = _as_number(distance_km_raw)
        declared_value = _as_number(declared_value_raw)

        if weight_kg is None or distance_km is None or declared_value is None:
            return None

        # DT-V bounds
        if not (3 <= weight_kg <= 19400):
            return None
        if not (25 <= distance_km <= 7150):
            return None
        if not (50 <= declared_value <= 83000):
            return None

        return {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
        }

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a quote request according to the CargoQuote specification."""
        # 1. Validate the request (DT-V). Invalid → reject, stop.
        validated = self._validate(request)
        if validated is None:
            return {"status": "rejected: invalid_request"}

        shipper_id = validated["shipper_id"]
        weight_kg = validated["weight_kg"]
        distance_km = validated["distance_km"]
        declared_value = validated["declared_value"]

        # 2. Store the draft quote with status draft.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            # On storage failure: return error; no screening, no pricing, no notification.
            return {"status": "error: store_unavailable"}

        # 3. Request the shipper's risk index from the Screening Service.
        # Behaviour on ScreeningUnavailableError is intentionally not defined
        # here (OD-1 open); the exception is allowed to propagate.
        risk_index = self.screening_service.screen(shipper_id)

        response: Dict[str, Any] = {"quote_id": quote_id}

        # 4. Apply screening decision (DT-S) and update stored quote.
        if risk_index <= 41:
            # Accept row: quoted, priced, notified (quote document).
            status = "quoted"
            # 5. Price the quote (DT-P).
            price = self.tariff_engine.price(weight_kg=weight_kg, distance_km=distance_km)
            # Update stored quote with status and price.
            self.quote_store.update_quote(quote_id=quote_id, status=status, price=price)
            # 6. Notify the shipper (fire-and-forget).
            try:
                self.notification_service.send_quote_document(
                    shipper_id=shipper_id,
                    quote_id=quote_id,
                    price=price,
                )
            except Exception:
                # Fire-and-forget: ignore any notification failure.
                pass
            response["status"] = status
            response["price"] = price

        elif 42 <= risk_index <= 66:
            # Review row: review_hold, not priced, not notified.
            status = "review_hold"
            self.quote_store.update_quote(quote_id=quote_id, status=status, price=None)
            response["status"] = status

        else:  # risk_index >= 67
            # Refuse row: refused_screening, not priced, refusal notice sent.
            status = "refused_screening"
            self.quote_store.update_quote(quote_id=quote_id, status=status, price=None)
            try:
                self.notification_service.send_refusal_notice(
                    shipper_id=shipper_id,
                    quote_id=quote_id,
                )
            except Exception:
                # Fire-and-forget: ignore any notification failure.
                pass
            response["status"] = status

        return response


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point required by the harness.

    This function instantiates the default collaborators. In a production or
    test environment, these classes are expected to be monkeypatched or
    subclassed to provide concrete behaviour.
    """
    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)

from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the QuoteStore is unavailable for storage operations."""
    pass


class ScreeningUnavailableError(Exception):
    """Raised when the ScreeningService is unavailable."""
    pass


class QuoteStore:
    """Persistence collaborator for quotes.

    In tests, methods are expected to be stubbed by name.
    """

    def store_draft(self, request: Dict[str, Any]) -> str:
        """Store a new draft quote and return its quote_id.

        May raise StoreUnavailableError on failure.
        """
        raise NotImplementedError

    def update_quote(self, quote_id: str, **fields: Any) -> None:
        """Update an existing quote with given fields (e.g. status, price).

        May raise StoreUnavailableError on failure.
        """
        raise NotImplementedError


class TariffEngine:
    """Pricing collaborator.

    It encapsulates the DT-P pricing logic.
    """

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute the price according to DT-P.

        Implemented here per the approved tariff rules.
        """
        # P1: base = 0.87 * weight_kg + 1.13 * distance_km (A:dt:P1|formula@v1)
        base = 0.87 * weight_kg + 1.13 * distance_km

        # P2: heavy surcharge if weight_kg > 1244, add 341.00 flat (A:dt:P2|threshold@v2, A:dt:P2|surcharge@v2)
        if weight_kg > 1244:
            base += 341.00

        # P3: long-haul multiplier if distance_km >= 4912, multiply running total by 1.19 after P2
        # (A:dt:P3|threshold@v1, A:dt:P3|factor@v1, A:dt:P3|order@v2)
        if distance_km >= 4912:
            base *= 1.19

        # P4: price = round(result, 2) (A:dt:P4|rounding@v1)
        price = round(base, 2)
        return price


class ScreeningService:
    """External screening collaborator to obtain a shipper risk index."""

    def screen(self, shipper_id: str, declared_value: float) -> int:
        """Return the risk index for the given shipper.

        May raise ScreeningUnavailableError on outage.
        """
        raise NotImplementedError


class NotificationService:
    """Fire-and-forget notification collaborator."""

    def send_quote_document(self, quote_id: str) -> None:
        """Send a quote document. Failures are fire-and-forget and do not affect response."""
        raise NotImplementedError

    def send_refusal_notice(self, quote_id: str) -> None:
        """Send a refusal notice. Failures are fire-and-forget and do not affect response."""
        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # Constants derived from specification / decision tables
    WEIGHT_MIN: float = 3.0
    WEIGHT_MAX: float = 19400.0
    DISTANCE_MIN: float = 25.0
    DISTANCE_MAX: float = 7150.0
    DECLARED_MIN: float = 50.0
    DECLARED_MAX: float = 83000.0

    ACCEPT_MAX: int = 41  # risk_index <= 41 => accept (quoted)
    REVIEW_MIN: int = 42  # 42 <= risk_index <= 66 => review_hold
    REVIEW_MAX: int = 66
    REFUSE_MIN: int = 67  # risk_index >= 67 => refused_screening

    STATUS_QUOTED: str = "quoted"
    STATUS_REVIEW_HOLD: str = "review_hold"
    STATUS_REFUSED_SCREENING: str = "refused_screening"
    STATUS_HELD_UNSCREENED: str = "held_unscreened"
    STATUS_REJECTED_INVALID: str = "rejected: invalid_request"
    STATUS_ERROR_STORE_UNAVAILABLE: str = "error: store_unavailable"

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a quote request according to the governed specification.

        request keys: shipper_id, weight_kg, distance_km, declared_value.
        Returns a response dict with at least a "status" key, and optionally
        quote_id, price, and hold, respecting the DT-S and API spec rules.
        """
        # 1. validate (A:spec:flow|order@v1, A:dt:invalid_request|behaviour@v1)
        shipper_id = request.get("shipper_id")
        weight_kg = request.get("weight_kg")
        distance_km = request.get("distance_km")
        declared_value = request.get("declared_value")

        if not isinstance(shipper_id, str) or not shipper_id:
            return {"status": self.STATUS_REJECTED_INVALID}

        # Basic type/convert handling: specification is numeric; we treat non-numeric
        # as invalid request as well.
        try:
            w = float(weight_kg)
            d = float(distance_km)
            v = float(declared_value)
        except (TypeError, ValueError):
            return {"status": self.STATUS_REJECTED_INVALID}

        if not (self.WEIGHT_MIN <= w <= self.WEIGHT_MAX):
            return {"status": self.STATUS_REJECTED_INVALID}
        if not (self.DISTANCE_MIN <= d <= self.DISTANCE_MAX):
            return {"status": self.STATUS_REJECTED_INVALID}
        if not (self.DECLARED_MIN <= v <= self.DECLARED_MAX):
            return {"status": self.STATUS_REJECTED_INVALID}

        # 2. store draft (A:spec:QuoteAPI|on_store_failure@v1)
        try:
            quote_id = self.quote_store.store_draft(
                {
                    "shipper_id": shipper_id,
                    "weight_kg": w,
                    "distance_km": d,
                    "declared_value": v,
                    "status": "draft",
                }
            )
        except StoreUnavailableError:
            # On storage failure nothing else runs (A:dt:QuoteAPI|on_store_failure@v1)
            return {"status": self.STATUS_ERROR_STORE_UNAVAILABLE}

        # 3. screen (A:spec:QuoteAPI|on_screening_outage@v1)
        try:
            risk_index = self.screening_service.screen(shipper_id, v)
        except ScreeningUnavailableError:
            # Screening outage path (DT-S note 5): price, held_unscreened, not notified, hold: true
            price = self.tariff_engine.price(w, d)
            try:
                self.quote_store.update_quote(
                    quote_id,
                    status=self.STATUS_HELD_UNSCREENED,
                    price=price,
                )
            except StoreUnavailableError:
                # Store failure here is not explicitly specified after draft success.
                # We propagate as store_unavailable error while a quote_id exists,
                # but we must not attempt further processing.
                return {"status": self.STATUS_ERROR_STORE_UNAVAILABLE, "quote_id": quote_id}

            response: Dict[str, Any] = {
                "status": self.STATUS_HELD_UNSCREENED,
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }
            return response

        # 4. decide based on risk_index (DT-S)
        # Ensure risk_index is an int-like value
        try:
            ri = int(risk_index)
        except (TypeError, ValueError):
            # Specification does not define behaviour for nonsensical risk_index.
            # Conservatively refuse screening with notification but no price.
            ri = self.REFUSE_MIN

        if ri <= self.ACCEPT_MAX:
            outcome = self.STATUS_QUOTED
        elif self.REVIEW_MIN <= ri <= self.REVIEW_MAX:
            outcome = self.STATUS_REVIEW_HOLD
        else:  # ri >= REFUSE_MIN
            outcome = self.STATUS_REFUSED_SCREENING

        # 5. price (only for priced rows, per DT-S and response|price_presence)
        price: Optional[float] = None
        if outcome == self.STATUS_QUOTED:
            price = self.tariff_engine.price(w, d)

        # 6. update stored quote and notify according to outcome
        if outcome == self.STATUS_QUOTED:
            # Accept row: quote issued, priced, notified with quote document
            try:
                self.quote_store.update_quote(
                    quote_id,
                    status=self.STATUS_QUOTED,
                    price=price,
                    risk_index=ri,
                )
            except StoreUnavailableError:
                return {"status": self.STATUS_ERROR_STORE_UNAVAILABLE, "quote_id": quote_id}

            try:
                self.notification_service.send_quote_document(quote_id)
            except Exception:
                # Fire-and-forget: response and stored quote remain unchanged
                # (A:dt:QuoteAPI|on_notification_failure@v1)
                pass

            response = {
                "status": self.STATUS_QUOTED,
                "quote_id": quote_id,
            }
            if price is not None:
                response["price"] = price
            return response

        if outcome == self.STATUS_REVIEW_HOLD:
            # Review row: held for manual review, not priced, not notified
            try:
                self.quote_store.update_quote(
                    quote_id,
                    status=self.STATUS_REVIEW_HOLD,
                    risk_index=ri,
                )
            except StoreUnavailableError:
                return {"status": self.STATUS_ERROR_STORE_UNAVAILABLE, "quote_id": quote_id}

            return {
                "status": self.STATUS_REVIEW_HOLD,
                "quote_id": quote_id,
            }

        # outcome == refused_screening
        try:
            self.quote_store.update_quote(
                quote_id,
                status=self.STATUS_REFUSED_SCREENING,
                risk_index=ri,
            )
        except StoreUnavailableError:
            return {"status": self.STATUS_ERROR_STORE_UNAVAILABLE, "quote_id": quote_id}

        try:
            self.notification_service.send_refusal_notice(quote_id)
        except Exception:
            # Fire-and-forget semantics
            pass

        return {
            "status": self.STATUS_REFUSED_SCREENING,
            "quote_id": quote_id,
        }


# Module-level handle(request) required by harness

# Instantiate default collaborators; in tests these can be replaced or their
# class methods stubbed.
_default_quote_api = QuoteAPI(
    quote_store=QuoteStore(),
    tariff_engine=TariffEngine(),
    screening_service=ScreeningService(),
    notification_service=NotificationService(),
)


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entrypoint delegating to QuoteAPI.handle."""
    return _default_quote_api.handle(request)

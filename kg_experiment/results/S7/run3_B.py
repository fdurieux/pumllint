from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


class StoreUnavailableError(Exception):
    """Raised when the Quote Store is unavailable for draft or update operations."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service is unavailable (screening outage)."""


class QuoteStore:
    """Persistence layer for quotes.

    In this implementation, methods are stubs meant to be overridden or
    monkeypatched by a test harness.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a new draft quote and return its quote_id.

        May raise StoreUnavailableError on storage failure.
        """

        # Placeholder implementation; tests are expected to stub this.
        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: float | None = None) -> None:
        """Update an existing quote's status and optionally its price.

        May raise StoreUnavailableError on storage failure (not normatively
        specified for this stage; behaviour in that case is left to callers).
        """

        # Placeholder implementation; tests are expected to stub this.
        raise NotImplementedError


class TariffEngine:
    """Tariff rules implementation (DT-P)."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute the freight price according to DT-P.

        Steps (DT-P):
        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: if weight_kg > 1244, add 316.00
        P3: if distance_km >= 4912, multiply running total by 1.19 (after P2)
        P4: price = round(result, 2)
        """

        # P1
        result = 0.87 * float(weight_kg) + 1.13 * float(distance_km)
        # P2
        if weight_kg > 1244:
            result += 316.00
        # P3
        if distance_km >= 4912:
            result *= 1.19
        # P4
        return round(result, 2)


class ScreeningService:
    """External denied-party screening provider wrapper."""

    def screen(self, shipper_id: str) -> int:
        """Return the integer risk_index for the given shipper.

        May raise ScreeningUnavailableError to represent a screening outage.
        """

        # Placeholder implementation; tests are expected to stub this.
        raise NotImplementedError


class NotificationService:
    """External notification provider wrapper.

    Notification calls are fire-and-forget: delivery failure must not
    affect the stored quote or API response.
    """

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send a quote document to the shipper.

        May raise an exception to signal delivery failure; callers must
        ignore such failures with respect to the outcome.
        """

        # Placeholder implementation; tests are expected to stub this.
        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send a refusal notice to the shipper.

        May raise an exception to signal delivery failure; callers must
        ignore such failures with respect to the outcome.
        """

        # Placeholder implementation; tests are expected to stub this.
        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # Validation bounds from DT-V
    MIN_WEIGHT = 3
    MAX_WEIGHT = 19400
    MIN_DISTANCE = 25
    MAX_DISTANCE = 7150
    MIN_DECLARED_VALUE = 50
    MAX_DECLARED_VALUE = 83000

    # Screening decision band boundaries from DT-S
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

    def _is_valid(self, request: Dict[str, Any]) -> bool:
        """Check DT-V validation rules.

        An invalid request is rejected immediately with status
        "rejected: invalid_request" and no further processing.
        """

        # V1: shipper_id present and non-empty
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or not shipper_id:
            return False

        # V2: weight_kg number, 3 <= weight_kg <= 19400
        weight = request.get("weight_kg")
        if not isinstance(weight, (int, float)):
            return False
        if not (self.MIN_WEIGHT <= float(weight) <= self.MAX_WEIGHT):
            return False

        # V3: distance_km number, 25 <= distance_km <= 7150
        distance = request.get("distance_km")
        if not isinstance(distance, (int, float)):
            return False
        if not (self.MIN_DISTANCE <= float(distance) <= self.MAX_DISTANCE):
            return False

        # V4: declared_value number, 50 <= declared_value <= 83000
        declared_value = request.get("declared_value")
        if not isinstance(declared_value, (int, float)):
            return False
        if not (self.MIN_DECLARED_VALUE <= float(declared_value) <= self.MAX_DECLARED_VALUE):
            return False

        return True

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Main quotation flow implementing the CargoQuote spec.

        Implements the flow order and decision semantics defined in
        contract/spec.md and contract/decision_table.md.
        """

        # 1. Validate request (DT-V). Invalid -> reject, stop.
        if not self._is_valid(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # 2. Store the draft quote with status draft. On failure: error and stop.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Prepare base response with quote_id for all stored drafts
        response: Dict[str, Any] = {"status": None, "quote_id": quote_id}

        # 3. Request risk index. Handle screening outage specially.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage path: price, store held_unscreened, no notification.
            price = self.tariff_engine.price(weight_kg, distance_km)
            try:
                self.quote_store.update_quote(
                    quote_id=quote_id,
                    status="held_unscreened",
                    price=price,
                )
            except StoreUnavailableError:
                # Behaviour not normatively specified; propagate or ignore would
                # both be plausible. We choose to propagate to surface the issue.
                raise

            response["status"] = "held_unscreened"
            response["price"] = price
            response["hold"] = True
            return response

        # 4. Apply DT-S based on risk_index
        if risk_index <= self.ACCEPT_MAX:
            # Accept row: quote issued, priced, notified with quote document.
            price = self.tariff_engine.price(weight_kg, distance_km)
            try:
                self.quote_store.update_quote(
                    quote_id=quote_id,
                    status="quoted",
                    price=price,
                )
            except StoreUnavailableError:
                # Not specified; propagate to signal inconsistency.
                raise

            # Fire-and-forget notification: ignore delivery failures.
            try:
                self.notification_service.send_quote_document(
                    shipper_id=shipper_id,
                    quote_id=quote_id,
                    price=price,
                )
            except Exception:
                # Outcome and response unchanged on notification failure.
                pass

            response["status"] = "quoted"
            response["price"] = price
            return response

        if self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review row: held for manual review, no price, no notification.
            try:
                self.quote_store.update_quote(
                    quote_id=quote_id,
                    status="review_hold",
                    price=None,
                )
            except StoreUnavailableError:
                # Not specified; propagate.
                raise

            response["status"] = "review_hold"
            # No price field in response.
            return response

        if risk_index >= self.REFUSE_MIN:
            # Refuse row: refused, no pricing, refusal notice sent.
            try:
                self.quote_store.update_quote(
                    quote_id=quote_id,
                    status="refused_screening",
                    price=None,
                )
            except StoreUnavailableError:
                # Not specified; propagate.
                raise

            # Fire-and-forget refusal notification.
            try:
                self.notification_service.send_refusal_notice(
                    shipper_id=shipper_id,
                    quote_id=quote_id,
                )
            except Exception:
                # Outcome and response unchanged on notification failure.
                pass

            response["status"] = "refused_screening"
            # No price field in response.
            return response

        # The decision tables specify that all integer risk_index values fall
        # into one of the above bands. If we somehow get here, treat as an
        # internal error.
        raise ValueError(f"Unexpected risk_index value: {risk_index}")


# Module-level handle function expected by the harness.

def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point that constructs collaborators and delegates.

    Tests can monkeypatch QuoteStore, TariffEngine, ScreeningService,
    and NotificationService by class name and method name.
    """

    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)

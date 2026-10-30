from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the QuoteStore cannot store or update a quote."""


class ScreeningUnavailableError(Exception):
    """Raised when the ScreeningService cannot complete screening."""


class QuoteStore:
    """Persistence for quotes.

    Methods are expected to raise StoreUnavailableError when storage fails.
    """

    def store_draft(self, data: Dict[str, Any]) -> str:
        """Store a draft quote and return its quote_id.

        May raise StoreUnavailableError.
        """
        raise NotImplementedError

    def update_quote(self, quote_id: str, updates: Dict[str, Any]) -> None:
        """Update an existing quote.

        May raise StoreUnavailableError.
        """
        raise NotImplementedError


class TariffEngine:
    """Pricing engine implementing DT-P (P1–P4)."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # P1: base = 0.87 * weight_kg + 1.13 * distance_km  [A:dt:P1|formula@v1]
        result = 0.87 * weight_kg + 1.13 * distance_km

        # P2: heavy surcharge: if weight_kg > 1244, add 316.00 (flat)
        # [A:dt:P2|threshold@v1, A:dt:P2|surcharge@v1]
        if weight_kg > 1244:
            result += 316.00

        # P3: long-haul multiplier: if distance_km >= 4912, multiply running
        # total by 1.19 — applied after P2
        # [A:dt:P3|threshold@v1, A:dt:P3|factor@v1, A:dt:P3|order@v1]
        if distance_km >= 4912:
            result *= 1.19

        # P4: price = round(result, 2)  [A:dt:P4|rounding@v1]
        price = round(result, 2)
        return price


class ScreeningService:
    """Service providing a shipper risk index for screening decisions."""

    def screen(self, shipper_id: str, declared_value: float) -> int:
        """Return a risk index integer.

        May raise ScreeningUnavailableError on outage.
        """
        raise NotImplementedError


class NotificationService:
    """Fire-and-forget notifications for quotes and refusals."""

    def send_quote_document(self, quote_id: str) -> None:
        """Send a quote document notification.

        Failures MUST NOT change stored quote or API response
        [A:dt:QuoteAPI|on_notification_failure@v1].
        """
        raise NotImplementedError

    def send_refusal_notice(self, quote_id: str) -> None:
        """Send a refusal notice notification (fire-and-forget)."""
        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # Validation bounds from DT-V
    MIN_WEIGHT = 3.0  # [A:dt:weight_kg|min@v1]
    MAX_WEIGHT = 19400.0  # [A:dt:weight_kg|max@v1]

    MIN_DISTANCE = 25.0  # [A:dt:distance_km|min@v1]
    MAX_DISTANCE = 7150.0  # [A:dt:distance_km|max@v1]

    MIN_DECLARED_VALUE = 50.0  # [A:dt:declared_value|min@v1]
    MAX_DECLARED_VALUE = 83000.0  # [A:dt:declared_value|max@v1]

    # Screening thresholds DT-S
    ACCEPT_MAX = 41  # risk_index <= 41 => accept [A:dt:S-accept|max@v1]
    REVIEW_MIN = 42  # [A:dt:S-review|min@v1]
    REVIEW_MAX = 66  # [A:dt:S-review|max@v1]
    REFUSE_MIN = 67  # [A:dt:S-refuse|min@v1]

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an instant freight quotation request.

        Implements the governed flow order:
        validate > store > screen > decide > price > notify > respond
        [A:spec:flow|order@v1].
        """

        # --- Step 1: validate ---
        shipper_id = request.get("shipper_id")
        weight_kg = request.get("weight_kg")
        distance_km = request.get("distance_km")
        declared_value = request.get("declared_value")

        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            # Invalid request behaviour [A:dt:invalid_request|behaviour@v1]
            return {"status": "rejected: invalid_request"}

        try:
            weight_val = float(weight_kg)
            distance_val = float(distance_km)
            declared_val = float(declared_value)
        except (TypeError, ValueError):
            return {"status": "rejected: invalid_request"}

        if not (self.MIN_WEIGHT <= weight_val <= self.MAX_WEIGHT):
            return {"status": "rejected: invalid_request"}
        if not (self.MIN_DISTANCE <= distance_val <= self.MAX_DISTANCE):
            return {"status": "rejected: invalid_request"}
        if not (self.MIN_DECLARED_VALUE <= declared_val <= self.MAX_DECLARED_VALUE):
            return {"status": "rejected: invalid_request"}

        # --- Step 2: store draft ---
        draft_data = {
            "shipper_id": shipper_id,
            "weight_kg": weight_val,
            "distance_km": distance_val,
            "declared_value": declared_val,
            "status": "draft",
        }

        try:
            quote_id = self.quote_store.store_draft(draft_data)
        except StoreUnavailableError:
            # On storage failure: status error: store_unavailable; no screening,
            # no pricing, no notification [A:spec:QuoteAPI|on_store_failure@v1]
            return {"status": "error: store_unavailable"}

        # From here on, a draft was stored, so quote_id will be present in
        # all non-error responses [A:spec:response|quote_id_presence@v1].

        # --- Step 3: screening ---
        screening_outage = False
        risk_index: Optional[int] = None
        try:
            risk_index = self.screening_service.screen(shipper_id, declared_val)
        except ScreeningUnavailableError:
            screening_outage = True

        # --- Step 4: decide & Step 5: price (when applicable) ---
        response: Dict[str, Any] = {"quote_id": quote_id}

        if screening_outage:
            # Screening outage path [A:spec:QuoteAPI|on_screening_outage@v1]
            price = self.tariff_engine.price(weight_val, distance_val)
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {"status": "held_unscreened", "price": price},
                )
            except StoreUnavailableError:
                # Spec only defines store failure on initial draft; for
                # updates we surface as store_unavailable and avoid
                # misrepresenting stored state.
                return {"status": "error: store_unavailable"}

            response["status"] = "held_unscreened"
            response["price"] = price
            response["hold"] = True  # held_unscreened only
            return response

        # Normal screening result path: risk_index is available
        assert risk_index is not None

        if risk_index <= self.ACCEPT_MAX:
            # Accept row: quote issued, priced, notified, status quoted
            # [A:dt:S-accept|status@v1, A:dt:S-accept|priced@v1,
            #  A:dt:S-accept|notified@v1]
            price = self.tariff_engine.price(weight_val, distance_val)
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {"status": "quoted", "price": price},
                )
            except StoreUnavailableError:
                return {"status": "error: store_unavailable"}

            # Fire-and-forget notification; failures must not affect response
            try:
                self.notification_service.send_quote_document(quote_id)
            except Exception:
                # Fire-and-forget: ignore failures
                # [A:dt:QuoteAPI|on_notification_failure@v1]
                pass

            response["status"] = "quoted"
            response["price"] = price
            return response

        if self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review row: held for manual review; no pricing, no notification
            # status review_hold [A:dt:S-review|status@v1,
            #                    A:dt:S-review|priced@v1,
            #                    A:dt:S-review|notified@v1]
            try:
                self.quote_store.update_quote(quote_id, {"status": "review_hold"})
            except StoreUnavailableError:
                return {"status": "error: store_unavailable"}

            response["status"] = "review_hold"
            return response

        # risk_index >= REFUSE_MIN: refusal row
        # [A:dt:S-refuse|min@v1, A:dt:S-refuse|status@v1,
        #  A:dt:S-refuse|priced@v1, A:dt:S-refuse|notified#1@v1]
        if risk_index >= self.REFUSE_MIN:
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {"status": "refused_screening"},
                )
            except StoreUnavailableError:
                return {"status": "error: store_unavailable"}

            # Fire-and-forget refusal notice
            try:
                self.notification_service.send_refusal_notice(quote_id)
            except Exception:
                # Fire-and-forget: ignore failures
                pass

            response["status"] = "refused_screening"
            return response

        # The DMN and decision tables cover all intended ranges; if an
        # out-of-range risk_index appears, treat it as invalid request rather
        # than guess behaviour.
        return {"status": "rejected: invalid_request"}


# Module-level handle function for the harness
_default_api: Optional[QuoteAPI] = None


def _get_default_api() -> QuoteAPI:
    global _default_api
    if _default_api is None:
        _default_api = QuoteAPI(
            quote_store=QuoteStore(),
            tariff_engine=TariffEngine(),
            screening_service=ScreeningService(),
            notification_service=NotificationService(),
        )
    return _default_api


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Entry point required by the harness.

    Delegates to QuoteAPI.handle.
    """

    api = _get_default_api()
    return api.handle(request)

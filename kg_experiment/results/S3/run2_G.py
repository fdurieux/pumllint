from dataclasses import dataclass
from typing import Any, Dict


class StoreUnavailableError(Exception):
    """Raised when the QuoteStore is unavailable for storing or updating quotes."""


class ScreeningUnavailableError(Exception):
    """Raised when the ScreeningService is unavailable to provide a risk index."""


# ASSUMPTION A:seq:S-accept|max@v1
# Placeholder numeric thresholds for risk banding; actual values must be confirmed.
ACCEPT_MAX = 41.0
# ASSUMPTION A:seq:S-review|min@v1
REVIEW_MIN = 42.0
# ASSUMPTION A:seq:S-review|max@v1
REVIEW_MAX = 66.0
# ASSUMPTION A:seq:S-refuse|min@v1
REFUSE_MIN = 67.0


class QuoteStore:
    """Persistence boundary for quotes.

    The real implementation is provided elsewhere; this is just the
    interface expected by QuoteAPI. Methods may raise StoreUnavailableError
    when storage or update fails. [A:spec:QuoteAPI|on_store_failure@v1]
    """

    def store_draft(self, payload: Dict[str, Any]) -> str:
        """Store a new draft quote and return its quote_id.

        May raise StoreUnavailableError on failure.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, fields: Dict[str, Any]) -> None:
        """Update an existing quote with new fields.

        May raise StoreUnavailableError on failure.
        """

        raise NotImplementedError


class TariffEngine:
    """Pricing engine implementing DT-P. [A:dt:P1|formula@v1, A:dt:P2|threshold@v1, A:dt:P3|threshold@v1, A:dt:P4|rounding@v1]"""

    def price(self, weight_kg: float, distance_km: float) -> float:
        base = 0.87 * weight_kg + 1.13 * distance_km  # A:dt:P1|formula@v1

        if weight_kg > 1244:  # A:dt:P2|threshold@v1
            base += 316.00  # A:dt:P2|surcharge@v1

        if distance_km >= 4912:  # A:dt:P3|threshold@v1
            base *= 1.19  # A:dt:P3|factor@v1, A:dt:P3|order@v1

        price = round(base, 2)  # A:dt:P4|rounding@v1
        return price


class ScreeningService:
    """Service providing shipper risk index.

    ScreeningService.screen may raise ScreeningUnavailableError to signal an
    outage. Other error modes are out of scope by assumption.
    [A:spec:QuoteAPI|on_screening_outage@v1]
    """

    def screen(self, shipper_id: str, declared_value: float) -> Dict[str, Any]:
        """Return a dict containing at least a numeric 'risk_index' field.

        May raise ScreeningUnavailableError when screening is unavailable.
        """

        raise NotImplementedError


class NotificationService:
    """Notification boundary for quote documents and refusal notices.

    Failures are fire-and-forget and must not affect response or storage.
    [A:dt:QuoteAPI|on_notification_failure@v1]
    """

    def send_quote_document(self, quote_id: str, price: float) -> None:
        raise NotImplementedError

    def send_refusal_notice(self, quote_id: str) -> None:
        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # Public entry point mirroring module-level handle
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process an instant freight quotation request.

        Implements the governed flow:
        1. validate
        2. store
        3. screen
        4. decide
        5. price
        6. notify
        7. respond
        [A:spec:flow|order@v1]
        """

        # 1. validate input fields
        validation_error = self._validate_request(request)
        if validation_error is not None:
            # Invalid request: reject immediately. [A:dt:invalid_request|behaviour@v1]
            return {
                "status": "rejected: invalid_request",
            }

        shipper_id = str(request["shipper_id"])
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # 2. store draft quote
        try:
            quote_id = self.quote_store.store_draft(
                {
                    "shipper_id": shipper_id,
                    "weight_kg": weight_kg,
                    "distance_km": distance_km,
                    "declared_value": declared_value,
                    "status": "draft",
                }
            )
        except StoreUnavailableError:
            # On storage failure nothing else runs; status error: store_unavailable.
            # [A:spec:QuoteAPI|on_store_failure@v1]
            return {
                "status": "error: store_unavailable",
            }

        # 3. screen
        screening_outage = False
        risk_index: float | None = None
        try:
            screening_result = self.screening_service.screen(
                shipper_id=shipper_id,
                declared_value=declared_value,
            )
            # ASSUMPTION A:seq:QuoteAPI|on_screening_outage@v1
            risk_index = float(screening_result["risk_index"])
        except ScreeningUnavailableError:
            # Screening outage path. [A:spec:QuoteAPI|on_screening_outage@v1]
            screening_outage = True

        # 4. decide and 5. price per outcome
        if screening_outage:
            # Screening outage: price anyway, store held_unscreened, no notify.
            # [A:spec:QuoteAPI|on_screening_outage@v1]
            price = self.tariff_engine.price(weight_kg, distance_km)
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {
                        "status": "held_unscreened",
                        "price": price,
                        "hold": True,
                    },
                )
            except StoreUnavailableError:
                # Spec does not define behaviour for update failure post-draft;
                # we propagate as a generic store error consistent with the
                # criticality of storage, without further actions.
                # (Open question for governance.)
                return {
                    "status": "error: store_unavailable",
                }

            response: Dict[str, Any] = {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }
            return response

        # Normal screening path: risk_index is available
        assert risk_index is not None

        # Decision branches by risk band using DT-S semantics, with assumed
        # numeric thresholds. [A:dt:S-accept|status@v1, A:dt:S-review|status@v1, A:dt:S-refuse|status@v1]
        if risk_index <= ACCEPT_MAX:
            # ACCEPT ROW: price, notify with quote document, status quoted.
            # [A:dt:S-accept|priced@v1, A:dt:S-accept|notified@v1, A:dt:S-accept|status@v1]
            price = self.tariff_engine.price(weight_kg, distance_km)
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {
                        "status": "quoted",
                        "price": price,
                    },
                )
            except StoreUnavailableError:
                return {
                    "status": "error: store_unavailable",
                }

            # Notification is fire-and-forget; failures must not change
            # stored quote or response. [A:dt:QuoteAPI|on_notification_failure@v1]
            try:
                self.notification_service.send_quote_document(quote_id, price)
            except Exception:
                pass

            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # REVIEW ROW: held for manual review; no pricing, no notification.
            # [A:dt:S-review|priced@v1, A:dt:S-review|notified@v1, A:dt:S-review|status@v1]
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {
                        "status": "review_hold",
                    },
                )
            except StoreUnavailableError:
                return {
                    "status": "error: store_unavailable",
                }

            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }

        if risk_index >= REFUSE_MIN:
            # REFUSE ROW: refused_screening, refusal notice, no pricing.
            # [A:dt:S-refuse|priced@v1, A:dt:S-refuse|notified#1@v1, A:dt:S-refuse|status@v1]
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {
                        "status": "refused_screening",
                    },
                )
            except StoreUnavailableError:
                return {
                    "status": "error: store_unavailable",
                }

            try:
                self.notification_service.send_refusal_notice(quote_id)
            except Exception:
                pass

            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }

        # If risk_index falls into a gap due to threshold assumptions,
        # default to review_hold as a conservative posture; this situation
        # should not occur once thresholds are governed.
        try:
            self.quote_store.update_quote(
                quote_id,
                {
                    "status": "review_hold",
                },
            )
        except StoreUnavailableError:
            return {
                "status": "error: store_unavailable",
            }

        return {
            "status": "review_hold",
            "quote_id": quote_id,
        }


# Module-level facade for the environment expected by the harness.

def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    quote_api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return quote_api.handle(request)

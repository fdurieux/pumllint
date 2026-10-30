from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the QuoteStore cannot persist or update a quote."""


class ScreeningUnavailableError(Exception):
    """Raised when the ScreeningService cannot return a risk index."""


class QuoteStore:
    """Persistence boundary for quotes.

    Methods may raise StoreUnavailableError on storage failure.
    """

    def store_draft(self, quote: Dict[str, Any]) -> str:
        """Persist a new draft quote and return its quote_id.

        May raise StoreUnavailableError.
        """
        raise NotImplementedError

    def update_quote(self, quote_id: str, fields: Dict[str, Any]) -> None:
        """Update an existing quote with the given fields.

        May raise StoreUnavailableError.
        """
        raise NotImplementedError


class TariffEngine:
    """Pricing boundary implementing DT-P (P1–P4)."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # P1: base = 0.87 * weight_kg + 1.13 * distance_km
        base = 0.87 * weight_kg + 1.13 * distance_km

        # P2: heavy surcharge: if weight_kg > 1244, add 316.00 (flat)
        if weight_kg > 1244:
            base += 316.00

        # P3: long-haul multiplier: if distance_km >= 4912, multiply by 1.19 — applied after P2
        if distance_km >= 4912:
            base *= 1.19

        # P4: price = round(result, 2)
        price = round(base, 2)
        return price


class ScreeningService:
    """External service providing shipper risk index.

    screen may raise ScreeningUnavailableError on outage.
    """

    def screen(self, shipper_id: str) -> int:
        """Return the risk index for the given shipper.

        May raise ScreeningUnavailableError on outage.
        """
        raise NotImplementedError


class NotificationService:
    """Asynchronous notification boundary (fire-and-forget)."""

    def send_quote_document(self, quote_id: str) -> None:
        """Send the quote document.

        Failures MUST NOT affect stored quote or API response
        (fire-and-forget semantics).
        """
        raise NotImplementedError

    def send_refusal_notice(self, quote_id: str) -> None:
        """Send the refusal notice.

        Failures MUST NOT affect stored quote or API response
        (fire-and-forget semantics).
        """
        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # Validation bounds
    MIN_WEIGHT_KG: float = 3.0
    MAX_WEIGHT_KG: float = 19400.0
    MIN_DISTANCE_KM: float = 25.0
    MAX_DISTANCE_KM: float = 7150.0
    MIN_DECLARED_VALUE: float = 50.0
    MAX_DECLARED_VALUE: float = 83000.0

    # Screening decision thresholds
    ACCEPT_MAX: int = 41
    REVIEW_MIN: int = 42
    REVIEW_MAX: int = 66
    REFUSE_MIN: int = 67

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a quote request according to the governed flow.

        Flow order (spec): validate > store > screen > decide > price > notify > respond.
        """
        # 1. validate
        validation_error = self._validate_request(request)
        if validation_error is not None:
            # Invalid request: immediate rejection, nothing else runs.
            return {
                "status": "rejected: invalid_request",
            }

        shipper_id = request["shipper_id"]
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # 2. store (draft)
        draft_quote = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
        }

        try:
            quote_id = self.quote_store.store_draft(draft_quote)
        except StoreUnavailableError:
            # On storage failure: no screening, no pricing, no notification.
            return {
                "status": "error: store_unavailable",
            }

        # From here on, a draft has been stored: responses must carry quote_id.

        # 3. screen
        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_outage = False
        except ScreeningUnavailableError:
            risk_index = None
            screening_outage = True

        # 4. decide & 5. price (where applicable)
        if screening_outage:
            # Screening outage path: price anyway, status held_unscreened, not notified, hold: true.
            price = self.tariff_engine.price(weight_kg, distance_km)

            # Update stored quote to held_unscreened with price.
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
                # Spec does not define behaviour for update failure; we must not invent it.
                # Best effort: we still return the logical response based on flow.
                pass

            # 6. notify: none
            # 7. respond
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Screening succeeded: risk_index is an int.
        assert risk_index is not None

        if risk_index <= self.ACCEPT_MAX:
            # Accept row: quote issued, priced yes, notified with quote document, status quoted.
            price = self.tariff_engine.price(weight_kg, distance_km)

            # Update stored quote to quoted with price.
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {
                        "status": "quoted",
                        "price": price,
                    },
                )
            except StoreUnavailableError:
                # Behaviour on update failure is unspecified; do not invent side effects.
                pass

            # 6. notify: send quote document (fire-and-forget)
            try:
                self.notification_service.send_quote_document(quote_id)
            except Exception:
                # Fire-and-forget: failures must not change stored quote or response.
                pass

            # 7. respond
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }

        if self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review row: held for manual review, not priced, not notified, status review_hold.
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {
                        "status": "review_hold",
                    },
                )
            except StoreUnavailableError:
                # Unspecified; keep API response consistent with decision table.
                pass

            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }

        # risk_index >= REFUSE_MIN (refuse row)
        if risk_index >= self.REFUSE_MIN:
            # Refuse row: refused, not priced, refusal notice sent, status refused_screening.
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {
                        "status": "refused_screening",
                    },
                )
            except StoreUnavailableError:
                # Unspecified; do not alter response semantics.
                pass

            # Notify: send refusal notice (fire-and-forget)
            try:
                self.notification_service.send_refusal_notice(quote_id)
            except Exception:
                # Fire-and-forget: ignore failures.
                pass

            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }

        # The decision tables cover all integer ranges; this line should be unreachable.
        # To remain defensive without inventing policy, fall back to review_hold semantics.
        try:
            self.quote_store.update_quote(
                quote_id,
                {
                    "status": "review_hold",
                },
            )
        except StoreUnavailableError:
            pass
        return {
            "status": "review_hold",
            "quote_id": quote_id,
        }

    def _validate_request(self, request: Dict[str, Any]) -> Optional[str]:
        """Return an error message if invalid, otherwise None.

        For this governed implementation, the concrete error message
        is not surfaced in the API response (only status is).
        """
        # shipper_id: required, present and non-empty
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or not shipper_id:
            return "shipper_id missing or empty"

        # weight_kg bounds
        try:
            weight = float(request.get("weight_kg"))
        except (TypeError, ValueError):
            return "weight_kg invalid"
        if not (self.MIN_WEIGHT_KG <= weight <= self.MAX_WEIGHT_KG):
            return "weight_kg out of bounds"

        # distance_km bounds
        try:
            distance = float(request.get("distance_km"))
        except (TypeError, ValueError):
            return "distance_km invalid"
        if not (self.MIN_DISTANCE_KM <= distance <= self.MAX_DISTANCE_KM):
            return "distance_km out of bounds"

        # declared_value bounds
        try:
            declared_value = float(request.get("declared_value"))
        except (TypeError, ValueError):
            return "declared_value invalid"
        if not (self.MIN_DECLARED_VALUE <= declared_value <= self.MAX_DECLARED_VALUE):
            return "declared_value out of bounds"

        return None


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level adapter for the CargoQuote QuoteAPI.

    Constructs real collaborator instances; test harnesses are expected
    to stub QuoteStore, TariffEngine, ScreeningService, and
    NotificationService by class and method name.
    """
    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)

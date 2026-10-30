from dataclasses import dataclass
from typing import Any, Dict


class StoreUnavailableError(Exception):
    """Raised by QuoteStore when storage is unavailable."""


class ScreeningUnavailableError(Exception):
    """Raised by ScreeningService when screening is unavailable."""


class QuoteStore:
    """Persistence layer for quotes.

    Real implementations are expected to raise StoreUnavailableError when
    storage is unavailable.
    """

    def store_draft(self, request: Dict[str, Any]) -> str:
        """Store a draft quote and return its quote_id.

        May raise StoreUnavailableError on failure.
        """
        # Stub implementation; real implementation provided elsewhere / via stubs.
        return "Q-Stub-Id"

    def update_quote(self, quote_id: str, updates: Dict[str, Any]) -> None:
        """Update an existing quote with the given fields.

        May raise StoreUnavailableError on failure.
        """
        # Stub implementation; real implementation provided elsewhere / via stubs.
        return None


class TariffEngine:
    """Tariff calculation engine implementing DT-P pricing."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # Base formula P1: base = 0.87 * weight_kg + 1.13 * distance_km
        base = 0.87 * weight_kg + 1.13 * distance_km

        # Heavy surcharge P2: if weight_kg > 1244, add 341.00 (flat)
        if weight_kg > 1244:
            base += 341.00

        # Long-haul multiplier P3: if distance_km >= 4912, multiply running total by 1.19
        # Applied after P2 (order normative).
        if distance_km >= 4912:
            base *= 1.19

        # P4 rounding: price = round(result, 2)
        price = round(base, 2)
        return price


class ScreeningService:
    """Service providing shipper risk index via screening."""

    def screen(self, shipper_id: str) -> int:
        """Return a risk index integer.

        May raise ScreeningUnavailableError when the service is unavailable.
        """
        # Stub implementation; real implementation provided elsewhere / via stubs.
        return 41


class NotificationService:
    """Service responsible for sending notifications (fire-and-forget)."""

    def send_quote_document(self, quote_id: str, price: float) -> None:
        """Send a quote document notification.

        Failures MUST NOT affect the stored quote or API response.
        """
        # Stub implementation; real implementation provided elsewhere / via stubs.
        return None

    def send_refusal_notice(self, quote_id: str) -> None:
        """Send a refusal notice notification.

        Failures MUST NOT affect the stored quote or API response.
        """
        # Stub implementation; real implementation provided elsewhere / via stubs.
        return None


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # Validation helpers based on DT-V and OpenAPI
    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        # shipper_id: present and non-empty
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or len(shipper_id) < 1:
            return False

        # weight_kg: number, 3 <= weight_kg <= 19400
        weight_kg = request.get("weight_kg")
        if not isinstance(weight_kg, (int, float)):
            return False
        if not (3 <= weight_kg <= 19400):
            return False

        # distance_km: number, 25 <= distance_km <= 7150
        distance_km = request.get("distance_km")
        if not isinstance(distance_km, (int, float)):
            return False
        if not (25 <= distance_km <= 7150):
            return False

        # declared_value: number, 50 <= declared_value <= 83000
        declared_value = request.get("declared_value")
        if not isinstance(declared_value, (int, float)):
            return False
        if not (50 <= declared_value <= 83000):
            return False

        return True

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Main QuoteAPI flow implementing validate > store > screen > decide > price > notify > respond."""

        # 1. validate
        if not self._is_valid_request(request):
            # Invalid request: immediate rejection, no store, no screening, no price, no notification.
            return {
                "status": "rejected: invalid_request"
            }

        # 2. store draft
        try:
            quote_id = self.quote_store.store_draft({
                "shipper_id": request["shipper_id"],
                "weight_kg": request["weight_kg"],
                "distance_km": request["distance_km"],
                "declared_value": request["declared_value"],
                "status": "draft",
            })
        except StoreUnavailableError:
            # On storage failure: nothing else runs; status error: store_unavailable.
            return {
                "status": "error: store_unavailable"
            }

        # At this point, a draft was stored; all non-error responses must include quote_id.

        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]

        # 3. screen
        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_outage = False
        except ScreeningUnavailableError:
            risk_index = None
            screening_outage = True

        # 4. decide based on screening result / outage
        if screening_outage:
            # Screening outage path: price, store held_unscreened, no notification, hold: true.
            price = self.tariff_engine.price(weight_kg, distance_km)

            try:
                self.quote_store.update_quote(quote_id, {
                    "status": "held_unscreened",
                    "price": price,
                })
            except StoreUnavailableError:
                # Spec only defines store failure on initial draft. For robustness,
                # we treat this as store_unavailable as well, with no further effects.
                return {
                    "status": "error: store_unavailable"
                }

            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # screening succeeded: route via DT-S
        assert risk_index is not None

        if risk_index <= 41:
            # accept row: quote issued, priced, notified with quote document, status quoted.
            price = self.tariff_engine.price(weight_kg, distance_km)

            try:
                self.quote_store.update_quote(quote_id, {
                    "status": "quoted",
                    "price": price,
                })
            except StoreUnavailableError:
                # As above, treat update failure as store_unavailable error.
                return {
                    "status": "error: store_unavailable"
                }

            # Notification is fire-and-forget; ignore failures.
            try:
                self.notification_service.send_quote_document(quote_id, price)
            except Exception:
                # Explicitly swallow to preserve response and stored state.
                pass

            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }

        if 42 <= risk_index <= 66:
            # review row: held for manual review; no pricing, no notification; status review_hold.
            try:
                self.quote_store.update_quote(quote_id, {
                    "status": "review_hold",
                })
            except StoreUnavailableError:
                return {
                    "status": "error: store_unavailable"
                }

            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }

        # risk_index >= 67 -> refuse row
        if risk_index >= 67:
            try:
                self.quote_store.update_quote(quote_id, {
                    "status": "refused_screening",
                })
            except StoreUnavailableError:
                return {
                    "status": "error: store_unavailable"
                }

            # Send refusal notice, fire-and-forget.
            try:
                self.notification_service.send_refusal_notice(quote_id)
            except Exception:
                pass

            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }

        # The DMN table is exhaustive, but guard just in case.
        return {
            "status": "error: store_unavailable"
        }


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point wrapping QuoteAPI.handle.

    Instantiates default collaborators so a test harness can stub them
    by class and method name.
    """
    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)

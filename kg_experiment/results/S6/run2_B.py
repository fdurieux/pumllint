from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the Quote Store is unavailable for storing or updating."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service cannot provide a risk index."""


class QuoteStore:
    """Persistence layer for quotes.

    In a real system, these would interact with a database. Here they are
    defined for stubbing/mocking by tests.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        May raise StoreUnavailableError on failure.
        """
        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> None:
        """Update the stored quote with final status and optional price.

        May raise StoreUnavailableError on failure.
        """
        raise NotImplementedError


class TariffEngine:
    """Implements DT-P pricing rules."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # P1: base = 0.87 * weight_kg + 1.13 * distance_km
        base = 0.87 * weight_kg + 1.13 * distance_km
        # P2: heavy surcharge if weight_kg > 1244, add 341.00
        if weight_kg > 1244:
            base += 341.00
        # P3: long-haul multiplier if distance_km >= 4912, multiply running total by 1.19
        if distance_km >= 4912:
            base *= 1.19
        # P4: price = round(result, 2)
        return round(base, 2)


class ScreeningService:
    """External service returning a risk index for a shipper."""

    def screen(self, shipper_id: str) -> int:
        """Return an integer risk index.

        May raise ScreeningUnavailableError on outage.
        """
        raise NotImplementedError


class NotificationService:
    """Fire-and-forget delivery of quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # ---- Public entrypoint ----
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a quote request following the CargoQuote spec and decision tables."""
        # 1. Validate request (DT-V). Invalid -> reject, stop.
        if not self._is_valid_request(request):
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
            # On storage failure, nothing else runs.
            return {"status": "error: store_unavailable"}

        # Base response always carries quote_id once draft is stored.
        response: Dict[str, Any] = {"quote_id": quote_id}

        # 3. Request risk index from Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage path: price, store held_unscreened, no notification, return price + hold: true.
            price = self.tariff_engine.price(weight_kg, distance_km)
            try:
                self.quote_store.update_quote(quote_id, status="held_unscreened", price=price)
            except StoreUnavailableError:
                # Spec is silent on update failures; response semantics remain as for success.
                pass
            response.update({
                "status": "held_unscreened",
                "price": price,
                "hold": True,
            })
            return response

        # 4. Apply screening decision DT-S based on risk_index.
        if risk_index <= 41:
            # Accept row: priced, notified with quote document, status quoted.
            price = self.tariff_engine.price(weight_kg, distance_km)
            try:
                self.quote_store.update_quote(quote_id, status="quoted", price=price)
            except StoreUnavailableError:
                # Response semantics unchanged.
                pass
            response.update({
                "status": "quoted",
                "price": price,
            })
            # 6. Notify shipper (fire-and-forget). Delivery failure must not change outcome/response.
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                # Fire-and-forget: ignore failures.
                pass
            return response

        if 42 <= risk_index <= 66:
            # Review row: held for manual review, no price, no notification.
            try:
                self.quote_store.update_quote(quote_id, status="review_hold")
            except StoreUnavailableError:
                pass
            response.update({"status": "review_hold"})
            return response

        # risk_index >= 67 -> refuse row
        try:
            self.quote_store.update_quote(quote_id, status="refused_screening")
        except StoreUnavailableError:
            pass
        response.update({"status": "refused_screening"})
        # Notify refusal, fire-and-forget.
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            pass
        return response

    # ---- Internal helpers ----
    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Check DT-V bounds and required fields.

        Any missing or wrongly-typed field (non-number where number required,
        non-string or empty `shipper_id`) is treated as invalid.
        """
        required_fields = ["shipper_id", "weight_kg", "distance_km", "declared_value"]
        for field in required_fields:
            if field not in request:
                return False

        shipper_id = request["shipper_id"]
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False

        # Helper to ensure numeric and within bounds
        def _in_num_range(value: Any, min_v: float, max_v: float) -> bool:
            try:
                num = float(value)
            except (TypeError, ValueError):
                return False
            return min_v <= num <= max_v

        if not _in_num_range(request["weight_kg"], 3, 19400):
            return False
        if not _in_num_range(request["distance_km"], 25, 7150):
            return False
        if not _in_num_range(request["declared_value"], 50, 83000):
            return False

        return True


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level handle function that wires default collaborators.

    For testing, the QuoteStore, TariffEngine, ScreeningService, and
    NotificationService classes are instantiated here so they can be
    monkeypatched or stubbed by class/method name.
    """
    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)

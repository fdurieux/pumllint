from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable for draft storage operations."""


class ScreeningUnavailableError(Exception):
    """Raised when the screening service is unavailable or times out."""


class QuoteStore:
    """Persistence layer for quotes.

    Methods are expected to raise StoreUnavailableError when the underlying
    storage is unavailable. On success, store_draft returns a quote_id string.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: float | None = None) -> None:
        raise NotImplementedError


class TariffEngine:
    """Implements DT-P pricing rules (REQ-08)."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # P1: base
        base = 0.87 * weight_kg + 1.13 * distance_km
        # P2: heavy surcharge
        if weight_kg > 1244:
            base += 316.00
        # P3: long-haul multiplier after P2
        if distance_km >= 4912:
            base *= 1.19
        # P4: rounding to 2 decimal places
        return round(base, 2)


class ScreeningService:
    """External screening provider returning a risk index for a shipper."""

    def screen(self, shipper_id: str) -> int:
        raise NotImplementedError


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

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

    def _validate(self, request: Dict[str, Any]) -> bool:
        """Validate request fields against DT-V bounds.

        Returns True if the request is valid, False otherwise.
        """

        # Check presence and basic type/empty constraints
        if "shipper_id" not in request:
            return False
        shipper_id = request["shipper_id"]
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False

        # Numeric fields: weight_kg, distance_km, declared_value
        for field, lower, upper in (
            ("weight_kg", 3, 19400),
            ("distance_km", 25, 7150),
            ("declared_value", 50, 83000),
        ):
            if field not in request:
                return False
            value = request[field]
            if not isinstance(value, (int, float)):
                return False
            if value < lower or value > upper:
                return False

        return True

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Main quotation handler implementing the CargoQuote flow.

        The response always includes a "status" key and may include
        "quote_id" whenever a draft was stored and "price" when priced.
        """

        # Step 1: Validate the request (DT-V)
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        shipper_id: str = request["shipper_id"]
        weight_kg: float = float(request["weight_kg"])
        distance_km: float = float(request["distance_km"])
        declared_value: float = float(request["declared_value"])

        # Step 2: Store draft quote; on failure, return error immediately
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: Request risk index from Screening Service
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Assumed policy for screening outage: refuse without pricing
            status = "refused_screening"
            # Update stored quote status; let unexpected store errors surface
            self.quote_store.update_quote(quote_id, status)

            # Notify refusal, fire-and-forget
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                # Fire-and-forget: ignore delivery failures
                pass

            return {"status": status, "quote_id": quote_id}

        # Step 4: Apply DT-S based on risk_index
        if risk_index <= 41:
            # Accept row: price and notify with quote document
            status = "quoted"
            # Step 5: pricing (DT-P)
            price = self.tariff_engine.price(weight_kg, distance_km)
            # Update stored quote with status and price
            self.quote_store.update_quote(quote_id, status, price)
            # Step 6: notify (fire-and-forget)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                # Fire-and-forget: ignore delivery failures
                pass
            # Step 7: return response
            return {"status": status, "quote_id": quote_id, "price": price}

        if 42 <= risk_index <= 66:
            # Review row: no price and no notification
            status = "review_hold"
            self.quote_store.update_quote(quote_id, status)
            return {"status": status, "quote_id": quote_id}

        # risk_index >= 67: refuse row
        status = "refused_screening"
        self.quote_store.update_quote(quote_id, status)
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            # Fire-and-forget: ignore delivery failures
            pass
        return {"status": status, "quote_id": quote_id}


# Module-level handle entry point expected by the harness

def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Functional entry point that wires default collaborators.

    In production this would wire real implementations; here we provide
    simple placeholders so that a test harness can stub them by class
    and method name.
    """

    quote_store = QuoteStore()
    tariff_engine = TariffEngine()
    screening_service = ScreeningService()
    notification_service = NotificationService()

    api = QuoteAPI(
        quote_store=quote_store,
        tariff_engine=tariff_engine,
        screening_service=screening_service,
        notification_service=notification_service,
    )
    return api.handle(request)

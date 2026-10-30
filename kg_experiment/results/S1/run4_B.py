from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the Quote Store cannot persist or update data."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service is unavailable (screening outage)."""


class QuoteStore:
    """Persistence boundary for quotes.

    Methods:
        - store_draft: persist a draft quote and return its quote_id.
        - update_quote: update status and optionally price for an existing quote.

    Error policy for this exercise:
        - store_draft MUST raise StoreUnavailableError when storage is unavailable.
        - update_quote MAY raise StoreUnavailableError; such errors are not
          normatively specified beyond the initial draft failure, so they are
          allowed to propagate.
    """

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        raise NotImplementedError

    def update_quote(
        self,
        quote_id: str,
        status: str,
        price: Optional[float] = None,
    ) -> None:
        raise NotImplementedError


class TariffEngine:
    """Implements DT-P pricing rules."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # P1: base
        base = 0.87 * weight_kg + 1.13 * distance_km
        result = base
        # P2: heavy surcharge
        if weight_kg > 1244:
            result += 316.00
        # P3: long-haul multiplier after P2
        if distance_km >= 4912:
            result *= 1.19
        # P4: round to 2 decimals
        price = round(result, 2)
        return price


class ScreeningService:
    """External Screening Service boundary."""

    def screen(self, shipper_id: str) -> int:
        """Return integer risk_index or raise ScreeningUnavailableError."""
        raise NotImplementedError


class NotificationService:
    """External Notification Service boundary.

    Both methods are fire-and-forget. Any exception they raise MUST NOT
    affect the stored quote or the API response.
    """

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

    # --- Public entry point ---
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a cargo quote request according to the specification."""

        # 1. Validate the request (DT-V). Invalid -> reject, stop.
        if not self._is_valid_request(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = str(request["shipper_id"])
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
            # storage failure -> error, nothing else runs
            return {"status": "error: store_unavailable"}

        # 3. Request risk index from Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage path: price, store held_unscreened, no notify.
            price = self.tariff_engine.price(weight_kg, distance_km)
            # Update quote with held_unscreened and price. Errors here are
            # not specified; allow exceptions to surface if they occur.
            self.quote_store.update_quote(
                quote_id=quote_id,
                status="held_unscreened",
                price=price,
            )
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4. Apply DT-S to risk index and act on each row.
        if risk_index <= 41:
            # Accept band -> quoted, priced, notified with quote document.
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id=quote_id,
                status="quoted",
                price=price,
            )
            # Fire-and-forget notification: swallow any exception.
            try:
                self.notification_service.send_quote_document(
                    shipper_id=shipper_id,
                    quote_id=quote_id,
                    price=price,
                )
            except Exception:
                # Outcome and response unchanged.
                pass
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }

        if 42 <= risk_index <= 66:
            # Review band -> review_hold, no price, no notification.
            self.quote_store.update_quote(
                quote_id=quote_id,
                status="review_hold",
            )
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }

        # risk_index >= 67: refused
        self.quote_store.update_quote(
            quote_id=quote_id,
            status="refused_screening",
        )
        # Fire-and-forget refusal notice: swallow any exception.
        try:
            self.notification_service.send_refusal_notice(
                shipper_id=shipper_id,
                quote_id=quote_id,
            )
        except Exception:
            pass
        return {
            "status": "refused_screening",
            "quote_id": quote_id,
        }

    # --- Internal helpers ---
    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Check DT-V bounds and required fields.

        Any type/shape issue is treated as invalid_request rather than
        raising out of the API.
        """

        required_fields = ["shipper_id", "weight_kg", "distance_km", "declared_value"]
        for field in required_fields:
            if field not in request:
                return False

        # V1: shipper_id present and non-empty string
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False

        # Numeric fields: attempt coercion; invalid -> reject.
        try:
            weight_kg = float(request.get("weight_kg"))
            distance_km = float(request.get("distance_km"))
            declared_value = float(request.get("declared_value"))
        except (TypeError, ValueError):
            return False

        # V2: 3 <= weight_kg <= 19400
        if not (3 <= weight_kg <= 19400):
            return False

        # V3: 25 <= distance_km <= 7150
        if not (25 <= distance_km <= 7150):
            return False

        # V4: 50 <= declared_value <= 83000
        if not (50 <= declared_value <= 83000):
            return False

        return True


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level handle function as required by the harness.

    It wires default concrete collaborators. In production/testing,
    a harness is expected to construct QuoteAPI with suitable stubs or
    implementations and bypass this function, or monkeypatch the
    collaborator classes prior to calling this.
    """

    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)

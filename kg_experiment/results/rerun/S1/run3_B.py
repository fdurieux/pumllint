from dataclasses import dataclass
from typing import Any, Dict


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable for draft or update operations."""


class ScreeningUnavailableError(Exception):
    """Raised when the screening service is unavailable or times out."""


class QuoteStore:
    """Persistence layer for quotes.

    Methods may raise StoreUnavailableError when storage is not available.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        On storage failure, raises StoreUnavailableError.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: float | None = None) -> None:
        """Update an existing quote's status, and optionally its price.

        On storage failure, may raise StoreUnavailableError (behavior unspecified by spec).
        """

        raise NotImplementedError


class TariffEngine:
    """Tariff engine implementing DT-P pricing rules."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # P1: base = 0.87 * weight_kg + 1.13 * distance_km
        base = 0.87 * weight_kg + 1.13 * distance_km

        # P2: heavy surcharge: if weight_kg > 1244, add 316.00 (flat)
        if weight_kg > 1244:
            base += 316.00

        # P3: long-haul multiplier: if distance_km >= 4912, multiply running total by 1.19
        if distance_km >= 4912:
            base *= 1.19

        # P4: price = round(result, 2)
        price = round(base, 2)
        return price


class ScreeningService:
    """External screening provider.

    screen() returns an integer risk_index or raises ScreeningUnavailableError
    when screening cannot be performed (outage).
    """

    def screen(self, shipper_id: str) -> int:
        raise NotImplementedError


class NotificationService:
    """External notification provider for quote documents and refusal notices.

    Any delivery failure must not alter the quote outcome or the API response.
    Implementations may signal delivery problems via exceptions, which are
    caught and ignored by QuoteAPI.
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

    # Public entry point used by the module-level handle()
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Validate request (DT-V). Invalid -> reject, stop.
        if not self._is_valid_request(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # 2. Store draft quote with status draft. On storage failure: error: store_unavailable; stop.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # 3. Request risk index from Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_outage = False
        except ScreeningUnavailableError:
            risk_index = None
            screening_outage = True

        # Screening outage path: price anyway, update to held_unscreened, no notification, return price and hold: true.
        if screening_outage:
            price = self.tariff_engine.price(weight_kg, distance_km)
            # Update stored quote to held_unscreened with price.
            self.quote_store.update_quote(quote_id, status="held_unscreened", price=price)
            return {"status": "held_unscreened", "quote_id": quote_id, "price": price, "hold": True}

        # 4. Apply screening decision DT-S to risk_index; 5. Price where required; 6. Notify where required.
        assert risk_index is not None

        if risk_index <= 41:
            # Accept row: priced, notified with quote document, status quoted.
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, status="quoted", price=price)

            # Fire-and-forget notification: ignore any delivery failure.
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                pass

            return {"status": "quoted", "quote_id": quote_id, "price": price}

        if 42 <= risk_index <= 66:
            # Review row: held for manual review, not priced, not notified.
            self.quote_store.update_quote(quote_id, status="review_hold", price=None)
            return {"status": "review_hold", "quote_id": quote_id}

        # risk_index >= 67: refused row, not priced, refusal notice sent.
        self.quote_store.update_quote(quote_id, status="refused_screening", price=None)

        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            pass

        return {"status": "refused_screening", "quote_id": quote_id}

    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Check DT-V validation rules against the incoming request.

        A request is valid iff all of V1-V4 hold; any violation rejects the
        request as invalid with no side effects.
        """

        # Required fields present and non-empty / correct type-ish
        required_fields = ["shipper_id", "weight_kg", "distance_km", "declared_value"]
        for field in required_fields:
            if field not in request:
                return False

        shipper_id = request["shipper_id"]
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False

        # Numeric bounds with coercion where possible; non-numeric -> invalid.
        try:
            weight_kg = float(request["weight_kg"])
            distance_km = float(request["distance_km"])
            declared_value = float(request["declared_value"])
        except (TypeError, ValueError):
            return False

        if not (3 <= weight_kg <= 19400):
            return False
        if not (25 <= distance_km <= 7150):
            return False
        if not (50 <= declared_value <= 83000):
            return False

        return True


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level API entry point.

    Constructs default collaborators and dispatches to QuoteAPI.handle.
    In tests, collaborators can be monkeypatched or subclasses provided
    by replacing QuoteStore, TariffEngine, ScreeningService, or
    NotificationService.
    """

    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)

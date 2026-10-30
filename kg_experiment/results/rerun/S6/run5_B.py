from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the Quote Store cannot be reached or used."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service is unavailable (screening outage)."""


class QuoteStore:
    """Persistence collaborator for quotes.

    Real implementations are expected to override these methods.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        On storage outage, must raise StoreUnavailableError.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> None:
        """Update an existing quote's status (and optionally price).

        On storage outage, should raise StoreUnavailableError.
        """

        raise NotImplementedError


class TariffEngine:
    """Pricing collaborator implementing DT-P."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # DT-P P1: base calculation
        base = 0.87 * weight_kg + 1.13 * distance_km

        # DT-P P2: heavy surcharge
        if weight_kg > 1244:
            base += 341.00

        # DT-P P3: long-haul multiplier after surcharge
        if distance_km >= 4912:
            base *= 1.19

        # DT-P P4: round to 2 decimals
        price = round(base, 2)
        return price


class ScreeningService:
    """External denied-party screening provider collaborator."""

    def screen(self, shipper_id: str) -> int:
        """Return an integer risk_index for the given shipper.

        On outage, must raise ScreeningUnavailableError.
        """

        raise NotImplementedError


class NotificationService:
    """Notification collaborator for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send a quote document.

        Delivery failure may raise an exception; it must not affect the
        outcome or response (fire-and-forget semantics).
        """

        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send a refusal notice.

        Delivery failure may raise an exception; it must not affect the
        outcome or response (fire-and-forget semantics).
        """

        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # --- Public entry point ---

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a quote request as per CargoQuote spec.

        Expects `request` dict with keys: shipper_id, weight_kg,
        distance_km, declared_value.
        """

        # 1. Validate request (DT-V). Invalid -> reject, stop.
        if not self._is_valid_request(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = str(request["shipper_id"])
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # 2. Store draft quote with status draft.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            # storage failure -> error: store_unavailable; nothing else runs
            return {"status": "error: store_unavailable"}

        response: Dict[str, Any] = {"status": None, "quote_id": quote_id}

        # 3. Request risk index from Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_outage = False
        except ScreeningUnavailableError:
            risk_index = None
            screening_outage = True

        # 4 & 5 & 6. Apply DT-S / DT-P and notifications.
        if screening_outage:
            # Screening outage path: priced, held_unscreened, no notification.
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, status="held_unscreened", price=price)
            response["status"] = "held_unscreened"
            response["price"] = price
            response["hold"] = True
            return response

        # Normal screening path with a risk_index.
        assert risk_index is not None

        if risk_index <= 41:
            # Accept band: price, store quoted, send quote document.
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, status="quoted", price=price)
            # Fire-and-forget notification; ignore any failure.
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                pass
            response["status"] = "quoted"
            response["price"] = price
            return response

        if 42 <= risk_index <= 66:
            # Review band: update status, no price, no notification.
            self.quote_store.update_quote(quote_id, status="review_hold", price=None)
            response["status"] = "review_hold"
            # Ensure no price key is present.
            response.pop("price", None)
            response.pop("hold", None)
            return response

        # risk_index >= 67 -> refuse band
        self.quote_store.update_quote(quote_id, status="refused_screening", price=None)
        # Fire-and-forget refusal notice; ignore any failure.
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            pass
        response["status"] = "refused_screening"
        # Ensure no price/hold keys are present.
        response.pop("price", None)
        response.pop("hold", None)
        return response

    # --- Internal helpers ---

    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Validate request against DT-V bounds and presence.

        Treats missing or wrongly typed fields as invalid.
        """

        # shipper_id: present and non-empty string
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False

        # Numeric fields: weight_kg, distance_km, declared_value
        try:
            weight_kg = float(request.get("weight_kg"))
            distance_km = float(request.get("distance_km"))
            declared_value = float(request.get("declared_value"))
        except (TypeError, ValueError):
            return False

        # Apply DT-V numeric bounds
        if not (3 <= weight_kg <= 19400):
            return False
        if not (25 <= distance_km <= 7150):
            return False
        if not (50 <= declared_value <= 83000):
            return False

        return True


# Module-level handle for the harness

def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point that wires default collaborators.

    In production, collaborators would be real implementations; for
    testing, they can be monkeypatched or subclassed.
    """

    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)

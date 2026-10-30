from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the Quote Store cannot persist or update data."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service cannot provide a risk index."""


class QuoteStore:
    """Persistence gateway for quote drafts and updates.

    In this implementation, methods are stubs meant to be overridden or
    monkeypatched in tests.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        May raise StoreUnavailableError on failure.
        """

        # Minimal placeholder implementation; tests are expected to stub this.
        return "Q-PLACEHOLDER"

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> None:
        """Update an existing quote's status and optionally its price.

        May raise StoreUnavailableError on failure (assumed), but behavior
        for such failures is not specified by the contract and is therefore
        not caught specially here.
        """

        # Placeholder no-op; override in tests.
        return None


class TariffEngine:
    """Implements the DT-P pricing rules."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # P1: base computation
        base = 0.87 * weight_kg + 1.13 * distance_km

        # P2: heavy surcharge
        if weight_kg > 1244:
            base += 316.00

        # P3: long-haul multiplier (after P2)
        if distance_km >= 4912:
            base *= 1.19

        # P4: round to 2 decimals
        return round(base, 2)


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id: str) -> int:
        """Return the risk index for the given shipper.

        May raise ScreeningUnavailableError to signal outage.
        """

        # Placeholder implementation; override in tests.
        return 0


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        # Fire-and-forget: any exception is to be swallowed by caller.
        return None

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        # Fire-and-forget: any exception is to be swallowed by caller.
        return None


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # ---- Public entrypoint ----

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Main orchestration for the CargoQuote instant quotation flow."""

        # 1. Validate request (DT-V). Invalid -> reject, stop.
        if not self._is_valid_request(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request.get("shipper_id")
        weight_kg = float(request.get("weight_kg"))
        distance_km = float(request.get("distance_km"))
        declared_value = float(request.get("declared_value"))

        # 2. Store draft quote with status draft.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            # On storage failure nothing else runs.
            return {"status": "error: store_unavailable"}

        # 3. Request risk index from Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage path.
            price = self.tariff_engine.price(weight_kg=weight_kg, distance_km=distance_km)
            # Update stored quote to held_unscreened with price.
            self.quote_store.update_quote(quote_id=quote_id, status="held_unscreened", price=price)
            return {"status": "held_unscreened", "quote_id": quote_id, "price": price, "hold": True}

        # 4. Apply screening decision (DT-S) based on risk_index.
        if risk_index <= 41:
            # Accept row: priced + notified, status quoted.
            price = self.tariff_engine.price(weight_kg=weight_kg, distance_km=distance_km)
            self.quote_store.update_quote(quote_id=quote_id, status="quoted", price=price)

            # Fire-and-forget notification; swallow any failure.
            try:
                self.notification_service.send_quote_document(
                    shipper_id=shipper_id,
                    quote_id=quote_id,
                    price=price,
                )
            except Exception:
                pass

            return {"status": "quoted", "quote_id": quote_id, "price": price}

        if 42 <= risk_index <= 66:
            # Review row: no price, no notification, status review_hold.
            self.quote_store.update_quote(quote_id=quote_id, status="review_hold", price=None)
            return {"status": "review_hold", "quote_id": quote_id}

        # risk_index >= 67: refuse row.
        self.quote_store.update_quote(quote_id=quote_id, status="refused_screening", price=None)

        # Fire-and-forget refusal notification; swallow any failure.
        try:
            self.notification_service.send_refusal_notice(shipper_id=shipper_id, quote_id=quote_id)
        except Exception:
            pass

        return {"status": "refused_screening", "quote_id": quote_id}

    # ---- Internal helpers ----

    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Check DT-V validation rules.

        A request is valid iff all of V1..V4 hold.
        """

        # V1: shipper_id present and non-empty string
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False

        # V2: weight_kg is number, 3 <= weight_kg <= 19400
        weight = request.get("weight_kg")
        if not isinstance(weight, (int, float)):
            return False
        if not (3 <= weight <= 19400):
            return False

        # V3: distance_km is number, 25 <= distance_km <= 7150
        distance = request.get("distance_km")
        if not isinstance(distance, (int, float)):
            return False
        if not (25 <= distance <= 7150):
            return False

        # V4: declared_value is number, 50 <= declared_value <= 83000
        declared_value = request.get("declared_value")
        if not isinstance(declared_value, (int, float)):
            return False
        if not (50 <= declared_value <= 83000):
            return False

        return True


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level handle function required by the harness.

    Constructs a QuoteAPI instance with default collaborators and
    delegates to its handle method.
    """

    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)

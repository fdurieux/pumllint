from typing import Any, Dict, Optional, Tuple


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable for operations."""


class ScreeningUnavailableError(Exception):
    """Raised when the screening service is unavailable."""


class QuoteStore:
    """Persistence layer for quotes.

    The concrete implementation is expected to raise StoreUnavailableError
    when storage operations fail.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a new draft quote and return its quote_id.

        May raise StoreUnavailableError on failure.
        """
        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> Any:
        """Update an existing quote's status and optionally its price.

        May raise StoreUnavailableError on failure.
        Return value is ignored by QuoteAPI.
        """
        raise NotImplementedError


class TariffEngine:
    """Pricing engine implementing DT-P tariff rules (REQ-08)."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute price according to DT-P.

        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: if weight_kg > 1244, add 316.00
        P3: if distance_km >= 4912, multiply running total by 1.19
        P4: price = round(result, 2)
        """
        base = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            base += 316.00
        if distance_km >= 4912:
            base *= 1.19
        return round(base, 2)


class ScreeningService:
    """External service returning a shipper risk index."""

    def screen(self, shipper_id: str) -> int:
        """Return risk_index as an integer.

        May raise ScreeningUnavailableError on outage.
        """
        raise NotImplementedError


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send quote document. Fire-and-forget; delivery failures must not
        affect the quote outcome or API response.
        """
        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send refusal notice. Fire-and-forget; delivery failures must not
        affect the quote outcome or API response.
        """
        raise NotImplementedError


class QuoteAPI:
    """Orchestrates the CargoQuote instantaneous quotation flow."""

    def __init__(self) -> None:
        self.quote_store = QuoteStore()
        self.tariff_engine = TariffEngine()
        self.screening_service = ScreeningService()
        self.notification_service = NotificationService()

    # --- Internal helpers ---

    def _validate(self, request: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate request against DT-V.

        Returns (is_valid, error_status). On invalid, error_status is
        "rejected: invalid_request".
        """
        # V1: shipper_id present and non-empty
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or not shipper_id.strip():
            return False, "rejected: invalid_request"

        # Helper to coerce numerics
        def _num(value: Any) -> Optional[float]:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        weight = _num(request.get("weight_kg"))
        distance = _num(request.get("distance_km"))
        declared = _num(request.get("declared_value"))

        if weight is None or distance is None or declared is None:
            return False, "rejected: invalid_request"

        # V2: 3 <= weight_kg <= 19400
        if not (3 <= weight <= 19400):
            return False, "rejected: invalid_request"

        # V3: 25 <= distance_km <= 7150
        if not (25 <= distance <= 7150):
            return False, "rejected: invalid_request"

        # V4: 50 <= declared_value <= 83000
        if not (50 <= declared <= 83000):
            return False, "rejected: invalid_request"

        return True, None

    # --- Public API ---

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a quote request according to the CargoQuote spec.

        Input: dict with keys shipper_id, weight_kg, distance_km, declared_value.
        Output: dict with at least key "status" and optional keys as per
        the API contract.
        """
        # 1. Validate the request (DT-V). Invalid → reject, stop.
        is_valid, error_status = self._validate(request)
        if not is_valid:
            return {"status": error_status}

        # At this point, types and bounds are acceptable; coerce to floats.
        shipper_id = str(request["shipper_id"]).strip()
        weight_kg = float(request["weight_kg"])  # type: ignore[arg-type]
        distance_km = float(request["distance_km"])  # type: ignore[arg-type]
        declared_value = float(request["declared_value"])  # type: ignore[arg-type]

        # 2. Store the draft quote with status draft.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            # storage failure → error: store_unavailable, nothing else runs
            return {"status": "error: store_unavailable"}

        # Normalize quote_id to string for the response
        quote_id_str = str(quote_id)

        # 3. Request the shipper's risk index from the Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_outage = False
        except ScreeningUnavailableError:
            risk_index = None
            screening_outage = True

        # 5/3 (outage path): pricing (DT-P) only on accept or outage paths.
        if screening_outage:
            # Screening outage path per spec: price anyway, update to held_unscreened,
            # no notification, response carries price and hold: true.
            price = self.tariff_engine.price(weight_kg, distance_km)
            try:
                self.quote_store.update_quote(
                    quote_id_str,
                    status="held_unscreened",
                    price=price,
                )
            except StoreUnavailableError:
                # Spec does not define behavior for update failures after draft stored;
                # allow to propagate or leave unhandled. Here we propagate.
                raise

            return {
                "status": "held_unscreened",
                "quote_id": quote_id_str,
                "price": price,
                "hold": True,
            }

        # 4. Apply screening decision (DT-S) to the risk index.
        assert isinstance(risk_index, int), "risk_index must be int when screening succeeds"

        if risk_index <= 41:
            # accept row: quote issued, priced, notified
            price = self.tariff_engine.price(weight_kg, distance_km)
            try:
                self.quote_store.update_quote(
                    quote_id_str,
                    status="quoted",
                    price=price,
                )
            except StoreUnavailableError:
                # Not specified for post-screening update failures; propagate.
                raise

            # Notification is fire-and-forget: ignore any failures.
            try:
                self.notification_service.send_quote_document(
                    shipper_id=shipper_id,
                    quote_id=quote_id_str,
                    price=price,
                )
            except Exception:
                # delivery failure never changes outcome or response
                pass

            return {
                "status": "quoted",
                "quote_id": quote_id_str,
                "price": price,
            }

        if 42 <= risk_index <= 66:
            # review row: held for manual review, no price, no notification
            try:
                self.quote_store.update_quote(
                    quote_id_str,
                    status="review_hold",
                    price=None,
                )
            except StoreUnavailableError:
                # propagate as unspecified error
                raise

            return {
                "status": "review_hold",
                "quote_id": quote_id_str,
            }

        # risk_index >= 67 → refused
        try:
            self.quote_store.update_quote(
                quote_id_str,
                status="refused_screening",
                price=None,
            )
        except StoreUnavailableError:
            # propagate as unspecified error
            raise

        # Fire-and-forget refusal notice
        try:
            self.notification_service.send_refusal_notice(
                shipper_id=shipper_id,
                quote_id=quote_id_str,
            )
        except Exception:
            # delivery failure never changes outcome or response
            pass

        return {
            "status": "refused_screening",
            "quote_id": quote_id_str,
        }


# Module-level handle for the harness
_api_instance: Optional[QuoteAPI] = None


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    global _api_instance
    if _api_instance is None:
        _api_instance = QuoteAPI()
    return _api_instance.handle(request)

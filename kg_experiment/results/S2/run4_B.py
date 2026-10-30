from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised by QuoteStore on storage failures."""


class ScreeningUnavailableError(Exception):
    """Raised by ScreeningService.screen on screening outages."""


@dataclass
class QuoteRecord:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: str
    price: Optional[float] = None


class QuoteStore:
    """Persistence adapter for quote records.

    Methods are designed to be stubbed in tests. By default this is an
    in-memory implementation suitable for demonstration; a real system
    would override these methods.
    """

    def __init__(self) -> None:
        self._store: Dict[str, QuoteRecord] = {}
        self._next_id: int = 1

    def _generate_id(self) -> str:
        quote_id = f"Q{self._next_id}"
        self._next_id += 1
        return quote_id

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        """Store a new draft quote and return its quote_id.

        May raise StoreUnavailableError on storage failure.
        """

        try:
            quote_id = self._generate_id()
            record = QuoteRecord(
                quote_id=quote_id,
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
                status="draft",
            )
            self._store[quote_id] = record
            return quote_id
        except Exception as exc:  # pragma: no cover - defensive
            raise StoreUnavailableError("failed to store draft quote") from exc

    def update_quote(
        self,
        quote_id: str,
        status: str,
        price: Optional[float] = None,
    ) -> None:
        """Update an existing quote with a new status and optional price.

        May raise StoreUnavailableError on storage failure.
        """

        try:
            record = self._store.get(quote_id)
            if record is None:
                # For simplicity, treat missing records as storage failure.
                raise StoreUnavailableError(f"quote_id {quote_id} not found")
            record.status = status
            record.price = price
        except StoreUnavailableError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise StoreUnavailableError("failed to update quote") from exc


class TariffEngine:
    """Computes freight price per DT-P."""

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
    """External denied-party screening provider returning a risk index."""

    def screen(self, shipper_id: str) -> int:
        """Return the risk index for the given shipper.

        May raise ScreeningUnavailableError on outage.
        """

        # Default stub: always-return low risk; real tests should stub.
        return 0


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send a quote document. Fire-and-forget: failures are ignored by caller."""
        # Stub: does nothing; tests may override.
        return None

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send a refusal notice. Fire-and-forget: failures are ignored by caller."""
        # Stub: does nothing; tests may override.
        return None


class QuoteAPI:
    """Implements the CargoQuote instant freight quotation flow."""

    def __init__(
        self,
        store: Optional[QuoteStore] = None,
        tariff_engine: Optional[TariffEngine] = None,
        screening_service: Optional[ScreeningService] = None,
        notification_service: Optional[NotificationService] = None,
    ) -> None:
        self._store = store or QuoteStore()
        self._tariff = tariff_engine or TariffEngine()
        self._screening = screening_service or ScreeningService()
        self._notify = notification_service or NotificationService()

    # --- Public entrypoint ---

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a quote request according to the CargoQuote specification.

        The request dict is expected to contain shipper_id, weight_kg,
        distance_km, declared_value. The response dict will always
        contain a status string and may contain quote_id and price.
        """

        # 1. Validate the request (DT-V). Invalid → reject, stop.
        if not self._is_request_valid(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = str(request["shipper_id"])
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # 2. Store the draft quote in the Quote Store with status `draft`.
        try:
            quote_id = self._store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            # storage failure → error: store_unavailable; nothing else runs
            return {"status": "error: store_unavailable"}

        # 3. Request the shipper's risk index from the Screening Service.
        # Behaviour on screening outage is unspecified; per assumptions
        # we let ScreeningUnavailableError or other exceptions propagate.
        risk_index = self._screening.screen(shipper_id)

        # 4. Apply the screening decision (DT-S) to the risk index.
        # Determine status, pricing flag, and notification kind.
        if risk_index <= 41:
            status = "quoted"
            priced = True
            notify_kind = "quote_document"
        elif 42 <= risk_index <= 66:
            status = "review_hold"
            priced = False
            notify_kind = "none"
        else:  # risk_index >= 67
            status = "refused_screening"
            priced = False
            notify_kind = "refusal_notice"

        price: Optional[float] = None

        # 5. Price the quote (DT-P) — only on the rows DT-S marks priced.
        if priced:
            price = self._tariff.price(weight_kg=weight_kg, distance_km=distance_km)

        # 4 (continued). Update the stored quote to the resulting status.
        # Behaviour on update failure is not specified; let exceptions propagate.
        self._store.update_quote(quote_id=quote_id, status=status, price=price)

        # 6. Notify the shipper — only on the rows DT-S marks notified;
        # fire-and-forget (delivery failure must not change outcome/response).
        if notify_kind == "quote_document":
            try:
                # price is not None in this branch by construction.
                assert price is not None
                self._notify.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                # Explicitly swallow to keep outcome/response unchanged.
                pass
        elif notify_kind == "refusal_notice":
            try:
                self._notify.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass

        # 7. Return the response.
        response: Dict[str, Any] = {"status": status, "quote_id": quote_id}
        if priced and price is not None:
            response["price"] = price
        return response

    # --- Internal helpers ---

    def _is_request_valid(self, request: Dict[str, Any]) -> bool:
        """Validate the request according to DT-V.

        Any violation yields False; exceptions in numeric conversion
        are treated as validation failure rather than propagated.
        """

        # V1: shipper_id present and non-empty
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or not shipper_id:
            return False

        # V2–V4: numeric bounds; treat conversion errors as invalid.
        try:
            weight_kg_raw = request.get("weight_kg")
            distance_km_raw = request.get("distance_km")
            declared_value_raw = request.get("declared_value")

            weight_kg = float(weight_kg_raw)
            distance_km = float(distance_km_raw)
            declared_value = float(declared_value_raw)
        except (TypeError, ValueError):
            return False

        if not (3 <= weight_kg <= 19400):
            return False
        if not (25 <= distance_km <= 7150):
            return False
        if not (50 <= declared_value <= 83000):
            return False

        return True


# Module-level handle function required by the task.

_quote_api_instance: Optional[QuoteAPI] = None


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entrypoint delegating to QuoteAPI.handle."""

    global _quote_api_instance
    if _quote_api_instance is None:
        _quote_api_instance = QuoteAPI()
    return _quote_api_instance.handle(request)

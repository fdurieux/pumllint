from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the QuoteStore cannot persist or update a quote."""


class ScreeningUnavailableError(Exception):
    """Raised when the ScreeningService is unavailable for screening calls."""


class QuoteStore:
    """Persistence boundary for quote drafts and updates."""

    def store_draft(self, request: Dict[str, Any]) -> str:
        """Store a draft quote and return its quote_id.

        May raise StoreUnavailableError on storage failure.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, fields: Dict[str, Any]) -> None:
        """Update an existing quote with the given fields.

        May raise StoreUnavailableError on storage failure.
        """

        raise NotImplementedError


class TariffEngine:
    """Pricing boundary implementing the DT-P tariff rules."""

    # Pricing constants from DT-P
    P1_WEIGHT_COEFF = 0.87  # A:dt:P1|formula@v1
    P1_DISTANCE_COEFF = 1.13  # A:dt:P1|formula@v1
    P2_THRESHOLD = 1244  # A:dt:P2|threshold@v2
    P2_SURCHARGE = 341.00  # A:dt:P2|surcharge@v2
    P3_THRESHOLD = 4912  # A:dt:P3|threshold@v1
    P3_FACTOR = 1.19  # A:dt:P3|factor@v1

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute the price according to DT-P.

        Implements P1 base, P2 heavy surcharge (if weight_kg > threshold),
        then P3 long-haul multiplier (if distance_km >= threshold), in that order,
        with final rounding to 2 decimal places.
        """

        # P1: base formula
        result = (
            self.P1_WEIGHT_COEFF * weight_kg
            + self.P1_DISTANCE_COEFF * distance_km
        )

        # P2: heavy surcharge, applied next
        if weight_kg > self.P2_THRESHOLD:
            result += self.P2_SURCHARGE

        # P3: long-haul multiplier, applied after P2
        if distance_km >= self.P3_THRESHOLD:
            result *= self.P3_FACTOR

        # P4: rounding
        price = round(result, 2)
        return price


class ScreeningService:
    """External service providing shipper risk index for screening."""

    def screen(self, shipper_id: str) -> int:
        """Return the risk index for the given shipper.

        May raise ScreeningUnavailableError on outage.
        """

        raise NotImplementedError


class NotificationService:
    """Notification boundary for quote documents and refusal notices."""

    def send_quote_document(self, quote_id: str, price: float) -> None:
        """Fire-and-forget sending of a quote document.

        Notification failures must not change stored quote or API response.
        """

        raise NotImplementedError

    def send_refusal_notice(self, quote_id: str) -> None:
        """Fire-and-forget sending of a refusal notice.

        Notification failures must not change stored quote or API response.
        """

        raise NotImplementedError


@dataclass
class QuoteDecision:
    status: str
    priced: bool
    notify: Optional[str]  # 'quote', 'refusal', or None
    hold: bool


class QuoteAPI:
    """Implements the CargoQuote QuoteAPI flow from the governed spec."""

    # Validation bounds
    MIN_WEIGHT_KG = 3
    MAX_WEIGHT_KG = 19400
    MIN_DISTANCE_KM = 25
    MAX_DISTANCE_KM = 7150
    MIN_DECLARED_VALUE = 50
    MAX_DECLARED_VALUE = 83000

    # Screening thresholds
    ACCEPT_MAX = 41  # risk_index <= 41 -> accept
    REVIEW_MIN = 42  # 42 <= risk_index <= 66 -> review
    REVIEW_MAX = 66
    REFUSE_MIN = 67  # risk_index >= 67 -> refuse

    STATUS_REJECTED_INVALID = "rejected: invalid_request"
    STATUS_ERROR_STORE_UNAVAILABLE = "error: store_unavailable"
    STATUS_QUOTED = "quoted"
    STATUS_REVIEW_HOLD = "review_hold"
    STATUS_REFUSED_SCREENING = "refused_screening"
    STATUS_HELD_UNSCREENED = "held_unscreened"

    def __init__(self) -> None:
        self.store = QuoteStore()
        self.tariff = TariffEngine()
        self.screening = ScreeningService()
        self.notification = NotificationService()

    # --- Public entry point -------------------------------------------------

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a quote request according to the governed policy."""

        # 1. validate
        if not self._is_valid_request(request):
            return {"status": self.STATUS_REJECTED_INVALID}

        # 2. store draft
        try:
            quote_id = self.store.store_draft(request)
        except StoreUnavailableError:
            # On storage failure nothing else runs
            return {"status": self.STATUS_ERROR_STORE_UNAVAILABLE}

        # 3. screen
        try:
            risk_index = self.screening.screen(str(request["shipper_id"]))
            screening_outage = False
        except ScreeningUnavailableError:
            risk_index = None
            screening_outage = True

        if screening_outage:
            # Screening outage path: price, set held_unscreened, no notify, hold: true
            price = self.tariff.price(
                float(request["weight_kg"]), float(request["distance_km"])
            )
            # Update stored quote status; storage failures here are not specified
            try:
                self.store.update_quote(
                    quote_id,
                    {
                        "status": self.STATUS_HELD_UNSCREENED,
                        "price": price,
                        "hold": True,
                    },
                )
            except StoreUnavailableError:
                # Spec does not define a second-store-failure path; propagate as-is
                raise

            return {
                "status": self.STATUS_HELD_UNSCREENED,
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4. decide (DT-S) based on risk_index
        decision = self._decide_from_risk(risk_index)

        # 5. price (only on priced rows)
        price: Optional[float] = None
        if decision.priced:
            price = self.tariff.price(
                float(request["weight_kg"]), float(request["distance_km"])
            )

        # Update stored quote according to final status and optional price/hold
        update_fields: Dict[str, Any] = {"status": decision.status}
        if price is not None:
            update_fields["price"] = price
        if decision.hold:
            update_fields["hold"] = True

        try:
            self.store.update_quote(quote_id, update_fields)
        except StoreUnavailableError:
            # Spec only defines store failure for the initial store; here we
            # propagate, as behaviour is unspecified.
            raise

        # 6. notify (fire-and-forget, no effect on response)
        if decision.notify == "quote" and price is not None:
            try:
                self.notification.send_quote_document(quote_id, price)
            except Exception:
                # Fire-and-forget: ignore failures
                pass
        elif decision.notify == "refusal":
            try:
                self.notification.send_refusal_notice(quote_id)
            except Exception:
                # Fire-and-forget: ignore failures
                pass

        # 7. respond
        response: Dict[str, Any] = {"status": decision.status}

        # quote_id whenever a draft was stored (all non-invalid paths)
        response["quote_id"] = quote_id

        # price exactly on priced rows
        if price is not None:
            response["price"] = price

        # hold: true exactly on held_unscreened
        if decision.hold:
            response["hold"] = True

        return response

    # --- Internal helpers ---------------------------------------------------

    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Validate the incoming request according to the contract."""

        # shipper_id present and non-empty
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or not shipper_id.strip():
            return False

        def _in_range(value: Any, min_v: float, max_v: float) -> bool:
            try:
                v = float(value)
            except (TypeError, ValueError):
                return False
            return min_v <= v <= max_v

        if not _in_range(
            request.get("weight_kg"), self.MIN_WEIGHT_KG, self.MAX_WEIGHT_KG
        ):
            return False

        if not _in_range(
            request.get("distance_km"), self.MIN_DISTANCE_KM, self.MAX_DISTANCE_KM
        ):
            return False

        if not _in_range(
            request.get("declared_value"),
            self.MIN_DECLARED_VALUE,
            self.MAX_DECLARED_VALUE,
        ):
            return False

        return True

    def _decide_from_risk(self, risk_index: int) -> QuoteDecision:
        """Decision table DT-S: map risk_index to decision row."""

        if risk_index <= self.ACCEPT_MAX:
            # accept row: priced, notified with quote document, status quoted
            return QuoteDecision(
                status=self.STATUS_QUOTED,
                priced=True,
                notify="quote",
                hold=False,
            )
        if self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # review row: held for manual review, not priced, not notified
            return QuoteDecision(
                status=self.STATUS_REVIEW_HOLD,
                priced=False,
                notify=None,
                hold=False,
            )
        # refuse row: refused, not priced, refusal notice
        if risk_index >= self.REFUSE_MIN:
            return QuoteDecision(
                status=self.STATUS_REFUSED_SCREENING,
                priced=False,
                notify="refusal",
                hold=False,
            )

        # The DMN covers all integers, but in case of an unexpected gap,
        # fail closed by refusing without pricing.
        return QuoteDecision(
            status=self.STATUS_REFUSED_SCREENING,
            priced=False,
            notify="refusal",
            hold=False,
        )


_api = QuoteAPI()


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point delegating to QuoteAPI.handle."""

    return _api.handle(request)

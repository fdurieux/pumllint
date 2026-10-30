class StoreUnavailableError(Exception):
    """Raised when the QuoteStore is unavailable or storage fails."""
    pass


class ScreeningUnavailableError(Exception):
    """Raised when the ScreeningService is unavailable or screening fails."""
    pass


class QuoteStore:
    """Persistence layer for quotes.

    In production this would talk to a database. Here it's just an interface
    that a test harness can stub.
    """

    def store_draft(self, request):
        """Store a draft quote and return a quote_id.

        May raise StoreUnavailableError on failure.
        """
        raise NotImplementedError

    def update_quote(self, quote_id, status, price=None, hold=None):
        """Update an existing quote's status and optional fields.

        May raise StoreUnavailableError on failure.
        """
        raise NotImplementedError


class TariffEngine:
    """Pricing logic implementing DT-P (P1..P4) for the current tariff."""

    # Constants from verified/approved tariff assertions
    BASE_WEIGHT_COEFF = 0.87  # from A:dt:P1|formula@v1
    BASE_DISTANCE_COEFF = 1.13  # from A:dt:P1|formula@v1
    HEAVY_SURCHARGE_THRESHOLD = 1244  # from A:dt:P2|threshold@v2
    HEAVY_SURCHARGE_AMOUNT = 341.00  # from A:dt:P2|surcharge@v2
    LONG_HAUL_THRESHOLD = 4912  # from A:dt:P3|threshold@v1
    LONG_HAUL_FACTOR = 1.19  # from A:dt:P3|factor@v1
    ROUNDING_PLACES = 2  # from A:dt:P4|rounding@v1

    def price(self, weight_kg, distance_km):
        """Compute the price according to DT-P using the current tariff.

        Steps:
        - P1: base = 0.87 * weight_kg + 1.13 * distance_km
        - P2: if weight_kg > 1244, add 341.00 flat
        - P3: if distance_km >= 4912, multiply running total by 1.19 (after P2)
        - P4: price = round(result, 2)
        """
        # P1
        result = (
            self.BASE_WEIGHT_COEFF * float(weight_kg)
            + self.BASE_DISTANCE_COEFF * float(distance_km)
        )

        # P2: heavy surcharge
        if float(weight_kg) > self.HEAVY_SURCHARGE_THRESHOLD:
            result += self.HEAVY_SURCHARGE_AMOUNT

        # P3: long-haul multiplier, applied after P2 (order normative)
        if float(distance_km) >= self.LONG_HAUL_THRESHOLD:
            result *= self.LONG_HAUL_FACTOR

        # P4: rounding
        price = round(result, self.ROUNDING_PLACES)
        return price


class ScreeningService:
    """External screening service to obtain a risk index for a shipper."""

    def screen(self, shipper_id, weight_kg, distance_km, declared_value):
        """Return a numeric risk_index for the given quote request.

        May raise ScreeningUnavailableError on outage.
        """
        raise NotImplementedError


class NotificationService:
    """Fire-and-forget notification sender for quote documents and refusals."""

    def send_quote_document(self, quote_id, price):
        """Send a quote document. Failures must not affect response or storage."""
        raise NotImplementedError

    def send_refusal_notice(self, quote_id):
        """Send a refusal notice. Failures must not affect response or storage."""
        raise NotImplementedError


class QuoteAPI:
    """Implements the governed CargoQuote flow according to the spec and DT-S."""

    # Validation bounds (all approved)
    MIN_WEIGHT_KG = 3
    MAX_WEIGHT_KG = 19400
    MIN_DISTANCE_KM = 25
    MAX_DISTANCE_KM = 7150
    MIN_DECLARED_VALUE = 50
    MAX_DECLARED_VALUE = 83000

    # Screening decision thresholds
    ACCEPT_MAX = 41  # risk_index <= 41 -> quoted
    REVIEW_MIN = 42  # 42 <= risk_index <= 66 -> review_hold
    REVIEW_MAX = 66
    REFUSE_MIN = 67  # risk_index >= 67 -> refused_screening

    def __init__(self, store=None, tariff_engine=None, screening=None, notifier=None):
        self.store = store or QuoteStore()
        self.tariff = tariff_engine or TariffEngine()
        self.screening = screening or ScreeningService()
        self.notifier = notifier or NotificationService()

    def handle(self, request):
        """Handle a quote request dict and return a response dict.

        request keys: shipper_id, weight_kg, distance_km, declared_value.
        """
        # 1. validate
        validation_error = self._validate_request(request)
        if validation_error is not None:
            # Invalid request behaviour: immediate rejection, nothing else runs
            return {
                "status": "rejected: invalid_request",
                "error": validation_error,
            }

        shipper_id = request.get("shipper_id")
        weight_kg = request.get("weight_kg")
        distance_km = request.get("distance_km")
        declared_value = request.get("declared_value")

        # 2. store draft
        try:
            quote_id = self.store.store_draft(
                {
                    "shipper_id": shipper_id,
                    "weight_kg": weight_kg,
                    "distance_km": distance_km,
                    "declared_value": declared_value,
                }
            )
        except StoreUnavailableError:
            # On storage failure nothing else runs
            return {
                "status": "error: store_unavailable",
            }

        # 3. screen
        try:
            risk_index = self.screening.screen(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except ScreeningUnavailableError:
            # Screening outage path: price anyway, held_unscreened, not notified, hold: true
            price = self.tariff.price(weight_kg, distance_km)
            try:
                self.store.update_quote(
                    quote_id=quote_id,
                    status="held_unscreened",
                    price=price,
                    hold=True,
                )
            except StoreUnavailableError:
                # Spec only defines store failure on initial draft; here we conservatively
                # reflect the storage error in status while preserving the computed price.
                return {
                    "status": "error: store_unavailable",
                    "quote_id": quote_id,
                }

            response = {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }
            # No notification in outage path
            return response

        # 4. decide based on risk_index
        if risk_index <= self.ACCEPT_MAX:
            # Accept -> quoted, priced yes, notified quote document
            price = self.tariff.price(weight_kg, distance_km)
            try:
                self.store.update_quote(
                    quote_id=quote_id,
                    status="quoted",
                    price=price,
                    hold=None,
                )
            except StoreUnavailableError:
                return {
                    "status": "error: store_unavailable",
                    "quote_id": quote_id,
                }

            response = {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }

            # Notify (fire-and-forget: failures do not change response or storage)
            try:
                self.notifier.send_quote_document(quote_id, price)
            except Exception:
                # On notification failure, response and stored quote remain unchanged
                pass

            return response

        if self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review -> review_hold, no pricing, no notification
            try:
                self.store.update_quote(
                    quote_id=quote_id,
                    status="review_hold",
                    price=None,
                    hold=None,
                )
            except StoreUnavailableError:
                return {
                    "status": "error: store_unavailable",
                    "quote_id": quote_id,
                }

            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }

        if risk_index >= self.REFUSE_MIN:
            # Refuse -> refused_screening, no pricing, refusal notice sent
            try:
                self.store.update_quote(
                    quote_id=quote_id,
                    status="refused_screening",
                    price=None,
                    hold=None,
                )
            except StoreUnavailableError:
                return {
                    "status": "error: store_unavailable",
                    "quote_id": quote_id,
                }

            response = {
                "status": "refused_screening",
                "quote_id": quote_id,
            }

            try:
                self.notifier.send_refusal_notice(quote_id)
            except Exception:
                # Fire-and-forget
                pass

            return response

        # The DMN covers all integer ranges, but if a weird non-numeric or unexpected
        # risk_index slipped through, treat defensively as review_hold without pricing.
        try:
            self.store.update_quote(
                quote_id=quote_id,
                status="review_hold",
                price=None,
                hold=None,
            )
        except StoreUnavailableError:
            return {
                "status": "error: store_unavailable",
                "quote_id": quote_id,
            }

        return {
            "status": "review_hold",
            "quote_id": quote_id,
        }

    def _validate_request(self, request):
        """Return an error string if invalid, else None.

        Enforces the decision table constraints for input fields.
        """
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or not shipper_id.strip():
            return "shipper_id must be a non-empty string"

        # Numeric fields must be present and within bounds
        def _as_number(name, min_val, max_val):
            if name not in request:
                return None, f"{name} is required"
            value = request[name]
            try:
                num = float(value)
            except (TypeError, ValueError):
                return None, f"{name} must be a number"
            if num < min_val or num > max_val:
                return None, f"{name} must be between {min_val} and {max_val}"
            return num, None

        _, err = _as_number("weight_kg", self.MIN_WEIGHT_KG, self.MAX_WEIGHT_KG)
        if err:
            return err
        _, err = _as_number("distance_km", self.MIN_DISTANCE_KM, self.MAX_DISTANCE_KM)
        if err:
            return err
        _, err = _as_number("declared_value", self.MIN_DECLARED_VALUE, self.MAX_DECLARED_VALUE)
        if err:
            return err

        return None


# Module-level handle function expected by the harness
_api_instance = QuoteAPI()


def handle(request):
    """Entry point delegating to QuoteAPI.handle."""
    return _api_instance.handle(request)

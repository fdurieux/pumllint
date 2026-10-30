class StoreUnavailableError(Exception):
    """Raised when the QuoteStore is unavailable for storage operations."""
    pass


class ScreeningUnavailableError(Exception):
    """Raised when the ScreeningService is unavailable or encounters an outage."""
    pass


class QuoteStore:
    """Persistence layer for quotes.

    Methods may raise StoreUnavailableError on storage failures.
    """

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        """Store a draft quote and return its quote_id.

        In real usage this would persist to a database. Here it's a stub
        that a test harness can override.
        """
        raise NotImplementedError

    def update_quote(self, quote_id, status, price=None, hold=None):
        """Update an existing quote's status and optional fields.

        May raise StoreUnavailableError if the store is unavailable.
        """
        raise NotImplementedError


class TariffEngine:
    """Tariff calculation engine implementing DT-P pricing rules."""

    # Pricing constants from DT-P
    BASE_WEIGHT_COEFF = 0.87  # from P1 formula
    BASE_DISTANCE_COEFF = 1.13  # from P1 formula
    HEAVY_THRESHOLD_KG = 1244  # from P2 threshold (v2)
    HEAVY_SURCHARGE = 341.00  # from P2 surcharge (v2)
    LONG_HAUL_THRESHOLD_KM = 4912  # from P3 threshold
    LONG_HAUL_FACTOR = 1.19  # from P3 factor

    def price(self, weight_kg, distance_km):
        """Compute the price according to DT-P.

        Implements:
        - P1: base = 0.87 * weight_kg + 1.13 * distance_km
        - P2: if weight_kg > 1244, add 341.00 flat
        - P3: if distance_km >= 4912, multiply running total by 1.19 (after P2)
        - P4: final rounding to 2 decimal places
        """
        # P1: base calculation
        result = (
            self.BASE_WEIGHT_COEFF * float(weight_kg)
            + self.BASE_DISTANCE_COEFF * float(distance_km)
        )

        # P2: heavy surcharge (applied after base)
        if float(weight_kg) > self.HEAVY_THRESHOLD_KG:
            result += self.HEAVY_SURCHARGE

        # P3: long-haul multiplier applied after P2
        if float(distance_km) >= self.LONG_HAUL_THRESHOLD_KM:
            result *= self.LONG_HAUL_FACTOR

        # P4: rounding to 2 decimal places
        price = round(result, 2)
        return price


class ScreeningService:
    """External screening service to obtain shipper risk index.

    screen(shipper_id) may raise ScreeningUnavailableError on outage.
    """

    def screen(self, shipper_id):
        """Return a numeric risk_index for the given shipper_id.

        May raise ScreeningUnavailableError if the service is unavailable.
        """
        raise NotImplementedError


class NotificationService:
    """Service to deliver quote documents and refusal notices.

    Failures here are fire-and-forget and must not affect response or storage.
    """

    def send_quote_document(self, quote_id):
        """Send a quote document for the given quote.

        Any exceptions must be treated as fire-and-forget by callers.
        """
        raise NotImplementedError

    def send_refusal_notice(self, quote_id):
        """Send a refusal notice for the given quote.

        Any exceptions must be treated as fire-and-forget by callers.
        """
        raise NotImplementedError


class QuoteAPI:
    """Implements the CargoQuote API flow according to the governed policy.

    Flow order (spec:flow|order@v1):
      1. validate
      2. store
      3. screen
      4. decide
      5. price
      6. notify
      7. respond
    """

    # Validation bounds
    WEIGHT_MIN = 3
    WEIGHT_MAX = 19400
    DISTANCE_MIN = 25
    DISTANCE_MAX = 7150
    DECLARED_VALUE_MIN = 50
    DECLARED_VALUE_MAX = 83000

    # Screening decision thresholds
    ACCEPT_MAX = 41  # risk_index <= 41 => accept
    REVIEW_MIN = 42  # 42 <= risk_index <= 66 => review
    REVIEW_MAX = 66
    REFUSE_MIN = 67  # risk_index >= 67 => refuse

    def __init__(self):
        self.store = QuoteStore()
        self.tariff = TariffEngine()
        self.screening = ScreeningService()
        self.notification = NotificationService()

    # --- Public entry point ---

    def handle(self, request):
        """Process a quote request dict and return a response dict.

        request keys: shipper_id, weight_kg, distance_km, declared_value.
        """
        # 1. validate
        valid, error_status = self._validate_request(request)
        if not valid:
            # invalid_request behaviour: reject immediately
            return {"status": error_status}

        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]

        # 2. store draft
        try:
            quote_id = self.store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            # On storage failure nothing else runs; status error: store_unavailable
            return {"status": "error: store_unavailable"}

        # 3. screen
        try:
            risk_index = self.screening.screen(shipper_id)
            screening_outage = False
        except ScreeningUnavailableError:
            # Screening outage path per QuoteAPI|on_screening_outage
            screening_outage = True
            risk_index = None

        response = {"quote_id": quote_id}

        if screening_outage:
            # Price anyway, update to held_unscreened, do not notify, respond with hold: true
            price = self.tariff.price(weight_kg, distance_km)
            try:
                self.store.update_quote(
                    quote_id=quote_id,
                    status="held_unscreened",
                    price=price,
                    hold=True,
                )
            except StoreUnavailableError:
                # Spec does not define a different behaviour here; since draft exists,
                # and store failure on update is not called out, we leave it to propagate.
                raise

            response["status"] = "held_unscreened"
            response["price"] = price
            response["hold"] = True
            return response

        # 4. decide based on risk_index
        if risk_index <= self.ACCEPT_MAX:
            decision = "accept"
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            decision = "review"
        else:  # risk_index >= REFUSE_MIN
            decision = "refuse"

        # 5. price (only for priced paths) and update stored quote
        if decision == "accept":
            # Accept row: priced, quoted, notified with quote document
            price = self.tariff.price(weight_kg, distance_km)
            try:
                self.store.update_quote(
                    quote_id=quote_id,
                    status="quoted",
                    price=price,
                    hold=None,
                )
            except StoreUnavailableError:
                # No special rule for update failure; propagate
                raise

            # 6. notify (fire-and-forget)
            try:
                self.notification.send_quote_document(quote_id)
            except Exception:
                # Fire-and-forget: a delivery failure never changes stored quote or response
                pass

            # 7. respond
            response["status"] = "quoted"
            response["price"] = price
            return response

        if decision == "review":
            # Review row: not priced, no notification, status review_hold
            try:
                self.store.update_quote(
                    quote_id=quote_id,
                    status="review_hold",
                    price=None,
                    hold=None,
                )
            except StoreUnavailableError:
                # No special rule for update failure; propagate
                raise

            response["status"] = "review_hold"
            return response

        # decision == "refuse"
        # Refuse row: not priced, refusal notice, status refused_screening
        try:
            self.store.update_quote(
                quote_id=quote_id,
                status="refused_screening",
                price=None,
                hold=None,
            )
        except StoreUnavailableError:
            # No special rule for update failure; propagate
            raise

        # Notify refusal, fire-and-forget
        try:
            self.notification.send_refusal_notice(quote_id)
        except Exception:
            # Fire-and-forget semantics
            pass

        response["status"] = "refused_screening"
        return response

    # --- Internal helpers ---

    def _validate_request(self, request):
        """Validate request according to the value constraints.

        Returns (is_valid: bool, error_status: str|None).
        """
        # shipper_id present and non-empty
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or len(shipper_id) == 0:
            return False, "rejected: invalid_request"

        # Validate numeric fields presence
        for field in ("weight_kg", "distance_km", "declared_value"):
            if field not in request:
                return False, "rejected: invalid_request"

        try:
            weight_kg = float(request["weight_kg"])
            distance_km = float(request["distance_km"])
            declared_value = float(request["declared_value"])
        except (TypeError, ValueError):
            return False, "rejected: invalid_request"

        if not (self.WEIGHT_MIN <= weight_kg <= self.WEIGHT_MAX):
            return False, "rejected: invalid_request"
        if not (self.DISTANCE_MIN <= distance_km <= self.DISTANCE_MAX):
            return False, "rejected: invalid_request"
        if not (self.DECLARED_VALUE_MIN <= declared_value <= self.DECLARED_VALUE_MAX):
            return False, "rejected: invalid_request"

        return True, None


# Module-level handle function expected by the harness
_api_instance = QuoteAPI()


def handle(request):
    """Module-level entry point delegating to QuoteAPI.handle."""
    return _api_instance.handle(request)

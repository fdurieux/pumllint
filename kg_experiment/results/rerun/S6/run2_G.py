class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable."""
    pass


class ScreeningUnavailableError(Exception):
    """Raised when the screening service is unavailable."""
    pass


class QuoteStore:
    def store_draft(self, request):
        """Store a draft quote and return a quote_id.

        May raise StoreUnavailableError on failure.
        """
        raise NotImplementedError

    def update_quote(self, quote_id, status, price=None, hold=None):
        """Update an existing quote with new status and optional price/hold.

        May raise StoreUnavailableError on failure.
        """
        raise NotImplementedError


class TariffEngine:
    def price(self, weight_kg, distance_km):
        """Compute the price according to DT-P (P1..P4)."""
        # P1: base = 0.87 * weight_kg + 1.13 * distance_km (A:dt:P1|formula@v1)
        base = 0.87 * weight_kg + 1.13 * distance_km

        # P2: heavy surcharge if weight_kg > 1244, add 341.00 flat
        # (A:dt:P2|threshold@v2, A:dt:P2|surcharge@v2)
        if weight_kg > 1244:
            base += 341.00

        # P3: long-haul multiplier if distance_km >= 4912, multiply by 1.19,
        # applied after P2 (A:dt:P3|threshold@v1, A:dt:P3|factor@v1, A:dt:P3|order@v2)
        if distance_km >= 4912:
            base *= 1.19

        # P4: price = round(result, 2) (A:dt:P4|rounding@v1)
        price = round(base, 2)
        return price


class ScreeningService:
    def screen(self, shipper_id, weight_kg, distance_km, declared_value):
        """Return a risk_index for the given request.

        May raise ScreeningUnavailableError on outage.
        """
        raise NotImplementedError


class NotificationService:
    def send_quote_document(self, quote_id):
        """Fire-and-forget quote document notification.

        Failures must not change stored quote or response
        (A:dt:QuoteAPI|on_notification_failure@v1).
        """
        try:
            self._send_quote_document_impl(quote_id)
        except Exception:
            # Fire-and-forget: ignore failures.
            pass

    def _send_quote_document_impl(self, quote_id):
        raise NotImplementedError

    def send_refusal_notice(self, quote_id):
        """Fire-and-forget refusal notice notification.

        Failures must not change stored quote or response
        (A:dt:QuoteAPI|on_notification_failure@v1).
        """
        try:
            self._send_refusal_notice_impl(quote_id)
        except Exception:
            # Fire-and-forget: ignore failures.
            pass

    def _send_refusal_notice_impl(self, quote_id):
        raise NotImplementedError


class QuoteAPI:
    def __init__(self):
        self.store = QuoteStore()
        self.tariff = TariffEngine()
        self.screening = ScreeningService()
        self.notification = NotificationService()

    def handle(self, request):
        """Process a quote request according to the governed specification.

        request: dict with keys shipper_id, weight_kg, distance_km, declared_value.
        Returns a dict with at least a 'status' key, and optionally
        'quote_id', 'price', and 'hold' according to DT-S and API spec.
        """
        shipper_id = request.get("shipper_id")
        weight_kg = request.get("weight_kg")
        distance_km = request.get("distance_km")
        declared_value = request.get("declared_value")

        # Step 1: validate (A:dt:shipper_id|present@v1, A:dt:weight_kg|min@v1, A:dt:weight_kg|max@v1,
        # A:dt:distance_km|min@v1, A:dt:distance_km|max@v1, A:dt:declared_value|min@v1,
        # A:dt:declared_value|max@v1, A:dt:invalid_request|behaviour@v1).
        if not isinstance(shipper_id, str) or shipper_id == "":
            return {"status": "rejected: invalid_request"}

        try:
            w = float(weight_kg)
            d = float(distance_km)
            v = float(declared_value)
        except (TypeError, ValueError):
            return {"status": "rejected: invalid_request"}

        if not (3 <= w <= 19400):
            return {"status": "rejected: invalid_request"}
        if not (25 <= d <= 7150):
            return {"status": "rejected: invalid_request"}
        if not (50 <= v <= 83000):
            return {"status": "rejected: invalid_request"}

        # Step 2: store draft (A:spec:flow|order@v1, A:dt:QuoteAPI|on_store_failure@v1).
        try:
            quote_id = self.store.store_draft({
                "shipper_id": shipper_id,
                "weight_kg": w,
                "distance_km": d,
                "declared_value": v,
                "status": "draft",
            })
        except StoreUnavailableError:
            # On storage failure: no screening, no pricing, no notification.
            return {"status": "error: store_unavailable"}

        # Step 3: screen (A:spec:flow|order@v1, A:spec:QuoteAPI|on_screening_outage@v1).
        try:
            risk_index = self.screening.screen(shipper_id, w, d, v)
            screening_outage = False
        except ScreeningUnavailableError:
            risk_index = None
            screening_outage = True

        # Screening outage path: price, held_unscreened, no notify, hold:true
        # (A:dt:QuoteAPI|on_screening_outage@v1, A:bpmn:QuoteAPI|on_screening_outage@v1,
        # A:seq:QuoteAPI|on_screening_outage@v1, A:spec:response|hold_presence@v1,
        # A:spec:response|price_presence@v1, A:spec:response|quote_id_presence@v1).
        if screening_outage:
            price = self.tariff.price(w, d)
            try:
                self.store.update_quote(quote_id, status="held_unscreened", price=price, hold=True)
            except StoreUnavailableError:
                # Spec only defines store failure on initial store; for update failures
                # no alternate behaviour is defined, so we propagate an error status
                # consistent with store_unavailable semantics.
                return {"status": "error: store_unavailable"}

            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4: decide based on risk_index (DT-S: accept/review/refuse rows).
        if risk_index <= 41:
            decision = "accept"
        elif 42 <= risk_index <= 66:
            decision = "review"
        else:  # risk_index >= 67
            decision = "refuse"

        # Step 5-6: price, notify, and update store according to decision.
        if decision == "accept":
            # Accept row: priced=yes, notified quote document, status quoted
            # (A:dt:S-accept|priced@v1, A:dt:S-accept|notified@v1, A:dt:S-accept|status@v1).
            price = self.tariff.price(w, d)
            try:
                self.store.update_quote(quote_id, status="quoted", price=price, hold=None)
            except StoreUnavailableError:
                return {"status": "error: store_unavailable"}

            # Fire-and-forget notification; failures do not affect response or store
            # (A:dt:QuoteAPI|on_notification_failure@v1).
            self.notification.send_quote_document(quote_id)

            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }

        if decision == "review":
            # Review row: no pricing, no notification, status review_hold
            # (A:dt:S-review|priced@v1, A:dt:S-review|notified@v1, A:dt:S-review|status@v1).
            try:
                self.store.update_quote(quote_id, status="review_hold", price=None, hold=None)
            except StoreUnavailableError:
                return {"status": "error: store_unavailable"}

            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }

        # decision == "refuse"
        # Refuse row: no pricing, refusal notice, status refused_screening
        # (A:dt:S-refuse|priced@v1, A:dt:S-refuse|notified#1@v1, A:dt:S-refuse|status@v1).
        try:
            self.store.update_quote(quote_id, status="refused_screening", price=None, hold=None)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        self.notification.send_refusal_notice(quote_id)

        return {
            "status": "refused_screening",
            "quote_id": quote_id,
        }


def handle(request):
    api = QuoteAPI()
    return api.handle(request)

ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000

HEAVY_THRESHOLD = 1244
HEAVY_SURCHARGE = 316.00
LONGHAUL_THRESHOLD = 4912
LONGHAUL_MULTIPLIER = 1.19


class ScreeningError(Exception):
    """Raised when the external screening provider is unavailable."""


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable."""


class NotificationError(Exception):
    """Raised when the notification provider fails to deliver."""


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, risk_index=0, available=True):
        self.risk_index = risk_index
        self.available = available

    def screen(self, shipper_id):
        if not self.available:
            raise ScreeningError("screening_unavailable")
        return int(self.risk_index)


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, available=True):
        self.available = available
        self.sent = []

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        if not self.available:
            raise NotificationError("delivery_failed")
        self.sent.append(("quote_document", shipper_id, quote_id, price_amount))
        return "delivered"

    def sendRefusalNotice(self, shipper_id, quote_id):
        if not self.available:
            raise NotificationError("delivery_failed")
        self.sent.append(("refusal_notice", shipper_id, quote_id))
        return "delivered"


class TariffEngine:
    """Computes the freight price from weight and distance per DT-P."""

    def price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > HEAVY_THRESHOLD:
            result += HEAVY_SURCHARGE
        if distance_km >= LONGHAUL_THRESHOLD:
            result *= LONGHAUL_MULTIPLIER
        return round(result, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available=True):
        self.available = available
        self._records = {}
        self._counter = 0

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self.available:
            raise StoreUnavailableError("store_unavailable")
        self._counter += 1
        quote_id = "Q-{:06d}".format(self._counter)
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def updateQuote(self, quote_id, status, price_amount=None):
        if not self.available:
            raise StoreUnavailableError("store_unavailable")
        record = self._records.get(quote_id, {})
        record["status"] = status
        if price_amount is not None:
            record["price"] = price_amount
        self._records[quote_id] = record
        return "updated"


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and
    pricing, and returns the quotation outcome."""

    def __init__(self, tariff_engine, quote_store, screening_service,
                 notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False
        for value in (weight_kg, distance_km, declared_value):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return False
        if not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            return False
        if not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            return False
        if not (VALUE_MIN <= declared_value <= VALUE_MAX):
            return False
        return True

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Step 1: validate
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        # Step 2: store draft
        try:
            quote_id = self.quote_store.storeDraft(
                shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            # Screening outage: price anyway, hold, do not notify.
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4-6: apply screening decision
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "quoted", price_amount)
            try:
                self.notification_service.sendQuoteDocument(
                    shipper_id, quote_id, price_amount)
            except NotificationError:
                pass  # fire-and-forget
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount,
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.updateQuote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.updateQuote(quote_id, "refused_screening")
            try:
                self.notification_service.sendRefusalNotice(shipper_id, quote_id)
            except NotificationError:
                pass  # fire-and-forget
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }


def _truthy_outage(value):
    if isinstance(value, str):
        return value.strip().lower() in (
            "error", "unavailable", "down", "outage", "failed", "false", "no")
    if isinstance(value, bool):
        return not value
    return False


def handle(request: dict) -> dict:
    request = request or {}

    # --- Configure the quote store ---
    store_available = True
    store_signal = request.get("store_result",
                               request.get("store_status",
                                           request.get("quote_store_result",
                                                       request.get("quote_store_status"))))
    if store_signal is not None and _truthy_outage(store_signal):
        store_available = False
    if request.get("store_exists") is False or request.get("quote_store_exists") is False:
        store_available = False
    quote_store = QuoteStore(available=store_available)

    # --- Configure the screening service ---
    screening_available = True
    risk_index = 0
    screening_signal = request.get("screening_result",
                                   request.get("screening_status"))
    if isinstance(screening_signal, bool):
        screening_available = not screening_signal is False and screening_signal
    elif isinstance(screening_signal, (int, float)):
        risk_index = int(screening_signal)
    elif isinstance(screening_signal, str):
        s = screening_signal.strip().lower()
        if s in ("error", "unavailable", "down", "outage", "failed"):
            screening_available = False
        else:
            try:
                risk_index = int(float(screening_signal))
            except ValueError:
                screening_available = True

    if "risk_index" in request and request["risk_index"] is not None:
        try:
            risk_index = int(request["risk_index"])
        except (ValueError, TypeError):
            pass

    if request.get("screening_exists") is False:
        screening_available = False
    screening_service = ScreeningService(risk_index=risk_index,
                                          available=screening_available)

    # --- Configure the notification service ---
    notification_available = True
    notif_signal = request.get("notification_result",
                               request.get("notification_status"))
    if notif_signal is not None and _truthy_outage(notif_signal):
        notification_available = False
    notification_service = NotificationService(available=notification_available)

    # --- Assemble API ---
    tariff_engine = TariffEngine()
    api = QuoteApi(tariff_engine, quote_store, screening_service,
                   notification_service)

    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    return api.requestQuote(shipper_id, weight_kg, distance_km, declared_value)
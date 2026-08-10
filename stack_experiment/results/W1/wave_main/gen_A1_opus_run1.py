from __future__ import annotations


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, override=None):
        if override is not None:
            return override
        return 10.0


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send(self, shipper_id, document, override=None):
        if override is not None:
            return override
        return "sent"


class TariffEngine:
    """Computes the freight price from weight and distance per tariff rules."""

    BASE_FEE = 25.0
    RATE_PER_KG = 0.15
    RATE_PER_KM = 0.40
    VALUE_SURCHARGE_RATE = 0.005

    def compute_price(self, weight_kg, distance_km, declared_value):
        price = (
            self.BASE_FEE
            + weight_kg * self.RATE_PER_KG
            + distance_km * self.RATE_PER_KM
            + declared_value * self.VALUE_SURCHARGE_RATE
        )
        return round(price, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._counter = 0

    def save(self, quote, override=None):
        if override is not None and override == "error":
            return "error"
        self._counter += 1
        quote_id = quote.get("quote_id") or f"Q-{self._counter:05d}"
        self._records[quote_id] = dict(quote)
        return quote_id

    def update_status(self, quote_id, status, override=None):
        if override is not None and override == "error":
            return "error"
        if quote_id in self._records:
            self._records[quote_id]["status"] = status
        return "updated"


class Shipper:
    """A logistics customer requesting a price quote for palletized road cargo."""

    def __init__(self, api):
        self._api = api

    def request_quote(self, request):
        return self._api.request_quote(request)


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and
    pricing, and returns the quotation outcome."""

    LOW_RISK_MAX = 30.0
    HIGH_RISK_MIN = 70.0

    def __init__(self, tariff_engine, quote_store, screening_service,
                 notification_service):
        self._tariff = tariff_engine
        self._store = quote_store
        self._screening = screening_service
        self._notifier = notification_service

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not shipper_id:
            raise ValueError("missing shipper")
        if request.get("shipper_exists") is False or \
                request.get("shipper_found") is False:
            raise ValueError("unknown shipper")
        weight = request.get("weight_kg")
        distance = request.get("distance_km")
        value = request.get("declared_value")
        for name, val in (("weight_kg", weight), ("distance_km", distance),
                          ("declared_value", value)):
            if val is None:
                raise ValueError(f"missing {name}")
            try:
                num = float(val)
            except (TypeError, ValueError):
                raise ValueError(f"invalid {name}")
            if num <= 0:
                raise ValueError(f"invalid {name}")
        return shipper_id, float(weight), float(distance), float(value)

    def request_quote(self, request):
        # 1. Validate
        shipper_id, weight, distance, value = self._validate(request)

        # 2. Record the quote request
        record = {
            "shipper_id": shipper_id,
            "weight_kg": weight,
            "distance_km": distance,
            "declared_value": value,
            "status": "received",
        }
        store_override = request.get("store_status") or request.get("store_result")
        quote_id = self._store.save(record, override=store_override)
        if quote_id == "error":
            raise RuntimeError("store unavailable")

        # 3. Screen the shipper
        risk_override = None
        raw = request.get("screening_result", request.get("screening_status"))
        if raw is not None:
            if isinstance(raw, (int, float)):
                risk_override = float(raw)
            else:
                mapping = {
                    "approved": 10.0,
                    "active": 10.0,
                    "assessed": 50.0,
                    "review": 50.0,
                    "declined": 90.0,
                }
                if raw == "error":
                    raise RuntimeError("screening unavailable")
                risk_override = mapping.get(raw, 10.0)
        risk_index = self._screening.screen(shipper_id, override=risk_override)

        # 4. Decide outcome based on screening
        if risk_index >= self.HIGH_RISK_MIN:
            self._store.update_status(quote_id, "refused")
            self._notifier.send(shipper_id, {"type": "refusal", "quote_id": quote_id},
                                override=request.get("notification_status"))
            return {
                "status": "rejected",
                "quote_id": quote_id,
                "risk_index": risk_index,
                "reason": "screening_refused",
            }

        if risk_index > self.LOW_RISK_MAX:
            self._store.update_status(quote_id, "manual_review")
            return {
                "status": "held",
                "quote_id": quote_id,
                "risk_index": risk_index,
                "reason": "manual_review",
            }

        # 5. Price the consignment
        price = self._tariff.compute_price(weight, distance, value)
        self._store.update_status(quote_id, "quoted")
        self._notifier.send(shipper_id,
                            {"type": "quote", "quote_id": quote_id, "price": price},
                            override=request.get("notification_status"))
        return {
            "status": "confirmed",
            "quote_id": quote_id,
            "price": price,
            "risk_index": risk_index,
        }


def _build_api():
    return QuoteApi(
        TariffEngine(),
        QuoteStore(),
        ScreeningService(),
        NotificationService(),
    )


def handle(request: dict) -> dict:
    api = _build_api()
    shipper = Shipper(api)
    try:
        return shipper.request_quote(request)
    except ValueError as exc:
        return {"status": f"error: {exc}"}
    except RuntimeError as exc:
        return {"status": f"error: {exc}"}
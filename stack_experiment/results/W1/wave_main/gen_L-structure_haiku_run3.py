import uuid
from typing import Any
from decimal import Decimal, ROUND_HALF_UP


class ScreeningService:
    """External screening provider — returns risk index for a shipper."""
    
    def __init__(self, risk_index: int | None = None, unavailable: bool = False):
        self.risk_index = risk_index
        self.unavailable = unavailable
    
    def screen(self, shipper_id: str) -> int | None:
        if self.unavailable:
            return None
        return self.risk_index


class TariffEngine:
    """Pricing engine — computes freight price per DT-P."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        base = 0.87 * weight_kg + 1.13 * distance_km
        
        if weight_kg > 1244:
            base += 316.00
        
        if distance_km >= 4912:
            base *= 1.19
        
        result = Decimal(str(base)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return float(result)


class QuoteStore:
    """Quote database — persists quote drafts and updates."""
    
    def __init__(self, unavailable: bool = False):
        self.unavailable = unavailable
        self.quotes = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str | None:
        if self.unavailable:
            return None
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            'shipper_id': shipper_id,
            'weight_kg': weight_kg,
            'distance_km': distance_km,
            'declared_value': declared_value,
            'status': 'draft',
            'price': None
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: float | None = None) -> dict | None:
        if quote_id not in self.quotes:
            return None
        self.quotes[quote_id]['status'] = status
        if price is not None:
            self.quotes[quote_id]['price'] = price
        return self.quotes[quote_id]


class NotificationService:
    """External notification provider — sends quote documents and refusal notices."""
    
    def __init__(self, failure: bool = False):
        self.failure = failure
        self.notifications = []
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> bool:
        if self.failure:
            return False
        self.notifications.append({
            'type': 'quote_document',
            'shipper_id': shipper_id,
            'quote_id': quote_id,
            'price': price
        })
        return True
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> bool:
        if self.failure:
            return False
        self.notifications.append({
            'type': 'refusal_notice',
            'shipper_id': shipper_id,
            'quote_id': quote_id
        })
        return True


class QuoteAPI:
    """Main quotation service — orchestrates the flow."""
    
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67
    
    def __init__(self, screening_service: ScreeningService, tariff_engine: TariffEngine,
                 quote_store: QuoteStore, notification_service: NotificationService):
        self.screening = screening_service
        self.tariff = tariff_engine
        self.store = quote_store
        self.notification = notification_service
    
    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> bool:
        """DT-V validation rules."""
        if not shipper_id or not isinstance(shipper_id, str) or len(shipper_id) == 0:
            return False
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False
        return True
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        """Main quotation flow."""
        
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {'status': 'rejected: invalid_request'}
        
        quote_id = self.store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        if quote_id is None:
            return {'status': 'error: store_unavailable'}
        
        risk_index = self.screening.screen(shipper_id)
        
        if risk_index is None:
            price = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, 'held_unscreened', price)
            return {
                'status': 'held_unscreened',
                'quote_id': quote_id,
                'price': price,
                'hold': True
            }
        
        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, 'quoted', price)
            self.notification.send_quote_document(shipper_id, quote_id, price)
            return {
                'status': 'quoted',
                'quote_id': quote_id,
                'price': price
            }
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.store.update_quote(quote_id, 'review_hold')
            return {
                'status': 'review_hold',
                'quote_id': quote_id
            }
        
        elif risk_index >= self.REFUSE_MIN:
            self.store.update_quote(quote_id, 'refused_screening')
            self.notification.send_refusal_notice(shipper_id, quote_id)
            return {
                'status': 'refused_screening',
                'quote_id': quote_id
            }


def handle(request: dict) -> dict:
    """End-to-end quotation flow."""
    
    shipper_id = request.get('shipper_id', '')
    weight_kg = request.get('weight_kg')
    distance_km = request.get('distance_km')
    declared_value = request.get('declared_value')
    
    screening_unavailable = request.get('screening_service_status') == 'unavailable'
    screening_risk_index = request.get('screening_service_result')
    
    store_unavailable = request.get('quote_store_exists') is False
    
    notification_failure = request.get('notification_service_status') == 'failure'
    
    screening_service = ScreeningService(
        risk_index=screening_risk_index,
        unavailable=screening_unavailable
    )
    
    tariff_engine = TariffEngine()
    
    quote_store = QuoteStore(unavailable=store_unavailable)
    
    notification_service = NotificationService(failure=notification_failure)
    
    api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)
    
    response = api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    
    return response
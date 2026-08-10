"""Cargo quote — screening and pricing flow (code-stub skeleton:
classes, signatures, and the control flow as comments; bodies are
`pass`)."""

# Actor: the Shipper — calls QuoteAPI.request_quote(...); receives
# every response named below.


class TariffEngine:  # engine
    def price(self, weight_kg, distance_km):
        """Compute priceAmount for a validated request."""
        pass


class ScreeningService:  # external
    def screen(self, shipper_id):
        """Return riskIndex. A screening failure surfaces as
        screeningUnavailableError (service unavailable)."""
        pass


class NotificationService:  # external
    def send_quote_document(self, shipper_id, quote_id, price_amount):
        """Deliver the quote document. Fire-and-forget: a delivery
        failure is the provider's retry problem and never changes the
        response (DT-S note 4)."""
        pass

    def send_refusal_notice(self, shipper_id, quote_id):
        """Deliver the refusal notice. Fire-and-forget, as above."""
        pass


class QuoteStore:  # database
    def store_draft(self, shipper_id, weight_kg, distance_km,
                    declared_value):
        """Store the draft; return quoteId. A storage failure surfaces
        as storeUnavailableError (storage unavailable)."""
        pass

    def update_quote(self, quote_id, status, price_amount=None):
        """Called as updateQuote(quoteId, status) or
        updateQuote(quoteId, status, priceAmount), exactly as the flow
        shows; returns updatedQuote."""
        pass


class QuoteAPI:  # service — the entry participant
    def request_quote(self, shipper_id, weight_kg, distance_km,
                      declared_value):
        """Flow, in order:

        1. If the request is valid (bounds: decision table DT-V):
           QuoteStore.store_draft(...) -> quoteId.
           Otherwise (validation error, bounds: decision table DT-V)
           -> respond rejectedInvalidRequest.
        2. If the draft was stored:
           ScreeningService.screen(shipper_id) -> riskIndex.
           On storeDraft failure (storage unavailable) -> respond
           storeUnavailableError. On storage failure nothing else
           runs: no screening call, no pricing, no notification
           (DT-S note 3).
        3. Apply the screening decision (decision table DT-S):
           - riskIndex <= ACCEPT_MAX (row accept):
             TariffEngine.price(weight_kg, distance_km) ->
             priceAmount; QuoteStore.update_quote(quoteId,
             statusQuoted, priceAmount) -> updatedQuote;
             NotificationService.send_quote_document(shipper_id,
             quoteId, priceAmount) async; respond quotedResponse.
             Notification is fire-and-forget: a delivery failure is
             the provider's retry problem and never changes the
             response (DT-S note 4).
           - REVIEW_MIN <= riskIndex <= REVIEW_MAX (row review):
             QuoteStore.update_quote(quoteId, statusReviewHold) ->
             updatedQuote; respond reviewHoldResponse. Review hold is
             not final: no pricing and no notification on this path
             (DT-S note 1).
           - riskIndex >= REFUSE_MIN (row refuse):
             QuoteStore.update_quote(quoteId,
             statusRefusedScreening) -> updatedQuote;
             NotificationService.send_refusal_notice(shipper_id,
             quoteId) async; respond refusedScreeningResponse.
             Refusal IS notified; pricing never runs on a refused
             quote (DT-S note 2).
           - screening failure (service unavailable):
             TariffEngine.price(weight_kg, distance_km) ->
             priceAmount; QuoteStore.update_quote(quoteId,
             statusHeldUnscreened, priceAmount) -> updatedQuote;
             respond heldUnscreenedResponse. Screening outage does
             NOT fail the quote: it is priced, stored on hold, and
             not notified (DT-S note 5).
        """
        pass

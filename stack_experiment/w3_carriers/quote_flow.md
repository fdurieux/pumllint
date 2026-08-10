# Cargo quote — screening and pricing flow (controlled-English rendering)

Same information as the UML sequence diagram, verbalized: flow order,
all branches and failure paths. Thresholds are symbolic — the numeric
bounds live only in decision tables DT-V, DT-S and DT-P.

Participants: the Shipper (actor), QuoteAPI (service), TariffEngine
(engine), ScreeningService (external), NotificationService (external),
and QuoteStore (database).

1. The Shipper calls QuoteAPI.requestQuote(shipperId, weightKg,
   distanceKm, declaredValue).
2. If the request is valid (bounds: decision table DT-V), QuoteAPI
   calls QuoteStore.storeDraft(shipperId, weightKg, distanceKm,
   declaredValue) and receives quoteId.
   Otherwise — the request is invalid (validation error, bounds:
   decision table DT-V) — QuoteAPI responds rejectedInvalidRequest to
   the Shipper and the flow stops.
3. If the draft was stored, QuoteAPI calls
   ScreeningService.screen(shipperId) and receives riskIndex.
   Otherwise — storeDraft failed (storage unavailable) — QuoteStore
   returns storeUnavailableError and QuoteAPI responds
   storeUnavailableError to the Shipper.
   Rule: on storage failure nothing else runs — no screening call, no
   pricing, no notification (DT-S note 3).
4. QuoteAPI applies the screening decision to riskIndex, one of four
   cases:
   a. If riskIndex <= ACCEPT_MAX (decision table DT-S, row accept):
      QuoteAPI calls TariffEngine.price(weightKg, distanceKm) and
      receives priceAmount; calls QuoteStore.updateQuote(quoteId,
      statusQuoted, priceAmount); sends
      NotificationService.sendQuoteDocument(shipperId, quoteId,
      priceAmount) asynchronously; and responds quotedResponse to the
      Shipper.
      Rule: notification is fire-and-forget — a delivery failure is
      the provider's retry problem and never changes the response
      (DT-S note 4).
   b. If REVIEW_MIN <= riskIndex <= REVIEW_MAX (decision table DT-S,
      row review): QuoteAPI calls QuoteStore.updateQuote(quoteId,
      statusReviewHold) and responds reviewHoldResponse to the
      Shipper.
      Rule: a review hold is not final — no pricing and no
      notification on this path (DT-S note 1).
   c. If riskIndex >= REFUSE_MIN (decision table DT-S, row refuse):
      QuoteAPI calls QuoteStore.updateQuote(quoteId,
      statusRefusedScreening); sends
      NotificationService.sendRefusalNotice(shipperId, quoteId)
      asynchronously; and responds refusedScreeningResponse to the
      Shipper.
      Rule: a refusal IS notified; pricing never runs on a refused
      quote (DT-S note 2).
   d. If screening failed (service unavailable): ScreeningService
      returns screeningUnavailableError; QuoteAPI calls
      TariffEngine.price(weightKg, distanceKm) and receives
      priceAmount; calls QuoteStore.updateQuote(quoteId,
      statusHeldUnscreened, priceAmount); and responds
      heldUnscreenedResponse to the Shipper.
      Rule: a screening outage does NOT fail the quote — it is
      priced, stored on hold, and not notified (DT-S note 5).

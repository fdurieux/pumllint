# CargoQuote — product brief

CargoQuote gives logistics customers an instant price quote for
palletized road cargo.

A shipper submits a quote request describing the consignment: who they
are, how heavy the cargo is, how far it travels, and its declared
value. CargoQuote validates the request, records it, has the shipper
screened by an external denied-party screening provider, prices the
consignment against the company tariff, and returns the outcome.
Depending on screening, a quote may be issued immediately, held for
manual review by the compliance team, or refused. Issued quote
documents and refusal notices are delivered to the shipper by an
external notification provider.

The quotation flow is synchronous: the shipper gets an immediate
response describing the outcome of their request.

Out of scope for this brief: booking, payment, carrier assignment, and
the manual-review workflow itself (only its entry point is part of the
quotation flow).

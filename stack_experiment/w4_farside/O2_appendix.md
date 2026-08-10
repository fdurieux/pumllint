# CargoQuote operations handbook — general appendix

Background material distributed with the CargoQuote specification
pack. Nothing in this appendix changes the quotation rules; the
normative decision semantics remain in decision_table.md.

## Company background

RoadRate Logistics BV was founded in 2004 as a two-truck courier
operation serving the Benelux corridor and grew through the 2010s
into a mid-sized palletized-freight specialist with cross-docking
hubs in Venlo, Duisburg and Lyon. The CargoQuote product line dates
from the 2019 digitalization programme, which replaced the
spreadsheet-and-phone quotation desk with self-service instant
quotation. The quotation desk's historical service level — a quote
within four business hours — shaped the programme's central promise:
a binding price in one synchronous request. Legacy quotation records
from before the programme are archived in the data warehouse under
retention class R-7 and play no role in the current flow.

## Related products (separate rule sets — not this specification)

- **AeroQuote** is the air-freight sibling product. Air quotations
  price on volumetric weight with a chargeable-weight divisor of
  6 000, apply fuel and security surcharges revised monthly, and are
  indicative rather than binding. None of AeroQuote's rules apply to
  road cargo; its tariff tables live with the AeroQuote
  specification.
- **ColdChain add-on** covers temperature-controlled trailers. It is
  quoted manually by the special-cargo desk and is out of scope for
  instant quotation.
- **Contract lanes**: customers with negotiated annual lane rates
  bypass instant quotation entirely; their pricing comes from the
  contract management system.

## Operational notes for the quotation service

The quotation service is operated by the platform team under the
standard on-call rota (follow-the-sun, primary and shadow). Deploys
ship through the regular weekly release train; quotation is not
exempt from the change-freeze weeks around fiscal year-end. Incident
severity for quotation follows the platform matrix: total outage of
the quotation endpoint is SEV-2 (customer-facing degradation),
elevated error rate is SEV-3. The screening provider and the
notification provider are external vendors under their own SLAs;
vendor escalation goes through procurement's vendor-management desk,
not through engineering on-call.

## Brand and communication guidelines (excerpt)

Quote documents and refusal notices are customer-facing artifacts
and follow the corporate template set: sender is always the product
brand, the subject line names the quote reference, and the body uses
the approved plain-language blocks maintained by the communications
team. Refusal notices in particular must use the approved neutral
wording and must not speculate about screening outcomes; the
approved block links the shipper to the compliance contact form.
Template changes go through the quarterly communications review.

## Glossary of adjacent terms (not used by the quotation rules)

- **Cross-docking**: transferring pallets between vehicles at a hub
  without warehouse storage.
- **Volumetric weight**: the dimensional-weight figure used by the
  air product; road cargo charges actual chargeable weight.
- **Lane**: a recurring origin–destination pair under a transport
  contract.
- **POD**: proof of delivery, captured by the driver app at
  hand-over; not part of quotation.
- **Demurrage**: waiting-time charges at loading or unloading;
  invoiced after transport, never quoted in advance.
- **Fuel floater**: the indexed fuel adjustment applied to contract
  lanes; instant quotation prices are all-in and carry no floater.

## Frequently asked questions from the quotation desk archive

**Can a held quote be released by phone?** No. A `review_hold`
outcome is released or refused by the compliance team in the review
queue; the desk cannot override it.

**Do we quote dangerous goods?** ADR classes are out of scope for
instant quotation and route to the special-cargo desk.

**Why did a shipper receive no message for a held quote?** By
design: hold outcomes are not notified. The shipper sees the hold in
the response; messages go out only for issued quotes and refusals.

**Is the instant price binding?** Yes, for the validity window
printed on the quote document; the desk cannot extend the window.

## Fleet and network overview

The road network operates 214 tractor units and 388 trailers across
three trailer classes: standard curtain-siders, box trailers for
weather-sensitive palletized goods, and mega-trailers for
high-volume low-density cargo. Fleet renewal follows a seven-year
cycle for tractors and a ten-year cycle for trailers, managed by the
fleet desk in Venlo. Route planning runs nightly in the transport
management system; the planning horizon is 72 hours, with intraday
re-planning for breakdowns and no-shows. None of the planning
outputs feed the quotation service: quotation prices from the
published tariff, not from network utilization.

## Pallet and handling standards

The network standardizes on EUR/EPAL pallets; industrial pallets
are accepted at cross-docking hubs with a handling note. Stacking
rules follow the load-securing guidance in the driver handbook:
heavy pallets low, no overhang, strapping per the trailer class.
Damaged pallets found at a hub are exchanged under the pallet-pool
agreement and logged in the hub system. Handling exceptions are a
delivery-operations concern and never affect an already-issued
quotation.

## Sustainability reporting (excerpt)

The company reports scope 1 and scope 2 emissions annually and has
piloted HVO fuel on the Venlo–Lyon lane since 2023. Emission figures
per consignment are published in the customer portal as informative
estimates derived from routed distance and vehicle class; they are
not part of the quotation response and carry no charge. A
sustainability surcharge was evaluated by the pricing committee in
2024 and rejected; should that decision ever change, it would enter
the tariff through the published tariff revision process, not
through the quotation service.

## Customs and documentation overview

For intra-EU road moves no customs declaration is required; the
consignment travels under the CMR consignment note. For UK-bound
moves the customs desk prepares export declarations and safety and
security declarations from the booking data after a quote is
accepted — customs documentation is a booking-time concern and out
of scope for quotation. Dangerous-goods documentation (ADR) routes
to the special-cargo desk as noted above.

## Driver app and proof of delivery

Drivers use the company app for trip sheets, load-securing
checklists, exception photos and proof-of-delivery capture. POD
records are retained for eighteen months and surface in the customer
portal within minutes of hand-over. App telemetry (idle time, route
deviation) feeds the operations dashboard; none of it is visible to
the quotation service.

## Quotation desk service history (informative)

Before instant quotation, the desk handled roughly 300 manual
quotations per business day with a four-hour service promise and a
measured median of 95 minutes. After the 2019 programme the desk
volume fell to under 40 per day, concentrated on special cargo,
contract-lane exceptions and multi-leg requests. Desk quotations use
the same published tariff but are prepared in the pricing workbench;
they are recorded in the same quote store with a `desk` origin
marker. The service-level dashboard tracks instant quotation
availability and latency percentiles; the desk's queue is tracked
separately.

## Facilities notes

The Venlo hub operates 22 dock doors on a two-shift pattern with a
night cross-dock window; Duisburg operates 16 doors and hosts the
tyre-and-brake workshop; Lyon operates 12 doors and the southern
relay yard. Yard access uses ANPR gates; visiting subcontractors
register in the yard app. Hub throughput statistics roll up weekly
to the network report used for capacity planning.


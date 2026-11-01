# 0003 — REL-06002 cites REQ-06, the screening-outage rule

Date: 2026-10-31. State: approved (fdurieux). Supersedes: none.

## Decision

The `supports` link REL-06002 (APP-0004 ScreeningService → PROC-0003 Screen the
shipper) carries `kit:requirements.md#REQ-06` in its evidence, beside the kit's
`links.toml` and the export manifest. Its rationale names the outcome REQ-06
prescribes (`held_unscreened`), and its approval is renewed against this record.
No node, state, relationship type or glossary term changes.

## Why

REQ-06 (screening outage → `held_unscreened` with price and `hold: true`, no
notification) was cited by no link, although REL-06002's rationale named it
since the pilot slice. pumllint's demo surfaced the gap on 2026-10-31 through
its register footprint: on scenarios S2, S4 and S5 the gate's rule hits on
REQ-06 joined to no link, so the register did not yet carry the requirement
the scenario turns on. The screening call is the right carrier: the outage is
the screening service's failure mode, and the link already joins the service to
the activity whose outcome REQ-06 fixes. The evidence anchor is the same form
the register uses for REQ-01, REQ-04 and REQ-05.

## Approvals recorded by this decision

REL-06002, whose `approval.record` names this file.

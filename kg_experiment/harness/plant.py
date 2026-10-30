"""The plant: mechanical patches per scenario (pre-registration §5).

Each patch is (path, old, new); a patch whose ``old`` is not found
exactly once is a hard error. ``DROP`` removes a file; ``ADD`` adds one.
"""

from __future__ import annotations

DROP = object()
ADD = object()

# --- S2: the screening-outage rule removed everywhere it is stated ------
S2 = [
    ("contract/decision_table.md",
     """5. A screening outage does **not** fail the quote: the quote is still
   priced, stored with status `held_unscreened`, and **not** notified
   until screening completes (out of scope here). The response carries
   the price and `hold: true`.
""", ""),
    ("contract/decision_table.md",
     "## DT-P — pricing (only on DT-S rows accept and screening-outage hold)",
     "## DT-P — pricing (only on DT-S row accept)"),
    ("contract/spec.md",
     """3. Request the shipper's risk index from the Screening Service.
   If screening is unavailable: price anyway (DT-P), update the
   stored quote to `held_unscreened`, do **not** notify, and return
   the price with `hold: true` (DT-S note 5).
""",
     """3. Request the shipper's risk index from the Screening Service.
"""),
    ("contract/spec.md",
     "| 6 | screening outage | `held_unscreened` with price and `hold: true`, **no** notification |\n",
     ""),
    ("contract/spec.md",
     """- **Quote outcome**: exactly one of `quoted`, `review_hold`,
  `refused_screening`, `held_unscreened` (screening outage), plus the
  rejection/error statuses in the API contract below.""",
     """- **Quote outcome**: exactly one of `quoted`, `review_hold`,
  `refused_screening`, plus the rejection/error statuses in the API
  contract below."""),
    ("contract/spec.md",
     """- `"quoted"` | `"review_hold"` | `"refused_screening"` |
  `"held_unscreened"`""",
     """- `"quoted"` | `"review_hold"` | `"refused_screening"`"""),
    ("contract/spec.md",
     """plus `quote_id` (string) whenever a draft was stored, `price`
(number) exactly on the priced rows (DT-S), and `hold: true` exactly
on `held_unscreened`.""",
     """plus `quote_id` (string) whenever a draft was stored and `price`
(number) exactly on the priced rows (DT-S)."""),
    ("contract/openapi.yaml",
     """            - "held_unscreened"
""", ""),
    ("contract/openapi.yaml",
     """        hold:
          type: boolean
          description: "true exactly on held_unscreened."
""", ""),
    ("behavior/quote_flow.puml",
     """else screening failure (service unavailable)
  ScreeningService --> QuoteAPI : screeningUnavailableError
  QuoteAPI -> TariffEngine : price(weightKg, distanceKm)
  activate TariffEngine
  TariffEngine --> QuoteAPI : priceAmount
  deactivate TariffEngine
  QuoteAPI -> QuoteStore : updateQuote(quoteId, statusHeldUnscreened, priceAmount)
  activate QuoteStore
  QuoteStore --> QuoteAPI : updatedQuote
  deactivate QuoteStore
  QuoteAPI --> Shipper : heldUnscreenedResponse
  note right of QuoteAPI
    Screening outage does NOT fail the quote: it is priced,
    stored on hold, and not notified (DT-S note 5).
  end note
end
""", "end\n"),
    ("tests_input/acceptance.feature",
     """  Scenario: G4 - screening outage holds the quote instead of failing it
    Given a valid quote request with weight 400 kg and distance 900 km
    And the screening service is unavailable
    When the quote request is submitted
    Then the response status is "held_unscreened"
    And the response carries a price and hold set to true
    And no notification of any kind is sent

""", ""),
    ("kit/quote_process.bpmn",
     """    <bpmn:task id="t_price_outage" name="Price (DT-P)"/>
    <bpmn:task id="t_update_held" name="Update stored quote to held_unscreened"/>
    <bpmn:endEvent id="end_held" name="held_unscreened (hold: true, not notified)"/>
""", ""),
    ("kit/quote_process.bpmn",
     """    <bpmn:sequenceFlow id="f18" name="screening outage" sourceRef="g_screen" targetRef="t_price_outage"/>
    <bpmn:sequenceFlow id="f19" sourceRef="t_price_outage" targetRef="t_update_held"/>
    <bpmn:sequenceFlow id="f20" sourceRef="t_update_held" targetRef="end_held"/>
""", ""),
    ("kit/requirements.md",
     "| REQ-06 | screening outage → `held_unscreened` with price and `hold: true`, **no** notification [spec.md criterion 6] |",
     "| REQ-06 | behaviour on a screening outage: NOT YET SPECIFIED (open decision OD-1, owner: compliance) |"),
    ("kit/links.toml",
     """[[verifies]]
scenario = "G4"
requirement = "REQ-06"
""", ""),
]

# --- S3: DT-S rows made vague; symbols undefined; DMN not yet authored ---
S3 = [
    ("contract/decision_table.md",
     """`risk_index` is the integer returned by the Screening Service; higher
is worse. Symbolic names used by the diagrams: `ACCEPT_MAX = 41`,
`REVIEW_MIN = 42`, `REVIEW_MAX = 66`, `REFUSE_MIN = 67`.
""",
     """`risk_index` is the integer returned by the Screening Service; higher
is worse.
"""),
    ("contract/decision_table.md",
     "| accept | `risk_index <= 41` | quote issued | yes | yes (quote document) | `quoted` |",
     "| accept | risk index clearly low — below the low forties | quote issued | yes | yes (quote document) | `quoted` |"),
    ("contract/decision_table.md",
     "| review | `42 <= risk_index <= 66` | held for manual review | **no** | **no** | `review_hold` |",
     "| review | from the low forties up to the mid-sixties | held for manual review | **no** | **no** | `review_hold` |"),
    ("contract/decision_table.md",
     "| refuse | `risk_index >= 67` | refused | **no** | **yes** (refusal notice) | `refused_screening` |",
     "| refuse | anything higher | refused | **no** | **yes** (refusal notice) | `refused_screening` |"),
    ("contract/decision_table.md",
     """Boundary readings, spelled out: 41 is accepted; 42 is review; 66 is
review; 67 is refused.

""", ""),
    ("kit/screening_decision.dmn", DROP, None),
    ("kit/requirements.md",
     "`screening_decision.dmn` mirrors DT-S as a DMN 1.3 decision table;\n`decision_table.md` remains the normative text.",
     "`screening_decision.dmn` is not yet authored; `decision_table.md` is\nthe normative text."),
]

# --- S4: the diagram and the BPMN fail the quote on an outage ------------
S4 = [
    ("behavior/quote_flow.puml",
     """else screening failure (service unavailable)
  ScreeningService --> QuoteAPI : screeningUnavailableError
  QuoteAPI -> TariffEngine : price(weightKg, distanceKm)
  activate TariffEngine
  TariffEngine --> QuoteAPI : priceAmount
  deactivate TariffEngine
  QuoteAPI -> QuoteStore : updateQuote(quoteId, statusHeldUnscreened, priceAmount)
  activate QuoteStore
  QuoteStore --> QuoteAPI : updatedQuote
  deactivate QuoteStore
  QuoteAPI --> Shipper : heldUnscreenedResponse
  note right of QuoteAPI
    Screening outage does NOT fail the quote: it is priced,
    stored on hold, and not notified (DT-S note 5).
  end note
end
""",
     """else screening failure (service unavailable)
  ScreeningService --> QuoteAPI : screeningUnavailableError
  QuoteAPI -> QuoteStore : updateQuote(quoteId, statusErrorScreening)
  activate QuoteStore
  QuoteStore --> QuoteAPI : updatedQuote
  deactivate QuoteStore
  QuoteAPI --> Shipper : screeningUnavailableResponse
  note right of QuoteAPI
    A screening outage fails the quote: no price is computed,
    the quote is stored as error: screening_unavailable, and
    nothing is notified.
  end note
end
"""),
    ("kit/quote_process.bpmn",
     """    <bpmn:task id="t_price_outage" name="Price (DT-P)"/>
    <bpmn:task id="t_update_held" name="Update stored quote to held_unscreened"/>
    <bpmn:endEvent id="end_held" name="held_unscreened (hold: true, not notified)"/>
""",
     """    <bpmn:task id="t_update_err" name="Update stored quote to error: screening_unavailable"/>
    <bpmn:endEvent id="end_err" name="error: screening_unavailable (no price, not notified)"/>
"""),
    ("kit/quote_process.bpmn",
     """    <bpmn:sequenceFlow id="f18" name="screening outage" sourceRef="g_screen" targetRef="t_price_outage"/>
    <bpmn:sequenceFlow id="f19" sourceRef="t_price_outage" targetRef="t_update_held"/>
    <bpmn:sequenceFlow id="f20" sourceRef="t_update_held" targetRef="end_held"/>
""",
     """    <bpmn:sequenceFlow id="f18" name="screening outage" sourceRef="g_screen" targetRef="t_update_err"/>
    <bpmn:sequenceFlow id="f20" sourceRef="t_update_err" targetRef="end_err"/>
"""),
    ("tests_input/acceptance.feature",
     """  Scenario: G4 - screening outage holds the quote instead of failing it
    Given a valid quote request with weight 400 kg and distance 900 km
    And the screening service is unavailable
    When the quote request is submitted
    Then the response status is "held_unscreened"
    And the response carries a price and hold set to true
    And no notification of any kind is sent

""", ""),
    ("kit/links.toml",
     """[[verifies]]
scenario = "G4"
requirement = "REQ-06"
""", ""),
]

# --- S5: S2 plus one AI-inferred statement -------------------------------
NOTES = """# Auto-generated analysis notes (architecture assistant, 2026-10-27; not reviewed)

Reading the quotation flow against the compliance posture of the
screening step: the screening call is the control that keeps denied
parties from receiving a price. On a screening outage the quote is
refused with status `refused_screening`, so that no price reaches an
unscreened shipper. This resolves open decision OD-1.
"""
S5 = S2 + [("notes/analysis_notes.md", ADD, NOTES)]

INFERRED = {
    "id": "A:llm:QuoteAPI|on_screening_outage",
    "entity": "QuoteAPI", "predicate": "on_screening_outage",
    "value": "priced=no;status=refused_screening;notified=no",
    "text": ("On a screening outage the quote is refused with status "
             "refused_screening, so that no price reaches an unscreened shipper."),
    "basis": "inferred", "agent": "llm",
    "note": "proposed by the architecture assistant, 2026-10-27, as a resolution of OD-1; not reviewed",
}

# --- S6, stage 2: the tariff changes after verification ------------------
S6_STAGE2 = [
    ("contract/decision_table.md",
     "| P2 | heavy surcharge: if `weight_kg > 1244`, add `316.00` (flat) |",
     "| P2 | heavy surcharge: if `weight_kg > 1244`, add `341.00` (flat) |"),
    ("contract/decision_table.md",
     """Worked example (both surcharges): `weight_kg = 1500`,
`distance_km = 5000` → base `1305.00 + 5650.00 = 6955.00` → +316 →
`7271.00` → ×1.19 → **`8652.49`**. (Applying P3 before P2 gives the
wrong `8592.45` — the order is normative.)""",
     """Worked example (both surcharges): `weight_kg = 1500`,
`distance_km = 5000` → base `1305.00 + 5650.00 = 6955.00` → +341 →
`7296.00` → ×1.19 → **`8682.24`**. (Applying P3 before P2 gives the
wrong `8622.20` — the order is normative.)"""),
]

PLANTS = {"S1": [], "S2": S2, "S3": S3, "S4": S4, "S5": S5, "S6": [], "S7": []}


def apply_plant(kit: dict[str, str], scenario: str, stage: int = 1) -> dict[str, str]:
    patches = list(PLANTS[scenario])
    if scenario == "S6" and stage == 2:
        patches = S6_STAGE2
    kit = dict(kit)
    for path, old, new in patches:
        if old is DROP:
            if path not in kit:
                raise RuntimeError(f"plant: cannot drop missing {path}")
            del kit[path]
            continue
        if old is ADD:
            kit[path] = new
            continue
        n = kit[path].count(old)
        if n != 1:
            raise RuntimeError(f"plant: {scenario} patch on {path} matched {n} times:\n{old[:80]}")
        kit[path] = kit[path].replace(old, new)
    return kit


if __name__ == "__main__":
    from kitio import pristine
    for s in PLANTS:
        k = apply_plant(pristine(), s)
        print(s, "ok", len(k), "files")
    apply_plant(pristine(), "S6", 2)
    print("S6 stage 2 ok")

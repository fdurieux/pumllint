# Declared overlap: tests-as-input vs the grading suite

The W1 pre-registration obligation (research-charter §7 W1, from
verification finding 3): the relationship between the generation-input
tests (acceptance.feature, G1–G7) and the frozen grading suite
(tools/acceptance/cargo_quote_suite.py, 11 scenarios) is declared
here, per scenario, BEFORE any scored run. W1's analysis reports the
tests-as-input rung's marginal effect split by overlap class — the
same-behavior class measures oracle leakage risk, the adjacent and
disjoint classes measure artifact value.

Classes: **same** = the input scenario states the same behavior at the
same decision point as a grading scenario; **adjacent** = same rule,
different values (the grading suite probes a point the input does not
give away); **disjoint** = behavior the grading suite does not test at
all.

| Input | Grading scenario(s) | Class | Note |
|---|---|---|---|
| G1 quoted happy | quoted_low_risk | adjacent | different weight/distance/risk; G1's example price (2121.40) does not appear in any grading scenario |
| G2 underweight reject | invalid_weight_low | **same** | both sit on the V2 lower bound with weight 2 |
| G3 refuse extreme | refuse_high_risk | adjacent | risk 90 vs 93; same band interior |
| G4 screening-outage hold | screening_down_hold | **same** | the prior-inverting rule; deliberately included in the input set so W1 measures whether tests-as-input pins it |
| G5 exact price (no surcharges) | price_exact_heavy, price_exact_both | adjacent | G5 exercises P1+P4 only; the grading scenarios probe P2 (flat surcharge) and P2→P3 order, which G5's values do not reveal |
| G6 review interior | review_boundary_42 | adjacent | risk 50 interior vs the 41/42 boundary the grading suite probes |
| G7 notification-failure tolerance | — | **disjoint** | the grading suite never stubs a notification failure |

Not revealed by the input set at all: every DT-V bound except V2-low,
the DT-S boundary values (41/42/66/67 — G1/G3/G5/G6 use interior
points), the flat-surcharge threshold and amount (P2), the multiplier
threshold and P2→P3 order (P3), accept-boundary behavior, storage
failure, and refusal-path pricing/notification interaction checks.

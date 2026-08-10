# CargoQuote — exhaustive worked examples (enumeration appendix)

Every value below is derived from decision_table.md (DT-V, DT-S,
DT-P) and repeats it exactly; the tables remain the authority.

## Exhaustive pricing grid (EUR, DT-P applied verbatim)

| weight_kg \ distance_km | 25 | 900 | 1200 | 2500 | 4911 | 4912 | 5000 | 7150 |
|---|---|---|---|---|---|---|---|---|
| **3** | 30.86 | 1019.61 | 1358.61 | 2827.61 | 5552.04 | 6608.27 | 6726.61 | 9617.71 |
| **100** | 115.25 | 1104.00 | 1443.00 | 2912.00 | 5636.43 | 6708.70 | 6827.03 | 9718.13 |
| **400** | 376.25 | 1365.00 | 1704.00 | 3173.00 | 5897.43 | 7019.29 | 7137.62 | 10028.73 |
| **620** | 567.65 | 1556.40 | 1895.40 | 3364.40 | 6088.83 | 7247.05 | 7365.39 | 10256.49 |
| **1000** | 898.25 | 1887.00 | 2226.00 | 3695.00 | 6419.43 | 7640.47 | 7758.80 | 10649.90 |
| **1244** | 1110.53 | 2099.28 | 2438.28 | 3907.28 | 6631.71 | 7893.08 | 8011.41 | 10902.52 |
| **1245** | 1427.40 | 2416.15 | 2755.15 | 4224.15 | 6948.58 | 8270.15 | 8388.49 | 11279.59 |
| **1500** | 1649.25 | 2638.00 | 2977.00 | 4446.00 | 7170.43 | 8534.16 | 8652.49 | 11543.59 |
| **2000** | 2084.25 | 3073.00 | 3412.00 | 4881.00 | 7605.43 | 9051.81 | 9170.14 | 12061.24 |
| **5000** | 4694.25 | 5683.00 | 6022.00 | 7491.00 | 10215.43 | 12157.71 | 12276.04 | 15167.14 |
| **19400** | 17222.25 | 18211.00 | 18550.00 | 20019.00 | 22743.43 | 27066.03 | 27184.36 | 30075.47 |

Reading aids: the heavy surcharge (+316.00 flat) first applies at
weight 1245 (1244 is surcharge-free); the long-haul multiplier
(x1.19, applied after the surcharge) first applies at distance
4912 (4911 is unmultiplied).

## Risk-index banding, enumerated (DT-S applied verbatim)

| risk_index | outcome | priced? | notified? |
|---|---|---|---|
| 0 | `quoted` | yes | yes (quote document) |
| 1 | `quoted` | yes | yes (quote document) |
| 5 | `quoted` | yes | yes (quote document) |
| 12 | `quoted` | yes | yes (quote document) |
| 25 | `quoted` | yes | yes (quote document) |
| 40 | `quoted` | yes | yes (quote document) |
| 41 | `quoted` | yes | yes (quote document) |
| 42 | `review_hold` | no | no |
| 50 | `review_hold` | no | no |
| 60 | `review_hold` | no | no |
| 66 | `review_hold` | no | no |
| 67 | `refused_screening` | no | yes (refusal notice) |
| 75 | `refused_screening` | no | yes (refusal notice) |
| 90 | `refused_screening` | no | yes (refusal notice) |
| 100 | `refused_screening` | no | yes (refusal notice) |

## Validation bounds, enumerated (DT-V applied verbatim)

| field | just invalid | lowest valid | highest valid | just invalid |
|---|---|---|---|---|
| weight_kg | 2 | 3 | 19400 | 19401 |
| distance_km | 24 | 25 | 7150 | 7151 |
| declared_value | 49 | 50 | 83000 | 83001 |

Any single violation rejects the request (`rejected:
invalid_request`) before storage, screening, pricing or
notification.

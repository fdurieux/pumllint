"""Regenerate O3_worked_examples.md from DT-V/DT-S/DT-P by
computation, so every enumerated number is correct by construction.

    python stack_experiment/w4_farside/gen_O3.py

Deterministic; overwrites O3_worked_examples.md in place. The three
asserts at the bottom pin the hand-verifiable anchors: the DT-P
worked example (8652.49), the grading-suite exact price 3186.00, and
the G1 input-example price 2121.40 (NOT suite-graded — see
cargo_quote/tests_input/oracle_overlap.md).
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent


def price(w, d):
    t = 0.87 * w + 1.13 * d
    if w > 1244:
        t += 316.00
    if d >= 4912:
        t *= 1.19
    return round(t, 2)


W = [3, 100, 400, 620, 1000, 1244, 1245, 1500, 2000, 5000, 19400]
D = [25, 900, 1200, 2500, 4911, 4912, 5000, 7150]


def main() -> None:
    lines = [
        "# CargoQuote — exhaustive worked examples (enumeration appendix)",
        "",
        "Every value below is derived from decision_table.md (DT-V, DT-S,",
        "DT-P) and repeats it exactly; the tables remain the authority.",
        "",
        "## Exhaustive pricing grid (EUR, DT-P applied verbatim)",
        "",
        "| weight_kg \\ distance_km | "
        + " | ".join(str(d) for d in D) + " |",
        "|---|" + "---|" * len(D),
    ]
    for w in W:
        lines.append(f"| **{w}** | "
                     + " | ".join(f"{price(w, d):.2f}" for d in D) + " |")
    lines += [
        "",
        "Reading aids: the heavy surcharge (+316.00 flat) first applies at",
        "weight 1245 (1244 is surcharge-free); the long-haul multiplier",
        "(x1.19, applied after the surcharge) first applies at distance",
        "4912 (4911 is unmultiplied). Rounding is DT-P's round(x, 2) with",
        "float semantics on exact half-cent ties; no graded scenario",
        "touches a tie cell.",
        "",
        "## Risk-index banding, enumerated (DT-S applied verbatim)",
        "",
        "| risk_index | outcome | priced? | notified? |",
        "|---|---|---|---|",
    ]
    for r in [0, 1, 5, 12, 25, 40, 41, 42, 50, 60, 66, 67, 75, 90, 100]:
        if r <= 41:
            row = ("quoted", "yes", "yes (quote document)")
        elif r <= 66:
            row = ("review_hold", "no", "no")
        else:
            row = ("refused_screening", "no", "yes (refusal notice)")
        lines.append(f"| {r} | `{row[0]}` | {row[1]} | {row[2]} |")
    lines += [
        "",
        "## Validation bounds, enumerated (DT-V applied verbatim)",
        "",
        "| field | just invalid | lowest valid | highest valid |"
        " just invalid |",
        "|---|---|---|---|---|",
        "| weight_kg | 2 | 3 | 19400 | 19401 |",
        "| distance_km | 24 | 25 | 7150 | 7151 |",
        "| declared_value | 49 | 50 | 83000 | 83001 |",
        "",
        "Any single violation rejects the request (`rejected:",
        "invalid_request`) before storage, screening, pricing or",
        "notification.",
        "",
    ]
    (HERE / "O3_worked_examples.md").write_text("\n".join(lines),
                                                encoding="utf-8")


assert price(1500, 5000) == 8652.49
assert price(2000, 1000) == 3186.00
assert price(620, 1400) == 2121.40

if __name__ == "__main__":
    main()
    print("O3_worked_examples.md regenerated")

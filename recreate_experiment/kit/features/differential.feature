Feature: The tolerance-based provider differential

  Background:
    Given an empty store
    And the store holds "yahoo_small.csv" as yahoo/SMALL declared stock

  @JDL-082 @JDL-083 @JDL-140
  Scenario: A stored series against a CSV with one changed cell and unmatched dates
    When I run "jef-data differential --a-symbol SMALL --a-exchange yahoo --b-csv {fixtures}/csv/diff_b.csv --output rep.txt --store {store}"
    Then the exit code is 1
    And stdout is:
      """
      differential: yahoo/SMALL vs {fixtures}/csv/diff_b.csv (relative tolerance 0.0001)
      rows: 4 in yahoo/SMALL, 4 in {fixtures}/csv/diff_b.csv, 3 dates in common
      only in yahoo/SMALL: 1 date(s): 2024-01-04
      only in {fixtures}/csv/diff_b.csv: 1 date(s): 2024-01-05
      Open: within tolerance (max 0.000%)
      High: within tolerance (max 0.000%)
      Low: within tolerance (max 0.000%)
      Close: 1/3 beyond tolerance, worst 0.943% on 2024-01-02 (yahoo/SMALL=np.float64(10.5), {fixtures}/csv/diff_b.csv=np.float64(10.6))
      Adj Close: within tolerance (max 0.000%)
      Volume: 1/3 beyond tolerance, worst 100.000% on 2024-01-03 (yahoo/SMALL=np.float64(0.0), {fixtures}/csv/diff_b.csv=np.float64(5.0))
      VERDICT: 2 cell(s) beyond tolerance, 2 unmatched date(s) - review before scale-out
      """
    And the file "rep.txt" is:
      """
      differential: yahoo/SMALL vs {fixtures}/csv/diff_b.csv (relative tolerance 0.0001)
      rows: 4 in yahoo/SMALL, 4 in {fixtures}/csv/diff_b.csv, 3 dates in common
      only in yahoo/SMALL: 1 date(s): 2024-01-04
      only in {fixtures}/csv/diff_b.csv: 1 date(s): 2024-01-05
      Open: within tolerance (max 0.000%)
      High: within tolerance (max 0.000%)
      Low: within tolerance (max 0.000%)
      Close: 1/3 beyond tolerance, worst 0.943% on 2024-01-02 (yahoo/SMALL=np.float64(10.5), {fixtures}/csv/diff_b.csv=np.float64(10.6))
      Adj Close: within tolerance (max 0.000%)
      Volume: 1/3 beyond tolerance, worst 100.000% on 2024-01-03 (yahoo/SMALL=np.float64(0.0), {fixtures}/csv/diff_b.csv=np.float64(5.0))
      VERDICT: 2 cell(s) beyond tolerance, 2 unmatched date(s) - review before scale-out
      """

  @JDL-082 @JDL-140
  Scenario: Two stored series that agree are aligned within tolerance
    Given the store holds "yahoo_small.csv" as eodhd/SMALL.US declared stock
    When I run "jef-data differential --a-symbol SMALL.US --b-symbol SMALL --store {store} --tolerance 0.01"
    Then the exit code is 0
    And stdout is:
      """
      differential: eodhd/SMALL.US vs yahoo/SMALL (relative tolerance 0.01)
      rows: 4 in eodhd/SMALL.US, 4 in yahoo/SMALL, 4 dates in common
      Open: within tolerance (max 0.000%)
      High: within tolerance (max 0.000%)
      Low: within tolerance (max 0.000%)
      Close: within tolerance (max 0.000%)
      Adj Close: within tolerance (max 0.000%)
      Volume: within tolerance (max 0.000%)
      VERDICT: within tolerance, aligned
      """

  @JDL-140 @JDL-134
  Scenario: A differential with nothing to compare against is refused
    When I run "jef-data differential --a-symbol SMALL --a-exchange yahoo --store {store}"
    Then the exit code is 1
    And stdout is empty
    And stderr is:
      """
      differential: pass --b-csv or --b-symbol
      """

Feature: The daily chain - stage order, the publish gate, the exec guard and the hard cap
  The chain script named by JDL_CHAIN runs with every external command it
  calls replaced by a recording stub on PATH (aws, jef-data, jef-binning,
  timeout, curl, date, python3). `date` answers 2026-10-22 / 1700000000 /
  2026-10-22T053000Z; `timeout` records itself and runs the rest of its
  arguments. Recorded calls exclude `date` and `python3 -c`. Unless a scenario
  says otherwise: JEF_S3_BUCKET=bkt, JEF_IMAGE_DIGEST=sha256:feed,
  JEF_ASSETS="AAPL BTC", JEF_APP_DIR, JEF_EVENT_DIR and JEF_DASH_DIR point into
  the scenario's directory, and every stub exits 0.

  Background:
    Given the chain under test with stubbed externals

  @JDL-146 @JDL-150 @JDL-152 @JDL-154 @JDL-155 @JDL-156 @JDL-157 @JDL-158 @JDL-148
  Scenario: A green run executes every stage in order and publishes last
    Given the chain environment:
      | name                 | value |
      | STUB_MANIFEST_ASSETS | BTC   |
    When the chain runs
    Then the chain exit code is 0
    And the external calls are:
      """
      timeout --signal=TERM --kill-after=60 3600 {chain} --inner
      aws s3 sync s3://bkt/store/ data/ --only-show-errors
      jef-data sync --asset AAPL --asset BTC --store data --summary-json out/2026-10-22/.diagnostics/sync.json
      python3 -m jef.events emit --stage sync --rc 0 --t0 1700000000 --t1 1700000000 --run-date 2026-10-22 --out {events}/2026-10-22T053000Z-sync.jsonl --attach out/2026-10-22/.diagnostics/sync.json
      aws s3 cp {events}/2026-10-22T053000Z-sync.jsonl s3://bkt/events/v1/2026-10-22T053000Z-sync.jsonl --only-show-errors
      jef-data status --asset AAPL --asset BTC --store data --json
      python3 -m jef.events emit --stage status --rc 0 --t0 1700000000 --t1 1700000000 --run-date 2026-10-22 --out {events}/2026-10-22T053000Z-status.jsonl --attach out/2026-10-22/.diagnostics/status.json
      aws s3 cp {events}/2026-10-22T053000Z-status.jsonl s3://bkt/events/v1/2026-10-22T053000Z-status.jsonl --only-show-errors
      jef-binning --asset AAPL --store data --counter-start latest --counter-end latest --output-dir out/2026-10-22/AAPL
      python3 -m jef.events emit --stage binning --rc 0 --t0 1700000000 --t1 1700000000 --run-date 2026-10-22 --out {events}/2026-10-22T053000Z-binning.jsonl --asset AAPL
      jef-binning --asset BTC --store data --counter-start latest --counter-end latest --output-dir out/2026-10-22/BTC
      python3 - out/2026-10-22/BTC/run_manifest_1.json out/2026-10-22/.diagnostics/binning-BTC.json
      python3 -m jef.events emit --stage binning --rc 0 --t0 1700000000 --t1 1700000000 --run-date 2026-10-22 --out {events}/2026-10-22T053000Z-binning.jsonl --asset BTC --manifest out/2026-10-22/BTC/run_manifest_1.json --manifest-root out/2026-10-22 --manifest-prefix runs/2026-10-22
      aws s3 cp {events}/2026-10-22T053000Z-binning.jsonl s3://bkt/events/v1/2026-10-22T053000Z-binning.jsonl --only-show-errors
      aws s3 sync data/ s3://bkt/store/ --only-show-errors
      aws s3 sync out/2026-10-22/ s3://bkt/runs/2026-10-22/ --only-show-errors
      aws s3 cp - s3://bkt/runs/2026-10-22/image_digest.txt --only-show-errors
      stdin sha256:feed
      """
    And the chain stdout is:
      """
      == jef daily 2026-10-22 assets: AAPL BTC
      {"alerts_total": 0}
      == green (sha256:feed)
      WARN: no store at data/market_data, dashboard publish skipped
      """
    And the app directory holds the file "out/2026-10-22/.diagnostics/status.json"
    And jef-data ran with the environment:
      | name             | value              |
      | JEF_IMAGE_DIGEST | sha256:feed        |
      | JEF_RUN_STAMP    | 2026-10-22T053000Z |
      | PWD              | {app}              |

  @JDL-155 @JDL-153 @JDL-158 @JDL-146
  Scenario: A red sync stops the chain with its exit code after emitting, and the dashboard still publishes
    Given the chain environment:
      | name        | value   |
      | JEF_ASSETS  | <unset> |
      | STUB_SYNC_RC | 3      |
    And the restored store holds a market_data directory
    When the chain runs
    Then the chain exit code is 3
    And the external calls are:
      """
      timeout --signal=TERM --kill-after=60 3600 {chain} --inner
      aws s3 sync s3://bkt/store/ data/ --only-show-errors
      jef-data sync --asset AAPL --asset BTC --asset TLT --asset NVDA --asset TSLA --asset IBM --store data --summary-json out/2026-10-22/.diagnostics/sync.json
      python3 -m jef.events emit --stage sync --rc 3 --t0 1700000000 --t1 1700000000 --run-date 2026-10-22 --out {events}/2026-10-22T053000Z-sync.jsonl --attach out/2026-10-22/.diagnostics/sync.json
      aws s3 cp {events}/2026-10-22T053000Z-sync.jsonl s3://bkt/events/v1/2026-10-22T053000Z-sync.jsonl --only-show-errors
      aws s3 sync s3://bkt/events/v1/ {events}-wc/ --only-show-errors
      python3 -m jef.dashboard publish --events {events}-wc --store data --out {dash} --run-date 2026-10-22 --snapshot-out {events}-wc/2026-10-22T053000Z-health.jsonl
      aws s3 sync {dash}/ s3://bkt/dashboard/v1/ --cache-control no-cache --only-show-errors
      aws s3 cp dashboard/index.html s3://bkt/dashboard/index.html --cache-control no-cache --only-show-errors
      """

  @JDL-156 @JDL-158
  Scenario: Status alerts stop the chain before binning and publish nothing
    Given the chain environment:
      | name           | value |
      | JEF_ASSETS     | IBM   |
      | STUB_STATUS_RC | 1     |
    When the chain runs
    Then the chain exit code is 1
    And the external calls are:
      """
      timeout --signal=TERM --kill-after=60 3600 {chain} --inner
      aws s3 sync s3://bkt/store/ data/ --only-show-errors
      jef-data sync --asset IBM --store data --summary-json out/2026-10-22/.diagnostics/sync.json
      python3 -m jef.events emit --stage sync --rc 0 --t0 1700000000 --t1 1700000000 --run-date 2026-10-22 --out {events}/2026-10-22T053000Z-sync.jsonl --attach out/2026-10-22/.diagnostics/sync.json
      aws s3 cp {events}/2026-10-22T053000Z-sync.jsonl s3://bkt/events/v1/2026-10-22T053000Z-sync.jsonl --only-show-errors
      jef-data status --asset IBM --store data --json
      python3 -m jef.events emit --stage status --rc 1 --t0 1700000000 --t1 1700000000 --run-date 2026-10-22 --out {events}/2026-10-22T053000Z-status.jsonl --attach out/2026-10-22/.diagnostics/status.json
      aws s3 cp {events}/2026-10-22T053000Z-status.jsonl s3://bkt/events/v1/2026-10-22T053000Z-status.jsonl --only-show-errors
      """

  @JDL-157
  Scenario: The binning loop stops at the first failing asset, which is still emitted
    Given the chain environment:
      | name              | value        |
      | JEF_ASSETS        | AAPL BTC TLT |
      | STUB_FAIL_ASSETS  | BTC          |
      | STUB_BINNING_RC   | 4            |
    When the chain runs
    Then the chain exit code is 4
    And the external calls are:
      """
      timeout --signal=TERM --kill-after=60 3600 {chain} --inner
      aws s3 sync s3://bkt/store/ data/ --only-show-errors
      jef-data sync --asset AAPL --asset BTC --asset TLT --store data --summary-json out/2026-10-22/.diagnostics/sync.json
      python3 -m jef.events emit --stage sync --rc 0 --t0 1700000000 --t1 1700000000 --run-date 2026-10-22 --out {events}/2026-10-22T053000Z-sync.jsonl --attach out/2026-10-22/.diagnostics/sync.json
      aws s3 cp {events}/2026-10-22T053000Z-sync.jsonl s3://bkt/events/v1/2026-10-22T053000Z-sync.jsonl --only-show-errors
      jef-data status --asset AAPL --asset BTC --asset TLT --store data --json
      python3 -m jef.events emit --stage status --rc 0 --t0 1700000000 --t1 1700000000 --run-date 2026-10-22 --out {events}/2026-10-22T053000Z-status.jsonl --attach out/2026-10-22/.diagnostics/status.json
      aws s3 cp {events}/2026-10-22T053000Z-status.jsonl s3://bkt/events/v1/2026-10-22T053000Z-status.jsonl --only-show-errors
      jef-binning --asset AAPL --store data --counter-start latest --counter-end latest --output-dir out/2026-10-22/AAPL
      python3 -m jef.events emit --stage binning --rc 0 --t0 1700000000 --t1 1700000000 --run-date 2026-10-22 --out {events}/2026-10-22T053000Z-binning.jsonl --asset AAPL
      jef-binning --asset BTC --store data --counter-start latest --counter-end latest --output-dir out/2026-10-22/BTC
      python3 -m jef.events emit --stage binning --rc 4 --t0 1700000000 --t1 1700000000 --run-date 2026-10-22 --out {events}/2026-10-22T053000Z-binning.jsonl --asset BTC
      aws s3 cp {events}/2026-10-22T053000Z-binning.jsonl s3://bkt/events/v1/2026-10-22T053000Z-binning.jsonl --only-show-errors
      """

  @JDL-149 @JDL-148
  Scenario: Arguments other than --inner are executed in place of the daily chain
    Given the chain environment:
      | name                 | value |
      | STUB_RC_override_cmd | 7     |
    When the chain runs with arguments "override-cmd one 'two words'"
    Then the chain exit code is 7
    And the external calls are:
      """
      override-cmd one two words
      """
    And the chain stdout is empty

  @JDL-151 @JDL-150
  Scenario: Without a bucket the inner run stops before any stage
    Given the chain environment:
      | name          | value   |
      | JEF_S3_BUCKET | <unset> |
    When the chain runs
    Then the chain exit code is 1
    And the chain stderr ends with "JEF_S3_BUCKET must name the venue bucket"
    And the external calls are:
      """
      timeout --signal=TERM --kill-after=60 3600 {chain} --inner
      """

  @JDL-154
  Scenario: A failed store restore stops the chain with the restore's exit code
    Given the chain environment:
      | name        | value |
      | STUB_AWS_RC | 5     |
    When the chain runs
    Then the chain exit code is 5
    And the external calls are:
      """
      timeout --signal=TERM --kill-after=60 3600 {chain} --inner
      aws s3 sync s3://bkt/store/ data/ --only-show-errors
      """

  @JDL-147
  Scenario Outline: Without a digest the chain reads it, and the task size, from the task metadata once
    Given the chain environment:
      | name                          | value       |
      | JEF_IMAGE_DIGEST              | <unset>     |
      | ECS_CONTAINER_METADATA_URI_V4 | http://meta |
      | STUB_CURL_BODY                | <body>      |
      | JEF_ASSETS                    | AAPL        |
      | STUB_SYNC_RC                  | 9           |
    When the chain runs
    Then the chain exit code is 9
    And the external calls are:
      """
      curl -s http://meta/task
      timeout --signal=TERM --kill-after=60 3600 {chain} --inner
      aws s3 sync s3://bkt/store/ data/ --only-show-errors
      jef-data sync --asset AAPL --store data --summary-json out/2026-10-22/.diagnostics/sync.json
      python3 -m jef.events emit --stage sync --rc 9 --t0 1700000000 --t1 1700000000 --run-date 2026-10-22 --out {events}/2026-10-22T053000Z-sync.jsonl --attach out/2026-10-22/.diagnostics/sync.json
      aws s3 cp {events}/2026-10-22T053000Z-sync.jsonl s3://bkt/events/v1/2026-10-22T053000Z-sync.jsonl --only-show-errors
      """
    And jef-data ran with the environment:
      | name               | value    |
      | JEF_IMAGE_DIGEST   | <digest> |
      | JEF_TASK_VCPU      | <vcpu>   |
      | JEF_TASK_MEMORY_GB | <mem>    |

    Examples:
      | body | digest | vcpu | mem |
      | {"Containers": [{"ImageID": "sha256:img"}], "Limits": {"CPU": 0.5, "Memory": 2048}} | sha256:img | 0.5 | 2.0 |
      | {"Containers": [{"ImageDigest": "sha256:dig", "ImageID": "sha256:img"}], "Limits": {"CPU": 2, "Memory": 512}} | sha256:dig | 2 | 0.5 |
      | not json | unknown | <unset> | <unset> |

  @JDL-153
  Scenario: A TERM during a stage emits that stage with rc 143, exits 143 and still publishes the dashboard
    Given the restored store holds a market_data directory
    And the chain environment:
      | name       | value |
      | JEF_ASSETS | AAPL  |
    When the chain receives TERM while its sync stage runs
    Then the chain exit code is 143
    And the external calls are:
      """
      timeout --signal=TERM --kill-after=60 3600 {chain} --inner
      aws s3 sync s3://bkt/store/ data/ --only-show-errors
      jef-data sync --asset AAPL --store data --summary-json out/2026-10-22/.diagnostics/sync.json
      python3 -m jef.events emit --stage sync --rc 143 --t0 1700000000 --t1 1700000000 --run-date 2026-10-22 --out {events}/2026-10-22T053000Z-sync.jsonl
      aws s3 cp {events}/2026-10-22T053000Z-sync.jsonl s3://bkt/events/v1/2026-10-22T053000Z-sync.jsonl --only-show-errors
      aws s3 sync s3://bkt/events/v1/ {events}-wc/ --only-show-errors
      python3 -m jef.dashboard publish --events {events}-wc --store data --out {dash} --run-date 2026-10-22 --snapshot-out {events}-wc/2026-10-22T053000Z-health.jsonl
      aws s3 sync {dash}/ s3://bkt/dashboard/v1/ --cache-control no-cache --only-show-errors
      aws s3 cp dashboard/index.html s3://bkt/dashboard/index.html --cache-control no-cache --only-show-errors
      """

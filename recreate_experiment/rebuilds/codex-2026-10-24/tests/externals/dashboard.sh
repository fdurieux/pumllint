# Test double derived from the contract and the chain feature's expected calls.
jef_publish_dashboard() {
  if [[ ! -d data/market_data ]]; then
    echo 'WARN: no store at data/market_data, dashboard publish skipped'
    return 0
  fi
  local events="${JEF_EVENT_DIR:-/tmp/jef-events}-wc"
  local dash="${JEF_DASH_DIR:-/tmp/jef-dashboard}"
  mkdir -p "$events" "$dash"
  aws s3 sync "s3://${JEF_S3_BUCKET}/events/v1/" "$events/" --only-show-errors || true
  python3 -m jef.dashboard publish --events "$events" --store data --out "$dash" --run-date "$RUN_DATE" --snapshot-out "${events}/${JEF_RUN_STAMP}-health.jsonl" || true
  aws s3 sync "$dash/" "s3://${JEF_S3_BUCKET}/dashboard/v1/" --cache-control no-cache --only-show-errors || true
  aws s3 cp dashboard/index.html "s3://${JEF_S3_BUCKET}/dashboard/index.html" --cache-control no-cache --only-show-errors || true
  return 0
}

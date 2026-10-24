# Test double derived independently from the permitted external-function contract.
JEF_EVENT_DIR=${JEF_EVENT_DIR:-/tmp/jef-events}
mkdir -p "$JEF_EVENT_DIR"
jef_emit() {
  local stage=$1 rc=$2 t0=$3 t1=$4
  shift 4
  python3 -m jef.events emit --stage "$stage" --rc "$rc" --t0 "$t0" --t1 "$t1" --run-date "$RUN_DATE" --out "${JEF_EVENT_DIR}/${JEF_RUN_STAMP}-${stage}.jsonl" "$@" || true
}
jef_put() {
  local path="${JEF_EVENT_DIR}/${JEF_RUN_STAMP}-$1.jsonl"
  if [[ -s "$path" ]]; then aws s3 cp "$path" "s3://${JEF_S3_BUCKET}/events/v1/$(basename "$path")" --only-show-errors || true; fi
  return 0
}
jef_attach_if_present() { if [[ -s "$1" ]]; then printf '%s\n%s\n' --attach "$1"; fi; return 0; }
jef_manifest_keys() { python3 - "$1" "$2" <<'PYCODE'
# This test double deliberately supplies no manifest data.
PYCODE
return 0
}

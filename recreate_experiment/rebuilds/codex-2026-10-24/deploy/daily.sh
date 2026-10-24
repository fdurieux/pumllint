#!/bin/bash
set -euo pipefail
if [[ -z "${JEF_IMAGE_DIGEST:-}" ]]; then
  _meta=$(curl -s "${ECS_CONTAINER_METADATA_URI_V4:-}/task" 2>/dev/null || true)
  JEF_IMAGE_DIGEST=$(python3 -c 'import sys,json; exec("try:\n d=json.loads(sys.argv[1]); c=(d.get(\"Containers\") or [{}])[0]; print(c.get(\"ImageDigest\") or c.get(\"ImageID\") or \"unknown\")\nexcept Exception: print(\"unknown\")")' "$_meta")
  _size=$(python3 -c 'import sys,json; exec("try:\n d=json.loads(sys.argv[1])[\"Limits\"]; print(str(d[\"CPU\"])+\" \"+str(d[\"Memory\"]/1024))\nexcept Exception: pass")' "$_meta")
  if [[ -n "$_size" ]]; then
    read -r _cpu _mem <<< "$_size"
    : "${JEF_TASK_VCPU=$_cpu}" "${JEF_TASK_MEMORY_GB=$_mem}"
    export JEF_TASK_VCPU JEF_TASK_MEMORY_GB
  fi
fi
export JEF_IMAGE_DIGEST
export JEF_RUN_STAMP="${JEF_RUN_STAMP:-$(date -u +%Y-%m-%dT%H%M%SZ)}"
if [[ $# -gt 0 && "$1" != --inner ]]; then exec "$@"; fi
if [[ "${1:-}" != --inner ]]; then exec timeout --signal=TERM --kill-after=60 3600 "$0" --inner; fi
: "${JEF_S3_BUCKET:?JEF_S3_BUCKET must name the venue bucket}"
read -ra ASSETS <<< "${JEF_ASSETS:-AAPL BTC TLT NVDA TSLA IBM}"
RUN_DATE=$(date -u +%F)
STORE=data
OUT="out/${RUN_DATE}"
DIAG="${OUT}/.diagnostics"
source "$(dirname "$0")/events.sh"
source "$(dirname "$0")/dashboard.sh"
cd "${JEF_APP_DIR:-/app}"
echo "== jef daily ${RUN_DATE} assets: ${ASSETS[*]}"
mkdir -p "$DIAG"
trap 'jef_emit "${STAGE:-unknown}" 143 "${STAGE_T0:-0}" "$(date +%s)"; jef_put "${STAGE:-unknown}"; exit 143' TERM
trap 'jef_publish_dashboard' EXIT
aws s3 sync "s3://${JEF_S3_BUCKET}/store/" data/ --only-show-errors
FILTERS=()
for a in "${ASSETS[@]}"; do FILTERS+=(--asset "$a"); done
STAGE=sync
STAGE_T0=$(date +%s)
rc=0
jef-data sync "${FILTERS[@]}" --store data --summary-json "${DIAG}/sync.json" || rc=$?
jef_emit sync "$rc" "$STAGE_T0" "$(date +%s)" $(jef_attach_if_present "${DIAG}/sync.json")
jef_put sync
if [[ $rc -ne 0 ]]; then exit "$rc"; fi
STAGE=status
STAGE_T0=$(date +%s)
rc=0
jef-data status "${FILTERS[@]}" --store data --json | tee "${DIAG}/status.json" || rc=$?
jef_emit status "$rc" "$STAGE_T0" "$(date +%s)" $(jef_attach_if_present "${DIAG}/status.json")
jef_put status
if [[ $rc -ne 0 ]]; then exit "$rc"; fi
STAGE=binning
rc=0
for a in "${ASSETS[@]}"; do
  STAGE_T0=$(date +%s)
  rc=0
  jef-binning --asset "$a" --store data --counter-start latest --counter-end latest --output-dir "${OUT}/${a}" || rc=$?
  manifest=$(find "${OUT}/${a}" -maxdepth 1 -name 'run_manifest*.json' -print -quit 2>/dev/null || true)
  args=(--asset "$a")
  if [[ -n "$manifest" ]]; then
    jef_manifest_keys "$manifest" "${DIAG}/binning-${a}.json"
    args+=(--manifest "$manifest" --manifest-root "$OUT" --manifest-prefix "runs/${RUN_DATE}")
  fi
  jef_emit binning "$rc" "$STAGE_T0" "$(date +%s)" "${args[@]}" $(jef_attach_if_present "${DIAG}/binning-${a}.json")
  if [[ $rc -ne 0 ]]; then break; fi
done
jef_put binning
if [[ $rc -ne 0 ]]; then exit "$rc"; fi
aws s3 sync data/ "s3://${JEF_S3_BUCKET}/store/" --only-show-errors
aws s3 sync "${OUT}/" "s3://${JEF_S3_BUCKET}/runs/${RUN_DATE}/" --only-show-errors
echo "$JEF_IMAGE_DIGEST" | aws s3 cp - "s3://${JEF_S3_BUCKET}/runs/${RUN_DATE}/image_digest.txt" --only-show-errors
echo "== green (${JEF_IMAGE_DIGEST})"

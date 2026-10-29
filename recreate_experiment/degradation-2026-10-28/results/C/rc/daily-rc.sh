#!/usr/bin/env bash
# The daily venue chain: restore the store, sync, status, binning per asset,
# and publish the store and the run outputs only when every stage is green.
set -euo pipefail

# Image provenance and task size, read once from the task metadata when the
# digest is not handed in; exported before the exec guard so a re-exec and an
# override command inherit them.
if [[ -z "${JEF_IMAGE_DIGEST:-}" ]]; then
    _meta="$(curl -s "${ECS_CONTAINER_METADATA_URI_V4:-}/task" 2>/dev/null || true)"
    JEF_IMAGE_DIGEST="$(printf '%s' "${_meta}" | python3 -c 'import json, sys; c = json.load(sys.stdin)["Containers"][0]; print(c.get("ImageDigest") or c.get("ImageID") or "unknown")' 2>/dev/null || echo unknown)"
    _size="$(printf '%s' "${_meta}" | python3 -c 'import json, sys; l = json.load(sys.stdin)["Limits"]; print(l["CPU"], l["Memory"] / 1024)' 2>/dev/null || true)"
    if [[ -n "${_size}" ]]; then
        read -r _vcpu _mem <<< "${_size}"
        : "${JEF_TASK_VCPU:=${_vcpu}}"
        : "${JEF_TASK_MEMORY_GB:=${_mem}}"
        export JEF_TASK_VCPU JEF_TASK_MEMORY_GB
    fi
fi
export JEF_IMAGE_DIGEST

# One run stamp for every stage of this invocation and its re-exec.
if [[ -z "${JEF_RUN_STAMP:-}" ]]; then
    JEF_RUN_STAMP="$(date -u +%Y-%m-%dT%H%M%SZ)"
fi
export JEF_RUN_STAMP

# Override commands arrive as arguments: run them instead of the chain.
if [[ $# -gt 0 && "$1" != "--inner" ]]; then
    exec "$@"
fi

# Hard cap: TERM after an hour, KILL a minute later.
if [[ "${1:-}" != "--inner" ]]; then
    exec timeout --signal=TERM --kill-after=60 3600 "$0" --inner
fi

: "${JEF_S3_BUCKET:?JEF_S3_BUCKET must name the venue bucket}"

set -f
ASSETS=(${JEF_ASSETS:-AAPL BTC TLT NVDA TSLA IBM})
set +f
RUN_DATE="$(date -u +%F)"
STORE="data"
OUT="out/${RUN_DATE}"
DIAG="${OUT}/.diagnostics"

_here="$(dirname "$0")"
source "${_here}/events.sh"
source "${_here}/dashboard.sh"

cd "${JEF_APP_DIR:-/app}"
echo "== jef daily ${RUN_DATE} assets: ${ASSETS[*]}"
mkdir -p "${DIAG}"

trap 'jef_emit "${STAGE:-unknown}" 143 "${STAGE_T0:-0}" "$(date +%s)"; jef_put "${STAGE:-unknown}"; exit 143' TERM
trap 'jef_publish_dashboard' EXIT

aws s3 sync "s3://${JEF_S3_BUCKET}/store/" "${STORE}/" --only-show-errors

FILTERS=()
for asset in "${ASSETS[@]}"; do
    FILTERS+=(--asset "${asset}")
done

# Stage: sync
STAGE=sync
STAGE_T0="$(date +%s)"
rc=0
jef-data sync "${FILTERS[@]}" --store "${STORE}" --summary-json "${DIAG}/sync.json" || rc=$?
jef_emit sync "${rc}" "${STAGE_T0}" "$(date +%s)" $(jef_attach_if_present "${DIAG}/sync.json")
jef_put sync
if [[ "${rc}" -ne 0 ]]; then
    exit "${rc}"
fi

# Stage: status (one evaluation, printed and captured)
STAGE=status
STAGE_T0="$(date +%s)"
rc=0
jef-data status "${FILTERS[@]}" --store "${STORE}" --json | tee "${DIAG}/status.json" || rc=$?
jef_emit status "${rc}" "${STAGE_T0}" "$(date +%s)" $(jef_attach_if_present "${DIAG}/status.json")
jef_put status
if [[ "${rc}" -ne 0 ]]; then
    exit "${rc}"
fi

# Stage: binning, one emit per asset, stopping at the first failing asset
STAGE=binning
STAGE_T0="$(date +%s)"
rc=0
for asset in "${ASSETS[@]}"; do
    a_t0="$(date +%s)"
    a_rc=0
    jef-binning --asset "${asset}" --store "${STORE}" --counter-start latest \
        --counter-end latest --output-dir "${OUT}/${asset}" || a_rc=$?
    manifest="$(find "${OUT}/${asset}" -maxdepth 1 -name 'run_manifest*.json' -print -quit 2>/dev/null || true)"
    extra=(--asset "${asset}")
    keys="${DIAG}/binning-${asset}.json"
    if [[ -n "${manifest}" ]]; then
        jef_manifest_keys "${manifest}" "${keys}"
        extra+=(--manifest "${manifest}" --manifest-root "${OUT}" --manifest-prefix "runs/${RUN_DATE}")
    fi
    jef_emit binning "${a_rc}" "${a_t0}" "$(date +%s)" "${extra[@]}" $(jef_attach_if_present "${keys}")
    if [[ "${a_rc}" -ne 0 ]]; then
        rc="${a_rc}"
        break
    fi
done
jef_put binning
if [[ "${rc}" -ne 0 ]]; then
    exit "${rc}"
fi

# Publish: green only
aws s3 sync "${STORE}/" "s3://${JEF_S3_BUCKET}/store/" --only-show-errors
aws s3 sync "${OUT}/" "s3://${JEF_S3_BUCKET}/runs/${RUN_DATE}/" --only-show-errors
echo "${JEF_IMAGE_DIGEST}" | aws s3 cp - "s3://${JEF_S3_BUCKET}/runs/${RUN_DATE}/image_digest.txt" --only-show-errors
echo "== green (${JEF_IMAGE_DIGEST})"
exit 0

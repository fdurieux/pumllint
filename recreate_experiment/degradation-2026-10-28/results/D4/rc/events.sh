#!/usr/bin/env bash
# Ledger emission for the venue's stage wrappers (docs/A3A_PLAN.md §2,
# decisions 1-4). SOURCED by daily.sh and model.sh, never executed - it
# defines functions and nothing else, so it is safe to source under
# `set -euo pipefail`.
#
# One definition, two callers, deliberately: the same emit-and-put pair
# duplicated in both scripts is the drift shape this repo has paid for
# more than once (a fix landed at one site and the other silently
# disagreed).
#
# EMISSION IS TELEMETRY, NEVER OPERATIONS (decision 2). Every function
# here returns 0 whatever happens, so a failed ledger write can never
# turn a green run red. Red stages still emit: the caller captures the
# real rc, passes it in, and exits it afterwards, so the chain's failure
# semantics - alarms included - stay byte-for-byte what they were.
#
# The ledger object is s3://<bucket>/events/v1/<run_stamp>-<stage>.jsonl,
# ONE per (run_stamp, stage), written once at stage end (decision 3). A
# stage with per-asset lines (binning) calls jef_emit once per asset -
# `emit --out` appends - and jef_put once, after the loop.

JEF_EVENT_DIR="${JEF_EVENT_DIR:-/tmp/jef-events}"

# The local .jsonl this stage accumulates into.
jef_event_file() {
    printf '%s/%s-%s.jsonl' "${JEF_EVENT_DIR}" "${JEF_RUN_STAMP}" "$1"
}

# jef_emit <stage> <rc> <t0> <t1> [extra emit args...]
# Appends this stage's lines. Extra args are passed through verbatim, so
# a caller can add --asset/--manifest/--attach without this layer having
# to know about them.
jef_emit() {
    local stage="$1" rc="$2" t0="$3" t1="$4"
    shift 4
    local out
    out="$(jef_event_file "${stage}")"
    mkdir -p "${JEF_EVENT_DIR}" 2>/dev/null || true
    python3 -m jef.events emit \
        --stage "${stage}" --rc "${rc}" --t0 "${t0}" --t1 "${t1}" \
        --run-date "${RUN_DATE}" --out "${out}" "$@" >/dev/null \
        || echo "WARN: ledger emit failure, stage ${stage} (telemetry only)"
    return 0
}

# jef_put <stage>
# Uploads the stage's object once. Absent file = the stage never emitted
# (a hard kill past the TERM grace); absence is the signal, so this says
# so and moves on rather than inventing an empty object.
jef_put() {
    local stage="$1" out
    out="$(jef_event_file "$1")"
    if [[ ! -s "${out}" ]]; then
        echo "WARN: no ledger lines for stage ${stage}, nothing to put"
        return 0
    fi
    aws s3 cp "${out}" \
        "s3://${JEF_S3_BUCKET}/events/v1/$(basename "${out}")" \
        --only-show-errors \
        || echo "WARN: ledger put failure, stage ${stage} (telemetry only)"
    return 0
}

# jef_manifest_keys <manifest.json> <out.json>
# The intent-vs-state JOIN KEYS, extracted from a run manifest into a
# small diagnostics attachment: counter, outputs (a count), the
# universe fingerprint, and runtime_pins_ok (the manifest's recorded
# env compared against jef.api.RUNTIME_PINS - two recorded values, no
# recomputation). This is what docs/A3B_PLAN.md decision 9's read-model
# join consumes; the fixtures modelled it from day one and the venue
# emit now carries it (Arc A A7 C4 - it was fixture-only before, the
# audit-finding-2 drift class in miniature). Telemetry rules apply:
# always returns 0, and on any failure writes nothing - an absent
# attachment renders absent downstream, never a guess.
jef_manifest_keys() {
    local manifest="$1" out="$2"
    if ! python3 - "${manifest}" "${out}" <<'JEF_KEYS_PY'
import json
import sys

from jef.api import RUNTIME_PINS

with open(sys.argv[1], encoding="utf-8") as handle:
    manifest = json.load(handle)
keys = {}
if "counter_end" in manifest:
    keys["counter"] = manifest["counter_end"]
if "outputs" in manifest:
    keys["outputs"] = len(manifest["outputs"])
if "runtime_pins" in manifest:
    keys["runtime_pins_ok"] = manifest["runtime_pins"] == RUNTIME_PINS
if manifest.get("universe_sha256"):
    keys["universe_sha256"] = manifest["universe_sha256"]
with open(sys.argv[2], "w", encoding="utf-8") as handle:
    json.dump(keys, handle, sort_keys=True)
JEF_KEYS_PY
    then
        rm -f "${out}"
        echo "WARN: manifest key extraction failed (telemetry only)"
    fi
    return 0
}

# jef_attach_if_present <path> - echoes `--attach <path>` when the file
# exists, nothing otherwise. A stage that died before writing its
# diagnostics still emits an outcome; it just carries no attachment.
jef_attach_if_present() {
    [[ -s "$1" ]] && printf -- '--attach\n%s\n' "$1"
    return 0
}

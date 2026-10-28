#!/usr/bin/env bash
# Generate Arm W: OpenWiki over the clean-room subject tree, non-interactively.
#
#   run_openwiki.sh <clean-room-dir> <results-dir>
#
# Preconditions, each checked: Node >= 22.22.0; the openwiki CLI on PATH at
# the pinned version; exactly one provider credential in the environment
# (OPENAI_API_KEY or ANTHROPIC_API_KEY); the clean room is a git repository
# with a clean working tree. The provider and model are taken from
# OPENWIKI_PROVIDER / OPENWIKI_MODEL_ID when set, else OpenWiki's defaults
# (recorded either way). Reasoning effort is set only where OpenWiki
# supports it (the OpenAI gpt-5.6 family); it is recorded as "unsupported"
# otherwise. Telemetry is disabled. The whole run's stdout and stderr go to
# <results-dir>/run.log; the generated wiki (pages, .claims sidecars, page
# manifest) is copied to <results-dir>/openwiki/, and PROVENANCE.json records
# version, provider, model, effort, subject tree hash, start, end and
# duration. Nothing under the clean room is modified except what OpenWiki
# itself writes (openwiki/, AGENTS.md), and that diff is recorded.
set -euo pipefail
PINNED_OPENWIKI="0.7.2"
ROOM=${1:?clean-room dir}
RES=${2:?results dir}
mkdir -p "$RES"

node_v=$(node --version 2>/dev/null | sed 's/^v//') || { echo "node not found (need >= 22.22.0)"; exit 2; }
python3 - "$node_v" <<'EOF' || { echo "node $node_v is below 22.22.0"; exit 2; }
import sys
major, minor, *_ = (int(x) for x in sys.argv[1].split("."))
sys.exit(0 if (major, minor) >= (22, 22) else 1)
EOF
# openwiki has no --version flag ("Unknown option: --version"); read the
# installed package's own version instead.
command -v openwiki >/dev/null || { echo "openwiki not on PATH (npm install -g openwiki@$PINNED_OPENWIKI)"; exit 2; }
ow_v=$(node -p "require('$(npm root -g)/openwiki/package.json').version" 2>/dev/null || true)
[ "$ow_v" = "$PINNED_OPENWIKI" ] || { echo "openwiki $ow_v on PATH; the pre-registration pins $PINNED_OPENWIKI (npm install -g openwiki@$PINNED_OPENWIKI)"; exit 2; }

keys=0
[ -n "${OPENAI_API_KEY:-}" ] && keys=$((keys+1)) && provider_default=openai
[ -n "${ANTHROPIC_API_KEY:-}" ] && keys=$((keys+1)) && provider_default=anthropic
[ "$keys" -eq 1 ] || { echo "exactly one of OPENAI_API_KEY / ANTHROPIC_API_KEY must be set (found $keys)"; exit 2; }
export OPENWIKI_PROVIDER=${OPENWIKI_PROVIDER:-$provider_default}
case "$OPENWIKI_PROVIDER" in
  openai) export OPENWIKI_MODEL_ID=${OPENWIKI_MODEL_ID:-gpt-5.6-terra}; export OPENWIKI_REASONING_EFFORT=${OPENWIKI_REASONING_EFFORT:-xhigh}; effort=$OPENWIKI_REASONING_EFFORT ;;
  anthropic) export OPENWIKI_MODEL_ID=${OPENWIKI_MODEL_ID:-claude-opus-5}; unset OPENWIKI_REASONING_EFFORT; effort=unsupported ;;
  *) echo "unexpected OPENWIKI_PROVIDER=$OPENWIKI_PROVIDER"; exit 2 ;;
esac
export OPENWIKI_PAGE_CONCURRENCY=1
export OPENWIKI_TELEMETRY_DISABLED=1
export DO_NOT_TRACK=1

cd "$ROOM"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "$ROOM is not a git repository"; exit 2; }
[ -z "$(git status --porcelain)" ] || { echo "$ROOM has uncommitted changes; the subject must be clean"; exit 2; }
[ ! -e openwiki ] || { echo "$ROOM/openwiki already exists; refuse to overwrite an earlier arm"; exit 2; }
tree_hash=$(git ls-files -z | sort -z | xargs -0 sha256sum | sha256sum | cut -c1-64)
subject_head=$(git rev-parse HEAD)

start=$(date -u +%Y-%m-%dT%H:%M:%SZ); t0=$(date +%s)
echo "openwiki $ow_v · provider $OPENWIKI_PROVIDER · model $OPENWIKI_MODEL_ID · effort $effort · subject tree $tree_hash" | tee "$RES/run.log"
set +e
openwiki --print --init </dev/null >>"$RES/run.log" 2>&1
rc=$?
set -e
end=$(date -u +%Y-%m-%dT%H:%M:%SZ); t1=$(date +%s)
echo "exit $rc after $((t1-t0)) s" | tee -a "$RES/run.log"

git status --porcelain > "$RES/subject.diff-names.txt" || true
if [ -d openwiki ]; then
  rm -rf "$RES/openwiki"; cp -a openwiki "$RES/openwiki"
  [ -f AGENTS.md ] && cp AGENTS.md "$RES/AGENTS.md"
  pages=$(find openwiki -name '*.md' -not -path '*/.claims/*' | wc -l | tr -d ' ')
  sidecars=0
  [ -d openwiki/.claims ] && sidecars=$(find openwiki/.claims -name '*.json' | wc -l | tr -d ' ')
else
  pages=0; sidecars=0
fi
python3 - "$RES/PROVENANCE.json" "$ow_v" "$OPENWIKI_PROVIDER" "$OPENWIKI_MODEL_ID" "$effort" "$tree_hash" "$subject_head" "$start" "$end" "$((t1-t0))" "$rc" "$pages" "$sidecars" <<'EOF'
import json, sys
keys = ["openwiki_version", "provider", "model", "reasoning_effort", "subject_tree_sha256",
        "subject_git_head", "started_utc", "ended_utc", "duration_s", "exit_code", "pages", "claim_sidecars"]
vals = sys.argv[2:]
rec = dict(zip(keys, vals))
for k in ("duration_s", "exit_code", "pages", "claim_sidecars"):
    rec[k] = int(rec[k])
rec["page_concurrency"] = 1
rec["command"] = "openwiki --print --init </dev/null"
json.dump(rec, open(sys.argv[1], "w"), indent=1)
print(json.dumps(rec, indent=1))
EOF
exit $rc

#!/bin/bash
# suite.sh KITDIR IMPL LABEL : run a kit's suite against IMPL (orig, or a mutant id); summary to $L/suites/LABEL.txt
. "$(dirname "$0")/env.sh"
KIT=$1; IMPL=$2; LABEL=$3; mkdir -p "$L/suites"
if [[ "$IMPL" == orig ]]; then EXE=jef-data; PP="$L/hidden_py"; else EXE="$L/mut/$IMPL/bin/jef-data"; PP="$L/mut/$IMPL/src:$L/hidden_py"; fi
cd "$KIT" && JDL_UNDER_TEST="$EXE" JDL_CHAIN="$L/chain_original/daily.sh" JDL_ADAPTER=adapter_original PYTHONPATH="$PP" \
  python -m pytest -p no:cacheprovider -q -rf --basetemp="$L/pytest-tmp/$LABEL" features/steps > "$L/suites/$LABEL.txt" 2>&1
grep -E "^FAILED|passed|failed" "$L/suites/$LABEL.txt" | tail -12

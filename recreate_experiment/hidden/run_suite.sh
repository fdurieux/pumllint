#!/bin/bash
# Run the kit's feature suite against the subject (calibration).
H=/tmp/claude-0/-home-user/2ad689ab-3a24-5b0f-9348-2331660d6b34/scratchpad/kit_work/hidden
. /home/user/.re-venv/bin/activate
export PYTHONDONTWRITEBYTECODE=1
export JDL_UNDER_TEST=${JDL_UNDER_TEST:-jef-data}
export JDL_CHAIN=${JDL_CHAIN:-$H/chain_original/daily.sh}
export JDL_ADAPTER=${JDL_ADAPTER:-adapter_original}
export PYTHONPATH=$H${PYTHONPATH:+:$PYTHONPATH}
cd $H/../kit
mkdir -p $H/scratch/pytest-tmp
python -m pytest -p no:cacheprovider -q --basetemp=$H/scratch/pytest-tmp/run-$$ features/steps "$@"

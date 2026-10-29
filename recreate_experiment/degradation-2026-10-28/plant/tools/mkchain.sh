#!/bin/bash
# mkchain.sh ID : give mutant ID its own copy of the chain with the given externals beside it
. "$(dirname "$0")/env.sh"
mkdir -p "$L/mut/$1/chain" && cp "$JF/deploy/daily.sh" "$JF/deploy/events.sh" "$JF/deploy/dashboard.sh" "$L/mut/$1/chain/"

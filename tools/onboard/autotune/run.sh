#!/bin/bash
# autotune chain for ONE robot (pod; cuRobo-only, no render -> any non-render card). The only manual input is
# tools/onboard/autotune/robots/<profile>.json (URDF, root height or stand range, hand descriptor per arm, the
# robot's real cameras, optional lift/torso joints). Output: harvest/l9/assets9/env_profiles/<profile>.json.
# usage: run.sh <gpu uuid prefix> <profile> [shards]
#   e.g. run.sh 2f884eb2 g1        (bin/runat.sh picks the card by UUID; one process per shard, all on that card)
set -e
UU=$1; P=$2; N=${3:-1}
A=/data/harvest/autotune
C=$(cd "$(dirname "$0")/../../.." && pwd)
S=$C/tools/onboard/autotune
OUT=$A/out/$P
mkdir -p "$OUT"
for k in $(seq 0 $((N - 1))); do
  $S/runat.sh "$UU" "${P}_s$k" "$C" "$S/sweep.py" "$S/robots/$P.json" "$OUT" --shard "$k/$N" --selftest &
done
wait
$S/runat.sh "$UU" "${P}_prof" "$C" "$S/make_profile.py" "$S/robots/$P.json" "$OUT" \
  "$C/harvest/l9/assets9/env_profiles/$P.json"
$S/runat.sh "$UU" "${P}_cmp" "$C" "$S/compare.py" "$S/robots/$P.json" "$OUT"
tail -n 3 $A/logs/${P}_prof.log $A/logs/${P}_cmp.log

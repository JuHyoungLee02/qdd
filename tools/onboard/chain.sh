#!/bin/bash
# Onboarding tool (A) chain (pod juhyoung-native-7a2a, design doc
# docs/research/embodiment_onboarding_2026-10-03.md §4.1). One robot -> one config bundle + self-check report.
# Every step below is an EXISTING tool except width_table.py / ready_search.py / selfcheck.py (tools/onboard/, new,
# small, no new algorithm -- see their docstrings). Deploy first:
#   tools/l9/v2robot/deploy.sh tools/onboard/spec.py tools/onboard/width_table.py tools/onboard/ready_search.py \
#       tools/onboard/selfcheck.py tools/onboard/chain.sh
# usage (on the pod): chain.sh <robot> <profile> <arm> <out dir>
# <robot>   = robots_v2.ROBOTS key (build_curobo9.py / width_table.py input)
# <profile> = curobo9.PROFILES key (reach_v2.py / ready_search.py input; same robot, cuRobo-config naming)
set -e
ROBOT=$1; PROFILE=$2; ARM=$3; OUT=${4:-/data/harvest/l9v2robot/out/onboard/$ROBOT}
C=/data/harvest/l9v2robot/code
R=$C/tools/l9/v2robot/run.sh
mkdir -p "$OUT"

echo "[1/6] cuRobo yml + TCP + collision spheres + ik_smoke + self-collision-at-stow"
bash "$R" "ob_${ROBOT}_build" "$C/tools/l9/v2robot/build_curobo9.py" "$ROBOT" --out "$OUT/curobo"

echo "[2/6] width table: independent FK re-measurement vs the shipped width_to_joint table (self-check 4)"
python3 - "$ROBOT" "$ARM" <<'PY'
import sys
sys.path.insert(0, "tools/l9/v2robot")
import robots_v2 as RV
robot, arm = sys.argv[1], sys.argv[2]
a = RV.ROBOTS[robot]["arms"][arm]
print("  width_table.py verify", RV.prepared_urdf(robot), a["parent"], ",".join(a["fingers"]),
     ",".join(str(x) for x in a["approach"]), RV.tcp_link(arm),
     f"harvest/l9/assets9/grippers/{robot}_{arm}.json", "--kind", RV.ROBOTS[robot].get("mesh_kind", "visual"))
PY

echo "[3/6] reach map: batched cuRobo IK over a grid in front of the base (existing tool, unchanged)"
bash "$R" "ob_${ROBOT}_reach" "$C/tools/l9/v2robot/reach_v2.py" "$PROFILE" "$ARM" --out "$OUT/reach"

echo "[4/6] ready pose SEARCH: lowest TCP height that clears clutter + joint margin (self-check 5)"
echo "  (run ready_search.py by hand with this robot's surface x/y and a z-candidate ladder)"

echo "[5/6] joint limits: sim = URDF = yml (self-check 2, existing tool)"
echo "  (run verify_limits.py by hand with a workspace box for this profile; see reach_v2.BOXES)"

echo "[6/6] render probe (self-check 6): needs enable_cameras + a render-OK GPU -- coordinate with the L9 owner,"
echo "  then run tools/l9/v2robot/spawn_smoke9.py (r1pro/g1) or tools/l9r/probe_franka.py (franka) / the AI Worker"
echo "  env directly, pointed at the ready_search.py output."

echo "collect: selfcheck.py $ROBOT $ARM --build $OUT/curobo/${ROBOT}_build.json --width ... --ready ... \\"
echo "  --limits-log ... --smoke ... --out $OUT/${ROBOT}_${ARM}_report.md"

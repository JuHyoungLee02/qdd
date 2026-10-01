#!/bin/bash
# (laptop) deploy the worktree's tools/l9/v2robot files + L9 v2 robot files, then run one job and print its log tail.
# usage: tools/l9/v2robot/pod.sh <tag> <script relative to code dir> [args...]
set -e
export MSYS_NO_PATHCONV=1
TAG=$1; SCRIPT=$2; shift 2
EXTRA=$(ls tools/l9/v2robot/*.py tools/l9/v2robot/*.sh harvest/l9/robot9.py harvest/l9/hcam9.py harvest/l9/curobo9.py \
  harvest/l9/assets9/curobo/* harvest/l9/assets9/reach_v2/* harvest/l9/assets9/grippers/* 2>/dev/null || true)
bash tools/l9/v2robot/deploy.sh $EXTRA >/dev/null
kubectl exec -n p-test2 juhyoung-native-7a2a -- bash -c "L9V2R_TIMEOUT=\${L9V2R_TIMEOUT:-3000} bash /data/harvest/l9v2robot/code/tools/l9/v2robot/run.sh $TAG /data/harvest/l9v2robot/code/$SCRIPT $*; grep -av '^Warp\|^Module\|it/s\]\|^\[.*Warning\|^  warnings.warn' /data/harvest/l9v2robot/logs/$TAG.log | tail -${TAIL:-40}"

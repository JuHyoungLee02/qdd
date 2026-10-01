#!/bin/bash
# (laptop) deploy HEAD + every modified / untracked file of the worktree (harvest tools tests third_party), then run one
# job and print its log tail. usage: tools/l9/v2robot/pod.sh <tag> <script relative to code dir> [args...]
set -e
export MSYS_NO_PATHCONV=1
TAG=$1; SCRIPT=$2; shift 2
EXTRA=$( (git -c safe.directory=* diff --name-only HEAD; git -c safe.directory=* ls-files --others --exclude-standard) \
  | grep -E '^(harvest|tools|tests|third_party)/' | sort -u)
bash tools/l9/v2robot/deploy.sh $EXTRA >/dev/null
kubectl exec -n p-test2 juhyoung-native-7a2a -- bash -c "L9V2R_TIMEOUT=\${L9V2R_TIMEOUT:-3000} bash /data/harvest/l9v2robot/code/tools/l9/v2robot/run.sh $TAG /data/harvest/l9v2robot/code/$SCRIPT $*; grep -av '^Warp\|^Module\|it/s\]\|^\[.*Warning\|^  warnings.warn' /data/harvest/l9v2robot/logs/$TAG.log | tail -${TAIL:-40}"

#!/bin/bash
# Prompt health check dynamic tests (user-log 96/97) on the pod: free local VLM only, no simulator, no paid calls.
# usage: run_all.sh <smoke|full> <url> <served> <label> [tests]
#   smoke: 2 snapshots per test, base variant only, to catch adapter / parser bugs before the full run (user-log 87)
set -u
source /data/harvest/env.sh
export OMP_WAIT_POLICY=PASSIVE
MODE=$1; URL=$2; SERVED=$3; LABEL=$4; TESTS=${5:-"grasp couple_g couple_r frame"}; SUF=${6:-}
CODE=/data/harvest/tmp/prompt_health/code
OUT=/data/harvest/logs/prompt_health
cd $CODE
export PYTHONPATH=$CODE
PY=/data/harvest/venv_vllm/bin/python  # numpy, PIL, httpx
for T in $TESTS; do
  if [ "$MODE" = smoke ]; then
    $PY tools/prompt_health/run_dyn.py --test $T --url $URL --served $SERVED --label $LABEL \
      --out $OUT/smoke_${LABEL}.jsonl --limit 2 --only base,prod --n-hot 0
  else
    $PY tools/prompt_health/run_dyn.py --test $T --url $URL --served $SERVED --label $LABEL \
      --out $OUT/dyn_${LABEL}${SUF}.jsonl
  fi
  echo "EXIT $T $?"
done
echo "ALL_DONE $MODE $LABEL"

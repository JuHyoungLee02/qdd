#!/bin/bash
# Wait for a marker line in a log, then run dist8_eval_seq.sh (never start vLLM on a half-written merged model).
# usage: dist8_after.sh <log file> <marker> <dist8_eval_seq.sh args...>
LOGF=$1; MARK=$2; shift 2
until grep -q "$MARK" "$LOGF" 2>/dev/null; do sleep 30; done
bash "$1/tools/teach_pt/dist8_eval_seq.sh" "$@"

#!/bin/bash
# E-ACC stage 2 (prereg change 5): (A) v2_med on off_a/off_c 13, (B) v2_gc on off_a/off_c 13 + on 5.
# usage: stage2.sh <code dir> probe | full     (probe = the first 3 calls of each arm, then stop for the self-check)
set -uo pipefail
source /data/harvest/env.sh
C=$1; MODE=$2
PY=/data/harvest/venv_vllm/bin/python
L=/data/harvest/logs/eacc; O=/data/harvest/out/eacc
cd $C
export PYTHONPATH=$C OMP_WAIT_POLICY=PASSIVE
SF=${SF:-0.8}
run() {  # run <arms> <kinds> <limit> <out tag>
  $PY tools/eacc/run_eacc.py --bench $O/bench --set paid --kinds $2 --limit $3 --arms $1 --model astra \
    --out $O/astra_$4.jsonl --tag $4 --ledger $L/astra_ledger_r2.jsonl --prices $L/prices_2026-09-26.json \
    --cap-krw 8000 --stop-frac $SF >> $L/astra_$4.log 2>&1
  echo "EXIT $? $1 $2 $3 $(date -u +%FT%TZ)" >> $L/astra_$4.log
}
if [ "$MODE" = bprime_probe ]; then  # prereg change 6: B-prime, stop ratio 0.95 (SF set by the caller)
  run v2_gc2 off_a,off_c 3 s2bp
elif [ "$MODE" = bprime ]; then
  run v2_gc2 off_a,off_c 0 s2bp
  run v2_gc2 on 5 s2bp
elif [ "$MODE" = probe ]; then
  run v2_med off_a,off_c 3 s2a
  run v2_gc off_a,off_c 3 s2b
else
  run v2_med off_a,off_c 0 s2a
  run v2_gc off_a,off_c 0 s2b
  run v2_gc on 5 s2b
fi
echo "STAGE2_DONE $MODE $(date -u +%FT%TZ)" >> $L/astra_s2.log

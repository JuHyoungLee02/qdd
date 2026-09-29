#!/bin/bash
# P1 of docs/stage3/prereg_astra_solo.md: Astra low closed loop, one episode per Isaac process, in the registered order
# (standard 0), (dr 0), (standard 1), (dr 1), (standard 2), (dr 2). run.py applies the episode gate (3,000 KRW) and the
# ledger hard stop (5,000 KRW); a BUDGET_GATE / BUDGET_STOP / REDESIGN_STOP line ends the loop.
# usage (on the pod): pilot.sh <frozen code dir>
C=$1
L=/data/harvest/logs/astra_solo
for pair in standard:0 dr:0 standard:1 dr:1 standard:2 dr:2; do
  v=${pair%%:*}; s=${pair##*:}
  bash $C/tools/astra_solo/run.sh $C p1_${v}_${s} run --model astra-low --variant $v --seeds $s --video-first 1 \
    --cap-krw 3000 --est-krw 900
  if grep -qE '^(BUDGET_GATE|BUDGET_STOP|REDESIGN_STOP|Traceback)' $L/p1_${v}_${s}.log; then
    echo "P1 stop after $v $s $(date -u +%FT%TZ)" >> $L/p1.log; break
  fi
  echo "P1 done $v $s $(date -u +%FT%TZ)" >> $L/p1.log
done
echo "P1_END $(date -u +%FT%TZ)" >> $L/p1.log

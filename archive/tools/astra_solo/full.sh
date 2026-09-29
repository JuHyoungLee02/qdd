#!/bin/bash
# Full AS arm (docs/stage3/prereg_astra_solo.md change 2): Astra low, E-Couple pairing = DEV layout seeds 0-19 x
# {standard, dr}, order (standard s, dr s) for s = 0..19 so any prefix stays paired; one episode per Isaac process.
# Ledger ledger_full.jsonl, hard stop and episode gate 25,000 KRW (run.py), est. 591.5 KRW / episode (pilot).
# A BUDGET_GATE / BUDGET_STOP / API_STOP / REDESIGN_STOP / Traceback line ends the loop.
# usage (on the pod): full.sh <frozen code dir>
C=$1
L=/data/harvest/logs/astra_solo
O=/data/harvest/out/astra_solo_full
for s in $(seq 0 19); do
  for v in standard dr; do
    bash $C/tools/astra_solo/run.sh $C full_${v}_${s} run --out $O --model astra-low --variant $v --seeds $s \
      --video-first 1 --cap-krw 25000 --est-krw 591.5 --ledger $L/ledger_full.jsonl
    if grep -qE '^(BUDGET_GATE|BUDGET_STOP|API_STOP|REDESIGN_STOP|Traceback)' $L/full_${v}_${s}.log; then
      echo "FULL stop after $v $s $(date -u +%FT%TZ)" >> $L/full.log; echo "FULL_END $(date -u +%FT%TZ)" >> $L/full.log; exit 0
    fi
    echo "FULL done $v $s $(date -u +%FT%TZ)" >> $L/full.log
  done
done
echo "FULL_END $(date -u +%FT%TZ)" >> $L/full.log

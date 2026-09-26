#!/bin/bash
# The 4 registered episodes (prereg_open_vlm_solo.md §1): (standard 0) (dr 0) (standard 1) (dr 1), one Isaac process each,
# gpt-5.2 effort low, early end 20 calls / 60 s motion, hard stop 3,000 KRW. A stop line ends the loop.
# usage (pod): proxy4.sh <frozen code dir>
C=$1
L=/data/harvest/logs/open_vlm_proxy
for pair in standard:0 dr:0 standard:1 dr:1; do
  v=${pair%%:*}; s=${pair##*:}
  bash $C/tools/open_vlm/run_proxy.sh $C p_${v}_${s} run --model proxy-low --api-model gpt-5.2-2025-12-11 \
    --out /data/harvest/out/open_vlm_proxy --ledger $L/ledger.jsonl --variant $v --seeds $s --video-first 1 \
    --stop-calls 20 --stop-motion 60 --cap-krw 3000 --est-krw 500 --est-krw-per-call 20
  if grep -qE '^(BUDGET_GATE|BUDGET_STOP|REDESIGN_STOP|API_STOP|Traceback)' $L/p_${v}_${s}.log; then
    echo "STOP after $v $s $(date -u +%FT%TZ)" >> $L/proxy4.log; break
  fi
  echo "DONE $v $s $(date -u +%FT%TZ)" >> $L/proxy4.log
done
echo "PROXY4_END $(date -u +%FT%TZ)" >> $L/proxy4.log

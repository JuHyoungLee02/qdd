#!/bin/bash
# The 4 registered episodes (prereg_open_vlm_solo.md §1): (standard 0) (dr 0) (standard 1) (dr 1), one Isaac process each,
# effort low, early end 20 calls / 60 s motion, hard stop 3,000 KRW on ONE shared ledger (all proxies together).
# A stop line ends the loop.
# usage (pod): proxy4.sh <frozen code dir> [api model (gpt-5.2-2025-12-11)] [out dir] [tag prefix (p)]
C=$1
M=${2:-gpt-5.2-2025-12-11}
O=${3:-/data/harvest/out/open_vlm_proxy}
T=${4:-p}
L=/data/harvest/logs/open_vlm_proxy
for pair in standard:0 dr:0 standard:1 dr:1; do
  v=${pair%%:*}; s=${pair##*:}
  bash $C/tools/open_vlm/run_proxy.sh $C ${T}_${v}_${s} run --model proxy-low --api-model $M \
    --out $O --ledger $L/ledger.jsonl --variant $v --seeds $s --video-first 1 \
    --stop-calls 20 --stop-motion 60 --cap-krw 3000 --est-krw 500 --est-krw-per-call 20
  if grep -qE '^(BUDGET_GATE|BUDGET_STOP|REDESIGN_STOP|API_STOP|Traceback)' $L/${T}_${v}_${s}.log; then
    echo "STOP after $M $v $s $(date -u +%FT%TZ)" >> $L/${T}4.log; break
  fi
  echo "DONE $M $v $s $(date -u +%FT%TZ)" >> $L/${T}4.log
done
echo "PROXY4_END $M $(date -u +%FT%TZ)" >> $L/${T}4.log

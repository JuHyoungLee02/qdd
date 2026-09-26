#!/bin/bash
# Staged AS arm (docs/stage3/prereg_astra_solo.md change 3). Episodes (standard s, dr s) for s = FIRST..LAST in that
# order; episodes already in /data/harvest/out/astra_solo_full are skipped by run.py (resume). Runner-side early end
# after 20 call sites or 60 s of robot motion (prompt unchanged). Ledger ledger_full.jsonl; CAP = this stage's
# cumulative hard stop on that ledger (episode gate uses the same value).
# usage (on the pod): stage.sh <frozen code dir> <FIRST> <LAST> <CAP_KRW>
C=$1; FIRST=$2; LAST=$3; CAP=$4
L=/data/harvest/logs/astra_solo
O=/data/harvest/out/astra_solo_full
for s in $(seq $FIRST $LAST); do
  for v in standard dr; do
    [ -f $O/astra-low/$v/s$s/result.json ] && continue
    bash $C/tools/astra_solo/run.sh $C full_${v}_${s} run --out $O --model astra-low --variant $v --seeds $s \
      --video-first 1 --cap-krw $CAP --est-krw 460 --ledger $L/ledger_full.jsonl --stop-calls 20 --stop-motion 60
    if grep -qE '^(BUDGET_GATE|BUDGET_STOP|API_STOP|REDESIGN_STOP|Traceback)' $L/full_${v}_${s}.log; then
      echo "STAGE stop after $v $s $(date -u +%FT%TZ)" >> $L/stage.log; echo "STAGE_END $(date -u +%FT%TZ)" >> $L/stage.log; exit 0
    fi
    echo "STAGE done $v $s $(date -u +%FT%TZ)" >> $L/stage.log
  done
done
echo "STAGE_END $(date -u +%FT%TZ)" >> $L/stage.log

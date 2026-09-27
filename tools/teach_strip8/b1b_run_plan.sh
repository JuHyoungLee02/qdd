#!/bin/bash
# boost1b: run plan lines '<combos> <episode dirs...>' on render GPU <g> against an already served B-D (port / name).
# usage: b1b_run_plan.sh <code dir> <gpu> <port> <served name> <plan file> <tag>
C=$1; G=$2; PORT=$3; N=$4; PLAN=$5; T=$6
cd $C; export PYTHONPATH=$C
k=0
while read -r combos eps; do
  [ -n "$eps" ] || continue
  k=$((k + 1))
  bash $C/tools/teach_strip8/isaac.sh $C $G b1b_${T}_$k harvest.teach_strip8.run_boost --combos $combos \
    --qwen-url http://127.0.0.1:$PORT --qwen-name $N --out /data/harvest/out/strip8/boost1b --episodes $eps
done < $PLAN
echo "B1B_LANE_DONE $T $(date -u +%FT%TZ)" >> /data/harvest/logs/strip8/lanes.log

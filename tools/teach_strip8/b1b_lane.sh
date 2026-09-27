#!/bin/bash
# boost1b lane on one GPU (e.g. fe08): serve B-D on <port>, then run the plan lines '<combos> <episode dirs...>'
# of <plan file> (one Isaac process per line, all episodes of a line share one world config).
# usage: b1b_lane.sh <code dir> <gpu> <port> <plan file> <tag>
C=$1; G=$2; PORT=$3; PLAN=$4; T=$5
L=/data/harvest/logs/strip8; O=/data/harvest/out/strip8/boost1b
cd $C; export PYTHONPATH=$C
(bash $C/tools/teach_strip8/vllm.sh $G /data/harvest/out/dist8/merged_b_d-min b1b_$T $PORT 0.30 &)
for i in $(seq 120); do curl -s -m 5 http://127.0.0.1:$PORT/v1/models | grep -q '"id"' && break; sleep 10; done
k=0
while read -r combos eps; do
  [ -n "$eps" ] || continue
  k=$((k + 1))
  bash $C/tools/teach_strip8/isaac.sh $C $G b1b_${T}_$k harvest.teach_strip8.run_boost --combos $combos \
    --qwen-url http://127.0.0.1:$PORT --qwen-name b1b_$T --out $O --episodes $eps
done < $PLAN
bash $C/tools/teach_strip8/stop.sh b1b_$T
echo "B1B_LANE_DONE $T $(date -u +%FT%TZ)" >> $L/lanes.log

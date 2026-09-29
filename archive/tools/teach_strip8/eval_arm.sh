#!/bin/bash
# E-STRIP8 offline evaluation of one served model (prereg_strip8.md §4) on the minimal request (s-min rows) of DEV and
# OOD-H, or on another row file. Scoring = harvest.teach_pt.evaluate --arm nd-xyz (v2 xyz answers, E-PT scorer).
# usage: eval_arm.sh <code dir> <served name> <port> <tag> [data prefix s-min|s-stale] [sets "dev ood_h"]
#   -> /data/harvest/out/strip8/eval/<set>_<tag>
C=$1; N=$2; PORT=$3; TAG=$4; P=${5:-s-min}; SETS=${6:-"dev ood_h"}
D=/data/harvest/out/strip8/data
O=/data/harvest/out/strip8/eval
for s in $SETS; do
  bash $C/tools/teach_strip8/py.sh vllm - ev_${s}_${TAG//-/_} $C harvest.teach_pt.evaluate --data $D/${s}_$P.jsonl \
    --arm nd-xyz --url http://127.0.0.1:$PORT --name $N --out $O/${s}_$TAG
done
echo "EVAL_ARM_DONE $TAG $P $(date -u +%FT%TZ)" >> /data/harvest/logs/strip8/lanes.log

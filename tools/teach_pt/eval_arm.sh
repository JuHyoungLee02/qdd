#!/bin/bash
# E-PT offline evaluation of one served model on the DEV and OOD-H sets of an arm (prereg_pt.md §4).
# usage: eval_arm.sh <code dir> <arm> <served name> <port> <tag>   -> /data/harvest/out/teach_pt/eval/{dev,ood_h}_<tag>
C=$1; A=$2; N=$3; PORT=$4; TAG=$5
D=/data/harvest/out/teach_pt/data
O=/data/harvest/out/teach_pt/eval
for s in dev ood_h; do
  bash $C/tools/teach_pt/py.sh vllm - ev_${s}_${TAG} $C harvest.teach_pt.evaluate --data $D/${s}_$A.jsonl --arm $A \
    --url http://127.0.0.1:$PORT --name $N --out $O/${s}_$TAG
done
echo "EVAL_ARM_DONE $A $TAG $(date -u +%FT%TZ)" >> /data/harvest/logs/teach_pt/lanes.log

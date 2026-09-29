#!/bin/bash
# E-DIST8: finish only an arm that is already training on this GPU (wait for the trainer, merge, evaluate).
# usage: dist8_finish.sh <code dir> <gpu> <arm> <track r-min|d-min|h-min> <port>
C=$1; G=$2; A=$3; T=$4; PORT=$5
L=/data/harvest/logs/dist8
until grep -q "TRAIN_DONE\|Traceback" /data/harvest/logs/teach_pt/train_$A.log 2>/dev/null; do sleep 60; done
E=$(ls -d /data/harvest/out/dist8/run_$A/epoch* 2>/dev/null | sort -V | tail -1)
[ -n "$E" ] && bash $C/tools/teach_pt/py.sh train $G merge_$A $C harvest.teach_l8.merge --adapter $E \
  --out /data/harvest/out/dist8/merged_$A
echo "TRAIN_DONE $A $E $(date -u +%FT%TZ)" >> $L/dist8_open.log
bash $C/tools/teach_pt/dist8_eval_seq.sh $C $G $PORT 0.60 ${A}:/data/harvest/out/dist8/merged_$A:$T

#!/bin/bash
# E-DIST8 change 6: finish only the R arm already training on this GPU (merge + evaluate it), then run H arms here.
# usage: dist8_rstop.sh <code dir> <gpu> <running R arm> <H arm> [<H arm> ...]
C=$1; G=$2; R=$3; shift 3
L=/data/harvest/logs/dist8
until grep -q "TRAIN_DONE\|Traceback" /data/harvest/logs/teach_pt/train_$R.log 2>/dev/null; do sleep 60; done
E=$(ls -d /data/harvest/out/dist8/run_$R/epoch* 2>/dev/null | sort -V | tail -1)
[ -n "$E" ] && bash $C/tools/teach_pt/py.sh train $G merge_$R $C harvest.teach_l8.merge --adapter $E \
  --out /data/harvest/out/dist8/merged_$R
echo "TRAIN_DONE $R $E $(date -u +%FT%TZ)" >> $L/dist8_open.log
bash $C/tools/teach_pt/dist8_eval_seq.sh $C $G 8471 0.60 ${R}:/data/harvest/out/dist8/merged_$R:r-min
bash $C/tools/teach_pt/dist8_open.sh $C $G "$@"

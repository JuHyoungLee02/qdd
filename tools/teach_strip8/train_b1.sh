#!/bin/bash
# E-STRIP8b training of one arm on L8-X b1 (prereg_strip8b.md §2): L8 recipe, 816 optimizer steps (13,056 samples),
# seed 0, then merge the last adapter. usage: train_b1.sh <code dir> <gpu> <arm s-full|s-min|s-drop> [workers]
# data: s-full = L8D train_v2.jsonl as is; s-min / s-drop = /data/harvest/out/strip8/data_b1/train_<arm>.jsonl
C=$1; G=$2; A=$3; W=${4:-6}
if [ "$A" = s-full ]; then D=/data/harvest/out/teach_l8d/data/b1/train_v2.jsonl; else D=/data/harvest/out/strip8/data_b1/train_$A.jsonl; fi
R=/data/harvest/out/strip8/run_b1_$A
M=/data/harvest/out/strip8/merged_b1_$A
J=trb1_${A//-/_}
bash $C/tools/teach_strip8/py.sh train $G $J $C harvest.teach_l8.train --data $D --out $R \
  --epochs 1 --max-steps 816 --micro 8 --accum 2 --log-every 10 --workers $W
E=$(ls -d $R/epoch* 2>/dev/null | sort -V | tail -1)
[ -n "$E" ] && bash $C/tools/teach_strip8/py.sh train $G mgb1_${A//-/_} $C harvest.teach_l8.merge --adapter $E --out $M
echo "TRAIN_B1_DONE $A $E $(date -u +%FT%TZ)" >> /data/harvest/logs/strip8/lanes.log

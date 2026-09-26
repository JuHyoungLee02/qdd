#!/bin/bash
# E-DIST8 A-H on its own card (re-plan): train (L8 recipe, 816 steps) and merge. usage: dist8_ah.sh <code dir> <gpu>
C=$1; G=$2
D=/data/harvest/out/dist8/data_a
bash $C/tools/teach_pt/py.sh train $G train_a_h_min $C harvest.teach_l8.train --data $D/train_h-min.jsonl \
  --out /data/harvest/out/dist8/run_a_h-min --epochs 3 --max-steps 816 --micro 8 --accum 2 --log-every 10
E=$(ls -d /data/harvest/out/dist8/run_a_h-min/epoch* 2>/dev/null | sort -V | tail -1)
[ -n "$E" ] && bash $C/tools/teach_pt/py.sh train $G merge_a_h_min $C harvest.teach_l8.merge --adapter $E \
  --out /data/harvest/out/dist8/merged_a_h-min
echo "TRAIN_DONE h-min $E $(date -u +%FT%TZ)" >> /data/harvest/logs/dist8/dist8_a.log

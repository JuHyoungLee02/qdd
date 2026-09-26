#!/bin/bash
# E-DIST8 re-plan (L8D's b1 pt rows are slow to build; keep every card busy): main GPU 2 finishes A-D (already
# training), merges it, then waits for b1 train_pt and runs B-D (dist8_b.sh) on the same card. A-H runs on x2 GPU 0
# (separate script call). usage: dist8_chain2.sh <code dir> <gpu>
C=$1; G=$2
L=/data/harvest/logs/dist8
until grep -q "TRAIN_DONE" /data/harvest/logs/teach_pt/train_a_d_min.log; do sleep 30; done
E=$(ls -d /data/harvest/out/dist8/run_a_d-min/epoch* 2>/dev/null | sort -V | tail -1)
[ -n "$E" ] && bash $C/tools/teach_pt/py.sh train $G merge_a_d_min $C harvest.teach_l8.merge --adapter $E \
  --out /data/harvest/out/dist8/merged_a_d-min
echo "TRAIN_DONE d-min $E $(date -u +%FT%TZ)" >> $L/dist8_a.log
bash $C/tools/teach_pt/dist8_b.sh $C $G 6

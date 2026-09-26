#!/bin/bash
# E-DIST8 level B (L8-X b1 bundle; prereg_dist8.md §1.3): wait for L8D's pt arm file of the bundle, convert it to
# d-min training rows (min_format.convert), train B-D on one GPU (L8 recipe, 816 steps, --workers W) and merge.
# B-R = STRIP8's S-min(b1) adapter (reused, change 1). usage: dist8_b.sh <code dir> <gpu> [workers]
C=$1; G=$2; W=${3:-6}
P=/data/harvest/venv_train/bin/python
B=/data/harvest/out/teach_l8d/data/b1
D=/data/harvest/out/dist8/data_b1
L=/data/harvest/logs/dist8
mkdir -p $D $L
cd $C; export PYTHONPATH=$C
until [ -f $B/train_pt.counts.json ]; do sleep 60; done
echo "START $(date -u +%FT%TZ) convert b1" >> $L/dist8_b.log
$P tools/teach_pt/convert_min.py $B/train_pt.jsonl $D d-min train_d-min.jsonl >> $L/build_b.log 2>&1
echo "CONVERT_DONE $(date -u +%FT%TZ)" >> $L/dist8_b.log
bash $C/tools/teach_pt/py.sh train $G train_b_d_min $C harvest.teach_l8.train --data $D/train_d-min.jsonl \
  --out /data/harvest/out/dist8/run_b_d-min --epochs 3 --max-steps 816 --micro 8 --accum 2 --log-every 10 --workers $W
E=$(ls -d /data/harvest/out/dist8/run_b_d-min/epoch* 2>/dev/null | sort -V | tail -1)
[ -n "$E" ] && bash $C/tools/teach_pt/py.sh train $G merge_b_d_min $C harvest.teach_l8.merge --adapter $E \
  --out /data/harvest/out/dist8/merged_b_d-min
echo "TRAIN_DONE b-d-min $E $(date -u +%FT%TZ)" >> $L/dist8_b.log

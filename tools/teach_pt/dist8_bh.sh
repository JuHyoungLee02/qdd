#!/bin/bash
# E-DIST8 B-H (change 2): h-min training rows from L8D's b1 nd-xyz arm file (min_format.convert: same states /
# repeats / aux; depth off 50 % / zed_mini half of the kept / clean, from the row id), L8 recipe 816 steps, merge,
# then the offline evaluation on every set (H on / noisy / off). usage: dist8_bh.sh <code dir> <gpu>
C=$1; G=$2
P=/data/harvest/venv_train/bin/python
B=/data/harvest/out/teach_l8d/data/b1
D=/data/harvest/out/dist8/data_b1
L=/data/harvest/logs/dist8
mkdir -p $D $L
cd $C; export PYTHONPATH=$C
echo "START $(date -u +%FT%TZ) convert b1 h-min" >> $L/dist8_bh.log
$P tools/teach_pt/convert_min.py $B/train_nd-xyz.jsonl $D h-min train_h-min.jsonl >> $L/build_bh.log 2>&1
echo "CONVERT_DONE $(date -u +%FT%TZ)" >> $L/dist8_bh.log
bash $C/tools/teach_pt/py.sh train $G train_b_h_min $C harvest.teach_l8.train --data $D/train_h-min.jsonl \
  --out /data/harvest/out/dist8/run_b_h-min --epochs 3 --max-steps 816 --micro 8 --accum 2 --log-every 10
E=$(ls -d /data/harvest/out/dist8/run_b_h-min/epoch* 2>/dev/null | sort -V | tail -1)
[ -n "$E" ] && bash $C/tools/teach_pt/py.sh train $G merge_b_h_min $C harvest.teach_l8.merge --adapter $E \
  --out /data/harvest/out/dist8/merged_b_h-min
echo "TRAIN_DONE b-h-min $E $(date -u +%FT%TZ)" >> $L/dist8_bh.log
bash $C/tools/teach_pt/dist8_eval_seq.sh $C $G 8436 0.60 b_h-min:/data/harvest/out/dist8/merged_b_h-min:h-min

#!/bin/bash
# E-DIST8 level A (old L8, preliminary; prereg_dist8.md §1.3): build the minimal-request rows of D and H (train) and
# of R / D / H (DEV, OOD-H evaluation modes), then train A-D and A-H one after the other on one GPU (L8 recipe, 816
# steps) and merge. R at level A = the STRIP8 S-min adapter (reused). usage: dist8_a.sh <code dir> <gpu>
C=$1; G=$2
P=/data/harvest/venv_train/bin/python
SRC=/data/harvest/out/teach_pt/collect
D=/data/harvest/out/dist8/data_a
L=/data/harvest/logs/dist8
mkdir -p $D $L
cd $C; export PYTHONPATH=$C
echo "START $(date -u +%FT%TZ) build" >> $L/dist8_a.log
$P tools/teach_pt/build_min.py $SRC $D train d-min train >> $L/build_a.log 2>&1
$P tools/teach_pt/build_min.py $SRC $D train h-min train >> $L/build_a.log 2>&1
for s in dev ood_h; do
  $P tools/teach_pt/build_min.py $SRC $D $s r-min clean >> $L/build_a.log 2>&1
  for m in clean noisy; do $P tools/teach_pt/build_min.py $SRC $D $s d-min $m >> $L/build_a.log 2>&1; done
  for m in clean noisy off; do $P tools/teach_pt/build_min.py $SRC $D $s h-min $m >> $L/build_a.log 2>&1; done
done
echo "BUILD_DONE $(date -u +%FT%TZ)" >> $L/dist8_a.log
for a in d-min h-min; do
  J=a_${a//-/_}
  bash $C/tools/teach_pt/py.sh train $G train_$J $C harvest.teach_l8.train --data $D/train_$a.jsonl \
    --out /data/harvest/out/dist8/run_a_$a --epochs 3 --max-steps 816 --micro 8 --accum 2 --log-every 10
  E=$(ls -d /data/harvest/out/dist8/run_a_$a/epoch* 2>/dev/null | sort -V | tail -1)
  [ -n "$E" ] && bash $C/tools/teach_pt/py.sh train $G merge_$J $C harvest.teach_l8.merge --adapter $E \
    --out /data/harvest/out/dist8/merged_a_$a
  echo "TRAIN_DONE $a $E $(date -u +%FT%TZ)" >> $L/dist8_a.log
done

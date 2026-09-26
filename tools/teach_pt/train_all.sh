#!/bin/bash
# E-PT F2 driver (prereg_pt.md §3): TRAIN identity check (G1), per-arm TRAIN files, then the trainings in priority
# order on two GPUs of this pod: lane A (x2 GPU 0 from the x2 pod, or the given GPU) and lane B.
# usage: train_all.sh <code dir> <arm list for this lane, comma> <gpu>   (build of those arms first, then train each)
C=$1; ARMS=$2; G=$3
P=/data/harvest/venv_train/bin/python
L=/data/harvest/logs/teach_pt
cd $C; export PYTHONPATH=$C
for a in ${ARMS//,/ }; do
  [ -f /data/harvest/out/teach_pt/data/train_$a.jsonl ] || \
    $P tools/teach_pt/build.py /data/harvest/out/teach_pt/collect /data/harvest/out/teach_pt/data train --arms=$a \
      > $L/build_train_$a.log 2>&1
  bash $C/tools/teach_pt/train_arm.sh $C $G $a
done

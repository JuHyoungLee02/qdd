#!/bin/bash
# E-OPEN8 training (prereg_open8 §3): O-A then O-B on one free GPU. usage: open8_train.sh <gpu> <code dir>
source /data/harvest/env.sh
G=$1; C=$2
D=/data/harvest/out/xemb/open8
L=/data/harvest/logs/open8; mkdir -p $L
export CUDA_VISIBLE_DEVICES=$G PYTHONPATH=$C OMP_WAIT_POLICY=PASSIVE
for ARM in oa ob; do
  echo "START $ARM $(date -u +%FT%TZ) host=$(hostname) gpu=$G" >> $L/train_$ARM.log
  /data/harvest/venv_train/bin/python -m harvest.teach_l8.train --data $D/train_$ARM.jsonl --out $D/run_$ARM \
    --epochs 3 --max-steps 816 --micro 8 --accum 2 --log-every 10 >> $L/train_$ARM.log 2>&1
  echo "EXIT $ARM $? $(date -u +%FT%TZ)" >> $L/train_$ARM.log
done

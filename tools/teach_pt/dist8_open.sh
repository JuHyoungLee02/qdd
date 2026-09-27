#!/bin/bash
# E-DIST8 open-data arms (change 3): build the mixed training file and train (816 steps, L8 recipe), merge, evaluate —
# one arm after another on one GPU. arms: a_px_r a_px_d b_px_r b_px_d b_px_h c_r c_d c_px_r c_px_d
# usage: dist8_open.sh <code dir> <gpu> <arm> [<arm> ...]
C=$1; G=$2; shift 2
P=/data/harvest/venv_train/bin/python
K=/data/harvest/out/xemb/dist8_packs; PX=$K/t1t4_pixel.jsonl; P3=$K/t1t4_3d.jsonl
DA=/data/harvest/out/dist8/data_a; DB=/data/harvest/out/dist8/data_b1; B1=/data/harvest/out/teach_l8d/data/b1
M=/data/harvest/out/dist8/data_open; L=/data/harvest/logs/dist8
mkdir -p $M $L
cd $C; export PYTHONPATH=$C
for arm in "$@"; do
  case $arm in
    a_px_r) base=/data/harvest/out/strip8/data/train_s-min.jsonl; mix="$PX:0.25"; tr=r-min;;
    a_px_d) base=$DA/train_d-min.jsonl; mix="$PX:0.25"; tr=d-min;;
    b_px_r) base=$B1/train_s-min.jsonl; mix="$PX:0.25"; tr=r-min;;
    b_px_d) base=$DB/train_d-min.jsonl; mix="$PX:0.25"; tr=d-min;;
    b_px_h) base=$DB/train_h-min.jsonl; mix="$PX:0.25"; tr=h-min;;
    c_r) base=$B1/train_s-min.jsonl; mix="$P3:0.25"; tr=r-min;;
    c_d) base=$DB/train_d-min.jsonl; mix="$P3:0.25"; tr=d-min;;
    c_px_r) base=$B1/train_s-min.jsonl; mix="$P3:0.125 $PX:0.125"; tr=r-min;;
    c_px_d) base=$DB/train_d-min.jsonl; mix="$P3:0.125 $PX:0.125"; tr=d-min;;
    *) echo "unknown arm $arm" >> $L/dist8_open.log; continue;;
  esac
  until [ -f $base ]; do sleep 60; done
  $P tools/teach_pt/mix_pack.py $base $M/train_$arm.jsonl $mix >> $L/build_open.log 2>&1
  bash $C/tools/teach_pt/py.sh train $G train_$arm $C harvest.teach_l8.train --data $M/train_$arm.jsonl \
    --out /data/harvest/out/dist8/run_$arm --epochs 3 --max-steps 816 --micro 8 --accum 2 --log-every 10
  E=$(ls -d /data/harvest/out/dist8/run_$arm/epoch* 2>/dev/null | sort -V | tail -1)
  [ -n "$E" ] && bash $C/tools/teach_pt/py.sh train $G merge_$arm $C harvest.teach_l8.merge --adapter $E \
    --out /data/harvest/out/dist8/merged_$arm
  echo "TRAIN_DONE $arm $E $(date -u +%FT%TZ)" >> $L/dist8_open.log
  bash $C/tools/teach_pt/dist8_eval_seq.sh $C $G 84$((50 + RANDOM % 40)) 0.60 ${arm}:/data/harvest/out/dist8/merged_$arm:$tr
done

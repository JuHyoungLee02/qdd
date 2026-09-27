#!/bin/bash
# E-PRIV8 training of one arm on L8-X b1 (prereg_priv8.md §1): L8 recipe, 816 steps, seed 0, then merge.
# m1 = teach_l8.train on train_m1.jsonl; m3 = teach_strip8.train_curr (hand-info input curriculum) on train_m3.jsonl.
# usage: train_priv.sh <code dir> <gpu> <arm m1|m3> [workers]
C=$1; G=$2; A=$3; W=${4:-6}
D=/data/harvest/out/strip8/data_priv/train_$A.jsonl
R=/data/harvest/out/strip8/run_priv_$A
M=/data/harvest/out/strip8/merged_priv_$A
if [ "$A" = m3 ]; then MOD=harvest.teach_strip8.train_curr; else MOD=harvest.teach_l8.train; fi
bash $C/tools/teach_strip8/py.sh train $G trp_$A $C $MOD --data $D --out $R \
  --epochs 1 --max-steps 816 --micro 8 --accum 2 --log-every 10 --workers $W
E=$(ls -d $R/epoch* 2>/dev/null | sort -V | tail -1)
[ -n "$E" ] && bash $C/tools/teach_strip8/py.sh train $G mgp_$A $C harvest.teach_l8.merge --adapter $E --out $M
echo "TRAIN_PRIV_DONE $A $E $(date -u +%FT%TZ)" >> /data/harvest/logs/strip8/lanes.log

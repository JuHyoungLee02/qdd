#!/bin/bash
# E-PT F2 training of one arm (prereg_pt.md §3): L8 recipe, the same total optimizer steps as E-TEACH-L8 (816 =
# 13,056 samples at micro 8 x accum 2), then merge the last saved adapter for vLLM. One GPU (never a render GPU).
# usage: train_arm.sh <code dir> <gpu> <arm>   logs: /data/harvest/logs/teach_pt/train_<arm>.log, merge_<arm>.log
C=$1; G=$2; A=$3
D=/data/harvest/out/teach_pt/data
R=/data/harvest/out/teach_pt/run_$A
M=/data/harvest/out/teach_pt/merged_$A
J=train_${A//-/_}
bash $C/tools/teach_pt/py.sh train $G $J $C harvest.teach_l8.train --data $D/train_$A.jsonl --out $R \
  --epochs 3 --max-steps 816 --micro 8 --accum 2 --log-every 10
E=$(ls -d $R/epoch* 2>/dev/null | sort -V | tail -1)
[ -n "$E" ] && bash $C/tools/teach_pt/py.sh train $G merge_${A//-/_} $C harvest.teach_l8.merge --adapter $E --out $M
echo "TRAIN_ARM_DONE $A $E $(date -u +%FT%TZ)" >> /data/harvest/logs/teach_pt/lanes.log

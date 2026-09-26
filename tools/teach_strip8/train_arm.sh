#!/bin/bash
# E-STRIP8 training of one arm (prereg_strip8.md §3): the E-TEACH-L8 / E-PT recipe with the same total optimizer steps
# as L8 (816 = 13,056 samples at micro 8 x accum 2), then merge the last adapter for vLLM. One GPU, never a render GPU.
# usage: train_arm.sh <code dir> <gpu> <arm s-min|s-drop>   logs: /data/harvest/logs/strip8/train_<arm>.log, merge_<arm>.log
C=$1; G=$2; A=$3
D=/data/harvest/out/strip8/data
R=/data/harvest/out/strip8/run_$A
M=/data/harvest/out/strip8/merged_$A
J=train_${A//-/_}
bash $C/tools/teach_strip8/py.sh train $G $J $C harvest.teach_l8.train --data $D/train_$A.jsonl --out $R \
  --epochs 3 --max-steps 816 --micro 8 --accum 2 --log-every 10
E=$(ls -d $R/epoch* 2>/dev/null | sort -V | tail -1)
[ -n "$E" ] && bash $C/tools/teach_strip8/py.sh train $G merge_${A//-/_} $C harvest.teach_l8.merge --adapter $E --out $M
echo "TRAIN_ARM_DONE $A $E $(date -u +%FT%TZ)" >> /data/harvest/logs/strip8/lanes.log

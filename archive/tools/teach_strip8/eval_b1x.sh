#!/bin/bash
# E-STRIP8b descriptive evaluation on the L8-X protected sets (prereg_strip8b.md §3): OOD-H (0.74-0.98), OOD-D, OOD-S,
# control rows only. s-full answers L8D's v2 rows, s-min / s-drop L8D's s-min rows (checked = strip.minimal by
# check_l8x_min.py). usage: eval_b1x.sh <code dir> <arm> <served name> <port> -> /data/harvest/out/strip8/eval_b1x/<set>_<arm>
C=$1; A=$2; N=$3; PORT=$4; SETS=${5:-"ood_h ood_d ood_s"}
O=/data/harvest/out/strip8/eval_b1x
if [ "$A" = s-full ]; then F=v2; else F=s-min; fi
for s in $SETS; do
  bash $C/tools/teach_strip8/py.sh vllm - evx_${s}_${A//-/_} $C harvest.teach_pt.evaluate \
    --data /data/harvest/out/teach_l8d/data/eval/${s}_$F.jsonl --arm nd-xyz --kinds control \
    --url http://127.0.0.1:$PORT --name $N --out $O/${s}_$A
done
echo "EVAL_B1X_DONE $A $(date -u +%FT%TZ)" >> /data/harvest/logs/strip8/lanes.log

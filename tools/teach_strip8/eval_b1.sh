#!/bin/bash
# E-STRIP8b offline evaluation of one served b1 model (prereg_strip8b.md §3) on DEV and OOD-H (all four heights; the
# narrow / wide split is done in compare --only). s-full answers the v2 requests (E-PT dev_xyz / ood_h_xyz rows), s-min
# and s-drop the minimal requests (E-STRIP8 dev_s-min / ood_h_s-min rows). Scorer: teach_pt.evaluate --arm nd-xyz.
# usage: eval_b1.sh <code dir> <arm s-full|s-min|s-drop> <served name> <port>  -> /data/harvest/out/strip8/eval_b1/<set>_<arm>
C=$1; A=$2; N=$3; PORT=$4
O=/data/harvest/out/strip8/eval_b1
for s in dev ood_h; do
  if [ "$A" = s-full ]; then D=/data/harvest/out/teach_pt/data/${s}_xyz.jsonl; else D=/data/harvest/out/strip8/data/${s}_s-min.jsonl; fi
  bash $C/tools/teach_strip8/py.sh vllm - evb1_${s}_${A//-/_} $C harvest.teach_pt.evaluate --data $D --arm nd-xyz \
    --url http://127.0.0.1:$PORT --name $N --out $O/${s}_$A
done
echo "EVAL_B1_DONE $A $(date -u +%FT%TZ)" >> /data/harvest/logs/strip8/lanes.log

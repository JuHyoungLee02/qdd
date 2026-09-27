#!/bin/bash
# E-PRIV8 offline evaluation of one served arm (prereg_priv8.md §2), control rows only.
# usage: eval_priv.sh <code dir> <arm m1-keep|m1-drop|m3|g-px> <served name> <port>  -> /data/harvest/out/strip8/eval_priv/<set>_<arm>
C=$1; A=$2; N=$3; PORT=$4
O=/data/harvest/out/strip8/eval_priv
X=/data/harvest/out/teach_l8d/data/eval
P=/data/harvest/out/strip8/data_priv
case $A in
  m1-keep) SETS="dev_x=$P/ev_dev_x/dev_m1.jsonl ood_hx=$P/ev_ood_hx/dev_m1.jsonl dev=$P/ev_dev/dev_m1.jsonl ood_h=$P/ev_ood_h/dev_m1.jsonl"; ARM=nd-xyz;;
  m1-drop|m3) SETS="dev_x=$X/dev_x_s-min.jsonl ood_hx=$X/ood_h_s-min.jsonl dev=/data/harvest/out/strip8/data/dev_s-min.jsonl ood_h=/data/harvest/out/strip8/data/ood_h_s-min.jsonl"; ARM=nd-xyz;;
  g-px) SETS="dev_x=/data/harvest/out/strip8/data_gpx/x_dev_g-px.jsonl ood_hx=/data/harvest/out/strip8/data_gpx/x_ood_h_g-px.jsonl"; ARM=pt;;
  *) echo "arm?"; exit 2;;
esac
for s in $SETS; do
  k=${s%%=*}; D=${s#*=}
  bash $C/tools/teach_strip8/py.sh vllm - evp_${k}_${A//-/_} $C harvest.teach_pt.evaluate --data $D --arm $ARM \
    --kinds control --url http://127.0.0.1:$PORT --name $N --out $O/${k}_$A
done
echo "EVAL_PRIV_DONE $A $(date -u +%FT%TZ)" >> /data/harvest/logs/strip8/lanes.log

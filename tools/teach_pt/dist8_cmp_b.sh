#!/bin/bash
# E-DIST8 level-B comparisons on the L8-X sets: Q1 B-D vs B-R (= STRIP8 S-min(b1), its evaluation in
# /data/harvest/out/strip8/eval_b1x/<set>_s-min), Q5 D-noisy vs D-on and vs R, Q2 data effect B-D vs A-D and
# B-R vs A-R. usage: dist8_cmp_b.sh <code dir>  -> /data/harvest/out/dist8/cmp_b.jsonl
C=$1
E=/data/harvest/out/dist8/eval; S=/data/harvest/out/strip8/eval_b1x
O=/data/harvest/out/dist8/cmp_b.jsonl; P=/data/harvest/venv_train/bin/python
cd $C; export PYTHONPATH=$C
: > $O
for s in dev_x ood_h ood_d ood_o ood_s ood_t ood_hl; do
  x=x_${s/dev_x/dev}
  BD=$E/b_d-min/${x}_d-min_clean; BDN=$E/b_d-min/${x}_d-min_noisy; BR=$S/${s}_s-min
  AD=$E/a_d-min/${x}_d-min_clean; AR=$E/a_r-min/${x}_r-min_clean
  ok() { [ -f $1/scores.jsonl ] && [ -f $2/scores.jsonl ]; }
  ok $BD $BR && $P tools/teach_pt/dist8_compare.py "$s Q1 B-D vs B-R" $BD $BR >> $O
  ok $BDN $BD && $P tools/teach_pt/dist8_compare.py "$s Q5 B-D-noisy vs B-D" $BDN $BD >> $O
  ok $BDN $BR && $P tools/teach_pt/dist8_compare.py "$s Q5b B-D-noisy vs B-R" $BDN $BR >> $O
  ok $BD $AD && $P tools/teach_pt/dist8_compare.py "$s Q2 B-D vs A-D" $BD $AD >> $O
  ok $BR $AR && $P tools/teach_pt/dist8_compare.py "$s Q2 B-R vs A-R" $BR $AR >> $O
done
$P tools/teach_pt/dist8_table.py $O

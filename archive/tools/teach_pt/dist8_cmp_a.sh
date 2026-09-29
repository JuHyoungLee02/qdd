#!/bin/bash
# E-DIST8 level-A paired comparisons (prereg_dist8.md §4) on every set evaluated for all arms:
#   Q1  D-on vs R, Q5 D-noisy vs D-on, Q4 H-on vs D-on (+2 mm), H-noisy vs D-noisy (+2 mm), H-off vs R (r10).
# usage: dist8_cmp_a.sh <code dir> [level tag, default a]  -> /data/harvest/out/dist8/cmp_<level>.jsonl
C=$1; LV=${2:-a}
E=/data/harvest/out/dist8/eval
O=/data/harvest/out/dist8/cmp_$LV.jsonl
P=/data/harvest/venv_train/bin/python
cd $C; export PYTHONPATH=$C
: > $O
for s in dev ood_h x_dev x_ood_h x_ood_d x_ood_o x_ood_s x_ood_t x_ood_hl; do
  R=$E/${LV}_r-min/${s}_r-min_clean; D=$E/${LV}_d-min/${s}_d-min_clean; DN=$E/${LV}_d-min/${s}_d-min_noisy
  H=$E/${LV}_h-min/${s}_h-min_clean; HN=$E/${LV}_h-min/${s}_h-min_noisy; HO=$E/${LV}_h-min/${s}_h-min_off
  ok() { [ -f $1/scores.jsonl ] && [ -f $2/scores.jsonl ]; }
  ok $D $R && $P tools/teach_pt/dist8_compare.py "$s Q1 D-on vs R" $D $R >> $O
  ok $DN $D && $P tools/teach_pt/dist8_compare.py "$s Q5 D-noisy vs D-on" $DN $D >> $O
  ok $DN $R && $P tools/teach_pt/dist8_compare.py "$s Q5b D-noisy vs R" $DN $R >> $O
  ok $H $D && $P tools/teach_pt/dist8_compare.py "$s Q4a H-on vs D-on" $H $D 2 >> $O
  ok $HN $DN && $P tools/teach_pt/dist8_compare.py "$s Q4c H-noisy vs D-noisy" $HN $DN 2 >> $O
  ok $HO $R && $P tools/teach_pt/dist8_compare.py "$s Q4b H-off vs R" $HO $R r10 >> $O
done
cat $O

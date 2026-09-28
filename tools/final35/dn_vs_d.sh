#!/bin/bash
# Final 35B change 3 control: D (open point packs) vs D-nopub (L8-X only), both 2 epochs, per L8-X set and depth mode
# (clean / noisy): tools/teach_pt/dist8_compare.py, X = D, Y = D-nopub (BETTER = D lower). usage: dn_vs_d.sh <code dir>
C=$1; R=/data/harvest/out/dist8/eval; P=/data/harvest/venv_train/bin/python
for s in x_dev x_ood_h x_ood_hl x_ood_d x_ood_o x_ood_s x_ood_t; do
  for m in clean noisy; do
    [ -f $R/f35_d/${s}_d-min_$m/scores.jsonl ] && [ -f $R/f35_dn/${s}_d-min_$m/scores.jsonl ] || continue
    PYTHONPATH=$C $P $C/tools/teach_pt/dist8_compare.py ${s}_$m $R/f35_d/${s}_d-min_$m $R/f35_dn/${s}_d-min_$m 2 | tail -1
  done
done

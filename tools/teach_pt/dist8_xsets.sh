#!/bin/bash
# E-DIST8 L8-X evaluation rows (prereg_dist8.md §2): for each L8-X set that L8D has collected, the R / D / H
# minimal-request rows (D clean / noisy, H clean / noisy / off) in /data/harvest/out/dist8/data_x.
# usage: dist8_xsets.sh <code dir> <set> [<set> ...]   sets: ood_h ood_d ood_s ood_o ood_t ood_h_lift dev_x
C=$1; shift
P=/data/harvest/venv_train/bin/python
X=/data/harvest/out/teach_l8d/collect
D=/data/harvest/out/dist8/data_x
L=/data/harvest/logs/dist8
mkdir -p $D $L
cd $C; export PYTHONPATH=$C
for s in "$@"; do
  sp=x_${s/dev_x/dev}
  $P tools/teach_pt/build_min.py $X $D $sp r-min clean $X/$s
  for m in clean noisy; do $P tools/teach_pt/build_min.py $X $D $sp d-min $m $X/$s; done
  for m in clean noisy off; do $P tools/teach_pt/build_min.py $X $D $sp h-min $m $X/$s; done
  echo "XSET_DONE $s $(date -u +%FT%TZ)" >> $L/dist8_x.log
done >> $L/build_x.log 2>&1

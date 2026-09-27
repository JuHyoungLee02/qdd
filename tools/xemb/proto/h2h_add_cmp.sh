#!/bin/bash
# E-H2H-T add arms: comparisons vs h2h_base and add_t1t4 vs add_cpx2 on the 9 sets, then the compact table.
E=/data/harvest/out/xemb/h2h/eval
X=/data/harvest/out/xemb_proto
cd $E
for a in add_t1t4 add_cpx2; do ln -sfn dev_$a xe1dev_$a; ln -sfn ood_h_$a xe1ood_h_$a; done
cd $X/code
P=xe1dev,xe1ood_h,xdev_x,xood_h,xood_hl,xood_d,xood_s,xood_o,xood_t
PY=/data/harvest/venv_train/bin/python
$PY -m xemb.h2h_compare $E /data/harvest/out/xemb/h2h/cmp_add_vs_base.json $P h2h_base add_t1t4 add_cpx2 > /dev/null
$PY -m xemb.h2h_compare $E /data/harvest/out/xemb/h2h/cmp_add_t1t4_vs_cp.json $P add_cpx2 add_t1t4 > /dev/null
sed -e "s/h2h_t1t4/add_t1t4/g; s/h2h_cpg1/add_cpx2/g" $X/scratch/cmp_table.py > $X/scratch/cmp_table_add.py
$PY $X/scratch/cmp_table_add.py /data/harvest/out/xemb/h2h/cmp_add_vs_base.json /data/harvest/out/xemb/h2h/cmp_add_t1t4_vs_cp.json \
  > /data/harvest/out/xemb/h2h/add_table.txt

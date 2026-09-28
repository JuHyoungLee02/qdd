#!/bin/bash
# D round 2 closed-loop plans (prereg_dround2.md §2): OOD-O 8 (first 2 x 4 dirs) + OOD-H 0.98 4, lines '<combos> <eps>'.
# usage: dr2_plans.sh <code dir>  -> /data/harvest/logs/strip8/dr2_plan_{k,d,obj}.txt; links K0's reused boost1b episodes
C=$1
L=/data/harvest/logs/strip8; X=/data/harvest/out/teach_l8d/collect; P=/data/harvest/venv_train/bin/python
cd $C; export PYTHONPATH=$C
{ $P tools/teach_pt/dist8_pick.py $X/ood_o 2 drx_tz0.860 drx_tz0.940 standard_tz0.860 standard_tz0.940
  $P tools/teach_pt/dist8_pick.py $X/ood_h 4 drx_tz0.980; } | cut -d' ' -f2- > $L/dr2_eps.txt
sed 's/^/pts:none,pts:none:a /' $L/dr2_eps.txt > $L/dr2_plan_k.txt
sed 's/^/pts:none:d,pts:none:ad /' $L/dr2_eps.txt > $L/dr2_plan_d.txt
sed 's/^/pts:none /' $L/dr2_eps.txt > $L/dr2_plan_obj.txt
# K0 = boost1b pts_none (same model, executor, limits): link the finished episodes so they are not rerun
mkdir -p /data/harvest/out/strip8/dround2
[ -e /data/harvest/out/strip8/dround2/pts_none ] || cp -as /data/harvest/out/strip8/boost1b/pts_none /data/harvest/out/strip8/dround2/pts_none
wc -l $L/dr2_plan_*.txt

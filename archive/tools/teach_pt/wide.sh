#!/bin/bash
# E-PT change 2: wide OOD-H (tables 0.78 / 0.92): collect (DEV 0-9, standard, same behaviour policy), G-H truth
# closed loop (v2 and pt, s0 / s1), rebuild the OOD-H files (all four heights), re-evaluate L8-xyz (cached replies
# are reused), L8-xyz closed loop on the wide heights. usage: wide.sh <code dir>
C=$1
I="bash $C/tools/teach_pt/isaac.sh $C"
L=/data/harvest/logs/teach_pt
T=/data/harvest/out/teach_pt/closed_truth
lane() {
  G=$1; Z=$2
  $I $G oodh_${Z/./} harvest.teach_pt.run_collect --split ood_h --variant standard --table-z $Z --seeds 0-9
  for f in v2 pt; do $I $G truth_${f}_tz$Z harvest.teach_pt.run_closed --iface $f --model truth --table-z $Z --seeds 0,1 --out $T; done
}
lane 0 0.78 &
lane 1 0.92 &
wait
cd $C; export PYTHONPATH=$C
/data/harvest/venv_train/bin/python tools/teach_pt/build.py /data/harvest/out/teach_pt/collect /data/harvest/out/teach_pt/data ood_h --no-repeats > $L/build_oodh_wide.log 2>&1
echo "WIDE_DONE $(date -u +%FT%TZ)" >> $L/lanes.log
bash $C/tools/teach_pt/eval_arm.sh $C xyz l8_xyz 8395 l8xyz
bash $C/tools/teach_pt/l8_closed.sh $C 1

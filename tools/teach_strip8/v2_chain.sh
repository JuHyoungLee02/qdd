#!/bin/bash
# prereg_limits.md change 1: resolver v2 (mask near-depth 20th percentile + container opening / rim) vs v1 on 30 L8-X
# dev_x episodes (container-place tasks first), 8B B+obj-D served on the x2 pod (:8431), boost1b executor, render GPU
# <rg>. Same STOP file as the limits chain. usage: v2_chain.sh <code dir> <render gpu> <x2 pod ip>
C=$1; RG=$2; H=$3
L=/data/harvest/logs/strip8; O=/data/harvest/out/strip8/limits; P=/data/harvest/venv_train/bin/python
cd $C; export PYTHONPATH=$C
$P tools/teach_strip8/limits_pick.py v2set > $L/limits_v2set.txt
k=0
while read -r eps; do
  [ -n "$eps" ] || continue
  [ -f $L/limits.STOP ] && { echo "V2_STOPPED $(date -u +%FT%TZ)" >> $L/lanes.log; exit 0; }
  k=$((k + 1))
  bash $C/tools/teach_strip8/isaac.sh $C $RG lim_v2_$k harvest.teach_strip8.run_limits --conds ${V2_CONDS:-none,none:v2} \
    --qwen-url http://$H:8431 --qwen-name lim_bobj --out $O/v2 --episodes $eps
done < $L/limits_v2set.txt
echo "V2_DONE $(date -u +%FT%TZ)" >> $L/lanes.log

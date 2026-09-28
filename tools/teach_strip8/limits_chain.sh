#!/bin/bash
# user-log 171 chain (prereg_limits.md) on the main pod render GPU <rg>, models served on the x2 pod GPU0 (the caller
# starts them: 8B B+obj-D as 'lim_bobj' :8431, 35B f35_d as 'lim_f35d' :8432, --host 0.0.0.0; URL <host>).
# Parts: (A)+(B) limit map 15 conditions x 6 episodes (8B), then (C) f35_d 30 x {ood_h, ood_o, dev_x} (35B).
# A STOP file /data/harvest/logs/strip8/limits.STOP (written when the main training needs the card) ends the chain
# after the current Isaac process; every episode is saved as it finishes (restart skips finished ones).
# usage: limits_chain.sh <code dir> <render gpu> <x2 pod ip>
C=$1; RG=$2; H=$3
L=/data/harvest/logs/strip8; O=/data/harvest/out/strip8/limits; P=/data/harvest/venv_train/bin/python
mkdir -p $O; cd $C; export PYTHONPATH=$C
stop() { [ -f $L/limits.STOP ] && { echo "LIMITS_STOPPED $(date -u +%FT%TZ)" >> $L/lanes.log; exit 0; }; }
CONDS=none,none:r,hole:0.1,hole:0.3,hole:0.6,hole:0.1:r,hole:0.3:r,hole:0.6:r,noise:1,noise:2,noise:4,light:dim_warm,light:bright_cool,light:dark_green,occl:0.3,occl:0.6
$P tools/teach_strip8/limits_pick.py map > $L/limits_map.txt
k=0
while read -r eps; do
  [ -n "$eps" ] || continue; stop; k=$((k + 1))
  bash $C/tools/teach_strip8/isaac.sh $C $RG lim_map_$k harvest.teach_strip8.run_limits --conds $CONDS \
    --qwen-url http://$H:8431 --qwen-name lim_bobj --out $O/map --episodes $eps
done < $L/limits_map.txt
echo "LIMITS_MAP_DONE $(date -u +%FT%TZ)" >> $L/lanes.log
for s in ood_h ood_o dev_x; do
  $P tools/teach_strip8/limits_pick.py c30 $s > $L/limits_c30_$s.txt
  k=0
  while read -r eps; do
    [ -n "$eps" ] || continue; stop; k=$((k + 1))
    bash $C/tools/teach_strip8/isaac.sh $C $RG lim_c30_${s}_$k harvest.teach_strip8.run_limits --conds none \
      --qwen-url http://$H:8432 --qwen-name lim_f35d --out $O/c30 --episodes $eps
  done < $L/limits_c30_$s.txt
done
echo "LIMITS_DONE $(date -u +%FT%TZ)" >> $L/lanes.log

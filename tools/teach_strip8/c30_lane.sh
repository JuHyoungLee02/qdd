#!/bin/bash
# (C) f35_d 30-episode closed loop for one set on one render GPU (prereg_limits.md §3); the 35B is served at <url>.
# Same STOP file; finished episodes are skipped. usage: c30_lane.sh <code dir> <render gpu> <set> <url host:port>
C=$1; RG=$2; S=$3; U=$4
L=/data/harvest/logs/strip8; O=/data/harvest/out/strip8/limits; P=/data/harvest/venv_train/bin/python
cd $C; export PYTHONPATH=$C
$P tools/teach_strip8/limits_pick.py c30 $S > $L/limits_c30_$S.txt
k=0
while read -r eps; do
  [ -n "$eps" ] || continue
  [ -f $L/limits.STOP ] && { echo "C30_STOPPED $S $(date -u +%FT%TZ)" >> $L/lanes.log; exit 0; }
  k=$((k + 1))
  bash $C/tools/teach_strip8/isaac.sh $C $RG lim_c30_${S}_$k harvest.teach_strip8.run_limits --conds none \
    --qwen-url http://$U --qwen-name lim_f35d --out $O/c30 --episodes $eps
done < $L/limits_c30_$S.txt
echo "C30_DONE $S $(date -u +%FT%TZ)" >> $L/lanes.log

#!/bin/bash
# GGX A/B lane: one Isaac process at a time on one GPU. usage: ab_lane.sh <code> <gpu> <ab dir> <tag>
# <ab dir>/q.txt lines "<arm> <plan> <job>", arm rule = production label rule, arm ggx = GGX cache + ggx_v1
C=$1; G=$2; R=$3; T=$4
mkdir -p $R/claim $R/done
while read -r arm plan job; do
  [ -f $R/STOP ] && exit 0
  mkdir $R/claim/${arm}_$job 2>/dev/null || continue
  if [ "$arm" = ggx ]; then
    export L9V2_GGX_GRASPS=/data/harvest/l9v2/grasps_ggx L9V2_GGX_TESTED=/data/harvest/l9v2/tested_ggx L9V2_SEL=ggx_v1
  else
    unset L9V2_GGX_GRASPS L9V2_GGX_TESTED L9V2_SEL
  fi
  bash $C/tools/l9/isaac.sh $C $G ${T}_${arm}_$job harvest.l9.run9 --plan $plan --job $job --v2 --p 0.15 --out $R/$arm/collect
  grep -q '^RUN_DONE' /data/harvest/logs/l9/${T}_${arm}_$job.log && touch $R/done/${arm}_$job
done < $R/q.txt
echo "LANE_DONE $T $(date -u +%FT%TZ)" >> $R/lanes.log

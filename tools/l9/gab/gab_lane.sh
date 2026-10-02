#!/bin/bash
# L9v2-general integrated A/B lane: one Isaac process at a time on one GPU.
# usage: gab_lane.sh <code dir> <gpu> <ab dir> <tag>
# <ab dir>/q.txt lines "<arm> <robot> <plan> <job>"; arm env = <ab dir>/<arm>.env (KEY=VALUE lines, exported only for
# that arm; every key must be on tools/l9/isaac.sh's whitelist). Output <ab dir>/<arm>/collect (HCAM_ON in <ab>/<arm>).
# STOP: touch <ab dir>/STOP (the lane ends before its next job).
C=$1; G=$2; R=$3; T=$4
mkdir -p $R/claim $R/done
export L9_OMP=${L9_OMP:-2} L9_KIT_THREADS=${L9_KIT_THREADS:-4} L9_PHYSX_THREADS=${L9_PHYSX_THREADS:-2} L9_TIMEOUT=${L9_TIMEOUT:-5400}
while read -r arm robot plan job; do
  [ -f $R/STOP ] && break
  mkdir $R/claim/${arm}_$job 2>/dev/null || continue
  (
    set -a; . $R/$arm.env; set +a
    bash $C/tools/l9/isaac.sh $C $G ${T}_${arm}_$job harvest.l9.run9 --plan $plan --job $job --v2 --p 0.15 --out $R/$arm/collect
  )
  grep -q '^RUN_DONE' /data/harvest/logs/l9/${T}_${arm}_$job.log && touch $R/done/${arm}_$job
done < $R/q.txt
echo "LANE_DONE $T $(hostname) gpu$G $(date -u +%FT%TZ)" >> $R/lanes.log

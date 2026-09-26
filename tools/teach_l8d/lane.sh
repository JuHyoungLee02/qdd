#!/bin/bash
# L8-D lane: run the jobs of one jobs_<k>.txt one after another on one GPU (one Isaac process at a time).
# usage: lane.sh <code dir> <gpu> <jobs file> <lane tag>   logs per job: /data/harvest/logs/teach_l8d/<tag>_<i>.log
C=$1; G=$2; J=$3; T=$4
i=0
while read -r line; do
  [ -z "$line" ] && continue
  i=$((i+1))
  [ -f /data/harvest/out/teach_l8d/STOP ] && { echo "STOP file: lane $T ends before job $i"; break; }
  bash $C/tools/teach_l8d/isaac.sh $C $G ${T}_$i harvest.teach_l8d.run_collect $line
done < $J
echo "LANE_DONE $T $(date -u +%FT%TZ)" >> /data/harvest/logs/teach_l8d/lanes.log

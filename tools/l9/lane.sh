#!/bin/bash
# L9 lane: one Isaac process at a time on one GPU, taking jobs from a shared queue (atomic mkdir claims).
# usage: lane.sh <code dir> <gpu> <run dir> <lane tag>
#   <run dir>/jobs.txt      one run9 argument line per job ("--plan P --job J")
#   <run dir>/claim/<J>     claimed by a lane (file "lane" inside); <run dir>/done/<J> finished (RUN_DONE)
#   <run dir>/collect       episode output; STOP file /data/harvest/out/l9/STOP ends every lane before its next job
#   L9_MOD (env, default harvest.l9.run9): the runner module (L9 articulated: harvest.l9art.run_art); it must print RUN_DONE
# A restarted lane first finishes the jobs it had claimed (run9 resumes: finished episodes are skipped).
C=$1; G=$2; R=$3; T=$4
mkdir -p $R/claim $R/done
Y=/data/harvest/out/l9/yield/$(hostname)_$G  # lent card: stop before the next job (run9 stops between episodes)
FAST=0
run_job() {
  local line="$1" j="$2" t0=$(date +%s)
  bash $C/tools/l9/isaac.sh $C $G ${T}_$j ${L9_MOD:-harvest.l9.run9} $line --out $R/collect --video-seeds "$(cat $R/video_seeds 2>/dev/null)"
  if grep -q '^RUN_DONE' /data/harvest/logs/l9/${T}_$j.log; then touch $R/done/$j; FAST=0; return; fi
  [ -f $Y ] || [ -f /data/harvest/out/l9/STOP ] || rm -rf $R/claim/$j  # unfinished (crash / watchdog): give it back
  if [ $(( $(date +%s) - t0 )) -lt 120 ]; then  # failed at start (P148): back off, give up after 3
    rm -rf $R/claim/$j; FAST=$((FAST + 1))
    echo "FAST_FAIL lane $T job $j ($FAST)"
    [ $FAST -ge 3 ] && { echo "LANE_STOP $T: 3 jobs failed at start $(date -u +%FT%TZ)" >> $R/lanes.log; exit 1; }
    sleep 120
  fi
}
while read -r line; do  # own unfinished claims first
  j=$(echo "$line" | awk '{print $4}')
  [ -f $R/claim/$j/lane ] && [ "$(cat $R/claim/$j/lane)" = "$T" ] && [ ! -f $R/done/$j ] || continue
  [ -f /data/harvest/out/l9/STOP ] && { echo "STOP: lane $T"; exit 0; }
  [ -f $Y ] && { echo "YIELD: lane $T"; exit 0; }
  run_job "$line" "$j"
done < $R/jobs.txt
while read -r line; do
  j=$(echo "$line" | awk '{print $4}')
  [ -f /data/harvest/out/l9/STOP ] && { echo "STOP: lane $T"; exit 0; }
  [ -f $Y ] && { echo "YIELD: lane $T"; exit 0; }
  mkdir $R/claim/$j 2>/dev/null || continue
  echo $T > $R/claim/$j/lane
  run_job "$line" "$j"
done < $R/jobs.txt
echo "LANE_DONE $T $(date -u +%FT%TZ)" >> $R/lanes.log

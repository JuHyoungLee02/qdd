#!/bin/bash
# L9R borrower lane (= tools/l9/lane.sh without the yield checks: this lane runs ON the lent card). One Isaac process
# at a time on one GPU, jobs from <run dir>/jobs.txt (atomic mkdir claims), output <run dir>/collect.
# usage: lane_r.sh <code dir> <gpu> <run dir> <lane tag>
# stop: touch /data/harvest/out/l9r/STOP (before the next job). Memory guard: a job starts only while the pod's
# anonymous memory is below 85 GiB (pod rule <= 100 GiB; one Isaac lane ~13 GB).
C=$1; G=$2; R=$3; T=$4
export IR_L9R_LENT=1  # run9: ignore the lent card's yield file (this process is the borrower)
mkdir -p $R/claim $R/done
STOP=/data/harvest/out/l9r/STOP
anon_gib() { awk '/^anon /{printf "%d", $2 / 1073741824}' /sys/fs/cgroup/memory.stat; }
FAST=0
run_job() {
  local line="$1" j="$2" t0=$(date +%s)
  bash $C/tools/l9/isaac.sh $C $G ${T}_$j harvest.l9.run9 $line --out $R/collect
  if grep -q '^RUN_DONE' /data/harvest/logs/l9/${T}_$j.log; then touch $R/done/$j; FAST=0; return; fi
  [ -f $STOP ] || rm -rf $R/claim/$j
  if [ $(( $(date +%s) - t0 )) -lt 120 ]; then
    rm -rf $R/claim/$j; FAST=$((FAST + 1))
    echo "FAST_FAIL lane $T job $j ($FAST)"
    [ $FAST -ge 3 ] && { echo "LANE_STOP $T: 3 jobs failed at start $(date -u +%FT%TZ)" >> $R/lanes.log; exit 1; }
    sleep 120
  fi
}
while read -r line <&3; do
  j=$(echo "$line" | awk '{print $4}')
  [ -f $STOP ] && { echo "STOP: lane $T"; exit 0; }
  [ -f $R/done/$j ] && continue
  mkdir $R/claim/$j 2>/dev/null || continue
  echo $T > $R/claim/$j/lane
  while [ "$(anon_gib)" -ge 85 ]; do echo "MEM_WAIT $T $(anon_gib) GiB"; sleep 60; [ -f $STOP ] && exit 0; done
  run_job "$line" "$j"
done 3< $R/jobs.txt
echo "LANE_DONE $T $(date -u +%FT%TZ)" >> $R/lanes.log

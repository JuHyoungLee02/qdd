#!/bin/bash
# One generator slot: runs the job lines of a job file in order, one Isaac process per line (gen exits when no
# claimable item is left, so several slots may run the same job file; items are shared through the queue locks).
# usage: ./worker.sh <slot> <gpu> <jobfile>        job line: <tag-suffix> <gen args...>   ('#' lines skipped)
# stop before the next job: touch /data/harvest/mar2d/STOP
D=/data/harvest/mar2d
W=$1; GPU=$2; JOBS=$3
echo "WORKER $W host=$(hostname) gpu=$GPU pid=$$ start $(date -u +%Y-%m-%dT%H:%M:%SZ) jobs=$JOBS" >> $D/logs/workers.log
while read -r suffix args; do
  case "$suffix" in ''|'#'*) continue ;; esac
  if [ -e $D/STOP ]; then echo "WORKER $W STOP seen $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> $D/logs/workers.log; break; fi
  # shellcheck disable=SC2086
  $D/run.sh ${W}_${suffix} $GPU $args < /dev/null  # Isaac must not read the job file
done < "$JOBS"
echo "WORKER $W done $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> $D/logs/workers.log

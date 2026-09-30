#!/bin/bash
# L9 supervisor (one per pod): keeps its lanes running until every job is done or the STOP file exists, restarts a
# lane that died, writes progress every 10 min. usage: supervisor.sh <code dir> <run dir> <lanes "gpu:tag gpu:tag ...">
#   [<wait line>]   optional: start only after this text appears in /data/harvest/out/l9/GPU_FREED (x2 GPU1 hand-back)
# STOP: touch /data/harvest/out/l9/STOP (lanes end before their next job; the supervisor exits).
C=$1; R=$2; LANES=$3; WAIT=$4
L=/data/harvest/logs/l9
mkdir -p $L $R/pids
log() { echo "$(date -u +%FT%TZ) $*" >> $R/supervisor_$(hostname).log; }
if [ -n "$WAIT" ]; then
  log "waiting for '$WAIT' in GPU_FREED"
  until grep -q "$WAIT" /data/harvest/out/l9/GPU_FREED 2>/dev/null; do
    [ -f /data/harvest/out/l9/STOP ] && { log "STOP while waiting"; exit 0; }
    sleep 120
  done
fi
log "start lanes: $LANES"
n=0
while true; do
  [ -f /data/harvest/out/l9/STOP ] && { log "STOP file: supervisor ends (lanes finish their current job)"; exit 0; }
  total=$(wc -l < $R/jobs.txt); done_n=$(ls $R/done 2>/dev/null | wc -l)
  if [ "$done_n" -ge "$total" ]; then log "all $total jobs done"; exit 0; fi
  for spec in $LANES; do
    g=${spec%%:*}; t=${spec##*:}
    p=$(cat $R/pids/$t 2>/dev/null)
    if [ -z "$p" ] || ! kill -0 $p 2>/dev/null; then
      if [ -n "$p" ]; then log "lane $t (pid $p) not running: restart"; fi
      nohup setsid bash $C/tools/l9/lane.sh $C $g $R $t >> $L/lane_$t.log 2>&1 < /dev/null &
      echo $! > $R/pids/$t
    fi
  done
  if [ $((n % 10)) -eq 0 ]; then
    /data/harvest/venv_train/bin/python $C/tools/l9/progress.py $R > $R/progress_$(hostname).json 2>> $R/supervisor_$(hostname).log
  fi
  n=$((n + 1))
  sleep 60
done

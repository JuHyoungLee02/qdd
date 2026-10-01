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
    [ -f /data/harvest/out/l9/yield/$(hostname)_$g ] && continue  # card lent (tools/l9/lend9.sh)
    p=$(cat $R/pids/$t 2>/dev/null)
    if [ -z "$p" ] || ! kill -0 $p 2>/dev/null; then
      if [ -n "$p" ]; then log "lane $t (pid $p) not running: restart"; fi
      nohup setsid bash $C/tools/l9/lane.sh $C $g $R $t >> $L/lane_$t.log 2>&1 < /dev/null &
      echo $! > $R/pids/$t
    fi
  done
  for spec in $LANES; do  # hung episode watchdog: a job log silent for 20 min = a hung Isaac (2.3 h seen on x2)
    t=${spec##*:}; f=$(ls -t /data/harvest/logs/l9/${t}_*.log 2>/dev/null | head -1)
    [ -n "$f" ] || continue
    tail -1 "$f" | grep -q '^EXIT' && continue
    age=$(( $(date +%s) - $(stat -c %Y "$f") ))
    if [ $age -gt 1200 ]; then
      inst=$(basename $f .log)
      pids=""
      for p in /proc/[0-9]*; do tr '\0' '\n' < $p/environ 2>/dev/null | grep -q "^IR_INST=l9_${inst}$" && pids="$pids ${p#/proc/}"; done
      # SIGTERM first: an Isaac killed with SIGKILL while holding carb's global semaphore blocks every later start (P149)
      [ -n "$pids" ] && kill $pids 2>/dev/null; sleep 30
      for q in $pids; do [ -d /proc/$q ] && kill -9 $q 2>/dev/null; done
      log "watchdog: $inst silent ${age}s, Isaac stopped (the lane gives the job back)"
      if grep -q 'may be in a stuck state' "$f"; then
        touch $R/ALERT_SEM; log "ALERT: carb semaphore stuck (P149): run tools/l9/sem_reset.sh with no Isaac running"
      fi
    fi
  done
  if [ $((n % 10)) -eq 0 ]; then
    bash $C/tools/l9/shm_clean.sh >> $R/supervisor_$(hostname).log 2>&1  # stale carb shm on the 64 MB /dev (P148)
    /data/harvest/venv_train/bin/python $C/tools/l9/progress.py $R > $R/progress_$(hostname).json 2>> $R/supervisor_$(hostname).log
  fi
  n=$((n + 1))
  sleep 60
done

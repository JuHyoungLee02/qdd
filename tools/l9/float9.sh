#!/bin/bash
# float9.sh: the floating render card (user 2026-10-02: "being called away comes first; with nothing to do it joins
# L9"). Runs inside the pod that owns the card (x2, GPU 1) next to the L9 production supervisor.
#   request : another team creates  /data/harvest/out/render_float/WANTED   (requester, reason, expected time)
#   grant   : this watcher stops the L9 lanes on the card at once (SIGTERM to the Isaac processes, no waiting for
#             the episode), gives their unfinished jobs back to the queue (claims released, not "failed"), waits until
#             the card's memory is free, resets carb's semaphore when no Isaac runs (P149), creates  .../GRANTED
#   return  : the requester creates  .../DONE  (or removes WANTED): within 5 min the L9 lanes come back (the
#             supervisor restarts them once the yield file is gone; memory guard MEM_USED_MAX_GB).
# usage: float9.sh <gpu> <lane tags "xa xb">   log: /data/harvest/out/render_float/float9.log
G=$1; TAGS=$2
F=/data/harvest/out/render_float
L=/data/harvest/out/l9
Y=$L/yield/$(hostname)_$G
C=$(dirname $(dirname $(dirname $(readlink -f $0))))
mkdir -p $F $L/yield
log() { echo "$(date -u +%FT%TZ) $*" >> $F/float9.log; }
gpu_mem() { nvidia-smi -i $G --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' '; }
l9_pids() {
  for p in /proc/[0-9]*; do
    e=$(tr '\0' '\n' < $p/environ 2>/dev/null) || continue
    echo "$e" | grep -q '^IR_INST=l9_' || continue
    echo "$e" | grep -q "^CUDA_VISIBLE_DEVICES=$G$" && echo ${p#/proc/}
  done
}
state=idle
[ -f $F/GRANTED ] && state=lent
log "start (card $(hostname):$G, lanes $TAGS, state $state)"
while true; do
  if [ $state = idle ] && [ -f $F/WANTED ] && [ ! -f $F/DONE ]; then
    t0=$(date +%s)
    log "WANTED: $(tr '\n' ' ' < $F/WANTED | cut -c1-200)"
    touch $Y
    for t in $TAGS; do [ -f $L/prod1/pids/$t ] && kill $(cat $L/prod1/pids/$t) 2>/dev/null; done  # lanes: no next job
    pids=$(l9_pids)
    [ -n "$pids" ] && kill $pids 2>/dev/null
    n=0
    while [ -n "$(l9_pids)" ] && [ $n -lt 15 ]; do sleep 1; n=$((n + 1)); done  # Isaac ignores SIGTERM (test: 60 s)
    left=$(l9_pids); [ -n "$left" ] && { kill -9 $left 2>/dev/null; log "SIGKILL after 15 s: $left"; }
    bash $L/release_claims.sh $L/prod1 "ka kb kc kd ke kf" >> $F/float9.log 2>&1  # x2 jobs back to the queue
    n=0
    while [ "$(gpu_mem)" -gt 1000 ] && [ $n -lt 120 ]; do sleep 2; n=$((n + 2)); done
    bash $C/tools/l9/sem_reset.sh >> $F/float9.log 2>&1 || log "semaphore not reset (an Isaac runs on the pod)"
    bash $C/tools/l9/shm_clean.sh >> $F/float9.log 2>&1
    echo "granted $(date -u +%FT%TZ) card $(hostname):$G gpu_mem_mib $(gpu_mem) after $(( $(date +%s) - t0 )) s" > $F/GRANTED
    log "GRANTED after $(( $(date +%s) - t0 )) s (gpu mem $(gpu_mem) MiB)"
    state=lent; tl=$(date +%s)
  elif [ $state = lent ] && { [ -f $F/DONE ] || [ ! -f $F/WANTED ]; }; then
    log "returned ($( [ -f $F/DONE ] && echo DONE || echo WANTED removed )) after $(( $(date +%s) - tl )) s lent"
    mkdir -p $F/history
    for x in WANTED GRANTED DONE; do [ -f $F/$x ] && mv $F/$x $F/history/$(date -u +%Y%m%dT%H%M%S)_$x; done
    rm -f $Y
    state=back; tb=$(date +%s)
  elif [ $state = back ]; then
    if [ -n "$(l9_pids)" ]; then log "L9 back on the card after $(( $(date +%s) - tb )) s"; state=idle
    elif [ $(( $(date +%s) - tb )) -ge 300 ]; then log "L9 not back after 300 s (memory guard / supervisor?)"; state=idle
    elif [ -f $F/WANTED ]; then state=idle; fi
  fi
  sleep 5
done

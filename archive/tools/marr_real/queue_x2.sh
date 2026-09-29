#!/bin/bash
# E-MAR-real x2 lane (prereg_marr §3). usage: bash queue_x2.sh <lane 0|1> <pid of the E-SR1d lane on this GPU>
# Waits until that E-SR1d lane process is gone (its eval follows its training with no GPU wait, so a free-memory poll
# alone could slip into the gap), then runs:
#   lane 0 (GPU 0): smoke -> c0 1 -> [wait READY] -> a 1 -> view -> sr0 1
#   lane 1 (GPU 1): c0 2 -> [wait READY] -> a 2 -> sr0 2
# READY = /data/harvest/data/marr_real/conv/READY, created by hand only after G-dry, G-label and G-count pass.
# Stop: touch /data/harvest/tmp/marr_real/STOP (checked between steps). log: /data/harvest/logs/marr_real/lane<g>.out
set -u
g=$1; other=$2
D="$(cd "$(dirname "$0")" && pwd)"
L=/data/harvest/logs/marr_real; STOP=/data/harvest/tmp/marr_real/STOP
mkdir -p $L /data/harvest/tmp/marr_real
export MARR_LANE=$g
log() { echo "$* $(date -u +%FT%TZ)" >> $L/lane$g.out; }
step() { [ -e $STOP ] && { log "STOP before $*"; exit 0; }; log "step $*"; bash $D/run_train.sh "$@" >> $L/lane$g.out 2>&1; }
log "lane $g waiting for pid $other"
while [ -d /proc/$other ]; do sleep 30; done
log "pid $other gone"
if [ "$g" = 0 ]; then
  step smoke 0
  step c0 1 0
else
  step c0 2 1
fi
until [ -e /data/harvest/data/marr_real/conv/READY ]; do [ -e $STOP ] && { log "STOP while waiting READY"; exit 0; }; sleep 60; done
log "READY seen"
if [ "$g" = 0 ]; then
  step a 1 0
  step view 0
  step sr0 1 0
else
  step a 2 1
  step sr0 2 1
fi
log "lane $g done"

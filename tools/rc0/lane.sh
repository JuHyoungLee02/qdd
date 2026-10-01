#!/bin/bash
# E-RC0 sim lane (docs/stage3/prereg_rc0.md): 78dc CPU (OSMesa), one process per task = its N episodes (successive resets
# of the seed-7 env). Jobs: one task name per line, claimed with mkdir <out>/claims/<arm>_<task>.
# usage: RC_QURL=.. RC_PIHOST=.. RC_PIPORT=.. lane.sh <code dir> <arm A|P> <lane name> <jobs file> [n=3]
C=$1; ARM=$2; LN=$3; J=$4; N=${5:-3}
O=/data/harvest/out/rc0; V=/data/harvest/videos/rc0; L=/data/harvest/logs/rc0
mkdir -p $O/claims $O/lanes $V $L
source $C/tools/rc0/env_rc.sh $C
export LIB0_JOB=rclane_$LN
log() { echo "$(date -u +%FT%TZ) $(hostname) $LN $*" >> $L/lanes.log; }
log "LANE_START arm=$ARM code=$C"
touch $O/lanes/$LN.alive
while IFS= read -r -u 3 TASK; do
  [ -f $O/STOP ] && break; [ -z "$TASK" ] && continue
  mkdir $O/claims/${ARM}_$TASK 2>/dev/null || continue
  log "RUN $ARM $TASK"
  if [ $ARM = A ]; then
    nice -n 10 timeout 21600 $PY -m harvest.rc0.run_a --task $TASK --n $N --qwen-url $RC_QURL --out $O --vid-root $V \
      --stop-files $O/STOP >> $L/lane_$LN.log 2>&1 < /dev/null
  else
    nice -n 10 timeout 21600 $PY -m harvest.rc0.run_p --task $TASK --n $N --host $RC_PIHOST --port $RC_PIPORT --out $O \
      --vid-root $V >> $L/lane_$LN.log 2>&1 < /dev/null
  fi
  log "END $ARM $TASK rc=$?"
done 3< $J
rm -f $O/lanes/$LN.alive
log "LANE_DONE"

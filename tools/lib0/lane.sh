#!/bin/bash
# E-LIB0 sim lane (docs/stage3/prereg_lib0.md): CPU OSMesa, one process per (suite, task) job = episodes k of that task.
# Jobs: tab-separated "<suite> <task> <ks>" lines; claimed with mkdir <out>/claims/<arm>_<suite>_<task>.
# Servers: arm A -> LIB0_QURL (vLLM, served name lib0_ep2_5); arms B / R -> LIB0_PIHOST:8702 (B) / 8701 (R).
# Stop: touch /data/harvest/out/lib0/STOP (between jobs; the runner also checks it between episodes).
# usage: lane.sh <code dir> <arm A|Ab|B|R> <lane name> <jobs file>   log -> /data/harvest/logs/lib0/lanes.log + lane_<name>.log
C=$1; ARM=$2; LN=$3; J=$4
O=/data/harvest/out/lib0; V=/data/harvest/videos/lib0; L=/data/harvest/logs/lib0
mkdir -p $O/claims $O/lanes $V $L
source $C/tools/lib0/env_lib.sh $C
export LIB0_JOB=lane_$LN
log() { echo "$(date -u +%FT%TZ) $(hostname) $LN $*" >> $L/lanes.log; }
log "LANE_START arm=$ARM code=$C"
touch $O/lanes/$LN.alive
while IFS=$'\t' read -r -u 3 SUITE TASK KS; do
  [ -f $O/STOP ] && { log "STOP"; break; }
  [ -z "$SUITE" ] && continue
  mkdir $O/claims/${ARM}_${SUITE}_$TASK 2>/dev/null || continue
  log "RUN $ARM $SUITE $TASK ks=$KS"
  if [ $ARM = A ] || [ $ARM = Ab ]; then
    FB=""; [ $ARM = Ab ] && FB=--fix-b  # Ab = E-LIB0b (prereg change 2)
    nice -n 10 timeout 10800 $PY -m harvest.lib0.run_a --suite $SUITE --task $TASK --ks $KS --qwen-url $LIB0_QURL \
      --qwen-name lib0_ep2_5 --out $O --vid-root $V --arm $ARM $FB --stop-files $O/STOP >> $L/lane_$LN.log 2>&1 < /dev/null
  else
    P=8702; [ $ARM = R ] && P=8701
    nice -n 10 timeout 10800 $PY -m harvest.lib0.run_pi --suite $SUITE --task $TASK --ks $KS --host $LIB0_PIHOST --port $P \
      --arm $ARM --out $O --vid-root $V --stop-files $O/STOP >> $L/lane_$LN.log 2>&1 < /dev/null
  fi
  log "END $ARM $SUITE $TASK rc=$?"
done 3< $J
rm -f $O/lanes/$LN.alive
log "LANE_DONE"

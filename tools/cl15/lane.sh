#!/bin/bash
# E-CL15 render lane (docs/stage3/prereg_cl15.md). Waits for READY (server up) and the L9 owner's hand-over file
# <root>/LANES_GO_7a2a_<gpu>, then takes jobs from <root>/jobs.txt (mkdir claim, one Isaac process per job =
# harvest.cl15.run_t1 on one L8S group). Stop: touch <root>/STOP (checked between episodes). The last lane to finish
# writes <root>/DONE and appends "<pod>:<gpu> returned by CL15 <UTC>" to /data/harvest/out/l9/GPU_FREED.
# usage: lane.sh <code dir> <gpu> <lane name> <url> <served name>
C=$1; G=$2; LN=$3; URL=$4; NAME=$5
R=/data/harvest/out/cl15; L=/data/harvest/logs/cl15; V=/data/harvest/videos/cl15/T1
mkdir -p $R/claims $R/lanes $L $V
log() { echo "$(date -u +%FT%TZ) $LN $*" >> $L/lanes.log; }
log "LANE_WAIT gpu=$G"
until [ -f $R/LANES_GO_7a2a_$G ] || [ -f $R/STOP ]; do sleep 20; done
log "LANE_START gpu=$G code=$C"
touch $R/lanes/$LN.alive
while IFS=$'\t' read -r GID JOB; do
  [ -f $R/STOP ] && break
  mkdir $R/claims/$GID 2>/dev/null || continue
  log "RUN $GID"
  bash $C/tools/teach_strip8/isaac.sh $C $G cl15_$LN harvest.cl15.run_t1 --job "$JOB" --episodes $R/eps_$GID.json \
    --conds none --ckpt ep1.5 --qwen-url $URL --qwen-name $NAME --out $R/res --vid-root $V --yield-files $R/STOP \
    --owner $LN --loop-break --stall-n 3
  log "END $GID $(tail -1 /data/harvest/logs/strip8/cl15_$LN.log)"
done < $R/jobs.txt
rm -f $R/lanes/$LN.alive
if [ -z "$(ls $R/lanes/*.alive 2>/dev/null)" ]; then
  /data/harvest/venv_train/bin/python $C/tools/cl15/summary.py >> $L/lanes.log 2>&1
  touch $R/DONE; echo "$(hostname):$G returned by CL15 $(date -u +%FT%TZ)" >> /data/harvest/out/l9/GPU_FREED
  log "DONE (card returned)"
fi

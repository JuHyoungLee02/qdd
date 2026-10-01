#!/bin/bash
# E-CL15 render lane (docs/stage3/prereg_cl15.md). Waits for READY (server up) and the L9 owner's hand-over file
# <root>/LANES_GO_7a2a_<gpu>, then takes jobs from <root>/jobs.txt (mkdir claim, one Isaac process per job =
# harvest.cl15.run_t1 on one L8S group). Stop: touch <root>/STOP (checked between episodes). The last lane to finish
# writes <root>/DONE and appends "<pod>:<gpu> returned by $(basename $R | tr a-z A-Z) <UTC>" to /data/harvest/out/l9/GPU_FREED.
# usage: [CL15_ROOT=.. CL15_VID=.. CL15_CKPT=.. CL15_EXTRA="runner args" CL15_JOBS=<jobs file>] lane.sh <code dir> <gpu> <lane name> <url> <served name>
# (defaults = the first run: /data/harvest/out/cl15, /data/harvest/videos/cl15/T1, ep1.5; E-CL15b arms set them)
C=$1; G=$2; LN=$3; URL=$4; NAME=$5
R=${CL15_ROOT:-/data/harvest/out/cl15}; V=${CL15_VID:-/data/harvest/videos/cl15/T1}; CK=${CL15_CKPT:-ep1.5}
L=/data/harvest/logs/$(basename $R)
mkdir -p $R/claims $R/lanes $L $V
log() { echo "$(date -u +%FT%TZ) $LN $*" >> $L/lanes.log; }
log "LANE_WAIT gpu=$G"
until [ -f $R/LANES_GO_7a2a_$G ] || [ -f $R/STOP ] || [ -f $R/STOP_$CK ]; do sleep 20; done
log "LANE_START gpu=$G code=$C"
touch $R/lanes/$LN.alive
while IFS=$'\t' read -r GID JOB; do
  { [ -f $R/STOP ] || [ -f $R/STOP_$CK ]; } && break  # STOP_<ckpt>: this arm only (e.g. the Astra budget stop)
  mkdir $R/claims/${CK}__$GID 2>/dev/null || continue
  log "RUN $GID"
  bash $C/tools/teach_strip8/isaac.sh $C $G $(basename $R)_$LN harvest.cl15.run_t1 --job "$JOB" --episodes $R/eps_$GID.json \
    --conds none --ckpt $CK --qwen-url $URL --qwen-name $NAME --out $R/res --vid-root $V --yield-files $R/STOP_$CK,$R/STOP \
    --owner $LN --loop-break --stall-n 3 $CL15_EXTRA < /dev/null
  log "END $GID $(tail -1 /data/harvest/logs/strip8/$(basename $R)_$LN.log)"
done 3< ${CL15_JOBS:-$R/jobs.txt}
rm -f $R/lanes/$LN.alive
if [ -z "$(ls $R/lanes/*.alive 2>/dev/null)" ]; then
  /data/harvest/venv_train/bin/python $C/tools/cl15/summary.py $R $V $CK >> $L/lanes.log 2>&1
  touch $R/DONE; echo "$(hostname):$G returned by $(basename $R | tr a-z A-Z) $(date -u +%FT%TZ)" >> /data/harvest/out/l9/GPU_FREED
  log "DONE (card returned)"
fi

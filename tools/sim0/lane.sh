#!/bin/bash
# E-SIM0 sim lane (docs/stage3/prereg_sim0.md): SAPIEN 2.2.2 with CPU Vulkan (Mesa lavapipe; the pods' NVIDIA Vulkan
# hangs in take_picture), 78dc CPU. Jobs: one line per episode-name list (comma); claimed with mkdir.
# usage: lane.sh <code dir> <arm A|B> <lane name> <jobs file>   env: SIM0_QURL (A), SIM0_PIHOST (B, port 8703)
C=$1; ARM=$2; LN=$3; J=$4
O=/data/harvest/out/sim0; V=/data/harvest/videos/sim0; L=/data/harvest/logs/sim0; S=/data/harvest/simpler
mkdir -p $O/claims $O/lanes $V $L
export LD_LIBRARY_PATH=$S/vk/lib:/data/harvest/lib0/mesa/lib VK_ICD_FILENAMES=/data/harvest/lib0/mesa/share/vulkan/icd.d/lvp_icd.x86_64.json
export XDG_RUNTIME_DIR=/data/harvest/tmp/xdg HOME=/data/harvest/home XDG_CACHE_HOME=$S/cache TMPDIR=/data/harvest/tmp
export LP_NUM_THREADS=2 OMP_NUM_THREADS=1 PYTHONPATH=$C PYTHONPYCACHEPREFIX=/data/harvest/cache/pyc_sim0 LIB0_JOB=simlane_$LN
log() { echo "$(date -u +%FT%TZ) $(hostname) $LN $*" >> $L/lanes.log; }
log "LANE_START arm=$ARM code=$C"
touch $O/lanes/$LN.alive
n=0
while IFS= read -r -u 3 EPS; do
  n=$((n+1)); [ -f $O/STOP ] && break; [ -z "$EPS" ] && continue
  mkdir $O/claims/${ARM}_$n 2>/dev/null || continue
  log "RUN $ARM job $n"
  if [ $ARM = A ]; then
    nice -n 10 timeout 14400 $S/venv/bin/python -m harvest.sim0.run_a --eps $EPS --qwen-url $SIM0_QURL --qwen-name lib0_ep2_5 \
      --out $O --vid-root $V --arm A --stop-files $O/STOP >> $L/lane_$LN.log 2>&1 < /dev/null
  else
    nice -n 10 timeout 14400 $S/venv/bin/python -m harvest.sim0.run_pi --eps $EPS --host $SIM0_PIHOST --port 8703 --arm B \
      --out $O --vid-root $V --stop-files $O/STOP >> $L/lane_$LN.log 2>&1 < /dev/null
  fi
  log "END $ARM job $n rc=$?"
done 3< $J
rm -f $O/lanes/$LN.alive
log "LANE_DONE"

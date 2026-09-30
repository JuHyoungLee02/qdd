#!/bin/bash
# E-CJ1 render lane (docs/stage3/prereg_cj1.md) on a render card (7a2a GPU 0/1/3, x2 GPU 1 only).
# kind run: one Isaac process harvest.couple_joy.run (commander x executor arms, one variant, seeds claimed by mkdir)
# kind v0 : VLA alone = harvest.eval.closed (tools/vla_alone/vla_closed.py) C5 fused, one process per episode
# YIELD (L9 priority, mandatory; = tools/main35_closed/lane.sh): /data/harvest/out/l9/GPU_WANTED or <R>/lanes/<lane>.WANTED
# exists, or an L9 process is on this GPU -> the running episode finishes (checked between episodes; the Isaac chain
# is stopped after 600 s), the lane exits, and the last lane of this GPU appends "<pod>:<gpu> freed <UTC> (couple)"
# to /data/harvest/out/l9/GPU_FREED.
# usage: lane.sh <code dir> <gpu> <lane> <run|v0> <variant> <arms|-> <seeds> <vla url>
C=$1; G=$2; LN=$3; KIND=$4; V=$5; ARMS=$6; SEEDS=$7; VURL=$8
R=/data/harvest/out/couple/cj1; L=/data/harvest/logs/couple; P=/data/harvest/venv_train/bin/python
VID=/data/harvest/videos/couple_cj1
W1=/data/harvest/out/l9/GPU_WANTED; W2=$R/lanes/$LN.WANTED
POD=$(hostname); export COUPLE_JOB=lane_$LN
mkdir -p $R/lanes $L $VID
log() { echo "$(date -u +%FT%TZ) $LN $*" >> $L/lanes.log; }
l9_on_gpu() {
  local u; u=$(nvidia-smi -i $G --query-gpu=uuid --format=csv,noheader 2>/dev/null)
  nvidia-smi --query-compute-apps=pid,gpu_uuid --format=csv,noheader 2>/dev/null | while IFS=', ' read -r pid gu; do
    [ "$gu" = "$u" ] || continue
    tr '\0' '\n' < /proc/$pid/environ 2>/dev/null | grep -qE '^IR_INST=strip8_(cj|m35cl)' && continue
    tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null | sed 's#/data/harvest/out/l9/GPU_[A-Z]*##g' \
      | grep -qiE '(^|[^a-z0-9])l9([^0-9]|$)' && { echo $pid; break; }
  done
}
want() { [ -f $W1 ] && { echo GPU_WANTED; return; }; [ -f $W2 ] && { echo lane_WANTED; return; }
  local p; p=$(l9_on_gpu); [ -n "$p" ] && echo "l9_pid_$p"; }
freed() {
  rm -f $R/lanes/$LN.alive
  local left; left=$(ls $R/lanes/${POD}_g${G}_*.alive 2>/dev/null | wc -l)
  if [ "$left" = 0 ] && [ "$1" != lane_WANTED ]; then mkdir -p /data/harvest/out/l9
    echo "$POD:$G freed $(date -u +%FT%TZ) (couple)" >> /data/harvest/out/l9/GPU_FREED; fi
  log "YIELD_EXIT reason=$1 left_on_gpu=$left"; exit 0
}
watch() {  # watch <pid> <stop name>: keep alive, stop the chain 600 s after a yield request
  local ip=$1 t_w=0 w
  while kill -0 $ip 2>/dev/null; do
    sleep 15; touch $R/lanes/$LN.alive
    w=$(want)
    if [ -n "$w" ]; then
      [ $t_w = 0 ] && { log "YIELD_REQ $w"; t_w=$(date +%s); }
      [ $(( $(date +%s) - t_w )) -gt 600 ] && { log "YIELD_ABORT"; bash $C/tools/couple_joy/stop.sh $2 >> $L/lanes.log 2>&1; }
    fi
  done
}
log "LANE_START gpu=$G kind=$KIND variant=$V arms=$ARMS seeds=$SEEDS code=$C"
touch $R/lanes/$LN.alive
if [ $KIND = run ]; then
  while true; do
    w=$(want); [ -n "$w" ] && freed "$w"
    bash $C/tools/teach_strip8/isaac.sh $C $G cj_$LN harvest.couple_joy.run --arms $ARMS --variant $V \
      --seeds $SEEDS --vla-url $VURL --out $R/res --vid-root $VID --yield-files $W1,$W2 --owner $LN &
    ip=$!; watch $ip cj_$LN; wait $ip
    w=$(want); [ -n "$w" ] && freed "$w"
    tail -3 /data/harvest/logs/strip8/cj_$LN.log | grep -q RUN_DONE && break
    log "RESTART (no RUN_DONE)"; sleep 30
  done
else  # v0: VLA alone, one closed.py process per episode (seeds claimed by mkdir)
  cd $C
  for s in $(echo $SEEDS | tr ',' ' '); do
    w=$(want); [ -n "$w" ] && freed "$w"
    od=$R/res/v0/$V/s$s
    [ -f $od/closed.json ] && continue
    mkdir -p $od; mkdir $od/claim 2>/dev/null || continue
    log "V0 $V s$s"
    PYTHONPATH=$C OMP_WAIT_POLICY=PASSIVE $P tools/vla_alone/vla_closed.py --model /data/harvest/ckpt/sr1c/c1/last \
      --backend fused --url $VURL --out $od --split dev --seeds $s --variants $V --conditions C5 --max-seconds 120 \
      --couple off --astra none --isaac-gpu $G --inst-prefix strip8_cjv0_$LN --vla-speed 1.0 --vla-video-hz 10 \
      > $od/run.out 2>&1 &
    ip=$!; watch $ip cjv0_${LN}_$V; wait $ip; log "V0_EXIT $V s$s rc=$?"
  done
fi
rm -f $R/lanes/$LN.alive; log "LANE_DONE"

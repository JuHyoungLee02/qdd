#!/bin/bash
# JCR stage-1 data lane (docs/stage3/prereg_jcr1.md; jcr_design.md §5) on a render card (7a2a GPU 0/1/3, x2 GPU 1 only).
# One Isaac process harvest.jcr.record (one variant, R2_TRAIN seeds claimed by mkdir), restarted until RUN_DONE.
# YIELD (L9 priority, NOW.md §3): /data/harvest/out/l9/GPU_WANTED or <R>/lanes/<lane>.WANTED exists, or an L9
# process is on this GPU -> the running episode finishes (stopped after 600 s), the lane exits, and the last lane of
# this GPU appends "<pod>:<gpu> freed <UTC> (jcr)" to /data/harvest/out/l9/GPU_FREED.
# usage: lane.sh <code dir> <gpu> <lane> <variant> <seeds> <out> <vid root> [scale]
C=$1; G=$2; LN=$3; V=$4; SEEDS=$5; OUT=$6; VID=$7; SC=${8:-0.75}
R=/data/harvest/out/jcr; L=/data/harvest/logs/jcr; DIST=$R/upper_err_dist.json
W1=/data/harvest/out/l9/GPU_WANTED; W2=$R/lanes/$LN.WANTED
POD=$(hostname)
mkdir -p $R/lanes $L $VID
log() { echo "$(date -u +%FT%TZ) $LN $*" >> $L/lanes.log; }
l9_on_gpu() {
  local u; u=$(nvidia-smi -i $G --query-gpu=uuid --format=csv,noheader 2>/dev/null)
  nvidia-smi --query-compute-apps=pid,gpu_uuid --format=csv,noheader 2>/dev/null | while IFS=', ' read -r pid gu; do
    [ "$gu" = "$u" ] || continue
    tr '\0' '\n' < /proc/$pid/environ 2>/dev/null | grep -qE '^IR_INST=strip8_(jcr|cj|m35cl)' && continue
    tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null | sed 's#/data/harvest/out/l9/GPU_[A-Z]*##g' \
      | grep -qiE '(^|[^a-z0-9])l9([^0-9]|$)' && { echo $pid; break; }
  done
}
# GPU_WANTED names the cards L9 wants ("<pod short>:<gpu>" per line/word, e.g. 7a2a:3); an empty file = all cards.
# User 10-01 (render plan A): JCR keeps x2 GPU1 unless the file names it (x2:<G> / 7a2a-x2:<G>) or is empty / "all".
wanted_me() { [ -f $W1 ] || return 1; [ -s $W1 ] || return 0
  grep -qiE "(^|[^a-z0-9-])((7a2a-)?x2:$G|all)([^0-9]|$)" $W1; }
want() { wanted_me && { echo GPU_WANTED; return; }; [ -f $W2 ] && { echo lane_WANTED; return; }
  local p; p=$(l9_on_gpu); [ -n "$p" ] && echo "l9_pid_$p"; }
freed() {
  rm -f $R/lanes/$LN.alive
  local left; left=$(ls $R/lanes/${POD}_g${G}_*.alive 2>/dev/null | wc -l)
  if [ "$left" = 0 ] && [ "$1" != lane_WANTED ]; then mkdir -p /data/harvest/out/l9
    echo "$POD:$G freed $(date -u +%FT%TZ) (jcr)" >> /data/harvest/out/l9/GPU_FREED; fi
  log "YIELD_EXIT reason=$1 left_on_gpu=$left"; exit 0
}
watch() {
  local ip=$1 t_w=0 w
  while kill -0 $ip 2>/dev/null; do
    sleep 15; touch $R/lanes/$LN.alive
    w=$(want)
    if [ -n "$w" ]; then
      [ $t_w = 0 ] && { log "YIELD_REQ $w"; t_w=$(date +%s); }
      [ $(( $(date +%s) - t_w )) -gt 600 ] && { log "YIELD_ABORT"; bash $C/tools/teach_strip8/stop.sh jcr_$LN >> $L/lanes.log 2>&1; }
    fi
  done
}
log "LANE_START gpu=$G variant=$V seeds=$SEEDS out=$OUT scale=$SC code=$C"
touch $R/lanes/$LN.alive
while true; do
  w=$(want); [ -n "$w" ] && freed "$w"
  bash $C/tools/teach_strip8/isaac.sh $C $G jcr_$LN harvest.jcr.record --variant $V --seeds $SEEDS --out $OUT \
    --vid-root $VID --dist $DIST --scale $SC --yield-files $W1,$W2 --owner $LN &
  ip=$!; watch $ip; wait $ip
  w=$(want); [ -n "$w" ] && freed "$w"
  tail -3 /data/harvest/logs/strip8/jcr_$LN.log | grep -q RUN_DONE && break
  log "RESTART (no RUN_DONE)"; sleep 30
done
rm -f $R/lanes/$LN.alive; log "LANE_DONE"

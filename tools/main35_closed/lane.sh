#!/bin/bash
# E-M35CL render lane (docs/stage3/prereg_main35_closed.md): loop { sched next -> one Isaac process (run_closed_l8s)
# on GPU <gpu> for the served checkpoint }. YIELD (L9 priority, mandatory): /data/harvest/out/l9/GPU_WANTED or
# <root>/lanes/<lane>.WANTED exists, or an L9 process (command line with the token l9) is on this GPU -> the running
# Isaac finishes its episode (flag file checked between episodes; aborted after 600 s), the lane exits, and the last
# lane of this GPU appends "<pod>:<gpu> freed <UTC>" to /data/harvest/out/l9/GPU_FREED.
# usage: lane.sh <code dir> <gpu> <lane name>     (no pgrep / pkill patterns: stop = teach_strip8/stop.sh <tag>)
C=$1; G=$2; LN=$3
R=/data/harvest/out/main35_closed; L=/data/harvest/logs/main35_closed; P=/data/harvest/venv_train/bin/python
W1=/data/harvest/out/l9/GPU_WANTED; W2=$R/lanes/$LN.WANTED; YF=$R/lanes/$LN.YIELD
TAG=m35cl_$LN; POD=$(hostname)
mkdir -p $R/lanes $L
log() { echo "$(date -u +%FT%TZ) $LN $*" >> $L/lanes.log; }
l9_on_gpu() {  # an L9 process on this GPU (by its command line)
  local u; u=$(nvidia-smi -i $G --query-gpu=uuid --format=csv,noheader 2>/dev/null)
  nvidia-smi --query-compute-apps=pid,gpu_uuid --format=csv,noheader 2>/dev/null | while IFS=', ' read -r pid gu; do
    [ "$gu" = "$u" ] || continue
    tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null | grep -qiE '(^|[^a-z0-9])l9([^0-9]|$)' && { echo $pid; break; }
  done
}
want() { [ -f $W1 ] && { echo GPU_WANTED; return; }; [ -f $W2 ] && { echo lane_WANTED; return; }
  local p; p=$(l9_on_gpu); [ -n "$p" ] && echo "l9_pid_$p"; }
freed() {
  rm -f $R/lanes/$LN.alive $R/lanes/$LN.group $YF
  local left; left=$(ls $R/lanes/${POD}_g${G}_*.alive 2>/dev/null | wc -l)
  if [ "$left" = 0 ]; then mkdir -p /data/harvest/out/l9
    echo "$POD:$G freed $(date -u +%FT%TZ)$1" >> /data/harvest/out/l9/GPU_FREED; fi
  log "YIELD_EXIT reason=$2 left_on_gpu=$left"; exit 0
}
log "LANE_START gpu=$G code=$C"
while true; do
  touch $R/lanes/$LN.alive
  w=$(want); [ -n "$w" ] && freed "" "$w"
  cur=$(cat $R/CURRENT 2>/dev/null); set -- $cur
  if [ $# -ne 3 ]; then sleep 60; continue; fi
  CK=$1; URL=$2; NAME=$3
  nx=$($P $C/tools/main35_closed/sched.py next $LN 2>>$L/sched_err.log)
  set -- $nx
  if [ "$1" = WAIT ] || [ $# -ne 2 ]; then sleep 60; continue; fi
  GID=$1; CONDS=$2
  JOB=$($P -c "import json,sys;print([g for g in json.load(open('$R/groups.json'))['groups'] if g['id']=='$GID'][0]['job'])")
  echo $GID > $R/lanes/$LN.group
  log "RUN ckpt=$CK group=$GID conds=$CONDS"
  bash $C/tools/teach_strip8/isaac.sh $C $G $TAG harvest.teach_pt.run_closed_l8s --job "$JOB" \
    --episodes $R/eps_$GID.json --conds $CONDS --ckpt $CK --qwen-url $URL --qwen-name $NAME --out $R/res \
    --vid-root /data/harvest/videos/main35_closed --current $R/CURRENT --yield-files $W1,$W2,$YF --owner $LN &
  ip=$!; t_w=0
  while kill -0 $ip 2>/dev/null; do
    sleep 15; touch $R/lanes/$LN.alive $R/lanes/$LN.group
    w=$(want)
    if [ -n "$w" ]; then
      [ -f $YF ] || { echo "$w" > $YF; log "YIELD_REQ $w"; t_w=$(date +%s); }
      [ $(( $(date +%s) - t_w )) -gt 600 ] && { log "YIELD_ABORT episode"; bash $C/tools/teach_strip8/stop.sh $TAG >> $L/lanes.log 2>&1; }
    fi
  done
  wait $ip
  rm -f $R/lanes/$LN.group
  [ -f $YF ] && freed "" "$(cat $YF)"
  tail -1 /data/harvest/logs/strip8/$TAG.log | grep -q "EXIT 0" || sleep 30  # a failed process: back off
done

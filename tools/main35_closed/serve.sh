#!/bin/bash
# E-M35CL model server (x3 GPU 0, lent from the VLA reservation): per checkpoint in order f35d 0.5 1 1.5 2 2.5 3 ->
# wait for its merged BF16 weights, vLLM (tools/teach_35b/vllm.sh, bound to the pod IP), write <root>/CURRENT
# "<ckpt> <url> <name>", keep it until sched done <ckpt>, then stop and remove main35_closed/merged_ep<e> (f35_d's
# merged_d is never removed).
# VLA yield: /data/harvest/out/vla/GPU_WANTED -> CURRENT removed, server stopped at once, "<pod>:<gpu> freed <UTC>"
# appended to /data/harvest/out/vla/GPU_FREED; serving resumes only when that file is gone and the card is empty.
# L9: stops (and exits) when /data/harvest/out/l9/GPU_WANTED exists and no lane has been alive for 10 min.
# A server already answering with this checkpoint's name is adopted (restart of this script).
# usage: serve.sh <code dir> <gpu> <port>
C=$1; G=$2; PORT=$3
R=/data/harvest/out/main35_closed; L=/data/harvest/logs/main35_closed; P=/data/harvest/venv_train/bin/python
VW=/data/harvest/out/vla/GPU_WANTED
mkdir -p $L; IP=$(hostname -i | awk '{print $1}')
log() { echo "$(date -u +%FT%TZ) serve $*" >> $L/serve.log; }
# per-card yield (user approval 2026-10-01): VLA/JCR and L9 requests count only when they list this card
KEY=$(hostname | sed -E 's/.*7a2a-(x[0-9]+)$//; s/.*native-7a2a$/7a2a/')
listed() { [ -f "$1" ] && grep -oE "(^|[[:space:]])$KEY:[0-9,]+" "$1" | grep -qE "[:,]$G(,|$)"; }
lanes_alive() { find $R/lanes -name '*.alive' -mmin -10 2>/dev/null | grep -q .; }
mem() { nvidia-smi -i $G --query-gpu=memory.used --format=csv,noheader,nounits; }
stop_srv() { rm -f $R/CURRENT; bash $C/tools/teach_35b/stop.sh $1 >> $L/serve.log 2>&1; }
vla_free() {
  stop_srv $1; mkdir -p /data/harvest/out/vla
  echo "$(hostname):$G freed $(date -u +%FT%TZ)" >> /data/harvest/out/vla/GPU_FREED; log "VLA_YIELD $1 mem=$(mem)"
  while listed $VW || [ "$(mem)" -ge 1000 ]; do sleep 120; done
  log "VLA_RESUME"
}
for CK in f35d 0.5 1 1.5 2 2.5 3; do
  $P $C/tools/main35_closed/sched.py done $CK && { log "SKIP_DONE $CK"; continue; }
  if [ $CK = f35d ]; then M=/data/harvest/out/final35/merged_d; else M=$R/merged_ep$CK; fi
  until [ -f $M/config.json ] && { [ $CK = f35d ] || [ -f $M/MERGE_OK ]; }; do sleep 120; done
  N=m35cl_${CK/./_}
  until $P $C/tools/main35_closed/sched.py done $CK; do
    listed $VW && { vla_free $N; continue; }
    curl -s $IP:$PORT/v1/models | grep -q $N ||       setsid nohup bash $C/tools/teach_35b/vllm.sh $G $M $N $PORT 0.88 --host 0.0.0.0 < /dev/null > /dev/null 2>&1 &
    ok=0; for i in $(seq 1 120); do
      listed $VW && break
      curl -s $IP:$PORT/v1/models | grep -q $N && { ok=1; break; }; sleep 15; done
    listed $VW && { vla_free $N; continue; }
    [ $ok = 1 ] || { log "SERVER_FAIL $CK"; stop_srv $N; exit 1; }
    echo "$CK http://$IP:$PORT $N" > $R/CURRENT; log "SERVING $CK $M"
    until $P $C/tools/main35_closed/sched.py done $CK; do
      listed $VW && break
      if listed /data/harvest/out/l9/GPU_WANTED && ! lanes_alive; then stop_srv $N; log "L9_STOP $CK"; exit 0; fi
      sleep 30
    done
    listed $VW && vla_free $N
  done
  stop_srv $N
  $P $C/tools/main35_closed/sched.py summary > /dev/null 2>>$L/serve.log
  log "CKPT_DONE $CK"
  [ $CK != f35d ] && rm -rf $M
done
log "ALL_DONE"

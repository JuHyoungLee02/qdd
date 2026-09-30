#!/bin/bash
# E-M35CL model server (x3 GPU 0, non-render): per checkpoint in order f35d 0.5 1 1.5 2 2.5 3 -> wait for its merged
# BF16 weights, vLLM (tools/teach_35b/vllm.sh, bound to the pod IP), write <root>/CURRENT "<ckpt> <url> <name>", keep
# it until sched done <ckpt>, then stop and remove main35_closed/merged_ep<e> (f35_d's merged_d is never removed).
# Also stops (and exits) when GPU_WANTED exists and no lane has been alive for 10 min.
# usage: serve.sh <code dir> <gpu> <port>
C=$1; G=$2; PORT=$3
R=/data/harvest/out/main35_closed; L=/data/harvest/logs/main35_closed; P=/data/harvest/venv_train/bin/python
mkdir -p $L; IP=$(hostname -i | awk '{print $1}')
log() { echo "$(date -u +%FT%TZ) serve $*" >> $L/serve.log; }
lanes_alive() { find $R/lanes -name '*.alive' -mmin -10 2>/dev/null | grep -q .; }
for CK in f35d 0.5 1 1.5 2 2.5 3; do
  $P $C/tools/main35_closed/sched.py done $CK && { log "SKIP_DONE $CK"; continue; }
  if [ $CK = f35d ]; then M=/data/harvest/out/final35/merged_d; else M=$R/merged_ep$CK; fi
  until [ -f $M/config.json ] && { [ $CK = f35d ] || [ -f $M/MERGE_OK ]; }; do sleep 120; done
  N=m35cl_${CK/./_}
  setsid nohup bash $C/tools/teach_35b/vllm.sh $G $M $N $PORT 0.88 --host 0.0.0.0 < /dev/null > /dev/null 2>&1 &
  ok=0; for i in $(seq 1 120); do curl -s $IP:$PORT/v1/models | grep -q $N && { ok=1; break; }; sleep 15; done
  [ $ok = 1 ] || { log "SERVER_FAIL $CK"; bash $C/tools/teach_35b/stop.sh $N >> $L/serve.log 2>&1; exit 1; }
  echo "$CK http://$IP:$PORT $N" > $R/CURRENT; log "SERVING $CK $M"
  until $P $C/tools/main35_closed/sched.py done $CK; do
    if [ -f /data/harvest/out/l9/GPU_WANTED ] && ! lanes_alive; then
      rm -f $R/CURRENT; bash $C/tools/teach_35b/stop.sh $N >> $L/serve.log 2>&1; log "YIELD_STOP $CK"; exit 0; fi
    sleep 120
  done
  rm -f $R/CURRENT; bash $C/tools/teach_35b/stop.sh $N >> $L/serve.log 2>&1
  $P $C/tools/main35_closed/sched.py summary > /dev/null 2>>$L/serve.log
  log "CKPT_DONE $CK"
  [ $CK != f35d ] && rm -rf $M
done
log "ALL_DONE"

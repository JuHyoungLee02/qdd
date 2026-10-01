#!/bin/bash
# E-CL15d (prereg_cl15.md change 5) -- PAID (Astra): started only by the main session. One card borrow, two lanes:
#   astra  : the T1 episodes Astra has not finished (jobs_astra.txt, ep1.5 call count ascending), ledger shared with
#            cl15c, cumulative cap (default 30,000 KRW); after a budget stop the rest is left as 'not run (cap)'
#   base35 : the base35 episodes missing from cl15b (jobs_base35.txt), server = vLLM Qwen3.5-35B-A3B on 7a2a GPU2
# Two Astra lanes + one base35 lane on the card. Steps: base35 server up -> <root>/READY_FOR_LANES -> wait <root>/LANES_GO_7a2a_<gpu> -> both lanes -> the last lane
# writes <root>/DONE + GPU_FREED -> server down -> compare.py (3 arms x 10) + timing.py.
# usage: start_d.sh <code dir> [gpu=3] [cap KRW=30000]
C=$1; G=${2:-3}; CAP=${3:-30000}
R=/data/harvest/out/cl15d; LED=/data/harvest/out/cl15c/ledger.jsonl; L=/data/harvest/logs/cl15d
P=/data/harvest/venv_train/bin/python; PORT=8672; N=cl15d_base35; IP=127.0.0.1
mkdir -p $R $L
log() { echo "$(date -u +%FT%TZ) start_d $*" >> $L/lanes.log; }
if [ -s $R/jobs_base35.txt ]; then
  curl -s $IP:$PORT/v1/models | grep -q $N || setsid -f bash $C/tools/teach_35b/vllm.sh 2 /data/harvest/models/Qwen3.5-35B-A3B \
    $N $PORT 0.88 --host 0.0.0.0 > /dev/null 2>&1 < /dev/null
  for i in $(seq 1 80); do curl -s $IP:$PORT/v1/models | grep -q $N && break; sleep 15; done
  curl -s $IP:$PORT/v1/models | grep -q $N || { log "SERVER_FAIL"; echo "base35 server failed" > $R/ALERT_server; }
fi
echo "astra (paid, cap $CAP KRW incl. cl15c) + base35 on 7a2a GPU$G, waiting $(date -u +%FT%TZ)" > $R/READY_FOR_LANES
log "READY gpu=$G cap=$CAP"
until [ -f $R/LANES_GO_7a2a_$G ] || [ -f $R/STOP ]; do sleep 20; done
[ -f $R/STOP ] && { log "STOP before start"; bash $C/tools/teach_35b/stop.sh $N >> $L/lanes.log 2>&1; exit 0; }
if [ -s $R/jobs_base35.txt ] && [ ! -f $R/ALERT_server ]; then
  CL15_ROOT=$R CL15_VID=/data/harvest/videos/cl15/base35 CL15_CKPT=base35 CL15_JOBS=$R/jobs_base35.txt \
    setsid -f bash $C/tools/cl15/lane.sh $C $G g${G}_base35 http://$IP:$PORT $N > /dev/null 2>&1 < /dev/null
fi
sleep 5
for k in 1 2; do  # two Astra lanes (claims split the list; the ledger cap covers calls in flight)
  CL15_ROOT=$R CL15_VID=/data/harvest/videos/cl15/astra CL15_CKPT=astra CL15_JOBS=$R/jobs_astra.txt \
    CL15_EXTRA="--astra low --ledger $LED --cap-krw $CAP" setsid -f bash $C/tools/cl15/lane.sh $C $G g${G}_astra$k \
    http://none none > /dev/null 2>&1 < /dev/null
  sleep 5
done
until [ -f $R/DONE ]; do sleep 30; done
bash $C/tools/teach_35b/stop.sh $N >> $L/lanes.log 2>&1
$P $C/tools/cl15/compare.py >> $L/lanes.log 2>&1
$P $C/tools/cl15/timing.py >> $L/lanes.log 2>&1
log "ALL_DONE cum_krw=$($P -c "import json;print(round(sum(json.loads(x)['cost_krw'] for x in open('$LED')),1))" 2>/dev/null)"

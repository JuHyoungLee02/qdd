#!/bin/bash
# E-CL15c Astra arm (prereg_cl15.md change 3) -- PAID: started only by the main session. One command does all:
#  1. READY_FOR_LANES in <root>, wait for the L9 owner's <root>/LANES_GO_7a2a_<gpu>
#  2. Isaac dry run on that card with the stub transport (no network, no cost; 3 calls, separate root cl15c_stub)
#     -> must end with EXIT 0 and a result.json, else <root>/ALERT_stub and the card is returned (DONE)
#  3. one lane (lane.sh, episodes in jobs.txt order) with --astra low, ledger <root>/ledger.jsonl, cap 10,000 KRW
#  4. the lane writes summary + DONE + GPU_FREED; then timing.py (three-arm time / cost table)
# usage: start_c.sh <code dir> [gpu=3] [effort=low] [cap KRW=10000] [root=/data/harvest/out/cl15c] [ledger=<root>/ledger.jsonl] [stub=1]
C=$1; G=${2:-3}; EF=${3:-low}; CAP=${4:-10000}; R=${5:-/data/harvest/out/cl15c}; LED=${6:-$R/ledger.jsonl}; STUB=${7:-1}
S=${R}_stub; L=/data/harvest/logs/$(basename $R); P=/data/harvest/venv_train/bin/python
mkdir -p $R $S $L
log() { echo "$(date -u +%FT%TZ) start_c $*" >> $L/lanes.log; }
echo "astra arm (paid, cap $CAP KRW) on 7a2a GPU$G, waiting $(date -u +%FT%TZ)" > $R/READY_FOR_LANES
log "READY gpu=$G effort=$EF cap=$CAP"
until [ -f $R/LANES_GO_7a2a_$G ] || [ -f $R/STOP ]; do sleep 20; done
[ -f $R/STOP ] && { log "STOP before start"; exit 0; }
# 2. stub dry run (first job's episode)
if [ "$STUB" = 1 ]; then
IFS=$'\t' read -r GID JOB < <(head -1 $R/jobs.txt)
cp $R/eps_$GID.json $S/
log "STUB $GID"
bash $C/tools/teach_strip8/isaac.sh $C $G $(basename $S) harvest.cl15.run_t1 --job "$JOB" --episodes $S/eps_$GID.json \
  --conds none --ckpt astra_stub --qwen-url http://stub --qwen-name stub --out $S/res --vid-root $S/vid \
  --yield-files $S/STOP --owner stub --loop-break --stall-n 3 --stop-calls 3 \
  --astra $EF --astra-stub --ledger $S/ledger.jsonl --cap-krw $CAP < /dev/null
if ! tail -1 /data/harvest/logs/strip8/$(basename $S).log | grep -q "EXIT 0" || [ -z "$(find $S/res -name result.json)" ]; then
  log "STUB_FAIL"; echo "stub dry run failed, see /data/harvest/logs/strip8/$(basename $S).log" > $R/ALERT_stub
  touch $R/DONE; echo "$(hostname):$G returned by $(basename $R | tr a-z A-Z) (stub fail) $(date -u +%FT%TZ)" >> /data/harvest/out/l9/GPU_FREED
  exit 1
fi
log "STUB_OK $(find $S/res -name result.json | head -1)"
fi
# 3. the paid lane (one lane: the budget gate sees each finished episode before the next starts)
CL15_ROOT=$R CL15_VID=/data/harvest/videos/cl15/astra CL15_CKPT=astra \
  CL15_EXTRA="--astra $EF --ledger $LED --cap-krw $CAP" \
  bash $C/tools/cl15/lane.sh $C $G g${G}_astra http://none none
$P $C/tools/cl15/timing.py >> $L/lanes.log 2>&1
log "ALL_DONE cum_krw=$($P -c "import json;print(round(sum(json.loads(x)['cost_krw'] for x in open('$LED')),1))" 2>/dev/null)"

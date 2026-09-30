#!/bin/bash
# E-DEP1 stage 2 chain (prereg_deploy1.md §2 + change 1) on x2: vLLM (main35 ep1.5, util 0.55, GPU0, shared with the
# coming JCR1 training) + render lanes on GPU1 (shared with d1).
#  lanes: one Isaac process per variant (standard / dr), all arms over DEV seeds 0-19, restarted until RUN_DONE.
#  yield (per card, user 10-01): L9 GPU_WANTED naming x2:1 (or empty / all) -> lanes stop after the running episode;
#  the JCR chain handing x2:1 back ("returned to L9" in chain_events.log) -> lanes stop for good (never block it).
#  d1 guard: 30 min after start and every 30 min, if the d1 rate fell > 15 % below D1_REF (361/h) -> keep one lane.
# progress lines -> /data/harvest/out/jcr/chain_events.log ("| DEP |"); results -> $OUT/summary_cl.json
# usage: nohup bash cl_chain.sh <code dir> > /dev/null 2>&1 &
C=$1
Q=/data/harvest; OUT=$Q/out/deploy/cl1; VID=$Q/videos/deploy_cl1; CE=$Q/out/jcr/chain_events.log; W=$Q/out/l9/GPU_WANTED
M35C=/data/harvest/code_main35q_a5a915f; N=q35_dep15; PORT=8672; ARMS=S0,S1,S2x0.5,S2x1.0,S2x1.5; D1_REF=361
mkdir -p $OUT/lanes $VID
ev() { echo "$(TZ=Asia/Seoul date '+%F %H:%M') KST | DEP | $*" >> $CE; }
wanted_me() { [ -f $W ] || return 1; [ -s $W ] || return 0; grep -qiE "(^|[^a-z0-9-])((7a2a-)?x2:1|all)([^0-9]|$)" $W; }
returned() { grep -q "returned to L9" $CE 2>/dev/null; }
d1_rate() { local n0 n1; n1=$(ls $Q/out/jcr/d1/*/s*/ep.json | wc -l); n0=$(find $Q/out/jcr/d1 -maxdepth 3 -name ep.json -mmin +60 | wc -l); echo $((n1 - n0)); }
curl -sf localhost:$PORT/v1/models > /dev/null || { bash $M35C/tools/teach_35b/vllm.sh 0 $Q/out/deploy/merged_ep1.5 $N $PORT 0.55 & 
  for i in $(seq 90); do curl -sf localhost:$PORT/v1/models > /dev/null && break; sleep 10; done; }
lane() {  # lane <variant>
  local V=$1 L=cl_$1
  while true; do
    { wanted_me || returned; } && { rm -f $OUT/lanes/$L.alive; return; }
    touch $OUT/lanes/$L.alive
    bash $C/tools/teach_strip8/isaac.sh $C 1 dep_$L harvest.deploy.runner --arms $ARMS --variant $V --seeds 0-19 \
      --url http://127.0.0.1:$PORT --name $N --out $OUT --vid-root $VID --yield-files $OUT/lanes/$L.STOP --owner $L &
    local ip=$!
    while kill -0 $ip 2>/dev/null; do
      { wanted_me || returned || [ -f $OUT/lanes/$L.DROP ]; } && touch $OUT/lanes/$L.STOP
      sleep 20
    done
    rm -f $OUT/lanes/$L.STOP
    tail -3 $Q/logs/strip8/dep_$L.log | grep -q RUN_DONE && { rm -f $OUT/lanes/$L.alive; return; }
    [ -f $OUT/lanes/$L.DROP ] && { rm -f $OUT/lanes/$L.alive; return; }
    sleep 30
  done
}
ev "stage 2 start: vLLM $N (ep1.5, x2 GPU0 util 0.55), lanes standard+dr on x2 GPU1, arms $ARMS, code $C"
lane standard & la=$!
lane dr & lb=$!
t_chk=$(( $(date +%s) + 1800 ))
while kill -0 $la 2>/dev/null || kill -0 $lb 2>/dev/null; do
  if [ $(date +%s) -ge $t_chk ]; then
    r=$(d1_rate); t_chk=$(( $(date +%s) + 1800 ))
    n=$(ls $OUT/*/*/s*/ep.json 2>/dev/null | wc -l)
    if [ ! -f $Q/out/jcr/chain_d1.DONE ] && ! returned && [ $r -lt $(( D1_REF * 85 / 100 )) ] && [ ! -f $OUT/lanes/cl_dr.DROP ]; then
      touch $OUT/lanes/cl_dr.DROP; ev "d1 rate ${r}/h < 85 % of ${D1_REF}/h -> stage 2 down to 1 lane (${n}/200 eps)"
    else ev "stage 2 progress ${n}/200 eps, d1 rate ${r}/h"; fi
  fi
  sleep 60
done
# the dropped lane's arms continue on the remaining lane when it is rerun; finish what exists
PYTHONPATH=$C $Q/venv_train/bin/python $C/tools/deploy/cl_summary.py --out $OUT >> $Q/logs/deploy/cl_summary.log 2>&1
ev "stage 2 lanes ended ($(ls $OUT/*/*/s*/ep.json 2>/dev/null | wc -l)/200 eps): $(tail -1 $Q/logs/deploy/cl_summary.log | cut -c1-400)"
if ! returned && [ $(ls $OUT/*/*/s*/ep.json 2>/dev/null | wc -l) -lt 200 ] && [ -f $OUT/lanes/cl_dr.DROP ]; then
  rm -f $OUT/lanes/cl_dr.DROP; lane dr; PYTHONPATH=$C $Q/venv_train/bin/python $C/tools/deploy/cl_summary.py --out $OUT >> $Q/logs/deploy/cl_summary.log 2>&1
  ev "stage 2 dr lane finished: $(tail -1 $Q/logs/deploy/cl_summary.log | cut -c1-400)"
fi
bash $M35C/tools/teach_35b/stop.sh $N > /dev/null 2>&1; ev "vLLM $N stopped (x2 GPU0 free for JCR1)"
touch $OUT/DONE

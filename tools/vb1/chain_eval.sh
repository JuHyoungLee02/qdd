#!/bin/bash
# E-VB1 closed-loop chain on 78dc (docs/stage3/prereg_vb1.md change 1). The policy server runs on a free 78dc GPU
# (not a render card); the Isaac lanes (eval_lane.sh) on the render cards read <eval>/SERVER and connect over the pod
# network.
#  0. evalq.py build (work list; E-M35CL groups digest recorded)
#  1. pipeline check: after the 20-step smoke training, serve smoke_vb1 and run 'evsmoke' (2 episodes); at most 60 min
#     (render cards may be busy), then the server is stopped either way so the full training is not delayed
#  2. after TRAIN_DONE: checkpoint selection on 'sel60' for 20k, 25k, 30k (one server at a time) -> best = highest
#     success, ties -> later step
#  3. final sets 'ood_o58,l8s_val' with the best checkpoint -> <eval>/summary.json + EVAL_DONE
# usage (78dc): nohup bash chain_eval.sh <code dir> > /dev/null 2>&1 &
C=$1
Q=/data/harvest; R=$Q/out/vb1; E=$R/eval; L=$Q/logs/vb1; PV=$Q/venv_train/bin/python; PG=/data/GARO_pi/lerobot/.venv/bin/python
PORT=8161; IP=$(hostname -i | awk '{print $1}')
mkdir -p $E $L
ev() { echo "$(TZ=Asia/Seoul date '+%F %H:%M') KST | VB1 | $*" >> $R/events.log; }
q() { CODE=$C PYTHONPATH=$C $PV -m tools.vb1.evalq "$@"; }
free_gpu() { nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits | awk -F', ' '$2 < 1000 {print $1; exit}'; }
SPID=""
serve() {  # serve <ckpt tag> <model path> <sets>
  local g=""; until [ -n "$g" ]; do g=$(free_gpu); [ -z "$g" ] && sleep 300; done
  export HF_HUB_OFFLINE=1 HF_HOME=/data/juhyoung_pi05/.hf_cache TMPDIR=$Q/tmp XDG_CACHE_HOME=$Q/cache
  CUDA_VISIBLE_DEVICES=$g setsid nohup $PG $C/tools/vb1/server.py --model-path $2 --ckpt $1 --port $PORT \
    > $L/server_$1.log 2>&1 < /dev/null &
  SPID=$!
  for i in $(seq 90); do grep -q READY $L/server_$1.log && break; kill -0 $SPID 2> /dev/null || break; sleep 10; done
  grep -q READY $L/server_$1.log || { ev "ALERT server $1 did not start ($L/server_$1.log)"; echo "server $1" > $R/ALERT_server; return 1; }
  echo "http://$IP:$PORT $1 $3" > $E/SERVER
  ev "server $1 on 78dc GPU $g, sets $3"
}
unserve() { rm -f $E/SERVER; [ -n "$SPID" ] && kill $SPID 2> /dev/null; sleep 20; SPID=""; }
waitdone() {  # waitdone <max minutes or 0>
  local t=0; until q done; do sleep 300; t=$((t + 5)); [ "$1" != 0 ] && [ $t -ge $1 ] && return 1; done; return 0
}
ev "chain_eval start code=$C"
(cd $C && q build) >> $L/evalq_build.log 2>&1 || { ev "ALERT evalq build failed"; exit 1; }
ev "eval work list: $(tail -1 $L/evalq_build.log)"
# 1. pipeline check with the smoke checkpoint
until grep -q "train end .* rc=0" $L/train_smoke.log 2> /dev/null || [ -f $R/TRAIN_DONE ]; do sleep 300; done
SM=$(ls -d $R/train/smoke_vb1/checkpoints/*/pretrained_model 2> /dev/null | tail -1)
if [ -n "$SM" ] && [ ! -f $R/TRAIN_DONE ] && serve smoke $SM evsmoke; then
  if waitdone 60; then ev "eval smoke done: $(q summary smoke)"; else ev "eval smoke not finished in 60 min (render cards busy?): $(q summary smoke)"; fi
  unserve
fi
# 2. checkpoint selection
until [ -f $R/TRAIN_DONE ]; do sleep 600; done
best=""; bs=-1
for ck in 020000 025000 030000; do
  M=$R/train/vb1_pi05/checkpoints/$ck/pretrained_model
  [ -d $M ] || { ev "checkpoint $ck missing"; continue; }
  serve $ck $M sel60 || exit 1
  waitdone 0
  s=$(q summary $ck); unserve
  n=$(q succ $ck sel60)
  ev "selection $ck: $s"
  [ "$n" -ge "$bs" ] && { bs=$n; best=$ck; }
done
[ -n "$best" ] || { ev "ALERT no checkpoint evaluated"; exit 1; }
echo "$best" > $E/BEST
ev "best checkpoint $best (sel60 success $bs)"
# 3. final sets
serve $best $R/train/vb1_pi05/checkpoints/$best/pretrained_model ood_o58,l8s_val || exit 1
waitdone 0
q summary $best > $E/summary.json; unserve
touch $E/EVAL_DONE
ev "EVAL_DONE best=$best $(cat $E/summary.json)"

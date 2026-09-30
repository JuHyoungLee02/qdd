#!/bin/bash
# JCR1-0 chain (prereg_jcr1.md change 3; user "고" 10-01): d1 data -> change-3 relabel -> D0 gate -> sweep stage 1
# (CPU) + training JCR1-0A (label A) and JCR1-0P (label P = the model of rules B and C) on x2 GPU0.
#  1. while d1 has < N_EP episodes: when /data/harvest/out/l9/GPU_WANTED is absent and no JCR lane is alive, (re)start
#     the 4 render lanes on x2 GPU1 (they yield to L9 by themselves). Waits as long as L9 holds the render cards.
#  2. relabel (tools/jcr/relabel.py), gate (tools/jcr/data_gate.py): limits + G-br + normal share, all automatic
#     (the contact frame sheet is written for audit). Gate FAIL -> $R/ALERT_chain_d1 and stop.
#  3. sweep stage 1 in the background (nice, CPU), trainings A and P concurrently on GPU0 (the COUPLE C1 server stays),
#     offline eval included (train.py). DONE marker $R/chain_d1.DONE.
# Every milestone -> $R/chain_events.log ("<KST> | JCR | ..." lines to copy into the board events.log).
# usage (x2 pod): nohup bash tools/jcr/chain_d1.sh <code dir> > /dev/null 2>&1 &    stop: JCR_JOB=chain_d1 (stop.sh)
C=$1
Q=/data/harvest; R=$Q/out/jcr; D=$R/d1; V=$Q/videos/jcr_d1; P=$Q/venv_train/bin/python
N_EP=${N_EP:-2000}; W=$Q/out/l9/GPU_WANTED; POD=$(hostname)
export JCR_JOB=chain_d1
mkdir -p $R/lanes $Q/logs/jcr
ev() { echo "$(TZ=Asia/Seoul date '+%F %H:%M') KST | JCR | $*" >> $R/chain_events.log; }
wanted_me() { [ -f $W ] || return 1; [ -s $W ] || return 0; grep -qiE "(^|[^a-z0-9-])((7a2a-)?x2:1|all)([^0-9]|$)" $W; }
n_ep() { ls $D/*/s*/ep.json 2>/dev/null | wc -l; }
alive() { ls $R/lanes/${POD}_g1_*.alive 2>/dev/null | wc -l; }
eta() {  # finish estimate from the episodes of the last hour
  local n1 n0; n1=$(n_ep); n0=$(find $D -maxdepth 3 -name ep.json -mmin +60 2>/dev/null | wc -l)
  local r=$((n1 - n0)); [ $r -le 0 ] && { echo "ETA n/a"; return; }
  echo "rate ${r}/h, ETA $(TZ=Asia/Seoul date -d "+$(( (N_EP - n1) * 60 / r )) min" '+%m-%d %H:%M') KST"; }
ev "chain start code=$C d1=$(n_ep)/$N_EP"
last=-1
while [ "$(n_ep)" -lt "$N_EP" ]; do
  if ! wanted_me && [ "$(alive)" = 0 ]; then
    rm -f $R/lanes/${POD}_g1_*.WANTED
    for x in "h standard 11000-11999" "i dr 21000-21999" "j standard 11000-11999" "k dr 21000-21999"; do
      set -- $x; nohup bash $C/tools/jcr/lane.sh $C 1 ${POD}_g1_$1 $2 $3 $D $V 0.75 > /dev/null 2>&1 &
    done
    ev "d1 lanes (re)started at $(n_ep) eps"
    sleep 120
  fi
  n=$(n_ep); [ $((n / 100)) != $((last / 100)) ] && { ev "d1 progress $n/$N_EP (x2:1 wanted by L9=$(wanted_me && echo yes || echo no), $(eta))"; last=$n; }
  # all seeds claimed and lanes finished but short of N_EP (errors): proceed with what exists
  [ "$(alive)" = 0 ] && ! wanted_me && grep -q "LANE_DONE" $Q/logs/jcr/lanes.log && \
    [ "$(grep -c "_g1_[hijk] LANE_DONE" $Q/logs/jcr/lanes.log)" -ge 4 ] && { ev "d1 lanes done at $(n_ep) eps"; break; }
  sleep 300
done
cd $C
ev "d1 complete: $(n_ep) eps -> relabel"
PYTHONPATH=$C $P tools/jcr/relabel.py --data $D >> $Q/logs/jcr/chain_d1.log 2>&1 || { echo relabel > $R/ALERT_chain_d1; ev "ALERT relabel failed"; exit 1; }
PYTHONPATH=$C $P tools/jcr/data_gate.py --data $D --out $R/d1_gate >> $Q/logs/jcr/chain_d1.log 2>&1
ok=$($P -c "import json;g=json.load(open('$R/d1_gate/gate.json'))['gate'];print(int(all(g.values())))" 2>/dev/null)
if [ "$ok" != 1 ]; then
  cp $R/d1_gate/gate.json $R/ALERT_chain_d1; ev "ALERT D0 gate FAIL ($(cat $R/d1_gate/gate.json | tr -d '\n ' | cut -c1-300)) -> stopped, no training"; exit 1
fi
ev "D0 gate PASS ($(tr -d '\n ' < $R/d1_gate/gate.json | grep -o '"gbr_mm":{[^}]*}'))"
PYTHONPATH=$C nice -n 19 $P tools/jcr/rule_sweep.py --data $D --out $R/sweep1 --n 300 --procs 6 >> $Q/logs/jcr/sweep1.log 2>&1 &
sp=$!
for L in A P; do
  env=$([ $L = A ] && echo A || echo B)  # label P = envelope B / C (same model, different runtime composition)
  bash $C/tools/jcr/train.sh $C 0 jcr1_0$L tools/jcr/train.py train --data $D --out $Q/ckpt/jcr/jcr1_0$L \
    --steps 4000 --batch 8 --K 2 --lr 2e-4 --lr-heads 5e-4 --envelope $env --max-val 400 --save-every 1000 &
  eval "tp_$L=\$!"
done
ev "training started on x2 GPU0: JCR1-0A (label A) + JCR1-0P (label P = rules B/C), sweep stage 1 (CPU) pid $sp"
wait $tp_A; ev "JCR1-0A done: $(grep -h '^OFFLINE' $Q/logs/jcr/jcr1_0A.log | tail -1 | cut -c1-300)"
wait $tp_P; ev "JCR1-0P done: $(grep -h '^OFFLINE' $Q/logs/jcr/jcr1_0P.log | tail -1 | cut -c1-300)"
wait $sp; ev "sweep1 done: $(tail -1 $Q/logs/jcr/sweep1.log | cut -c1-400)"
touch $R/chain_d1.DONE

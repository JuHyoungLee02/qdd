#!/bin/bash
# E-JV1 evaluation chain (docs/stage3/prereg_jv1.md §4, §8), run on the x2 pod (servers on x2 GPU0, no rendering).
#  1. waits for arm B (out/jv1/TRAIN_B_DONE) and JCR1-0P (ckpt/jcr/jcr1_0P/last)
#  2. servers on x2 GPU0: arm A = JCR1-0P x 2 replicas (:8181-8182), arm B x 4 (:8171-8174)  [JCR_JOB=jv1_srv_*]
#  3. latency bench (idle replicas, n = 100 each) -> eval/lat_A.json, lat_B.json -> the condition-R constants
#  4. destination sensitivity A / B / C (n = 100, kinematic, no render) -> eval/sens_*.json
#  5. writes eval/SERVERS.json + eval/jobs.txt (arms x conditions x sets x variants) and waits: lanes need render cards
#     the USER approves (main writes the approval); start them with tools/jv1/start_lanes.sh on that pod
#  6. when all 400 episodes have ep.json (or eval/STOP_EVAL): servers down, summary -> eval/summary.json
# usage: JCR_JOB=jv1_chain_eval nohup bash chain_eval.sh <code dir> &
C=$1; Q=/data/harvest; O=$Q/out/jv1; E=$O/eval; P=$Q/venv_train/bin/python; SEL=$Q/out/jcr/d1_select.json
CK_A=$Q/ckpt/jcr/jcr1_0P/last; CK_B=$Q/ckpt/jv1/b_P/last
ev() { echo "$(TZ=Asia/Seoul date '+%F %H:%M') KST | JV1 | $*" >> $O/events.log; }
mkdir -p $E
ev "chain_eval armed (code $C)"
until [ -f $O/TRAIN_B_DONE ] && [ -f $CK_A/heads.pt ]; do [ -f $E/STOP_EVAL ] && exit 0; sleep 120; done
cd $C
for p in 8181 8182; do bash tools/jcr/train.sh $C 0 jv1_srv_A$p -m harvest.jcr.serve --ckpt $CK_A --port $p & done
for p in 8171 8172 8173 8174; do bash tools/jcr/train.sh $C 0 jv1_srv_B$p -m harvest.jv1.serve --ckpt $CK_B --port $p & done
for p in 8181 8182 8171 8172 8173 8174; do
  for i in $(seq 90); do curl -s localhost:$p/health >/dev/null && break; sleep 10; done
done
IP=$(hostname -i | awk '{print $1}')
echo "{\"A\": [\"http://$IP:8181\", \"http://$IP:8182\"], \"B\": [\"http://$IP:8171\", \"http://$IP:8172\", \"http://$IP:8173\", \"http://$IP:8174\"]}" > $E/SERVERS.json
ev "servers up on x2 GPU0 ($IP): A x2, B x2+2"
for a in A B; do port=$([ $a = A ] && echo 8181 || echo 8171)
  PYTHONPATH=$C $P tools/jv1/bench_latency.py --url http://127.0.0.1:$port --data $Q/out/jcr/d1 --select $SEL --n 100 \
    --out $E/lat_$a.json >> $Q/logs/jcr/jv1_eval.log 2>&1
done
ev "latency A: $(cut -c1-200 < $E/lat_A.json | tr -d '\n ') | B: $(cut -c1-200 < $E/lat_B.json | tr -d '\n ')"
PYTHONPATH=$C $P tools/jv1/sens.py --url http://127.0.0.1:8182 --data $Q/out/jcr/d1 --select $SEL --n 100 --out $E/sens_A.json >> $Q/logs/jcr/jv1_eval.log 2>&1 &
PYTHONPATH=$C $P tools/jv1/sens.py --url http://127.0.0.1:8172 --data $Q/out/jcr/d1 --select $SEL --n 100 --out $E/sens_B.json >> $Q/logs/jcr/jv1_eval.log 2>&1 &
PYTHONPATH=$C $P tools/jv1/sens.py --url truth --data $Q/out/jcr/d1 --select $SEL --n 100 --out $E/sens_C.json >> $Q/logs/jcr/jv1_eval.log 2>&1 &
wait $(jobs -p | tail -3)
ev "sensitivity: $(for a in A B C; do echo -n "$a $(grep -o '"sens_mean": [0-9.-]*' $E/sens_$a.json) "; done)"
LA=$($P -c "import json;print(json.load(open('$E/lat_A.json'))['lat_s'])"); PA=$($P -c "import json;print(json.load(open('$E/lat_A.json'))['period_dec'])")
LB=$($P -c "import json;print(json.load(open('$E/lat_B.json'))['lat_s'])"); PB=$($P -c "import json;print(json.load(open('$E/lat_B.json'))['period_dec'])")
{ echo "# name variant executor arm rt_lat rt_period disturbed  (fixed by chain_eval.sh before any episode)"
  for set in clean dist; do d=$([ $set = dist ] && echo 1 || echo 0)
    for v in standard dr; do
      echo "A_Z_$set $v jcr A - 1 $d"; echo "B_Z_$set $v jcr B - 1 $d"; echo "C_Z_$set $v jv1c - - 1 $d"
      echo "A_R_$set $v jcr A $LA $PA $d"; echo "B_R_$set $v jcr B $LB $PB $d"
    done
  done; } > $E/jobs.txt
touch $E/READY_FOR_LANES
ev "READY_FOR_LANES: jobs.txt 20 jobs x 20 episodes (A R: lat $LA s / every $PA dec, B R: lat $LB s / every $PB dec). Render cards need user approval -> bash $C/tools/jv1/start_lanes.sh $C <gpu> <n lanes> on that pod"
until [ "$(ls $E/*/*/s*/ep.json 2>/dev/null | wc -l)" -ge 400 ] || [ -f $E/STOP_EVAL ]; do sleep 300; done
for p in 8181 8182 8171 8172 8173 8174; do bash tools/jcr/stop.sh jv1_srv_$([ $p -gt 8180 ] && echo A || echo B)$p >> $Q/logs/jcr/jv1_eval.log 2>&1; done
PYTHONPATH=$C $P tools/jv1/summary.py --eval $E --out $E/summary.json >> $Q/logs/jcr/jv1_eval.log 2>&1
ev "eval done: $(grep -o '"verdict": *"[A-Z_]*"' $E/summary.json) -> $E/summary.json"

#!/bin/bash
# E-PT after one arm's training (prereg_pt.md §4-§5.3): serve the merged model, evaluate DEV + OOD-H offline, then
# (DEV gate passed) closed loop OOD-H s0 / s1 x table 0.82 / 0.88 with that arm's interface. Waits for the merge.
# usage: post_arm.sh <code dir> <arm> <serve gpu> <port> <isaac gpu>
C=$1; A=$2; G=$3; PORT=$4; IG=$5
N=pt8_${A//-/_}
M=/data/harvest/out/teach_pt/merged_$A
L=/data/harvest/logs/teach_pt
until grep -q "TRAIN_ARM_DONE $A " $L/lanes.log 2>/dev/null; do sleep 30; done
[ -f $M/config.json ] || { echo "POST_ARM_NO_MODEL $A" >> $L/lanes.log; exit 1; }
setsid nohup bash $C/tools/teach_pt/vllm.sh $G $M $N $PORT 0.35 < /dev/null > /dev/null 2>&1 &
for i in $(seq 1 90); do curl -s 127.0.0.1:$PORT/v1/models | grep -q $N && break; sleep 10; done
bash $C/tools/teach_pt/eval_arm.sh $C $A $N $PORT $N
if /data/harvest/venv_train/bin/python $C/tools/teach_pt/gate.py /data/harvest/out/teach_pt/eval/dev_$N/summary.json >> $L/gate_$N.log; then
  for z in 0.82 0.88 0.78 0.92; do
    bash $C/tools/teach_pt/isaac.sh $C $IG cl_${N}_tz$z harvest.teach_pt.run_closed --iface $A --model qwen8b \
      --qwen-url http://127.0.0.1:$PORT --qwen-name $N --table-z $z --seeds 0,1 --out /data/harvest/out/teach_pt/closed_f2 --arm $N
  done
fi
echo "POST_ARM_DONE $A $(date -u +%FT%TZ)" >> $L/lanes.log

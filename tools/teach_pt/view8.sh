#!/bin/bash
# E-VIEW8 driver (prereg_view8.md).
#   prep                     : build train_A0/A1/A2 (view8_build.py main), gsplit check, write the job queue
#   worker <gpu> <port> [marker file] : wait until the marker line exists (if given), then pop jobs "<arm> <seed>" from
#                              the queue and run each: train (--save-every 200, resume), merge, vLLM, G eval, L8-X eval
#   judge                    : A1 vs A0, A2 vs A1 (and A3 vs A1 when its evals exist)
# usage: view8.sh <code dir> prep | worker <gpu> <port> [marker] | judge
C=$1; CMD=$2
O=/data/harvest/out/view8; L=/data/harvest/logs/view8; P=/data/harvest/venv_train/bin/python
OP=/data/harvest/out/opratio
Q=${V8_QUEUE:-$O/queue.txt}  # V8_QUEUE: a per-worker job file (7a2a spill-over)
mkdir -p $O $L
cd $C; export PYTHONPATH=$C
if [ "$CMD" = prep ]; then
  rm -f $O/steps.txt
  $P tools/teach_pt/view8_build.py main $O $OP/base_d-min.jsonl > $L/prep.log 2>&1
  PYTHONPATH=$C/tools $P -m xemb.gsplit check $O/train_A0.jsonl $O/train_A1.jsonl $O/train_A2.jsonl >> $L/prep.log 2>&1 \
    && { printf 'A0 0\nA1 0\nA0 1\nA1 1\nA2 0\nA2 1\n' > $O/queue.txt; echo "PREP_DONE $(date -u +%FT%TZ)" >> $L/view8.log; } \
    || echo "PREP_FAIL $(date -u +%FT%TZ)" >> $L/view8.log
  exit 0
fi
if [ "$CMD" = judge ]; then
  for pair in "A1 A0" "A2 A1" "A3 A1"; do
    set -- $pair
    [ -f $O/eval/${1}_s1/x_ood_hl_d-min_clean/scores.jsonl ] || continue
    $P tools/teach_pt/view8_compare.py $O/eval $OP/g_eval.jsonl /data/harvest/out/dist8/data_x $1 $2 $O/verdict_$1_vs_$2.json >> $L/judge.log 2>&1
  done
  echo "JUDGE_DONE $(date -u +%FT%TZ)" >> $L/view8.log
  exit 0
fi
# worker
G=$3; PORT=$4; MARK=$5
until grep -q PREP_DONE $L/view8.log 2>/dev/null; do grep -q PREP_FAIL $L/view8.log && exit 1; sleep 60; done
[ -n "$MARK" ] && until grep -q S1_DONE $MARK 2>/dev/null; do sleep 120; done
while true; do
  JOB=$(flock $O/queue.lock bash -c "head -n 1 $Q; sed -i 1d $Q")
  [ -z "$JOB" ] && break
  set -- $JOB; ARM=$1; SEED=$2; A=${ARM}_s$SEED
  S=$(grep "^$ARM " $O/steps.txt | tail -n 1 | cut -d' ' -f2)
  echo "START $A gpu=$G steps=$S $(date -u +%FT%TZ)" >> $L/view8.log
  RES=""; [ -d $O/run_$A/state ] && RES="--resume"
  bash $C/tools/teach_pt/py.sh train $G train_v8_$A $C harvest.teach_l8.train --data $O/train_$ARM.jsonl --out $O/run_$A \
    --epochs 3 --max-steps $S --micro 8 --accum 2 --log-every 10 --save-every 200 --seed $SEED $RES
  E=$(ls -d $O/run_$A/epoch* 2>/dev/null | sort -V | tail -1)
  [ -z "$E" ] && { echo "TRAIN_FAIL $A $(date -u +%FT%TZ)" >> $L/view8.log; continue; }
  bash $C/tools/teach_pt/py.sh train $G merge_v8_$A $C harvest.teach_l8.merge --adapter $E --out $O/merged_$A
  echo "TRAIN_DONE $A $E $(date -u +%FT%TZ)" >> $L/view8.log
  N=v8_${A}_srv
  setsid nohup bash $C/tools/teach_pt/vllm.sh $G $O/merged_$A $N $PORT 0.60 < /dev/null > /dev/null 2>&1 &
  UP=0; for i in $(seq 1 90); do curl -s 127.0.0.1:$PORT/v1/models | grep -q $N && { UP=1; break; }; sleep 10; done
  [ $UP = 0 ] && { echo "VLLM_FAIL $A $(date -u +%FT%TZ)" >> $L/view8.log; bash $C/tools/teach_pt/stop.sh $N >> $L/view8.log 2>&1; continue; }
  bash $C/tools/teach_pt/py.sh vllm - geval_v8_$A $C tools/teach_pt/geval.py --data $OP/g_eval.jsonl --url http://127.0.0.1:$PORT \
    --name $N --out $O/eval/$A/g
  for f in /data/harvest/out/dist8/data_x/x_*_d-min_clean.jsonl; do
    b=$(basename $f .jsonl)
    bash $C/tools/teach_pt/py.sh vllm - ev_v8_${A}_$b $C harvest.teach_pt.evaluate --data $f --arm pt \
      --url http://127.0.0.1:$PORT --name $N --out $O/eval/$A/$b --kinds control
  done
  bash $C/tools/teach_pt/stop.sh $N >> $L/view8.log 2>&1
  echo "EVAL_DONE $A $(date -u +%FT%TZ)" >> $L/view8.log
done
echo "WORKER_END gpu=$G $(date -u +%FT%TZ)" >> $L/view8.log

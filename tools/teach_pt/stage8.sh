#!/bin/bash
# E-STAGE8 driver (prereg_stage8.md). Every step is resumable / skipped when done, so an arm can be restarted on any pod.
#   prep                            : train_mix / train_post (stage8_build.py), gsplit check
#   arm <M|S> <seed> <gpu> <port>   : M = one mixed run (2,856 steps); S = stage 1 on the mix (1,904 steps), merge,
#                                     stage 2 = a new LoRA on the merged stage-1 model with the post file (952 steps),
#                                     merge; then vLLM + G eval + L8-X eval. Heartbeat file hb_<arm>_s<seed> every 60 s.
#   judge                           : S vs M (view8_compare.py, pooled seeds 0 / 1)
#   takeover <gpu list>             : (7a2a) after 01:00 UTC, restart every arm without EVAL_DONE whose heartbeat is
#                                     older than 10 min on the next GPU of the list; then judge
# usage: stage8.sh <code dir> prep | arm M|S <seed> <gpu> <port> | judge | takeover "<gpus>"
C=$1; CMD=$2
O=/data/harvest/out/stage8; L=/data/harvest/logs/stage8; P=/data/harvest/venv_train/bin/python
OP=/data/harvest/out/opratio; MODEL=/data/harvest/models/Qwen3-VL-8B-Instruct
mkdir -p $O $L
cd $C; export PYTHONPATH=$C
TR="--epochs 3 --micro 8 --accum 2 --log-every 10 --save-every 200 --workers 3"

train_merge() {  # <job> <data> <run dir> <steps> <seed> <gpu> <base model> <merged out>
  [ -f $8/.ok ] && return 0
  local RES=""; [ -d $3/state ] && RES="--resume"
  bash $C/tools/teach_pt/py.sh train $6 $1 $C harvest.teach_l8.train --data $2 --out $3 --model $7 --max-steps $4 \
    --seed $5 $TR $RES
  local E=$(ls -d $3/epoch* 2>/dev/null | sort -V | tail -1)
  [ -z "$E" ] && return 1
  bash $C/tools/teach_pt/py.sh train $6 merge_$1 $C harvest.teach_l8.merge --adapter $E --out $8 --model $7 && touch $8/.ok
}

if [ "$CMD" = prep ]; then
  $P tools/teach_pt/stage8_build.py $O $OP/base_d-min.jsonl > $L/prep.log 2>&1
  PYTHONPATH=$C/tools $P -m xemb.gsplit check $O/train_mix.jsonl $O/train_post.jsonl >> $L/prep.log 2>&1 \
    && echo "PREP_DONE $(date -u +%FT%TZ)" >> $L/stage8.log || echo "PREP_FAIL $(date -u +%FT%TZ)" >> $L/stage8.log
  exit 0
fi
if [ "$CMD" = judge ]; then
  $P tools/teach_pt/view8_compare.py $O/eval $OP/g_eval.jsonl /data/harvest/out/dist8/data_x S M $O/verdict_S_vs_M.json >> $L/judge.log 2>&1
  echo "JUDGE_DONE $? $(date -u +%FT%TZ)" >> $L/stage8.log
  exit 0
fi
if [ "$CMD" = takeover ]; then
  GPUS=($3)
  until [ $(date -u +%s) -ge $(date -u -d "2026-09-29T01:00:00Z" +%s) ]; do
    [ $(grep -cE "^EVAL_DONE [MS]_s[01] " $L/stage8.log) -ge 4 ] && exit 0; sleep 300; done
  n=0; TAKEN=""
  until [ $(grep -cE "^EVAL_DONE [MS]_s[01] " $L/stage8.log) -ge 4 ]; do  # re-check: 78dc2 may die later
    for A in M_s0 M_s1 S_s0 S_s1; do
      grep -q "^EVAL_DONE $A " $L/stage8.log && continue
      [[ " $TAKEN " == *" $A "* ]] && continue
      [ -f $O/hb_$A ] && [ $(( $(date +%s) - $(stat -c %Y $O/hb_$A) )) -lt 600 ] && continue
      G=${GPUS[$n]}; n=$((n + 1)); [ -z "$G" ] && continue
      TAKEN="$TAKEN $A"
      echo "TAKEOVER $A gpu=$G host=$(hostname) $(date -u +%FT%TZ)" >> $L/stage8.log
      bash $0 $C arm ${A%_s*} ${A#*_s} $G $((8560 + G)) > $L/takeover_$A.log 2>&1 &
    done
    sleep 300
  done
  bash $0 $C judge
  exit 0
fi
# arm
ARM=$3; SEED=$4; G=$5; PORT=$6; A=${ARM}_s$SEED
until grep -q PREP_DONE $L/stage8.log 2>/dev/null; do grep -q PREP_FAIL $L/stage8.log && exit 1; sleep 60; done
( while true; do touch $O/hb_$A; sleep 60; done ) & HB=$!
echo "START $A gpu=$G host=$(hostname) $(date -u +%FT%TZ)" >> $L/stage8.log
if [ $ARM = M ]; then
  train_merge st8_$A $O/train_mix.jsonl $O/run_$A 2856 $SEED $G $MODEL $O/merged_$A || { echo "FAIL $A" >> $L/stage8.log; kill $HB; exit 1; }
else
  train_merge st8_${A}_st1 $O/train_mix.jsonl $O/run_${A}_st1 1904 $SEED $G $MODEL $O/merged_${A}_st1 \
    || { echo "FAIL ${A}_st1" >> $L/stage8.log; kill $HB; exit 1; }
  echo "STAGE1_DONE $A $(date -u +%FT%TZ)" >> $L/stage8.log
  train_merge st8_${A}_st2 $O/train_post.jsonl $O/run_${A}_st2 952 $SEED $G $O/merged_${A}_st1 $O/merged_$A \
    || { echo "FAIL ${A}_st2" >> $L/stage8.log; kill $HB; exit 1; }
fi
echo "TRAIN_DONE $A $(date -u +%FT%TZ)" >> $L/stage8.log
N=st8_${A}_srv
setsid nohup bash $C/tools/teach_pt/vllm.sh $G $O/merged_$A $N $PORT 0.60 < /dev/null > /dev/null 2>&1 &
UP=0; for i in $(seq 1 90); do curl -s 127.0.0.1:$PORT/v1/models | grep -q $N && { UP=1; break; }; sleep 10; done
[ $UP = 0 ] && { echo "VLLM_FAIL $A" >> $L/stage8.log; bash $C/tools/teach_pt/stop.sh $N; kill $HB; exit 1; }
bash $C/tools/teach_pt/py.sh vllm - geval_st8_$A $C tools/teach_pt/geval.py --data $OP/g_eval.jsonl --url http://127.0.0.1:$PORT \
  --name $N --out $O/eval/$A/g
for f in /data/harvest/out/dist8/data_x/x_*_d-min_clean.jsonl; do
  b=$(basename $f .jsonl)
  bash $C/tools/teach_pt/py.sh vllm - ev_st8_${A}_$b $C harvest.teach_pt.evaluate --data $f --arm pt \
    --url http://127.0.0.1:$PORT --name $N --out $O/eval/$A/$b --kinds control
done
bash $C/tools/teach_pt/stop.sh $N >> $L/stage8.log 2>&1
kill $HB
echo "EVAL_DONE $A $(date -u +%FT%TZ)" >> $L/stage8.log

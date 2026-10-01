#!/bin/bash
# E-JV1 arm B training chain (docs/stage3/prereg_jv1.md §3, §8) on x2 GPU0 (the JCR training card, NOW.md §3).
# Waits until BOTH JCR1-0 trainings (jcr1_0A, jcr1_0P) logged TRAIN_DONE -- never shares the card with them -- then
# trains arm B (label P = the pair of JCR1-0P) for the same 4,000 steps x 8 real + K=2 branches, checkpoints every 500
# (the GPU-time-matched secondary checkpoint), offline evaluation on the same 400 val decisions.
# Stop: touch /data/harvest/out/jv1/STOP_TRAIN (before the start) or tools/jcr/stop.sh jv1_b_P.
# usage: JCR_JOB=jv1_chain_train nohup bash chain_train.sh <code dir> &
C=$1; Q=/data/harvest; O=$Q/out/jv1; L=$Q/logs/jcr
ev() { echo "$(TZ=Asia/Seoul date '+%F %H:%M') KST | JV1 | $*" >> $O/events.log; }
mkdir -p $O
ev "chain_train armed (code $C): waits for jcr1_0A + jcr1_0P TRAIN_DONE on x2 GPU0"
until grep -q TRAIN_DONE $L/jcr1_0A.log 2>/dev/null && grep -q TRAIN_DONE $L/jcr1_0P.log 2>/dev/null; do
  [ -f $O/STOP_TRAIN ] && { ev "chain_train stopped by STOP_TRAIN"; exit 0; }
  sleep 60
done
ev "JCR1-0 done -> arm B training start on x2 GPU0 (jv1_b_P)"
bash $C/tools/jcr/train.sh $C 0 jv1_b_P tools/jv1/train_b.py train --data $Q/out/jcr/d1 \
  --select $Q/out/jcr/d1_select.json --out $Q/ckpt/jv1/b_P --label P --steps 4000 --batch 8 --K 2 --lr 2e-4 \
  --mb 6 --max-val 400 --save-every 500
if grep -q TRAIN_DONE $L/jv1_b_P.log; then
  ev "arm B done: $(grep -h '^OFFLINE' $L/jv1_b_P.log | tail -1 | cut -c1-500)"
  touch $O/TRAIN_B_DONE
else
  ev "ALERT arm B training failed: $(tail -2 $L/jv1_b_P.log | cut -c1-300)"; echo fail > $O/ALERT_train
fi

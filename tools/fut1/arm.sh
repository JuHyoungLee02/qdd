#!/bin/bash
# E-FUT1 one arm on one GPU (prereg_fut1.md §4): LoRA on the merged base (1 epoch of train_<arm>.jsonl, global batch
# 24 = micro 4 x accum 6, lr 1e-4 r16 = the main35 recipe) -> shard merge (CPU) -> vLLM -> evaluation -> stop.
# Arms Z* (Z15 = main35 ep1.5, Zb = main35 best) = the base itself (no training): evaluation only.
# Evaluation sets (skipped when already scored = resumable):
#   Delta rows  mm_<variant> (held-out d1, E-DEP1 stage-1 rule) for the arm's variants + mm1 (the E-DEP1 stage-1 rows)
#   static      x_val_l8s, g_val_open, g, the 7 L8-X sets, ood_o58 (= main35_eval.sh; ni_judge needs all 7 L8-X sets)
# YIELD: a line in /data/harvest/out/{l9,vla}/GPU_WANTED listing <key>:<gpu> WITHOUT the tag FUT1 -> stop at once
# (training keeps its --save-every state; a rerun resumes), log YIELD, exit 3.
# usage: arm.sh <code dir> <key e.g. 78dc|x3> <gpu> <arm F0..F4|Z> <base merged dir> "<variants e.g. cur roll>"
C=$1; KEY=$2; G=$3; ARM=$4; BASE=$5; VARS=$6
Q=/data/harvest; F=$Q/out/fut1; D=$F/data; A=$F/arms/$ARM; L=$Q/logs/fut1
mkdir -p $A $L
PORT=$((8761 + G)); N=q35_fut1_${ARM,,}; R=$A/fut1_tr_${ARM,,}
ev() { echo "$(TZ=Asia/Seoul date '+%F %H:%M') KST | FUT1 | $ARM | $*" >> $F/events.log; }
wanted() { for w in $Q/out/l9/GPU_WANTED $Q/out/vla/GPU_WANTED; do
  [ -f $w ] && grep -v FUT1 $w | grep -oE "(^|[[:space:]])$KEY:[0-9,]+" | grep -qE "[:,]$G(,|$)" && return 0; done; return 1; }
guard() {  # $1 = job to stop on yield
  while kill -0 $2 2>/dev/null; do
    if wanted; then bash $C/tools/teach_35b/stop.sh $1 > /dev/null; ev "YIELD ($KEY:$G wanted) during $1"; exit 3; fi
    sleep 20
  done; }
wanted && { ev "YIELD before start ($KEY:$G wanted)"; exit 3; }
M=$BASE
if [[ $ARM != Z* ]]; then
  M=$F/merged/$ARM
  if [ ! -f $M/MERGE_OK ]; then
    if [ ! -f $R/epoch1/adapter_model.safetensors ]; then
      RES=""; [ -d $R/state ] && RES=--resume
      ev "train start on $KEY:$G ($(wc -l < $D/train_$ARM.jsonl) rows) $RES"
      PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True bash $C/tools/teach_35b/train.sh $C $G $D/train_$ARM.jsonl $R \
        --model $BASE --epochs 1 --micro 4 --accum 6 --save-every 100 $RES &
      guard $(basename $R) $!
      [ -f $R/epoch1/adapter_model.safetensors ] || { ev "TRAIN_FAIL (log $Q/logs/teach_35b/$(basename $R).log)"; exit 1; }
      ev "train done: $(tail -1 $R/log.jsonl | cut -c1-160)"
    fi
    bash $C/tools/teach_35b/py.sh train - fut1_merge_${ARM,,} $C harvest.teach_35b.merge --adapter $R/epoch1 \
      --out $M --model $BASE
    [ -f $M/config.json ] || { ev "MERGE_FAIL"; exit 1; }
    touch $M/MERGE_OK
  fi
fi
wanted && { ev "YIELD before serving"; exit 3; }
setsid nohup bash $C/tools/teach_35b/vllm.sh $G $M $N $PORT 0.85 < /dev/null > /dev/null 2>&1 &
for i in $(seq 120); do curl -sf 127.0.0.1:$PORT/v1/models | grep -q $N && break; wanted && break; sleep 10; done
curl -sf 127.0.0.1:$PORT/v1/models | grep -q $N || { bash $C/tools/teach_35b/stop.sh $N > /dev/null;
  wanted && { ev "YIELD while loading"; exit 3; }; ev "SERVE_FAIL"; exit 1; }
ev "serving on $KEY:$G :$PORT"
run_ev() {  # <data> <out name> <evaluator: pt|geval>
  [ -f $A/eval/$2/scores.jsonl ] && return 0
  if [ $3 = geval ]; then
    bash $C/tools/teach_35b/py.sh vllm - fut1_ev_${ARM,,}_$2 $C tools/teach_pt/geval.py --data $1 \
      --url http://127.0.0.1:$PORT --name $N --out $A/eval/$2 &
  else
    bash $C/tools/teach_35b/py.sh vllm - fut1_ev_${ARM,,}_$2 $C harvest.teach_pt.evaluate --data $1 --arm pt \
      --url http://127.0.0.1:$PORT --name $N --out $A/eval/$2 --kinds ${4:-control} --workers 8 &
  fi
  local p=$!
  while kill -0 $p 2>/dev/null; do
    if wanted; then bash $C/tools/teach_35b/stop.sh fut1_ev_${ARM,,}_$2 > /dev/null; bash $C/tools/teach_35b/stop.sh $N > /dev/null
      ev "YIELD during $2"; exit 3; fi
    sleep 20
  done; }
for v in $VARS; do run_ev $D/eval_$v.jsonl mm_$v pt; done
run_ev $Q/out/deploy/mm1/rows.jsonl mm1 pt
[ "$ARM" = F4 ] && run_ev $D/eval_aux.jsonl aux pt aux
if [[ $ARM != Z* ]]; then
  M35=$Q/out/main35/data; X=$Q/out/dist8/data_x
  run_ev $M35/x_val_l8s_d-min_clean.jsonl x_val_l8s_d-min_clean pt
  run_ev $M35/val_open.jsonl g_val_open geval
  run_ev $Q/out/opratio/g_eval.jsonl g geval
  for s in dev ood_h ood_d ood_o ood_s ood_t ood_hl; do run_ev $X/x_${s}_d-min_clean.jsonl x_${s}_d-min_clean pt; done
  run_ev $Q/out/c35/data/x_ood_o58_d-min_clean.jsonl x_ood_o58_d-min_clean pt
fi
bash $C/tools/teach_35b/stop.sh $N > /dev/null
touch $A/DONE
ev "DONE (eval $(ls $A/eval | tr '\n' ' '))"

#!/bin/bash
# Main 35B checkpoint evaluation queue (prereg_main35.md): on this pod, for each checkpoint in the fixed order
# 2 -> 1.5 -> 2.5 -> 1 -> 3, wait for its adapter, claim it (mkdir lock, so several pods can run this queue), merge
# (CPU) and run main35_eval.sh on the first listed GPU that is free (< 1000 MiB). Ends when all five are evaluated.
# usage: main35_evalq.sh <code dir> <gpu list e.g. 0 or 0,1,2,3> [wait-for-train-done 0|1] [order] [drop merged 0|1]
#   order: checkpoints to take, default "2 1.5 2.5 1 3" (the judged ones); the extra quarter-epoch queue passes
#   "0.25 0.5 0.75 1.25 1.75 2.25 2.75" with drop=1 (its 67 GB merged copies are removed after the evaluation)
C=$1; GL=$2; WAIT_TRAIN=${3:-0}; ORDER=${4:-"2 1.5 2.5 1 3"}; DROP=${5:-0}
O=/data/harvest/out/main35; R=$O/run; L=/data/harvest/logs/main35; P=/data/harvest/venv_train/bin/python
mkdir -p $L $O/claims $O/eval
log() { echo "$1 $(hostname) $(date -u +%FT%TZ)" >> $L/main35.log; }
[ "$WAIT_TRAIN" = 1 ] && until grep -q "^TRAIN_DONE" $L/main35.log 2>/dev/null; do sleep 300; done
freegpu() { for g in ${GL//,/ }; do
  [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i $g)" -lt 1000 ] && { echo $g; return; }; done; }
for e in $ORDER; do
  [ -f $O/eval/ep$e/EVAL_COMPLETE ] && continue
  until [ -f $R/epoch$e/adapter_model.safetensors ]; do sleep 300; done
  mkdir $O/claims/ep$e 2>/dev/null || continue  # another queue has it
  sleep 60  # the adapter file is written in one save; give it a minute
  M=$O/merged_ep$e
  [ -f $M/config.json ] || bash $C/tools/teach_35b/py.sh train - m35_merge_ep$e $C harvest.teach_35b.merge \
    --adapter $R/epoch$e --out $M
  [ -f $M/config.json ] || { log "MERGE_FAIL ep$e"; rmdir $O/claims/ep$e; continue; }
  g=""; until [ -n "$g" ]; do g=$(freegpu); [ -n "$g" ] || sleep 120; done
  if bash $C/tools/final35/main35_eval.sh $C $g $M m35_ep${e/./_} $((8651 + g)) $O/eval/ep$e; then
    touch $O/eval/ep$e/EVAL_COMPLETE; log "CKPT_EVAL_DONE ep$e"
    [ "$DROP" = 1 ] && rm -rf $M
  else
    log "CKPT_EVAL_FAIL ep$e"; rmdir $O/claims/ep$e
  fi
done
log "EVALQ_END"

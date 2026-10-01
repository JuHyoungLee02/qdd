#!/bin/bash
# E-HCAM8 evaluation of trained arms (prereg_hcam8 §4 (i) L8-X 7 sets + (iii) G / BEHAVIOR head pixels; (ii) the
# hold-out geometry sets are added when their renders exist: files /data/harvest/out/hcam8/data_eval/<set>.jsonl).
# Same commands as E-VIEW8 (tools/teach_pt/view8.sh worker): merged model -> vLLM on <gpu> -> geval + evaluate.
# usage: hcam8_eval.sh <code dir> <gpu> <port> <arm_seed>...   e.g. H0_s1 H0_s2     (waits for each TRAIN_DONE)
# H1 rows carry the camera line: its eval files are <set>_cam.jsonl (made by tools/l9r/hcam8_build.py), used when
# the arm name starts with H1.
C=$1; G=$2; PORT=$3; shift 3
O=/data/harvest/out/hcam8; L=/data/harvest/logs/hcam8; OP=/data/harvest/out/opratio
log() { echo "$(date -u +%FT%TZ) eval gpu$G $*" >> $L/hcam8.log; }
for A in "$@"; do
  until grep -q "TRAIN_DONE $A " $L/hcam8.log; do [ -f $O/STOP_EVAL ] && exit 0; sleep 120; done
  [ -f $O/eval/$A/EVAL_DONE ] && continue
  # card lock (shared with hcam8_worker.sh) and an empty card
  exec 9> $O/card_$G.lock; flock 9
  until [ "$(nvidia-smi -i $G --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' ')" -lt 2000 ]; do
    [ -f $O/STOP_EVAL ] && exit 0; sleep 120; done
  N=hc8_${A}_srv
  setsid nohup bash $C/tools/teach_pt/vllm.sh $G $O/merged_$A $N $PORT 0.60 < /dev/null > /dev/null 2>&1 &
  UP=0; for i in $(seq 1 90); do curl -s 127.0.0.1:$PORT/v1/models | grep -q $N && { UP=1; break; }; sleep 10; done
  [ $UP = 0 ] && { log "VLLM_FAIL $A"; bash $C/tools/teach_pt/stop.sh $N >> $L/hcam8.log 2>&1; flock -u 9; exec 9>&-; continue; }
  SUF=""; case "$A" in H1*) SUF="_cam";; esac
  G_DATA=$OP/g_eval.jsonl; [ -n "$SUF" ] && [ -f $O/data_eval/g_eval$SUF.jsonl ] && G_DATA=$O/data_eval/g_eval$SUF.jsonl
  bash $C/tools/teach_pt/py.sh vllm - geval_hc8_$A $C tools/teach_pt/geval.py --data $G_DATA --url http://127.0.0.1:$PORT \
    --name $N --out $O/eval/$A/g
  for f in /data/harvest/out/dist8/data_x/x_*_d-min_clean.jsonl $O/data_eval/l9_*.jsonl; do
    [ -f "$f" ] || continue
    case "$f" in *_cam.jsonl) continue;; esac
    b=$(basename $f .jsonl); src=$f
    [ -n "$SUF" ] && [ -f ${f%.jsonl}$SUF.jsonl ] && src=${f%.jsonl}$SUF.jsonl
    [ -f $O/eval/$A/$b/scores.jsonl ] && continue
    bash $C/tools/teach_pt/py.sh vllm - ev_hc8_${A}_$b $C harvest.teach_pt.evaluate --data $src --arm pt \
      --url http://127.0.0.1:$PORT --name $N --out $O/eval/$A/$b --kinds control
  done
  bash $C/tools/teach_pt/stop.sh $N >> $L/hcam8.log 2>&1
  mkdir -p $O/eval/$A && touch $O/eval/$A/EVAL_DONE
  log "EVAL_DONE $A"
  flock -u 9; exec 9>&-
done

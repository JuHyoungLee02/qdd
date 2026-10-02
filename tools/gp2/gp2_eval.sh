#!/bin/bash
# E-GP2 early pilot evaluation chain for one run (prereg_gp2 §5): merged models <run>_q<25 %>, <run>_q<50 %>, <run>_final
# in that order, each as soon as it exists -> vLLM on <gpu> (teach_pt/vllm.sh) -> harvest.teach_pt.evaluate on the
# held-out L9 v2 rows of the run's arm (all three models) and on the L8-X 7 sets of E-HCAM8 (final model only).
# Yields the card when /data/harvest/out/vla/GPU_WANTED names "<host tag>:<gpu>" (a line without "GP2").
# usage: gp2_eval.sh <code dir> <host tag x2|7a2a|x3> <gpu> <port> <arm a|b> <seed> [gpu mem util 0.60]
# env GP2_O / GP2_TAG as in gp2_worker.sh; GP2_EVAL_AFTER = a gp2.log line pattern to wait for before the first
# server (the earlier set's chain on the same card ends first: two 0.60 servers do not fit one card).
C=$1; HT=$2; G=$3; PORT=$4; ARM=$5; SEED=$6; U=${7:-0.60}; T=${GP2_TAG:-}
O=${GP2_O:-/data/harvest/out/gp2}; L=/data/harvest/logs/gp2; R=${ARM}_s$SEED
mkdir -p $L $O/eval
log() { echo "$(date -u +%FT%TZ) eval $HT gpu$G$T $*" >> $L/gp2.log; }
wanted() {
  [ -f /data/harvest/out/vla/GPU_WANTED ] || return 1
  while read -r tok rest; do
    case "$tok $rest" in *GP2*) continue;; esac
    [ "${tok%%:*}" = "$HT" ] || continue
    c=${tok#*:}; [ "$c" = g ] && return 0
    case ",$c," in *",$G,"*) return 0;; esac
  done < /data/harvest/out/vla/GPU_WANTED
  return 1
}
until [ -f $O/DATA_READY ]; do [ -f $O/STOP_EVAL ] && exit 0; sleep 120; done  # steps.txt is written by gp2_prep.sh
if [ -n "${GP2_EVAL_AFTER:-}" ]; then
  until grep -q -- "$GP2_EVAL_AFTER" $L/gp2.log; do [ -f $O/STOP_EVAL ] && exit 0; sleep 120; done
fi
S=$(grep "^$ARM " $O/steps.txt | tail -n 1 | cut -d' ' -f2)
[ -z "$S" ] && { log "NO_STEPS $R"; exit 1; }
for M in ${R}_q$((S / 4)) ${R}_q$((S / 2)) ${R}_final; do
  [ -f $O/eval/$M/EVAL_DONE ] && continue
  until [ -f $O/merged/$M/config.json ]; do
    [ -f $O/STOP_EVAL ] && exit 0; wanted && { log "GPU_WANTED $HT:$G, idle -> exit"; exit 0; }; sleep 120; done
  sleep 30  # merged dirs are renamed into place complete; small margin for the file system
  N=gp2${T}_${M}_srv
  setsid nohup bash $C/tools/teach_pt/vllm.sh $G $O/merged/$M $N $PORT $U < /dev/null > /dev/null 2>&1 &
  UP=0; for i in $(seq 1 90); do curl -s 127.0.0.1:$PORT/v1/models | grep -q $N && { UP=1; break; }; sleep 10; done
  [ $UP = 0 ] && { log "VLLM_FAIL $M"; bash $C/tools/teach_pt/stop.sh $N >> $L/gp2.log 2>&1; continue; }
  log "SERVE $M :$PORT"
  SETS="$O/data/l9_eval_$ARM.jsonl"
  case "$M" in *_final) SETS="$SETS $(ls /data/harvest/out/dist8/data_x/x_*_d-min_clean.jsonl)";; esac
  for f in $SETS; do
    b=$(basename $f .jsonl); [ -f $O/eval/$M/$b/summary.json ] && continue
    if wanted; then log "GPU_WANTED $HT:$G -> stop $M"; bash $C/tools/teach_pt/stop.sh $N >> $L/gp2.log 2>&1; exit 0; fi
    bash $C/tools/teach_pt/py.sh vllm - ev_gp2${T}_${M}_$b $C harvest.teach_pt.evaluate --data $f --arm pt \
      --url http://127.0.0.1:$PORT --name $N --out $O/eval/$M/$b --kinds control
  done
  bash $C/tools/teach_pt/stop.sh $N >> $L/gp2.log 2>&1
  touch $O/eval/$M/EVAL_DONE
  log "EVAL_DONE $M"
done
log "EVAL_CHAIN_END $R"

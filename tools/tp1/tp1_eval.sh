#!/bin/bash
# E-TP1 evaluation chain for one run (prereg_tp1 §3 + change 3): merged models <run>_q<25 %>, <run>_q<50 %>, <run>_final
# (tools/gp2/gp2_worker.sh outputs) -> vLLM on <gpu> -> the perspective hold-out items (all models,
# tools/tp1/tp1_persp_eval.py), and for the final model also the ego hold-out (harvest.teach_pt.evaluate), the
# directional third-person hold-out subset and the L8-X 7 sets. Waits for GP2_EVAL_AFTER (a gp2.log pattern) first.
# Yields the card when /data/harvest/out/vla/GPU_WANTED names "<host tag>:<gpu>" (a line without "GP2"/"TP1").
# usage: tp1_eval.sh <code dir> <host tag> <gpu> <port> <arm off|on|onaux> <seed> [gpu mem util 0.60]
C=$1; HT=$2; G=$3; PORT=$4; ARM=$5; SEED=$6; U=${7:-0.60}
O=/data/harvest/out/tp1; L=/data/harvest/logs/gp2; R=${ARM}_s$SEED
mkdir -p $L $O/eval
log() { echo "$(date -u +%FT%TZ) eval $HT gpu${G}_tp1 $*" >> $L/gp2.log; }
wanted() {
  [ -f /data/harvest/out/vla/GPU_WANTED ] || return 1
  while read -r tok rest; do
    case "$tok $rest" in *GP2*|*TP1*) continue;; esac
    [ "${tok%%:*}" = "$HT" ] || continue
    c=${tok#*:}; [ "$c" = g ] && return 0
    case ",$c," in *",$G,"*) return 0;; esac
  done < /data/harvest/out/vla/GPU_WANTED
  return 1
}
until [ -f $O/DATA_READY ]; do [ -f $O/STOP_EVAL ] && exit 0; sleep 120; done
if [ -n "${GP2_EVAL_AFTER:-}" ]; then
  until grep -q -- "$GP2_EVAL_AFTER" $L/gp2.log; do [ -f $O/STOP_EVAL ] && exit 0; sleep 120; done
fi
S=$(grep "^$ARM " $O/steps.txt | tail -n 1 | cut -d' ' -f2)
[ -z "$S" ] && { log "NO_STEPS $R"; exit 1; }
for M in ${R}_q$((S / 4)) ${R}_q$((S / 2)) ${R}_final; do
  [ -f $O/eval/$M/EVAL_DONE ] && continue
  until [ -f $O/merged/$M/config.json ]; do
    [ -f $O/STOP_EVAL ] && exit 0; wanted && { log "GPU_WANTED $HT:$G, idle -> exit"; exit 0; }; sleep 120; done
  sleep 30
  N=tp1_${M}_srv
  setsid nohup bash $C/tools/teach_pt/vllm.sh $G $O/merged/$M $N $PORT $U < /dev/null > /dev/null 2>&1 &
  UP=0; for i in $(seq 1 90); do curl -s 127.0.0.1:$PORT/v1/models | grep -q $N && { UP=1; break; }; sleep 10; done
  [ $UP = 0 ] && { log "VLLM_FAIL $M"; bash $C/tools/teach_pt/stop.sh $N >> $L/gp2.log 2>&1; continue; }
  log "SERVE $M :$PORT"
  if wanted; then log "GPU_WANTED $HT:$G -> stop $M"; bash $C/tools/teach_pt/stop.sh $N >> $L/gp2.log 2>&1; exit 0; fi
  [ -f $O/eval/$M/persp/DONE ] || bash $C/tools/teach_pt/py.sh vllm - evp_tp1_${M} $C tools/tp1/tp1_persp_eval.py \
    --data $O/data/persp_eval.jsonl --url http://127.0.0.1:$PORT --name $N --out $O/eval/$M/persp
  if [ "${M%_final}" != "$M" ]; then
    for f in $O/data/l9_eval_$ARM.jsonl $O/data/l9_eval_tpdir.jsonl $(ls /data/harvest/out/dist8/data_x/x_*_d-min_clean.jsonl); do
      b=$(basename $f .jsonl); [ "$b" = "l9_eval_$ARM" ] && b=l9_eval
      [ -f $O/eval/$M/$b/summary.json ] && continue
      if wanted; then log "GPU_WANTED $HT:$G -> stop $M"; bash $C/tools/teach_pt/stop.sh $N >> $L/gp2.log 2>&1; exit 0; fi
      bash $C/tools/teach_pt/py.sh vllm - ev_tp1_${M}_$b $C harvest.teach_pt.evaluate --data $f --arm pt \
        --url http://127.0.0.1:$PORT --name $N --out $O/eval/$M/$b --kinds control
    done
  fi
  bash $C/tools/teach_pt/stop.sh $N >> $L/gp2.log 2>&1
  touch $O/eval/$M/EVAL_DONE
  log "EVAL_DONE $M"
done
log "EVAL_CHAIN_END $R"

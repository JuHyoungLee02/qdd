#!/bin/bash
# E-HCAM8 training worker (prereg_hcam8 §3, E-VIEW8 recipe): pops "<arm> <seed>" lines from the queue and trains
# Qwen3-VL-8B LoRA on /data/harvest/out/hcam8/train_<arm>.jsonl for the steps in steps.txt, then merges.
# usage: hcam8_worker.sh <code dir> <gpu>       queue: /data/harvest/out/hcam8/queue.txt   stop: touch .../STOP_TRAIN
# 78dc GPU0-2 only (GPU3 is kept for benchmark evaluation; the main 35B training resources are never touched).
C=$1; G=$2
O=/data/harvest/out/hcam8; L=/data/harvest/logs/hcam8; Q=$O/queue.txt
mkdir -p $L
log() { echo "$(date -u +%FT%TZ) gpu$G $*" >> $L/hcam8.log; }
case "$(hostname)-$G" in *78dc-0|*78dc-1|*78dc-2) ;; *) echo "refused: $(hostname) GPU $G"; exit 2;; esac
while true; do
  [ -f $O/STOP_TRAIN ] && { log "STOP_TRAIN"; break; }
  JOB=$(flock $O/queue.lock bash -c "head -n 1 $Q; sed -i 1d $Q")
  [ -z "$JOB" ] && break
  set -- $JOB; ARM=$1; SEED=$2; A=${ARM}_s$SEED
  S=$(grep "^$ARM " $O/steps.txt | tail -n 1 | cut -d' ' -f2)
  [ -z "$S" ] && { log "NO_STEPS $A"; continue; }
  log "START $A steps=$S"
  RES=""; [ -d $O/run_$A/state ] && RES="--resume"
  bash $C/tools/teach_pt/py.sh train $G train_hc8_$A $C harvest.teach_l8.train --data $O/train_$ARM.jsonl --out $O/run_$A \
    --epochs 3 --max-steps $S --micro 8 --accum 2 --log-every 10 --save-every 200 --seed $SEED $RES
  E=$(ls -d $O/run_$A/epoch* 2>/dev/null | sort -V | tail -1)
  [ -z "$E" ] && { log "TRAIN_FAIL $A"; continue; }
  bash $C/tools/teach_pt/py.sh train $G merge_hc8_$A $C harvest.teach_l8.merge --adapter $E --out $O/merged_$A
  log "TRAIN_DONE $A $E"
done
log "WORKER_END"

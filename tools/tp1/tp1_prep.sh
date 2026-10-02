#!/bin/bash
# E-TP1 chain on 78dc (prereg_tp1): frozen episode list -> rows (tools/tp1/tp1_build.py, 64 + 4 parallel parts on CPU)
# -> merge (off / on, ego bytes identical, spec gates) -> train_<arm>.jsonl + steps (hcam8_build combine with an empty
# base = the E-GP2 stage-2 steps rule) -> training runs through tools/gp2/gp2_worker.sh (GP2_O / GP2_TAG, shared card
# locks): GPU1 off s0, GPU2 on s0, GPU3 off s1. usage: tp1_prep.sh <code dir>
C=$1
export GP2_O=/data/harvest/out/tp1 GP2_TAG=_tp1
O=$GP2_O; D=$O/data; L=/data/harvest/logs/gp2; P=/data/harvest/venv_sam3/bin/python
mkdir -p $D $L
log() { echo "$(date -u +%FT%TZ) prep_tp1 $*" >> $L/gp2.log; }
cd $C
export PYTHONPATH=$C
if [ ! -s $D/episodes.json ]; then
  log "SELECT start"
  $P tools/tp1/tp1_build.py select $D/episodes.json /data/harvest/l9v2/pilot1/collect /data/harvest/l9v2/pilotF/collect \
    > $D/select.json 2>> $L/prep_tp1.err || { log "SELECT_FAIL"; exit 1; }
  log "SELECT $(cat $D/select.json)"
fi
NT=64; NE=4
for k in $(seq 0 $((NT - 1))); do
  grep -q episodes $D/rows_train_$k.json 2>/dev/null && continue
  $P tools/tp1/tp1_build.py rows $D/episodes.json $D train --part $k/$NT > $D/rows_train_$k.json 2>> $L/prep_tp1_rows_$k.err &
done
for k in $(seq 0 $((NE - 1))); do
  grep -q episodes $D/rows_eval_$k.json 2>/dev/null && continue
  $P tools/tp1/tp1_build.py rows $D/episodes.json $D eval --part $k/$NE > $D/rows_eval_$k.json 2>> $L/prep_tp1_rows_e$k.err &
done
wait
$P tools/tp1/tp1_build.py merge $D $NT $NE > $D/merge.json 2>> $L/prep_tp1.err || { log "MERGE_FAIL $(head -c 600 $D/merge.json)"; exit 1; }
log "MERGE $(head -c 900 $D/merge.json)"
: > $D/empty_base.jsonl
for a in off on; do
  /data/harvest/venv_train/bin/python tools/l9r/hcam8_build.py combine $D/empty_base.jsonl $D/train_$a.jsonl $O/train_$a.jsonl \
    --steps-out $O/steps_$a.txt > $O/combine_$a.json 2>> $L/prep_tp1.err || { log "COMBINE_FAIL $a"; exit 1; }
  echo "$a $(cat $O/steps_$a.txt)" >> $O/steps.txt
  log "COMBINE $a $(cat $O/combine_$a.json)"
done
touch $O/DATA_READY
for x in "1 off 0" "2 on 0" "3 off 1"; do
  set -- $x
  setsid nohup bash $C/tools/gp2/gp2_worker.sh $C $1 $2 $3 >> $L/worker_tp1_g$1.log 2>&1 < /dev/null &
  sleep 5
done
log "WORKERS_STARTED"

#!/bin/bash
# E-GP2 early pilot chain on 78dc (prereg_gp2 §3-§4): frozen episode list -> d-min rows (build9, ego only, no slots,
# 16 + 4 parallel parts on CPU) -> arms a / b (tools/gp2/gp2_build.py arms) -> train_<arm>.jsonl = E-VIEW8 A0 rows +
# the arm's L9 rows (tools/l9r/hcam8_build.py combine, same steps formula) -> the three training runs
# (GPU1 a s0, GPU2 b s0, GPU3 a s2). usage: gp2_prep.sh <code dir>
# prereg change 4 (L9 v2 only): env GP2_O (output dir), GP2_TAG (job tag), GP2_L9ONLY=1 (no A0 base rows; same steps
# formula on the L9 rows), GP2_NT (train row parts), GP2_WORKERS ("g arm seed;..."), GP2_WAIT_LOG + GP2_WAIT_STEP
# (start the build when that training log reaches the step, so the list is frozen as late as possible).
C=$1
O=${GP2_O:-/data/harvest/out/gp2}; D=$O/data; L=/data/harvest/logs/gp2; P=/data/harvest/venv_sam3/bin/python
mkdir -p $D $L
log() { echo "$(date -u +%FT%TZ) prep${GP2_TAG:-} $*" >> $L/gp2.log; }
cd $C
export PYTHONPATH=$C GP2_O GP2_TAG
if [ -n "${GP2_WAIT_LOG:-}" ]; then
  log "WAIT build until $GP2_WAIT_LOG step >= $GP2_WAIT_STEP"
  while true; do
    st=$(tail -n 1 $GP2_WAIT_LOG 2>/dev/null | grep -o '"step": [0-9]*' | grep -o '[0-9]*$')
    [ -n "$st" ] && [ "$st" -ge "$GP2_WAIT_STEP" ] && break
    sleep 60
  done
fi
# a re-run keeps the frozen episode list and the finished row parts (only the missing steps run again)
if [ ! -s $D/episodes.json ]; then
  log "SELECT start"
  $P tools/gp2/gp2_build.py select $D/episodes.json /data/harvest/l9v2/pilot1/collect /data/harvest/l9v2/pilotF/collect \
    > $D/select.json 2>> $L/prep.err || { log "SELECT_FAIL"; exit 1; }
  log "SELECT $(cat $D/select.json)"
fi
NT=${GP2_NT:-16}; NE=$(( (NT + 3) / 4 ))
for k in $(seq 0 $((NT - 1))); do
  grep -q episodes $D/rows_train_$k.json 2>/dev/null && continue
  $P tools/gp2/gp2_build.py rows $D/episodes.json $D train --part $k/$NT > $D/rows_train_$k.json 2>> $L/prep_rows_$k.err &
done
for k in $(seq 0 $((NE - 1))); do
  grep -q episodes $D/rows_eval_$k.json 2>/dev/null && continue
  $P tools/gp2/gp2_build.py rows $D/episodes.json $D eval --part $k/$NE > $D/rows_eval_$k.json 2>> $L/prep_rows_e$k.err &
done
wait
for s in train eval; do
  n=$NT; [ $s = eval ] && n=$NE
  $P tools/gp2/gp2_build.py arms $D $s $n > $D/arms_$s.out 2>> $L/prep.err || { log "ARMS_FAIL $s"; exit 1; }
  log "ARMS $s $(head -c 900 $D/arms_$s.out)"
done
BASE=/data/harvest/out/view8/train_A0.jsonl
[ "${GP2_L9ONLY:-0}" = 1 ] && { BASE=$D/empty_base.jsonl; : > $BASE; }
for a in a b; do
  /data/harvest/venv_train/bin/python tools/l9r/hcam8_build.py combine $BASE \
    $D/l9_train_$a.jsonl $O/train_$a.jsonl --steps-out $O/steps_$a.txt > $O/combine_$a.json 2>> $L/prep.err \
    || { log "COMBINE_FAIL $a"; exit 1; }
  echo "$a $(cat $O/steps_$a.txt)" >> $O/steps.txt
  log "COMBINE $a $(cat $O/combine_$a.json)"
done
[ "$(cat $O/steps_a.txt)" = "$(cat $O/steps_b.txt)" ] || { log "STEPS_MISMATCH"; exit 1; }
touch $O/DATA_READY
IFS=';' read -ra WS <<< "${GP2_WORKERS:-1 a 0;2 b 0;3 a 2}"
for x in "${WS[@]}"; do
  set -- $x
  setsid nohup bash $C/tools/gp2/gp2_worker.sh $C $1 $2 $3 >> $L/worker${GP2_TAG:-}_g$1.log 2>&1 < /dev/null &
  sleep 5
done
log "WORKERS_STARTED"

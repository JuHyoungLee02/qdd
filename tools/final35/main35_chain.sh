#!/bin/bash
# Main 35B chain on 78dc (docs/stage3/prereg_main35.md). Stages (each skips work already done; run under
# main35_super.sh for automatic restarts):
#   0 gate: E-C35 JUDGE_DONE in c35.log and arm b vs f35_d NONINFERIOR (verdict_summary.json); else GATE_FAIL + ALERT stop
#   1 wait for L8S production end (l8s_prod/PROD_DONE), stop the pre-build, build the unbuilt tail in parallel
#   2 base (pre-built chunks, validation episodes held out) + L8S validation rows (parallel) + open pool (adopted,
#     3 % validation) + mix (open = min(0.75 x base, 2.0 x pool)) + G guard
#   3 train 78dc GPU 0-3, main35 settings, 3 epochs, adapters at every half epoch, resume on retry
#   4 checkpoint evaluation queue on 78dc (after training; x2 GPU0 queue runs during training) -> 5 judge -> MAIN35_DONE
# env for the dry run: GATE_LOG / GATE_FILE override the E-C35 files; DRYRUN=1 stops right after the gate decision.
# usage: main35_chain.sh <code dir>
C=$1
O=/data/harvest/out/main35; D=$O/data; L=/data/harvest/logs/main35; P=/data/harvest/venv_train/bin/python
PRE=$O/prebuild; ROOT=/data/harvest/out/teach_l8d/l8s_prod
GATE_LOG=${GATE_LOG:-/data/harvest/logs/c35/c35.log}; GATE_FILE=${GATE_FILE:-/data/harvest/out/c35/verdict/verdict_summary.json}
mkdir -p $D $L
log() { echo "$1 $(date -u +%FT%TZ)" >> $L/main35${DRYRUN:+_dryrun}.log; }
cd $C; export PYTHONPATH=$C
# 0. gate
until grep -q "^JUDGE_DONE" $GATE_LOG 2>/dev/null; do sleep 600; done
if [ -f $O/GATE_OVERRIDE ]; then
  log "GATE_OVERRIDE $(head -1 $O/GATE_OVERRIDE)"  # user decision after the E-C35 gate failure (prereg_main35 deviation 1)
elif ! $P tools/final35/main35_build.py gate $GATE_FILE >> $L/gate${DRYRUN:+_dryrun}.log 2>&1; then
  log "GATE_FAIL $(tail -1 $L/gate${DRYRUN:+_dryrun}.log)"
  [ -n "$DRYRUN" ] || echo "E-C35 b vs f35_d not NONINFERIOR: main 35B not started $(date -u +%FT%TZ)" > $O/ALERT_GATE_FAIL
  exit 3
else
  log "GATE_PASS"
fi
[ -n "$DRYRUN" ] && { log "DRYRUN_WOULD_BUILD_AND_TRAIN"; exit 0; }
# 1. production end -> pre-build stop -> unbuilt tail
until [ -f $ROOT/PROD_DONE ]; do sleep 900; done
touch $PRE/STOP
until grep -q "^STOPPED" $PRE/log/prebuild.log 2>/dev/null; do sleep 60; done
if [ ! -f $PRE/tail.done ]; then
  ls -tr $ROOT/train/*/*/meta.json | sed "s#$ROOT/train/##; s#/meta.json##" | grep -vxF -f $PRE/built_episodes.txt > $PRE/tail.txt
  if [ -s $PRE/tail.txt ]; then
    split -n r/16 -d -a 2 $PRE/tail.txt $PRE/tail_part_
    for f in $PRE/tail_part_*; do
      d=$PRE/chunks/ct${f##*_}
      printf '{"episodes": [%s]}\n' "$(sed 's/.*/"&"/' $f | paste -sd,)" > $d.json
      ( OMP_NUM_THREADS=1 $P tools/teach_l8d/build.py $ROOT $d train pt --manifest $d.json > $d.build.log 2>&1 && \
        OMP_NUM_THREADS=1 $P tools/teach_pt/convert_min.py $d/train_pt.jsonl $d d-min train_d-min.jsonl > $d.convert.log 2>&1 ) &
    done
    rc=0; while [ "$(jobs -rp | wc -l)" -gt 0 ]; do wait -n || rc=1; done
    [ $rc = 0 ] || { log "BUILD_FAIL tail"; exit 1; }
  fi
  touch $PRE/tail.done; log "TAIL_DONE $(wc -l < $PRE/tail.txt)"
fi
# 2. data
if [ ! -f $D/train_main35.jsonl ]; then
  $P tools/final35/main35_build.py base $PRE $D >> $L/build.log 2>&1 || { log BUILD_FAIL_base; exit 1; }
  rm -rf $D/val_src $D/val_part*; i=0
  while read -r e; do g=$((i % 16)); v=$(basename $(dirname $e)); mkdir -p $D/val_src/g$g/$v; ln -sfn $e $D/val_src/g$g/$v/; i=$((i + 1)); done < $D/val_episodes.txt
  for s in $D/val_src/g*; do
    OMP_NUM_THREADS=1 $P tools/teach_pt/build_min.py $s $D/val_part_$(basename $s) x_val_l8s d-min clean $s > $s.log 2>&1 &
  done
  rc=0; while [ "$(jobs -rp | wc -l)" -gt 0 ]; do wait -n || rc=1; done
  [ $rc = 0 ] || { log BUILD_FAIL_val; exit 1; }
  cat $D/val_part_*/x_val_l8s_d-min_clean.jsonl > $D/x_val_l8s_d-min_clean.jsonl
  $P tools/final35/c35_prep.py pool /data/harvest/out/poolv/verdict_fix.json $O/pool >> $L/build.log 2>&1 || { log BUILD_FAIL_pool; exit 1; }
  cp $O/pool/val_open.jsonl $D/val_open.jsonl
  $P tools/final35/main35_build.py mix $D/base_main35_d-min.jsonl $O/pool/pool_src $D/train_main35.jsonl.tmp >> $L/build.log 2>&1 && \
    PYTHONPATH=$C/tools $P -m xemb.gsplit check $D/train_main35.jsonl.tmp >> $L/build.log 2>&1 && \
    mv $D/train_main35.jsonl.tmp.counts.json $D/train_main35.counts.json && mv $D/train_main35.jsonl.tmp $D/train_main35.jsonl \
    || { log BUILD_FAIL_mix; exit 1; }
  log "BUILD_DONE rows=$(wc -l < $D/train_main35.jsonl) val_rows=$(wc -l < $D/x_val_l8s_d-min_clean.jsonl) $(tr -d ' \n' < $D/train_main35.counts.json | grep -o '"pool":[0-9]*,"base":[0-9]*,"open":[0-9]*,"open_over_base":[0-9.]*')"
fi
# 3. train
free4() { [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 < 1000' | wc -l)" -ge 4 ]; }
if ! grep -q "^TRAIN_DONE" $L/main35.log 2>/dev/null; then
  for n in 1 2 3 4 5; do
    [ -f $O/run/epoch3/adapter_model.safetensors ] && break
    until free4; do sleep 120; done
    RES=""; [ -d $O/run/state ] && RES="--resume"
    log "TRAIN_START try $n"
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True bash $C/tools/teach_35b/train.sh $C 0,1,2,3 $D/train_main35.jsonl \
      $O/run --epochs 3 --micro 2 --accum 3 --save-every 200 --adapter-every 0.25 $RES
  done
  [ -f $O/run/epoch3/adapter_model.safetensors ] || { log TRAIN_FAIL; exit 1; }
  log TRAIN_DONE
fi
# 4. evaluation queue here (the x2 GPU0 queue may already have taken some checkpoints)
allk() { for e in 2 1.5 2.5 1 3; do [ -f $O/eval/ep$e/EVAL_COMPLETE ] || return 1; done; }
for t in $(seq 1 6); do
  allk && break
  bash $C/tools/final35/main35_evalq.sh $C 0,1,2,3 0
  allk || sleep 1800  # a checkpoint claimed by the x2 queue may still be running (or was released after a failure)
done
allk || { log EVAL_INCOMPLETE; exit 1; }
# 5. judge
$P tools/final35/main35_judge.py $O/verdict >> $L/main35.log 2>&1 || { log JUDGE_FAIL; exit 1; }
log JUDGE_DONE
touch $O/MAIN35_DONE

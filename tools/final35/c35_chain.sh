#!/bin/bash
# E-C35 chain on 78dc (prereg_c35.md, change 2: two arms). Waits for the L8S audit PASS (l8s_prod/AUDIT300.json) and N
# finished production episodes, builds the data (arm b: open = 0.75 x base from the whole pool; arm a: same ratio from
# a one-third pool subset, repeated), trains b s0, a s0, b s1 (4-GPU DDP, main35 settings, 2 epochs / max steps),
# merges both epochs of each run, scores them on the validation split, keeps the better epoch per run, runs the full
# offline evaluation and the judge (b vs f35_d, a vs f35_d, a vs b). Every stage skips work already done.
# usage: c35_chain.sh <code dir> [N 1000]
C=$1; N=${2:-1000}
O=/data/harvest/out/c35; D=$O/data; L=/data/harvest/logs/c35; P=/data/harvest/venv_train/bin/python
T8=/data/harvest/out/teach_l8d  # audit gate: AUDIT800.json when present, else AUDIT300.json (change 3)
RUNS="b_s0 a_s0 b_s1"
mkdir -p $O/man $D $L
log() { echo "$1 $(date -u +%FT%TZ)" >> $L/c35.log; }
cd $C; export PYTHONPATH=$C
# 1. wait: audit PASS + every stratum (task kind, plan share of N; change 3/4/5) filled
audf() { [ -f $T8/l8s_prod/AUDIT800.json ] && echo $T8/l8s_prod/AUDIT800.json || echo $T8/l8s_prod/AUDIT300.json; }
until grep -q '"verdict": *"PASS"' $(audf) 2>/dev/null && \
  $P tools/final35/c35_prep.py strat_ready $N > $L/strat_ready.json 2>> $L/prep.log; do
  # change 5: an audit FAIL is not final (fixes are re-audited) -> keep waiting for PASS
  sleep 600
done
log "WAIT_DONE N=$N"
# 2. data
mixlog() { tr -d ' \n' < $1 | grep -o '"pool":[0-9]*\|"open_over_base":[0-9.]*,"open_share_of_file":[0-9.]*,"repeat":[0-9.]*' | tr '\n' ' '; }
if [ ! -f $D/train_c35_a.jsonl ]; then
  $P tools/final35/c35_prep.py strat $N $O/man >> $L/prep.log 2>&1 || { log PREP_FAIL_strat; exit 1; }
  for r in main; do  # change 6: ring V excluded (KeyError rp_ring); every build step's exit code is checked
    R=$T8/l8s_prod
    $P tools/teach_l8d/build.py $R $D/b_$r train pt --manifest $O/man/${r}_train.json >> $L/prep.log 2>&1 || { log "PREP_FAIL build $r"; exit 1; }
    $P tools/teach_pt/convert_min.py $D/b_$r/train_pt.jsonl $D d-min l8s_${r}_d-min.jsonl >> $L/prep.log 2>&1 || { log "PREP_FAIL convert $r"; exit 1; }
    for e in $(grep -o '"[^"]*_s[0-9]*"' $O/man/${r}_val.json | tr -d '"'); do
      mkdir -p $O/val_src/$(dirname $e); ln -sfn $R/train/$e $O/val_src/$e
    done
  done
  $P tools/teach_l8d/build.py /data/harvest/out/teach_l8d/b3d_drawer $D/b_drawer train pt \
    --manifest $C/docs/stage3/l8d_bundle_b3d.json >> $L/prep.log 2>&1 || { log "PREP_FAIL build drawer"; exit 1; }
  $P tools/teach_pt/convert_min.py $D/b_drawer/train_pt.jsonl $D d-min drawer_d-min.jsonl >> $L/prep.log 2>&1 || { log "PREP_FAIL convert drawer"; exit 1; }
  cat $D/l8s_main_d-min.jsonl $D/drawer_d-min.jsonl > $D/base_c35_d-min.jsonl || { log "PREP_FAIL base"; exit 1; }
  [ -s $D/l8s_main_d-min.jsonl ] && [ -s $D/drawer_d-min.jsonl ] || { log "PREP_FAIL empty base part"; exit 1; }
  $P tools/teach_pt/build_min.py $O/val_src $D x_val_l8s d-min clean $O/val_src >> $L/prep.log 2>&1 || { log "PREP_FAIL val"; exit 1; }
  $P tools/final35/c35_prep.py pool /data/harvest/out/poolv/verdict_fix.json $O/pool >> $L/prep.log 2>&1 || { log "PREP_FAIL pool"; exit 1; }
  $P tools/final35/c35_prep.py subset $O/pool >> $L/prep.log 2>&1 || { log "PREP_FAIL subset"; exit 1; }
  cp $O/pool/val_open.jsonl $D/val_open.jsonl
  for arm in b a; do
    [ $arm = b ] && { S=$O/pool/pool_src; CAP=3.0; } || { S=$O/pool/pool_src_a; CAP=4.0; }
    F=$D/train_c35_$arm.jsonl
    $P tools/final35/c35_prep.py mix $D/base_c35_d-min.jsonl $S $F.tmp $CAP >> $L/prep.log 2>&1 && \
      PYTHONPATH=$C/tools $P -m xemb.gsplit check $F.tmp >> $L/prep.log 2>&1 && \
      mv $F.tmp.counts.json $D/train_c35_$arm.counts.json && mv $F.tmp $F || { log "PREP_FAIL $arm"; exit 1; }
    log "PREP_DONE $arm rows=$(wc -l < $F) $(mixlog $D/train_c35_$arm.counts.json)"
  done
fi
# 3. train b s0, a s0, b s1 (wait for the 4 cards; resume on retry)
free4() { [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 < 1000' | wc -l)" -ge 4 ]; }
for run in $RUNS; do
  arm=${run%_s*}; s=${run#*_s}; R=$O/run_$run
  for n in 1 2 3; do
    [ -f $R/epoch2/adapter_model.safetensors ] && break
    until free4; do sleep 120; done
    RES=""; [ -d $R/state ] && RES="--resume"
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True bash $C/tools/teach_35b/train.sh $C 0,1,2,3 $D/train_c35_$arm.jsonl \
      $R --epochs 2 --micro 2 --accum 3 --max-steps 3500 --save-every 200 --seed $s $RES
    log "TRAIN_END $run try $n"
  done
  [ -d $R/epoch1 ] || { log "TRAIN_FAIL $run"; exit 1; }
done
# 4. merge (CPU, parallel) + validation scoring (one GPU per model, waves of 4)
for run in $RUNS; do for k in 1 2; do
  M=$O/merged_${run}_ep$k; [ -d $O/run_$run/epoch$k ] || continue
  [ -f $M/config.json ] || bash $C/tools/teach_35b/py.sh train - c35_merge_${run}_ep$k $C harvest.teach_35b.merge \
    --adapter $O/run_$run/epoch$k --out $M &
done; done
wait
g=0
for run in $RUNS; do for k in 1 2; do
  M=$O/merged_${run}_ep$k; [ -f $M/config.json ] || continue
  bash $C/tools/final35/c35_eval.sh $C $g $M c35_${run}_ep$k $((8631 + g)) $O/eval/${run}_ep$k val &
  g=$((g + 1)); [ $g -eq 4 ] && { wait; g=0; }
done; done
wait
log VAL_DONE
# 5. best epoch per run -> full evaluation -> judge
g=0
for run in $RUNS; do
  if [ -f $O/merged_${run}_ep2/config.json ]; then
    B=$($P tools/final35/c35_select.py $O/eval/${run}_ep1 $O/merged_${run}_ep1 $O/eval/${run}_ep2 $O/merged_${run}_ep2)
  else
    B=$O/merged_${run}_ep1
  fi
  echo $B > $O/best_$run.txt
  bash $C/tools/final35/c35_eval.sh $C $g $B c35_best_$run $((8641 + g)) $O/eval/best_$run full &
  g=$((g + 1))
done
until grep -q "EVAL_DONE c35_base full" $L/c35.log; do sleep 60; done  # baseline f35_d evaluation (started 09-29)
wait
$P tools/final35/c35_judge.py $O/eval /data/harvest/out/opratio/g_eval.jsonl $O/verdict >> $L/c35.log 2>&1
log JUDGE_DONE

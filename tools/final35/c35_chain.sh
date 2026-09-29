#!/bin/bash
# E-C35 chain on 78dc (prereg_c35.md). Waits for the L8S audit PASS (l8s_prod/AUDIT300.json) and N finished
# production episodes, builds the data, trains c35 seed 0 then seed 1 (4-GPU DDP, main35 settings, 2 epochs / max
# steps), merges both epochs, scores them on the validation split, keeps the better epoch per seed, runs the full
# offline evaluation and the judge. Every stage skips work already done (restart-safe).
# usage: c35_chain.sh <code dir> [N 1000]
C=$1; N=${2:-1000}
O=/data/harvest/out/c35; D=$O/data; L=/data/harvest/logs/c35; P=/data/harvest/venv_train/bin/python
T8=/data/harvest/out/teach_l8d; AUD=$T8/l8s_prod/AUDIT300.json
mkdir -p $O/man $D $L
log() { echo "$1 $(date -u +%FT%TZ)" >> $L/c35.log; }
cd $C; export PYTHONPATH=$C
# 1. wait: audit PASS + N finished episodes
until grep -q '"verdict": *"PASS"' $AUD 2>/dev/null && \
  [ "$(ls $T8/l8s_prod/train/*/*/meta.json $T8/l8s_prod_ring/train/*/*/meta.json 2>/dev/null | wc -l)" -ge $N ]; do
  grep -q '"verdict": *"FAIL"' $AUD 2>/dev/null && { log "WAIT_STOP audit FAIL"; exit 1; }
  sleep 300
done
log "WAIT_DONE N=$N"
# 2. data
if [ ! -f $D/train_c35.jsonl ]; then
  $P tools/final35/c35_prep.py l8s $N $O/man >> $L/prep.log 2>&1 || { log PREP_FAIL_l8s; exit 1; }
  for r in main ring; do
    [ $r = main ] && R=$T8/l8s_prod || R=$T8/l8s_prod_ring
    $P tools/teach_l8d/build.py $R $D/b_$r train pt --manifest $O/man/${r}_train.json >> $L/prep.log 2>&1
    $P tools/teach_pt/convert_min.py $D/b_$r/train_pt.jsonl $D d-min l8s_${r}_d-min.jsonl >> $L/prep.log 2>&1
    for e in $(grep -o '"[^"]*_s[0-9]*"' $O/man/${r}_val.json | tr -d '"'); do
      mkdir -p $O/val_src/$(dirname $e); ln -sfn $R/train/$e $O/val_src/$e
    done
  done
  $P tools/teach_l8d/build.py /data/harvest/out/teach_l8d/b3d_drawer $D/b_drawer train pt \
    --manifest $C/docs/stage3/l8d_bundle_b3d.json >> $L/prep.log 2>&1
  $P tools/teach_pt/convert_min.py $D/b_drawer/train_pt.jsonl $D d-min drawer_d-min.jsonl >> $L/prep.log 2>&1
  cat $D/l8s_main_d-min.jsonl $D/l8s_ring_d-min.jsonl $D/drawer_d-min.jsonl > $D/base_c35_d-min.jsonl 2>> $L/prep.log
  $P tools/teach_pt/build_min.py $O/val_src $D x_val_l8s d-min clean $O/val_src >> $L/prep.log 2>&1
  $P tools/final35/c35_prep.py pool /data/harvest/out/poolv/verdict_fix.json $O/pool >> $L/prep.log 2>&1
  cp $O/pool/val_open.jsonl $D/val_open.jsonl
  $P tools/final35/c35_prep.py mix $D/base_c35_d-min.jsonl $O/pool $D/train_c35.jsonl.tmp >> $L/prep.log 2>&1 && \
    PYTHONPATH=$C/tools $P -m xemb.gsplit check $D/train_c35.jsonl.tmp >> $L/prep.log 2>&1 && \
    mv $D/train_c35.jsonl.tmp $D/train_c35.jsonl || { log PREP_FAIL; exit 1; }
  log "PREP_DONE rows=$(wc -l < $D/train_c35.jsonl)"
fi
# 3. train seed 0 then 1 (wait for the 4 cards; resume on retry)
free4() { [ "$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '$1 < 1000' | wc -l)" -ge 4 ]; }
for s in 0 1; do
  R=$O/run_s$s
  for n in 1 2 3; do
    [ -f $R/epoch2/adapter_model.safetensors ] && break
    until free4; do sleep 120; done
    RES=""; [ -d $R/state ] && RES="--resume"
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True bash $C/tools/teach_35b/train.sh $C 0,1,2,3 $D/train_c35.jsonl $R \
      --epochs 2 --micro 2 --accum 3 --max-steps 3500 --save-every 200 --seed $s $RES
    log "TRAIN_END s$s try $n"
  done
  [ -d $R/epoch1 ] || { log "TRAIN_FAIL s$s"; exit 1; }
done
# 4. merge (CPU, parallel) + validation scoring (one GPU per model)
for s in 0 1; do for k in 1 2; do
  M=$O/merged_s${s}_ep$k; [ -d $O/run_s$s/epoch$k ] || continue
  [ -f $M/config.json ] || bash $C/tools/teach_35b/py.sh train - c35_merge_s${s}_ep$k $C harvest.teach_35b.merge \
    --adapter $O/run_s$s/epoch$k --out $M &
done; done
wait
g=0
for s in 0 1; do for k in 1 2; do
  M=$O/merged_s${s}_ep$k; [ -f $M/config.json ] || continue
  bash $C/tools/final35/c35_eval.sh $C $g $M c35_s${s}_ep$k $((8631 + g)) $O/eval/s${s}_ep$k val &
  g=$((g + 1))
done; done
wait
log VAL_DONE
# 5. best epoch per seed -> full evaluation -> judge
for s in 0 1; do
  if [ -f $O/merged_s${s}_ep2/config.json ]; then
    B=$($P tools/final35/c35_select.py $O/eval/s${s}_ep1 $O/merged_s${s}_ep1 $O/eval/s${s}_ep2 $O/merged_s${s}_ep2)
  else
    B=$O/merged_s${s}_ep1
  fi
  echo $B > $O/best_s$s.txt
  bash $C/tools/final35/c35_eval.sh $C $s $B c35_best_s$s $((8641 + s)) $O/eval/best_s$s full &
done
until grep -q "EVAL_DONE c35_base full" $L/c35.log; do sleep 60; done  # baseline f35_d evaluation (started 09-29)
wait
$P tools/final35/c35_judge.py $O/eval/best_s0 $O/eval/best_s1 $O/eval/f35_d /data/harvest/out/opratio/g_eval.jsonl \
  $O/verdict.json >> $L/c35.log 2>&1
log JUDGE_DONE

#!/bin/bash
# E-MAR-real factor A (docs/stage3/prereg_marr.md). Pod x2 (juhyoung-native-7a2a-x2) GPU 0 / 1, never preempting.
# Code = this script's ../.. (git archive of the base 1b68a6a harvest/ + the prereg commit's new files, LF).
# usage: run_train.sh smoke <gpu> | a <seed> <gpu> | c0 <seed> <gpu> | view <gpu> | sr0 <seed> <gpu> | verdict
#   smoke    20-step dry run on the partial labels (conv/partial), predict trained + base view, compare
#   a        train A seed <seed> (2,000 steps) + predict the full val 1,799 (+ --extra-out)
#   c0       predict C0 = motion_s<seed> on the full val with this code (reuse check (2) + the verdict's C0 input)
#   view     A s1 last/: trained vs base view on val 300 (runtime-path check, prereg §4)
#   sr0      outside the rule: E-SR0 joystick adherence tool (unmodified) on A seed <seed>
set -uo pipefail
source /data/harvest/env.sh
C="$(cd "$(dirname "$0")/../.." && pwd)"; PY=/data/harvest/venv_train/bin/python
R=/data/harvest/ckpt/marr_real; L=/data/harvest/logs/marr_real; N=/data/harvest/data/se2e_c1
T=/data/harvest/data/marr_real/conv; OLD=/data/harvest/ckpt/se2e_confirm
mkdir -p $R $L
cd $C
export PYTHONPATH=$C OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=8 MKL_NUM_THREADS=8
DATA="--data se2e --se2e-root $N/conv --se2e-t-root $N/conv"
MO="--motion-line se2e-motion@v1 --motion-bins $N/motion_bins.json"
ENTRY="-m harvest.train.se2e_tracept"
free_gpu() { [ "$(nvidia-smi -i $1 --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' ')" -lt 2000 ]; }
hashes() {
  { date -u +%FT%TZ; cat $C/CODE_VERSION; sha256sum harvest/train/*.py tools/marr_real/*.py tools/ma1/ma1b_verdict.py \
      tools/se2e/temporal_verdict.py $N/motion_bins.json $N/transition_val.json $N/conv/RB1.stageb.jsonl \
      $N/conv/RB2.stageb.jsonl $T/RB2.tracept.jsonl 2>/dev/null; } > $1/CODE_HASHES.txt
}
cmd=$1; shift
case $cmd in
  smoke)
    g=$1; export CUDA_VISIBLE_DEVICES=$g
    until free_gpu $g; do sleep 60; done
    AX="--aux-extra trace5-point@v1 --tracept-root $T/partial"
    S=/data/harvest/tmp/marr_real/smoke; rm -rf $S; mkdir -p $S
    echo "smoke start $(date -u +%FT%TZ)"
    $PY $ENTRY train $DATA $MO $AX --batch 8 --max-steps 20 --max-train 64 --lr 1e-4 --lr-heads 1e-4 \
      --eval-every 10 --val-per-kind 5 --val-seed 0 --seed 1 --out-root $S --run a > $L/smoke_train.out 2>&1
    echo "smoke train rc=$? $(date -u +%FT%TZ)"
    for V in trained base; do
      $PY $ENTRY predict $DATA $MO $AX --aux-view $V --val-per-kind 5 --val-seed 0 --seed 0 \
        --ckpt $S/a/last --out $S/pred_$V.jsonl --extra-out $S/extra_$V.json > $L/smoke_pred_$V.out 2>&1
      echo "smoke predict $V rc=$? $(date -u +%FT%TZ)"
    done
    $PY tools/marr_real/reuse_check.py pred $S/pred_trained.jsonl $S/pred_base.jsonl --ignore aux,ckpt \
      --out $L/smoke_view_cmp.json > /dev/null; echo "smoke view cmp rc=$? $(date -u +%FT%TZ)";;
  a)
    s=$1; g=$2; export CUDA_VISIBLE_DEVICES=$g
    AX="--aux-extra trace5-point@v1 --tracept-root $T"
    n=a_s$s; mkdir -p $R/$n; hashes $R/$n
    until free_gpu $g; do sleep 60; done
    echo "$n start $(date -u +%FT%TZ) gpu=$g"
    $PY $ENTRY train $DATA $MO $AX --batch 8 --max-steps 2000 --lr 1e-4 --lr-heads 1e-4 \
      --eval-every 500 --val-per-kind 150 --val-seed 0 --seed $s --out-root $R --run $n > $L/$n.out 2>&1
    echo "$n rc=$? $(date -u +%FT%TZ)"
    $PY $ENTRY predict $DATA $MO $AX --val-per-kind 0 --val-seed 0 --seed 0 \
      --ckpt $R/$n/last --out $L/predfull_$n.jsonl --extra-out $L/extra_$n.json > $L/predfull_$n.out 2>&1
    echo "$n predictfull rc=$? $(date -u +%FT%TZ)";;
  c0)
    s=$1; g=$2; export CUDA_VISIBLE_DEVICES=$g
    until free_gpu $g; do sleep 60; done
    $PY $ENTRY predict $DATA $MO --val-per-kind 0 --val-seed 0 --seed 0 \
      --ckpt $OLD/motion_s$s/last --out $L/predfull_c0_s$s.jsonl --extra-out $L/extra_c0_s$s.json \
      > $L/predfull_c0_s$s.out 2>&1
    echo "c0_s$s predictfull rc=$? $(date -u +%FT%TZ)"
    $PY tools/marr_real/reuse_check.py pred $L/predfull_c0_s$s.jsonl /data/harvest/logs/ma1b/predfull_none_s$s.jsonl \
      --out $L/reuse_pred_s$s.json > /dev/null; echo "c0_s$s reuse cmp rc=$? $(date -u +%FT%TZ)";;
  view)
    g=$1; export CUDA_VISIBLE_DEVICES=$g
    AX="--aux-extra trace5-point@v1 --tracept-root $T"
    until free_gpu $g; do sleep 60; done
    for V in trained base; do
      $PY $ENTRY predict $DATA $MO $AX --aux-view $V --val-per-kind 150 --val-seed 0 --seed 0 \
        --ckpt $R/a_s1/last --out $L/view300_$V.jsonl > $L/view300_$V.out 2>&1
      echo "view $V rc=$? $(date -u +%FT%TZ)"
    done
    $PY tools/marr_real/reuse_check.py pred $L/view300_trained.jsonl $L/view300_base.jsonl --ignore aux,ckpt \
      --out $L/view_cmp.json > /dev/null; echo "view cmp rc=$? $(date -u +%FT%TZ)";;
  sr0)
    s=$1; g=$2; export CUDA_VISIBLE_DEVICES=$g
    until free_gpu $g; do sleep 60; done
    $PY tools/sr0/sr0_eval.py $DATA $MO --val-per-kind 0 --val-seed 0 --seed 0 --ckpt $R/a_s$s/last \
      --out $L/sr0_a_s$s.jsonl > $L/sr0_a_s$s.out 2>&1
    echo "sr0 a_s$s rc=$? $(date -u +%FT%TZ)";;
  verdict)
    ok=$(grep -q '"identical": true' $L/view_cmp.json && echo yes || echo no)
    $PY tools/marr_real/verdict.py --trans $N/transition_val.json --labels $T/RB2.tracept.jsonl --runtime-identical $ok \
      --pred c0_s1=$L/predfull_c0_s1.jsonl a_s1=$L/predfull_a_s1.jsonl c0_s2=$L/predfull_c0_s2.jsonl \
             a_s2=$L/predfull_a_s2.jsonl --out $L/verdict_full.json > $L/verdict_full.out 2>&1
    echo "verdict rc=$? runtime_identical=$ok $(date -u +%FT%TZ)";;
  *) echo "unknown $cmd"; exit 2;;
esac

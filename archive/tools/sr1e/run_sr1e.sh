#!/bin/bash
# E-SR1e driver (docs/stage3/prereg_sr1e.md §2-§3), main pod, frozen code /data/harvest/code_sr1e (LF archive of the
# E-SR1d registration commit 32065de + the E-SR1e files of the E-SR1e registration commit).
#   bash run_sr1e.sh train <arm A|D> <seed 1|2> <gpu>   one training run + gates g0 / g2 / cfg
#        A = 6000 steps, branch share 0.5 (8 / step); D = 3000 steps, branch share 0.75 (24 / step) - about equal GPU time
#   bash run_sr1e.sh eval <gpu>   evaluation phase, one process at a time on one GPU (after every training run ended):
#        C0 s1 / s2 (+ G1) -> A s1 / s2 -> D s1 / s2 (--latency 50) -> verdict -> L1 CDG (E-SR1d C1 s1 / s2 at
#        w 1 / 1.5 / 2 / 3) -> L1 verdict -> outside the rule (half-way checkpoints of seed 1, TRAIN far snapshots)
# env DRY=1: pre-registration dry run (60 / 30 steps, 12 snapshots, logs under $L/dry).
set -u
CMD=$1
source /data/harvest/env.sh
export OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=8
cd ${CODE:-/data/harvest/code_sr1e}
PY=/data/harvest/venv_train/bin/python
R=/data/harvest/data/se2e_c1/conv
B=/data/harvest/data/se2e_c1/motion_bins.json
META=/data/harvest/data/sr1d/strata/meta.jsonl
BR=/data/harvest/data/sr1d/branches
L=/data/harvest/logs/sr1e
CK=/data/harvest/ckpt/sr1e
VPK=150; LIM=""; N=1799; SA=6000; SD=3000; MAXS_A=20000; MAXS_D=24000
if [ "${DRY:-0}" = "1" ]; then
  L=$L/dry; CK=$CK/dry; SA=60; SD=30; VPK=10; LIM="--limit 12"; N=12; MAXS_A=1e9; MAXS_D=1e9
fi
mkdir -p $L $CK
frac() { [ "$1" = "A" ] && echo 0.5 || echo 0.75; }
nb() { [ "$1" = "A" ] && echo 8 || echo 24; }
steps() { [ "$1" = "A" ] && echo $SA || echo $SD; }
maxs() { [ "$1" = "A" ] && echo $MAXS_A || echo $MAXS_D; }
EVARGS="--data se2e --state IMG --se2e-root $R --se2e-t-root $R --motion-line se2e-motion@v1 --motion-bins $B
  --val-per-kind 0 --val-seed 0 --seed 0 --meta $META"
ev() {  # ckpt name
  nice $PY tools/sr1d/sr1d_eval.py $EVARGS --ckpt $1 --out $L/eval_$2.jsonl --latency 50 $LIM > $L/eval_$2.out 2>&1
  echo "EXIT $? $(date -u +%FT%TZ)" >> $L/eval_$2.out
}
cdg() {  # w seed
  nice $PY tools/sr1e/cdg_eval.py --w $1 -- $EVARGS --ckpt /data/harvest/ckpt/sr1d/c1_s$2/last \
    --out $L/cdg_w$1_s$2.jsonl --latency 50 $LIM > $L/cdg_w$1_s$2.out 2>&1
  echo "EXIT $? $(date -u +%FT%TZ)" >> $L/cdg_w$1_s$2.out
}
ins() {  # ckpt name drawn_seed steps frac
  nice $PY tools/sr1e/diag_insample.py --n 400 --sel-seed 0 --branches $BR --drawn-seed $3 --steps $4 --frac $5 \
    --tags $L/ins_$2.tags.json -- $EVARGS --ckpt $1 --out $L/ins_$2.jsonl $LIM > $L/ins_$2.out 2>&1
  echo "EXIT $? $(date -u +%FT%TZ)" >> $L/ins_$2.out
}
if [ "$CMD" = "train" ]; then
  ARM=$2; SEED=$3; export CUDA_VISIBLE_DEVICES=$4
  RUN=$(echo $ARM | tr A-Z a-z)_s$SEED
  ST=$(steps $ARM)
  echo "train $RUN gpu $4 start $(date -u +%FT%TZ)" >> $L/lanes.out
  nice $PY -m harvest.train.sr1e train --data se2e --state IMG --se2e-root $R --se2e-t-root $R \
    --motion-line se2e-motion@v1 --motion-bins $B --sr1d-branch $BR --sr1d-frac $(frac $ARM) --sr1d-mode far \
    --sr1e-branch-chunk 8 --batch 8 --max-steps $ST --save-every $((ST / 2)) --lr 1e-4 --lr-heads 1e-4 \
    --eval-every 500 --val-per-kind $VPK --val-seed 0 --seed $SEED --run $RUN --out-root $CK > $L/train_$RUN.out 2>&1
  echo "train $RUN rc $? $(date -u +%FT%TZ)" >> $L/lanes.out
  LOG=$CK/$RUN/log.jsonl
  nice $PY tools/sr1e/sr1e_gate.py g0 --log $L/train_$RUN.out --stats $BR/stats.json --nb $(nb $ARM) > $L/gate_train_$RUN.out 2>&1
  nice $PY tools/sr1e/sr1e_gate.py g2 --log $LOG --max-s $(maxs $ARM) >> $L/gate_train_$RUN.out 2>&1
  nice $PY tools/sr1e/sr1e_gate.py cfg --log $LOG --ref /data/harvest/ckpt/se2e_confirm/motion_s$SEED/log.jsonl \
    >> $L/gate_train_$RUN.out 2>&1
  echo "gates $RUN done $(date -u +%FT%TZ)" >> $L/lanes.out
elif [ "$CMD" = "eval" ]; then
  export CUDA_VISIBLE_DEVICES=$2
  echo "eval phase start $(date -u +%FT%TZ)" >> $L/lanes.out
  for S in 1 2; do
    ev /data/harvest/ckpt/se2e_confirm/motion_s$S/last c0_s$S
    if [ "${DRY:-0}" != "1" ]; then
      nice $PY tools/sr1e/sr1e_gate.py g1 --eval $L/eval_c0_s$S.jsonl --sr0 /data/harvest/logs/sr0/sr0_motion_s$S.jsonl \
        > $L/gate_g1_s$S.out 2>&1 || { echo "G1 FAIL s$S $(date -u +%FT%TZ)" >> $L/lanes.out; exit 1; }
    fi
  done
  for RUN in a_s1 a_s2 d_s1 d_s2; do ev $CK/$RUN/last $RUN; done
  echo "main evals done $(date -u +%FT%TZ)" >> $L/lanes.out
  nice $PY tools/sr1e/sr1e_verdict.py --c0 $L/eval_c0_s1.jsonl $L/eval_c0_s2.jsonl \
    --arm A $L/eval_a_s1.jsonl $L/eval_a_s2.jsonl --arm D $L/eval_d_s1.jsonl $L/eval_d_s2.jsonl \
    --n $N --boot 10000 --out $L/verdict.json > $L/verdict.out 2>&1
  echo "EXIT $? $(date -u +%FT%TZ)" >> $L/verdict.out
  sha256sum $L/verdict.json | cut -c1-16 > $L/verdict.sha
  for W in 1 1.5 2 3; do for S in 1 2; do cdg $W $S; done; done
  nice $PY tools/sr1e/sr1e_verdict.py --c0 $L/eval_c0_s1.jsonl $L/eval_c0_s2.jsonl \
    --cdg-base $L/cdg_w1_s1.jsonl $L/cdg_w1_s2.jsonl --cdg 1.5 $L/cdg_w1.5_s1.jsonl $L/cdg_w1.5_s2.jsonl \
    --cdg 2 $L/cdg_w2_s1.jsonl $L/cdg_w2_s2.jsonl --cdg 3 $L/cdg_w3_s1.jsonl $L/cdg_w3_s2.jsonl \
    --n $N --out $L/verdict_cdg.json > $L/verdict_cdg.out 2>&1
  echo "EXIT $? $(date -u +%FT%TZ)" >> $L/verdict_cdg.out
  sha256sum $L/verdict_cdg.json | cut -c1-16 > $L/verdict_cdg.sha
  echo "L1 done $(date -u +%FT%TZ)" >> $L/lanes.out
  # outside the rule
  ev $CK/a_s1/ckpt/$(printf 'step_%06d' $((SA / 2))) a_s1_half
  ev $CK/d_s1/ckpt/$(printf 'step_%06d' $((SD / 2))) d_s1_half
  ins $CK/a_s1/last a_s1 1 $SA 0.5
  ins $CK/a_s2/last a_s2 2 $SA 0.5
  ins $CK/d_s1/last d_s1 1 $SD 0.75
  ins $CK/d_s2/last d_s2 2 $SD 0.75
  echo "eval phase done $(date -u +%FT%TZ)" >> $L/lanes.out
fi

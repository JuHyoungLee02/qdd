#!/bin/bash
# E-SR1d main driver (docs/stage3/prereg_sr1d.md §2-§3), one lane per seed on the x2 pod:
#   bash run_sr1d.sh <seed 1|2> <gpu>
# lane: C0 eval (motion_s<seed>, --latency 50) -> gate g1 (vs E-SR0) -> C1 training (seed) -> gates g0 / g2 / cfg ->
# C1 eval (--latency 50). Frozen code /data/harvest/code_sr1d (git archive of the registration commit, LF).
set -u
SEED=$1
GPU=$2
source /data/harvest/env.sh
export OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=8 CUDA_VISIBLE_DEVICES=$GPU
cd /data/harvest/code_sr1d
PY=/data/harvest/venv_train/bin/python
R=/data/harvest/data/se2e_c1/conv
B=/data/harvest/data/se2e_c1/motion_bins.json
L=/data/harvest/logs/sr1d
META=/data/harvest/data/sr1d/strata/meta.jsonl
BR=/data/harvest/data/sr1d/branches
mkdir -p $L
ev() {  # ckpt name
  nice $PY tools/sr1d/sr1d_eval.py --data se2e --state IMG --se2e-root $R --se2e-t-root $R --motion-line se2e-motion@v1 \
    --motion-bins $B --val-per-kind 0 --val-seed 0 --seed 0 --ckpt $1 --meta $META --out $L/eval_$2.jsonl \
    --latency 50 > $L/eval_$2.out 2>&1
  echo "EXIT $?" >> $L/eval_$2.out
}
echo "lane $SEED gpu $GPU start $(date -u +%FT%TZ)" >> $L/lane_$SEED.out
ev /data/harvest/ckpt/se2e_confirm/motion_s$SEED/last c0_s$SEED
nice $PY tools/sr1d/sr1d_gate.py g1 --eval $L/eval_c0_s$SEED.jsonl --sr0 /data/harvest/logs/sr0/sr0_motion_s$SEED.jsonl \
  > $L/gate_g1_s$SEED.out 2>&1 || { echo "G1 FAIL $(date -u +%FT%TZ)" >> $L/lane_$SEED.out; exit 1; }
echo "g1 ok $(date -u +%FT%TZ)" >> $L/lane_$SEED.out
nice $PY -m harvest.train.sr1d train --data se2e --state IMG --se2e-root $R --se2e-t-root $R \
  --motion-line se2e-motion@v1 --motion-bins $B --sr1d-branch $BR --sr1d-frac 0.5 --sr1d-mode far \
  --batch 8 --max-steps 2000 --lr 1e-4 --lr-heads 1e-4 --eval-every 500 --val-per-kind 150 --val-seed 0 \
  --seed $SEED --run c1_s$SEED --out-root /data/harvest/ckpt/sr1d > $L/train_c1_s$SEED.out 2>&1
echo "train rc $? $(date -u +%FT%TZ)" >> $L/lane_$SEED.out
LOG=/data/harvest/ckpt/sr1d/c1_s$SEED/log.jsonl
nice $PY tools/sr1d/sr1d_gate.py g0 --log $L/train_c1_s$SEED.out --stats $BR/stats.json > $L/gate_train_s$SEED.out 2>&1
nice $PY tools/sr1d/sr1d_gate.py g2 --log $LOG >> $L/gate_train_s$SEED.out 2>&1
nice $PY tools/sr1d/sr1d_gate.py cfg --log $LOG --ref /data/harvest/ckpt/se2e_confirm/motion_s$SEED/log.jsonl \
  >> $L/gate_train_s$SEED.out 2>&1
ev /data/harvest/ckpt/sr1d/c1_s$SEED/last c1_s$SEED
echo "done $(date -u +%FT%TZ)" >> $L/lane_$SEED.out

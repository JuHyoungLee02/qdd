#!/bin/bash
# E-SR0 driver (docs/stage3/prereg_sr0.md). usage: run_sr0.sh <code dir> dry|A|B|gate|verdict
#   dry     : GPU 2, first 12 snapshots of motion_s1 and c0 + gate + verdict smoke -> $L/dry
#   A       : GPU 2: motion_s1 (S-E2E val 1,799) -> c0 (R2 eval 1,200, --grip)
#   B       : GPU 3: motion_s2 (S-E2E val 1,799)
#   gate    : G1 path gate on the full outputs
#   verdict : sr0_verdict.py
set -uo pipefail
source /data/harvest/env.sh
C=$1; MODE=$2; PY=/data/harvest/venv_train/bin/python
L=/data/harvest/logs/sr0; N=/data/harvest/data/se2e_c1; B=$N/motion_bins.json
SE=/data/harvest/ckpt/se2e_confirm; D=/data/harvest/data/ma2; CK=/data/harvest/ckpt/ma2
MA3=/data/harvest/logs/ma3; MA2=/data/harvest/logs/ma2
mkdir -p $L
cd $C
export PYTHONPATH=$C OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=8
SDATA="--data se2e --se2e-root $N/conv --se2e-t-root $N/conv --motion-line se2e-motion@v1 --motion-bins $B --val-per-kind 0 --val-seed 0 --seed 0"
POOL=$(ls -d $D/view/*/*/P* | grep -v jsonl | paste -sd,)
EROWS=$(for f in ${POOL//,/ }; do echo -n "$f.eval.stageb.jsonl,"; done | sed 's/,$//')
RDATA="--data r2 --pool $POOL --rows $EROWS --eval-set $D/eval_set.json --grip --seed 0"
ts() { date -u +%FT%TZ; }
ev() {  # ev <out prefix> <args...>
  local o=$1; shift
  rm -f $o.jsonl
  echo "$(basename $o) start $(ts) gpu $CUDA_VISIBLE_DEVICES"
  nice $PY tools/sr0/sr0_eval.py "$@" --out $o.jsonl > $o.out 2>&1
  echo "$(basename $o) rc=$? $(ts)"
}
hashes() {
  { ts; sha256sum tools/sr0/*.py harvest/train/stageb_train.py harvest/train/stageb_model.py \
      harvest/train/stageb_expert.py harvest/train/stageb_data.py harvest/train/prefix_share.py \
      harvest/train/se2e_data.py harvest/train/se2e_temporal.py harvest/train/r2_ma2.py $B $D/eval_set.json; } > $1
}
case $MODE in
  dry)
    X=$L/dry; mkdir -p $X; export CUDA_VISIBLE_DEVICES=2
    hashes $X/CODE_HASHES.txt
    ev $X/motion_s1 $SDATA --ckpt $SE/motion_s1/last --limit 12
    ev $X/c0 $RDATA --ckpt $CK/c0/last --limit 12
    $PY tools/sr0/sr0_gate.py se2e $X/motion_s1.jsonl $MA3/chunk_none_s1.jsonl > $X/gate_se2e.out 2>&1
    echo "gate se2e rc=$? $(ts)"
    $PY tools/sr0/sr0_gate.py r2 $X/c0.jsonl $MA2/eval_c0.jsonl > $X/gate_r2.out 2>&1
    echo "gate r2 rc=$? $(ts)"
    $PY tools/sr0/sr0_verdict.py --se2e $X/motion_s1.jsonl $X/motion_s1.jsonl --n-se2e 12 --r2 $X/c0.jsonl \
      --n-r2 12 --boot 100 --out $X/verdict.json > $X/verdict.out 2>&1
    echo "verdict smoke rc=$? $(ts)"
    touch $X/dry.done;;
  A)
    export CUDA_VISIBLE_DEVICES=2
    hashes $L/CODE_HASHES.txt
    ev $L/sr0_motion_s1 $SDATA --ckpt $SE/motion_s1/last
    ev $L/sr0_c0 $RDATA --ckpt $CK/c0/last
    touch $L/A.done;;
  B)
    export CUDA_VISIBLE_DEVICES=3
    ev $L/sr0_motion_s2 $SDATA --ckpt $SE/motion_s2/last
    touch $L/B.done;;
  gate)
    for s in 1 2; do
      $PY tools/sr0/sr0_gate.py se2e $L/sr0_motion_s$s.jsonl $MA3/chunk_none_s$s.jsonl; echo "gate se2e s$s rc=$?"
    done
    $PY tools/sr0/sr0_gate.py r2 $L/sr0_c0.jsonl $MA2/eval_c0.jsonl; echo "gate r2 rc=$?";;
  verdict)
    $PY tools/sr0/sr0_verdict.py --se2e $L/sr0_motion_s1.jsonl $L/sr0_motion_s2.jsonl --n-se2e 1799 \
      --r2 $L/sr0_c0.jsonl --n-r2 1200 --out $L/verdict.json > $L/verdict.out 2>&1
    echo "verdict rc=$? $(ts)";;
esac

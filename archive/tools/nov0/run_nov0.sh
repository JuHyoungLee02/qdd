#!/bin/bash
# E-NOV0 driver (docs/stage3/prereg_nov0.md). usage: run_nov0.sh <code dir> dry|A|gate|latency|verdict
#   dry     : GPU 2, batch check (8 eval) + 120 evenly spaced per set (mem, cal, eval, se2e) + gate + latency + verdict smoke -> $L/dry
#   A       : GPU 2, full extraction: R2 mem, cal, eval -> S-E2E val -> $L/feat
#   gate    : G1 on $L/feat/eval.meta.jsonl (E-MA2 eval_c0, E-SR0 sr0_c0)
#   latency : GPU 2, scoring latency on $L/feat
#   verdict : nov0_verdict.py on $L/feat
set -uo pipefail
source /data/harvest/env.sh
C=$1; MODE=$2; PY=/data/harvest/venv_train/bin/python
L=/data/harvest/logs/nov0; D=/data/harvest/data/ma2; CK=/data/harvest/ckpt/ma2/c0/last
SE=/data/harvest/data/se2e_c1/conv
mkdir -p $L
cd $C
export PYTHONPATH=$C OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=8 CUDA_VISIBLE_DEVICES=2
POOL=$(ls -d $D/view/*/*/P* | grep -v jsonl | paste -sd,)
ts() { date -u +%FT%TZ; }
ex() {  # ex <out dir> <log name> <args...>
  local o=$1 n=$2; shift 2
  echo "$n start $(ts)"
  nice $PY tools/nov0/nov0_extract.py --ckpt $CK --out-dir $o --seed 0 "$@" > $o/$n.out 2>&1
  echo "$n rc=$? $(ts)"
}
hashes() {
  { ts; sha256sum tools/nov0/*.py tools/nov0/run_nov0.sh harvest/train/stageb_train.py harvest/train/stageb_model.py \
      harvest/train/stageb_expert.py harvest/train/stageb_data.py harvest/train/prefix_share.py \
      harvest/train/r2_ma2.py harvest/analysis/stats.py $CK/stageb.json; } > $1
}
case $MODE in
  dry)
    X=$L/dry; mkdir -p $X
    hashes $X/CODE_HASHES.txt
    ex $X bcheck --data r2 --pool $POOL --sets eval --limit 8 --batch 8 --batch-check
    ex $X r2 --data r2 --pool $POOL --sets mem,cal,eval --limit 120 --batch 8 --noise-ref $D/eval_set.json
    ex $X se2e --data se2e --se2e-root $SE --sets se2e --limit 120 --batch 8
    $PY tools/nov0/nov0_gate.py $X/eval.meta.jsonl /data/harvest/logs/ma2/eval_c0.jsonl \
      /data/harvest/logs/sr0/sr0_c0.jsonl > $X/gate.json 2>&1; echo "gate rc=$? $(ts)"
    nice $PY tools/nov0/nov0_latency.py --dir $X --out $X/latency.json --n 20 --warm 5 > $X/latency.out 2>&1
    echo "latency rc=$? $(ts)"
    $PY tools/nov0/nov0_verdict.py --dir $X --latency $X/latency.json --out $X/verdict.json --boot 50 --boot2 20 \
      > $X/verdict.out 2>&1; echo "verdict smoke rc=$? $(ts)"
    touch $X/dry.done;;
  drynoise)  # dry-run path check with E-SR0 noise numbering: 120 evenly spaced ids of the E-MA2 eval set
    X=$L/drynoise; mkdir -p $X
    ex $X r2 --data r2 --pool $POOL --sets eval --limit 120 --batch 8 --noise-ref $D/eval_set.json --only-ref
    $PY tools/nov0/nov0_gate.py $X/eval.meta.jsonl /data/harvest/logs/ma2/eval_c0.jsonl \
      /data/harvest/logs/sr0/sr0_c0.jsonl > $X/gate.json 2>&1; echo "gate rc=$? $(ts)"
    touch $X/drynoise.done;;
  A)
    X=$L/feat; mkdir -p $X
    hashes $L/CODE_HASHES.txt
    ex $X r2 --data r2 --pool $POOL --sets mem,cal,eval --batch 8 --noise-ref $D/eval_set.json
    ex $X se2e --data se2e --se2e-root $SE --sets se2e --batch 8
    touch $L/A.done;;
  gate)
    $PY tools/nov0/nov0_gate.py $L/feat/eval.meta.jsonl /data/harvest/logs/ma2/eval_c0.jsonl \
      /data/harvest/logs/sr0/sr0_c0.jsonl > $L/gate.json 2>&1; echo "gate rc=$? $(ts)";;
  latency)
    nice $PY tools/nov0/nov0_latency.py --dir $L/feat --out $L/latency.json > $L/latency.out 2>&1
    echo "latency rc=$? $(ts)";;
  verdict)
    $PY tools/nov0/nov0_verdict.py --dir $L/feat --latency $L/latency.json --out $L/verdict.json \
      --expect-eval 7308 > $L/verdict.out 2>&1; echo "verdict rc=$? $(ts)";;
esac

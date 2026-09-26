#!/bin/bash
# E-CONF driver (docs/stage3/prereg_conf.md). usage: run_conf.sh <code dir> build|dry|A|gate|verdict
#   build   : CPU, held-out views of never-trained R2_TRAIN episodes -> $V (heldout.json)
#   dry     : GPU 2, 40 evenly spaced snapshots per unit + gate + verdict smoke -> $L/dry (outputs not printed)
#   A       : GPU 2, full extraction: r2_c0_cal, r2_c0_test, r2_c1_cal, r2_c1_test, se2e_s1, se2e_s2 -> $L/ext
#   gate    : G1 on $L/ext (E-NOV0 eval.meta, E-SR1c eval_c1, E-SR0 sr0_motion_s1/s2)
#   verdict : conf_verdict.py on $L/ext
set -uo pipefail
source /data/harvest/env.sh
C=$1; MODE=$2; PY=/data/harvest/venv_train/bin/python
L=/data/harvest/logs/conf; V=/data/harvest/data/conf; D=/data/harvest/data/ma2; N=/data/harvest/data/se2e_c1
C0=/data/harvest/ckpt/ma2/c0/last; C1=/data/harvest/ckpt/sr1c/c1/last; SE=/data/harvest/ckpt/se2e_confirm
mkdir -p $L
cd $C
export PYTHONPATH=$C OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=8 CUDA_VISIBLE_DEVICES=2
CAL=$(ls -d $D/view/*/*/P* | grep -v jsonl | paste -sd,)
SDATA="--data se2e --se2e-root $N/conv --se2e-t-root $N/conv --motion-line se2e-motion@v1 --motion-bins $N/motion_bins.json --seed 0"
ts() { date -u +%FT%TZ; }
ex() {  # ex <out jsonl> <args...>
  local o=$1; shift
  echo "$(basename $o) start $(ts)"
  nice $PY tools/conf/conf_extract.py --out $o --batch 8 --k-extra 4 --seed 0 "$@" > ${o%.jsonl}.out 2>&1
  local rc=$?
  echo "$(basename $o) rc=$rc $(ts)"
}
hashes() {
  { ts; sha256sum tools/conf/*.py tools/conf/run_conf.sh tools/nov0/nov0_lib.py harvest/train/stageb_train.py \
      harvest/train/stageb_model.py harvest/train/stageb_expert.py harvest/train/stageb_data.py \
      harvest/train/prefix_share.py harvest/train/sr1c_film.py harvest/runtime/calibration.py \
      harvest/analysis/stats.py $C0/stageb.json $C1/stageb.json $SE/motion_s1/last/stageb.json \
      $SE/motion_s2/last/stageb.json $V/heldout.json; } > $1
}
units() {  # units <dir> <extra args>
  local X=$1; shift
  local T=$(ls -d $V/view/*/*/P* | grep -v jsonl | paste -sd,)
  ex $X/r2_c0_cal.jsonl --data r2 --pool $CAL --set cal --noise-ref $D/eval_set.json --ckpt $C0 --latency 200 "$@"
  ex $X/r2_c0_test.jsonl --data r2 --pool $T --set test --ckpt $C0 "$@"
  ex $X/r2_c1_cal.jsonl --data r2 --pool $CAL --set cal --noise-ref $D/eval_set.json --ckpt $C1 --latency 200 "$@"
  ex $X/r2_c1_test.jsonl --data r2 --pool $T --set test --ckpt $C1 "$@"
  ex $X/se2e_s1.jsonl $SDATA --set se2e --ckpt $SE/motion_s1/last --latency 200 "$@"
  ex $X/se2e_s2.jsonl $SDATA --set se2e --ckpt $SE/motion_s2/last --latency 200 "$@"
}
gates() {  # gates <dir> -> <dir>/gate.json lines
  local X=$1
  { $PY tools/conf/conf_gate.py $X/r2_c0_cal.jsonl /data/harvest/logs/nov0/feat/eval.meta.jsonl; echo "g1 c0 rc=$?"
    $PY tools/conf/conf_gate.py $X/r2_c1_cal.jsonl /data/harvest/logs/sr1c/eval_c1.jsonl; echo "g1 c1 rc=$?"
    $PY tools/conf/conf_gate.py $X/se2e_s1.jsonl /data/harvest/logs/sr0/sr0_motion_s1.jsonl; echo "g1 s1 rc=$?"
    $PY tools/conf/conf_gate.py $X/se2e_s2.jsonl /data/harvest/logs/sr0/sr0_motion_s2.jsonl; echo "g1 s2 rc=$?"
  } > $X/gate.out 2>&1
}
case $MODE in
  build)
    mkdir -p $V
    OMP_NUM_THREADS=1 nice $PY tools/conf/conf_build.py --src /data/harvest/r2/train --dst $V --cap 100 > $L/build.out 2>&1
    echo "build rc=$? $(ts)";;
  dry)
    X=$L/dry; mkdir -p $X
    hashes $X/CODE_HASHES.txt
    units $X --limit 40
    gates $X; echo "dry gate done $(ts)"
    $PY tools/conf/conf_verdict.py --dir $X --heldout $V/heldout.json --out $X/verdict.json --boot 20 \
      > $X/verdict.out 2>&1; echo "verdict smoke rc=$? $(ts)"
    touch $X/dry.done;;
  A)
    X=$L/ext; mkdir -p $X
    hashes $L/CODE_HASHES.txt
    units $X
    touch $L/A.done;;
  gate)
    gates $L/ext; echo "gate done $(ts)";;
  verdict)
    $PY tools/conf/conf_verdict.py --dir $L/ext --heldout $V/heldout.json --out $L/verdict.json \
      --expect r2_c0_cal=7308,r2_c1_cal=7308,r2_c0_test=8208,r2_c1_test=8208,se2e_s1=1799,se2e_s2=1799 > $L/verdict.out 2>&1
    echo "verdict rc=$? $(ts)";;
esac

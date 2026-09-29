#!/bin/bash
# E-SR1b driver (docs/stage3/prereg_sr1b.md). usage: run_sr1b.sh <code dir> <mode> [gpu]
#   dry <lane>   : 20-step training of the lane's first arm (+ C0 s1 on M3) on the full data, sr1b_eval of the first
#                  12 snapshots (full w grid), train gate; M2 also the full-set reproduction eval of E-MA2 C0 (w = 1)
#                  and the repro gate -> $L/dry
#   X0|X1|M2|M3  : main lanes (train -> train gate -> eval, twice); M2 then waits for every lane and runs latency
#   verdict      : manifest + sr1b_verdict.py
# Lanes (pod juhyoung-native-7a2a-x2 GPUs 0 / 1 = X0 / X1, pod juhyoung-native-7a2a GPUs 2 / 3 = M2 / M3):
#   X0: A s0 -> B s1     X1: B s0 -> AB s1     M2: AB s0 -> C0 s1 -> latency
#   M3: A s1 -> A02 s0 -> eval of the E-MA2 C0 checkpoint (= C0 s0, w = 1) + repro gate
# Arms: C0 = E-MA2 C0 recipe (--ma2 c0, options off); A = dropout 0.3; B = hindsight relabel; AB = both;
#       A02 = dropout 0.2 (one seed, outside the rule). Seeds = the training --seed (eval noise seed 0 always).
set -uo pipefail
source /data/harvest/env.sh
C=$1; MODE=$2; PY=/data/harvest/venv_train/bin/python
L=/data/harvest/logs/sr1b; CK=/data/harvest/ckpt/sr1b; D=/data/harvest/data/ma2
SR0=/data/harvest/logs/sr0/sr0_c0.jsonl; MA2=/data/harvest/logs/ma2/eval_c0.jsonl; C0=/data/harvest/ckpt/ma2/c0/last
W="1,1.5,2,3,5,8"
mkdir -p $L $CK
cd $C
export PYTHONPATH=$C OMP_WAIT_POLICY=PASSIVE
case $MODE in X0|X1) export OMP_NUM_THREADS=5;; *) export OMP_NUM_THREADS=8;; esac
case $MODE in X0) G=0;; X1) G=1;; M2) G=2;; M3) G=3;; *) G=${3:-2};; esac
[ "$MODE" = dry ] && case ${3:-} in X0) G=0; export OMP_NUM_THREADS=5;; X1) G=1; export OMP_NUM_THREADS=5;;
  M2) G=2;; M3) G=3;; esac
export CUDA_VISIBLE_DEVICES=$G
POOL=$(ls -d $D/view/*/*/P* | grep -v jsonl | paste -sd,)
EROWS=$(for f in ${POOL//,/ }; do echo -n "$f.eval.stageb.jsonl,"; done | sed 's/,$//')
RDATA="--data r2 --pool $POOL --rows $EROWS --eval-set $D/eval_set.json --grip --seed 0"
ts() { date -u +%FT%TZ; }
opts() {  # opts <arm>
  case $1 in C0) echo "";; A) echo "--sr1b-drop 0.3";; B) echo "--sr1b-relabel";;
    AB) echo "--sr1b-drop 0.3 --sr1b-relabel";; A02) echo "--sr1b-drop 0.2";; esac
}
grid() { case $1 in A|AB|A02) echo $W;; *) echo 1;; esac; }
train() {  # train <arm> <seed> <out root> <steps>
  local arm=$1 seed=$2 root=$3 steps=$4 run=$1_s$2
  echo "train $run start $(ts) gpu $G"
  nice $PY -m harvest.train.sr1b train --data r2 --pool $POOL --ma2 c0 --ma2-root $D $(opts $arm) --run $run \
    --out-root $root --max-steps $steps --batch 8 --lr 1e-4 --lr-heads 1e-4 --seed $seed --val-per-kind 50 \
    --val-seed 0 --eval-every 500 --overwrite > $root/train_$run.out 2>&1
  echo "train $run rc=$? $(ts)"
  local rl=""; case $arm in B|AB) rl="--relabel";; esac
  $PY tools/sr1b/sr1b_gate.py train $root/$run/log.jsonl $root/train_$run.out $rl --max-min 90 \
    > $root/gate_train_$run.out 2>&1
  local g=$?
  echo "gate train $run rc=$g $(ts)"
  return $g
}
ev() {  # ev <arm> <seed> <ckpt> <out prefix> [--limit N]
  local arm=$1 seed=$2 ck=$3 o=$4; shift 4
  echo "eval $(basename $o) start $(ts) gpu $G"
  nice $PY tools/sr1b/sr1b_eval.py $RDATA --ckpt $ck --cfg-w $(grid $arm) --out $o "$@" > $o.out 2>&1
  echo "eval $(basename $o) rc=$? $(ts)"
}
hashes() {
  { ts; sha256sum tools/sr1b/*.py tools/sr1b/*.sh tools/sr0/*.py harvest/train/sr1b.py harvest/train/r2_ma2.py \
      harvest/train/stageb_train.py harvest/train/stageb_model.py harvest/train/stageb_expert.py \
      harvest/train/stageb_data.py harvest/train/prefix_share.py harvest/train/se2e_data.py $D/eval_set.json; } > $1
}
lane() {  # lane <arm1> <seed1> <arm2> <seed2>
  hashes $L/CODE_HASHES_$MODE.txt
  for pair in "$1 $2" "$3 $4"; do
    set -- $pair
    if ! train $1 $2 $CK 2000; then echo "STOP lane $MODE: train gate $1_s$2 failed $(ts)"; touch $L/$MODE.fail; exit 3; fi
    cp $CK/train_$1_s$2.out $CK/$1_s$2/train.out
    ev $1 $2 $CK/$1_s$2/last $L/ev_$1_s$2
  done
}
case $MODE in
  dry)
    LN=$3; X=$L/dry; XC=/data/harvest/tmp/sr1b/ckpt; mkdir -p $X $XC
    hashes $X/CODE_HASHES_$LN.txt
    case $LN in X0) arms="A 0";; X1) arms="B 0";; M2) arms="AB 0";; M3) arms="A02 0 C0 1";; esac
    set -- $arms
    while [ $# -ge 2 ]; do
      train $1 $2 $XC 20 || echo "DRY GATE FAILED $1_s$2"
      ev $1 $2 $XC/$1_s$2/last $X/ev_$1_s$2 --limit 12
      shift 2
    done
    if [ "$LN" = M2 ]; then
      ev C0 0 $C0 $X/repro_c0_s0
      $PY tools/sr1b/sr1b_gate.py repro $X/repro_c0_s0_w1.jsonl $SR0 $MA2 > $X/gate_repro.out 2>&1
      echo "gate repro rc=$? $(ts)"
    fi
    touch $X/dry_$LN.done;;
  X0) lane A 0 B 1; touch $L/X0.done;;
  X1) lane B 0 AB 1; touch $L/X1.done;;
  M3)
    lane A 1 A02 0
    ev C0 0 $C0 $L/ev_C0_s0
    $PY tools/sr1b/sr1b_gate.py repro $L/ev_C0_s0_w1.jsonl $SR0 $MA2 > $L/gate_repro.out 2>&1
    echo "gate repro rc=$? $(ts)"
    touch $L/M3.done;;
  M2)
    lane AB 0 C0 1
    touch $L/M2.done
    until [ -f $L/X0.done -o -f $L/X0.fail ] && [ -f $L/X1.done -o -f $L/X1.fail ] && [ -f $L/M3.done -o -f $L/M3.fail ]; do
      sleep 60
    done
    echo "latency start $(ts)"
    nice $PY tools/sr1b/sr1b_latency.py --ckpt $C0 --pool $POOL --rows $EROWS --eval-set $D/eval_set.json \
      --out $L/latency.json > $L/latency.out 2>&1
    echo "latency rc=$? $(ts)"
    touch $L/M2.latency.done;;
  verdict)
    $PY tools/sr1b/make_manifest.py $L "$W" > $L/manifest.json
    $PY tools/sr1b/sr1b_verdict.py --manifest $L/manifest.json --latency $L/latency.json --n 1200 \
      --out $L/verdict.json > $L/verdict.out 2>&1
    echo "verdict rc=$? $(ts)";;
esac

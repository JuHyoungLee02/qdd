#!/bin/bash
# E-SR1c driver (docs/stage3/prereg_sr1c.md). usage: run_sr1c.sh <code dir> <mode> [arm]
#   gen       CPU: branch rows of every far fit snapshot -> $B (+ stats.json)
#   gbr       GPU 0 (Isaac, CPU PhysX, no rendering): G-br replay of >= 200 branches (100 dr + 100 standard, parallel)
#   evalc0    GPU 1: C0 (E-MA2 c0 checkpoint) on the 1,200 eval snapshots + chunk latency (50 x 4)
#   train A   GPU 1: train arm A (c1 | c2 | s); evalA: evaluate arm A
#   gates / verdict
#   dry       pipeline check: 5 far snapshots per folder -> dev branches, G-br on 8 branches, 50-step C1 / C2 runs,
#             12-snapshot evaluations of C0 / C1 / C2, gates and verdict smoke (values not read) -> $L/dry
set -uo pipefail
source /data/harvest/env.sh
C=$1; MODE=$2; ARM=${3:-}; PY=/data/harvest/venv_train/bin/python
L=/data/harvest/logs/sr1c; D=/data/harvest/data/ma2; B=/data/harvest/data/sr1c/branches; CK=/data/harvest/ckpt/sr1c
MA2=/data/harvest/logs/ma2; SR0=/data/harvest/logs/sr0; R2=/data/harvest/r2/train
mkdir -p $L
cd $C
export PYTHONPATH=$C OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=8
POOL=$(ls -d $D/view/*/*/P* | grep -v jsonl | paste -sd,)
EROWS=$(for f in ${POOL//,/ }; do echo -n "$f.eval.stageb.jsonl,"; done | sed 's/,$//')
EDATA="--data r2 --pool $POOL --rows $EROWS --eval-set $D/eval_set.json --grip --seed 0 --r2 $R2"
TRAIN="--data r2 --pool $POOL --ma2 c0 --ma2-root $D --batch 8 --eval-every 500 --val-per-kind 50 --max-steps 2000 --seed 0"
ts() { date -u +%FT%TZ; }
hashes() {
  { ts; sha256sum tools/sr1c/*.py tools/sr1c/*.sh tools/sr0/sr0_eval.py tools/sr0/sr0_verdict.py \
      harvest/train/sr1c*.py harvest/train/stageb_train.py harvest/train/stageb_model.py harvest/train/stageb_expert.py \
      harvest/train/stageb_data.py harvest/train/prefix_share.py harvest/train/r2_ma2.py $D/eval_set.json; } > $1
}
armflags() {
  case $1 in
    c1) echo "--cf-branch $2 --cf-frac 0.5";;
    c2) echo "--cf-branch $2 --cf-frac 0.5 --dec-cond adaln@v1";;
    *) echo "unknown arm $1" >&2; exit 2;;
  esac
}
ev() {  # ev <out prefix> <ckpt> [extra args]
  local o=$1 ck=$2; shift 2
  rm -f $o.jsonl
  echo "$(basename $o) eval start $(ts) gpu $CUDA_VISIBLE_DEVICES"
  nice $PY tools/sr1c/sr1c_eval.py $EDATA --ckpt $ck --out $o.jsonl "$@" > $o.out 2>&1
  echo "$(basename $o) eval rc=$? $(ts)"
}
isaac() {  # isaac <inst> <variant> <n> <out> <branches>
  ( cd /data/harvest/ir && IR_ROOT=cyclo IR_INST=$1 CUDA_VISIBLE_DEVICES=0 nice ./ir_run.sh env \
      HOME=/data/harvest/home TMPDIR=/data/harvest/tmp XDG_CACHE_HOME=/data/harvest/cache \
      WARP_CACHE_PATH=/data/harvest/cache/warp PYTHONPATH=$C OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=4 \
      /isaac-sim/python.sh $C/tools/sr1c/replay_check.py --branches $5 --variant $2 --n $3 --out $4 ) > $4.log 2>&1
  echo "isaac $1 rc=$? $(ts)"
}
case $MODE in
  gen)
    hashes $L/CODE_HASHES_gen.txt
    OMP_NUM_THREADS=1 nice $PY tools/sr1c/gen_branches.py --out $B --procs 12 > $L/gen.out 2>&1
    echo "gen rc=$? $(ts)";;
  gbr)
    isaac sr1c_brA dr 100 $L/gbr_dr.jsonl $B &
    isaac sr1c_brB standard 100 $L/gbr_standard.jsonl $B &
    wait; touch $L/gbr.done;;
  evalc0)
    export CUDA_VISIBLE_DEVICES=1
    hashes $L/CODE_HASHES_eval.txt
    ev $L/eval_c0 /data/harvest/ckpt/ma2/c0/last --latency 50
    touch $L/evalc0.done;;
  train)
    export CUDA_VISIBLE_DEVICES=1
    hashes $L/CODE_HASHES_train_$ARM.txt
    echo "train $ARM start $(ts)"
    nice $PY -m harvest.train.sr1c train $TRAIN $(armflags $ARM $B) --run $ARM --out-root $CK > $L/train_$ARM.out 2>&1
    echo "train $ARM rc=$? $(ts)"
    touch $L/train_$ARM.done;;
  eval)
    export CUDA_VISIBLE_DEVICES=1
    ev $L/eval_$ARM $CK/$ARM/last --latency 50
    touch $L/eval_$ARM.done;;
  verdict)
    X=""; [ -f $L/eval_c2.jsonl ] && X="--c2 $L/eval_c2.jsonl"
    $PY tools/sr1c/sr1c_verdict.py --c0 $L/eval_c0.jsonl --c1 $L/eval_c1.jsonl $X --n 1200 --out $L/verdict.json \
      > $L/verdict.out 2>&1
    echo "verdict rc=$? $(ts)";;
  dry)
    X=$L/dry; mkdir -p $X; export CUDA_VISIBLE_DEVICES=1
    hashes $X/CODE_HASHES.txt
    OMP_NUM_THREADS=1 nice $PY tools/sr1c/gen_branches.py --out $X/branches --limit-snaps 5 --procs 12 > $X/gen.out 2>&1
    echo "dry gen rc=$? $(ts)"
    isaac sr1c_dry dr 8 $X/gbr_dr.jsonl $X/branches
    for A in c1 c2; do
      nice $PY -m harvest.train.sr1c train ${TRAIN/--max-steps 2000/--max-steps 50} --eval-every 25 --val-per-kind 2 \
        $(armflags $A $X/branches) --run $A --out-root $X/ckpt --overwrite > $X/train_$A.out 2>&1
      echo "dry train $A rc=$? $(ts)"
    done
    ev $X/eval_c0 /data/harvest/ckpt/ma2/c0/last --limit 12 --latency 3
    ev $X/eval_c1 $X/ckpt/c1/last --limit 12 --latency 3
    ev $X/eval_c2 $X/ckpt/c2/last --limit 12 --latency 3
    $PY tools/sr1c/sr1c_gate.py ga $X/eval_c0.jsonl > $X/gate_ga.out 2>&1; echo "dry ga rc=$?"
    $PY tools/sr1c/sr1c_gate.py g1 $X/eval_c0.jsonl $SR0/sr0_c0.jsonl > $X/gate_g1.out 2>&1; echo "dry g1 rc=$?"
    for A in c1 c2; do
      $PY tools/sr1c/sr1c_gate.py g0 $X/train_$A.out --n-registered $(grep -o '"branches": [0-9]*' $X/gen.out | tail -1 | grep -o '[0-9]*$') > $X/gate_g0_$A.out 2>&1; echo "dry g0 $A rc=$?"
      $PY tools/sr1c/sr1c_gate.py cfg $MA2/train_c0.out $X/train_$A.out > $X/gate_cfg_$A.out 2>&1; echo "dry cfg $A rc=$?"
    done
    $PY tools/sr1c/sr1c_verdict.py --c0 $X/eval_c0.jsonl --c1 $X/eval_c1.jsonl --c2 $X/eval_c2.jsonl --n 12 \
      --boot 100 --out $X/verdict.json > $X/verdict.out 2>&1
    echo "dry verdict rc=$? $(ts)"
    touch $X/dry.done;;
  *) echo "mode?"; exit 2;;
esac

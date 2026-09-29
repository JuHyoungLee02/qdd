#!/bin/bash
# E-VLA-solo driver (docs/stage3/prereg_vla_solo.md). Main pod, Isaac + fused VLA on GPU 3 ONLY (GPU 2 never renders;
# GPU 0 / 1 / x2 not used). No paid call (--astra none --couple off; vla_closed.py refuses otherwise).
# usage: run_vla.sh <code dir> dry | main | arm <NAME> | analyze
#   code dir = /data/harvest/code_vla_solo_<commit> (E-Couple dry-run copy 9322853 + tools/vla_alone of the commit)
set -uo pipefail
source /data/harvest/env.sh
C=$1; MODE=$2
PY=/data/harvest/venv_train/bin/python
O=/data/harvest/out/vla_solo; L=/data/harvest/logs/vla_solo
CK=/data/harvest/ckpt/sr1c/c1/last
mkdir -p $O $L
cd $C
export PYTHONPATH=$C OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=8
ts() { date -u +%FT%TZ; }
run() {  # run <out> <backend> <model> <condition> <speed> <seeds> <variants> <max s> [extra]
  echo "$(basename $1) start $(ts)" >> $L/lanes.out
  nice $PY tools/vla_alone/vla_closed.py --model $3 --backend $2 --out $1 --split dev --seeds $6 --variants $7 \
    --conditions $4 --max-seconds $8 --couple off --astra none --isaac-gpu 3 --gpu 3 --parallel \
    --inst-prefix vla_solo_$(basename $1) --vla-speed $5 --vla-video-hz 2 ${9:-} > $1.out 2>&1
  echo "$(basename $1) rc=$? $(ts)" >> $L/lanes.out
}
arm() {  # arm <NAME> <seeds> <variants> <max s> <out root>
  case $1 in
    A) run $5/A fused $CK C5 1.0 $2 $3 $4;;
    B) run $5/B fused $CK C3 1.0 $2 $3 $4;;
    C) run $5/C fused $CK C3 0.75 $2 $3 $4;;
    D) run $5/D fused $CK C3 0.5 $2 $3 $4;;
    E) run $5/E fused $CK C5 0.5 $2 $3 $4;;
    F) run $5/F modular mock C5 1.0 $2 $3 $4;;
    G) run $5/G fused mock_fused C5 1.0 $2 $3 $4 "--vla-noop 1";;
    *) echo "arm?"; exit 2;;
  esac
}
case $MODE in
  dry)
    mkdir -p $O/dry
    for a in A D F G; do arm $a 0 standard 15 $O/dry; done
    $PY tools/vla_alone/analyze_vla.py --n 1 $(for a in A D F G; do echo --arm $a=$O/dry/$a; done) \
      --out $O/dry/verdict_dry.json > $O/dry/analyze.out 2>&1; echo "analyze rc=$? $(ts)" >> $L/lanes.out;;
  main)
    for a in F G A B C D E; do arm $a 0-5 standard,dr 60 $O; done
    bash $0 $C analyze;;
  arm) arm $3 0-5 standard,dr 60 $O;;
  dryarm) mkdir -p $O/dry; arm $3 0 standard 15 $O/dry;;
  analyze)
    $PY tools/vla_alone/analyze_vla.py --n 12 $(for a in A B C D E F G; do echo --arm $a=$O/$a; done) \
      --out $O/verdict.json > $O/analyze.out 2>&1
    echo "analyze rc=$? $(ts)" >> $L/lanes.out
    sha256sum $O/verdict.json | cut -c1-16 > $O/verdict.sha;;
  *) echo "mode?"; exit 2;;
esac

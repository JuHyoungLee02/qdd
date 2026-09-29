#!/bin/bash
# E-Couple dry run driver (docs/stage3/prereg_couple_dry.md). Main pod, GPU 1 ONLY: Isaac render + fused VLA server +
# the local Qwen3-VL stream model. No paid call (--astra none, --couple-upper local; dry_closed.py refuses otherwise).
# usage: run_dry.sh <code dir> serve | smoke | main | analyze <out> | sheets <out> | stop
set -uo pipefail
source /data/harvest/env.sh
C=$1; MODE=$2
PY=/data/harvest/venv_train/bin/python; PYV=/data/harvest/venv_vllm/bin/python
L=/data/harvest/logs/couple_dry; O=/data/harvest/out/couple_dry
CK=/data/harvest/ckpt/sr1c/c1/last
PORT=8371; NAME=qwen8b_dry
mkdir -p $L $O
cd $C
export PYTHONPATH=$C OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=8
ts() { date -u +%FT%TZ; }
common() {  # common <out> <seeds> <variants> <max s>
  echo "$(basename $1) start $(ts)"
  nice $PY tools/couple_dry/dry_closed.py --model $CK --backend fused --out $1 --split dev --seeds $2 \
    --variants $3 --conditions C5 --max-seconds $4 --couple off,serial --couple-upper local \
    --couple-local-url http://127.0.0.1:$PORT --couple-local-model $NAME --astra none \
    --couple-ledger $1/ledger.jsonl --isaac-gpu 1 --gpu 1 --inst-prefix couple_dry > $1.out 2>&1
  echo "$(basename $1) rc=$? $(ts)"
}
case $MODE in
  serve)
    export VLLM_CACHE_ROOT=/data/harvest/cache/vllm TRITON_CACHE_DIR=/data/harvest/cache/triton
    export TORCHINDUCTOR_CACHE_DIR=/data/harvest/cache/inductor CUDA_CACHE_PATH=/data/harvest/cache/nv
    export FLASHINFER_WORKSPACE_BASE=/data/harvest/cache/flashinfer VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1
    export VLLM_USE_FLASHINFER_SAMPLER=0 CUDA_VISIBLE_DEVICES=1 VLLM_BATCH_INVARIANT=1
    export CC=/data/harvest/jevl/bin/cc ZIG_GLOBAL_CACHE_DIR=/data/harvest/cache/zig
    setsid nohup /data/harvest/venv_vllm/bin/vllm serve /data/harvest/models/Qwen3-VL-8B-Instruct \
      --served-model-name $NAME --host 127.0.0.1 --port $PORT --dtype bfloat16 --max-model-len 12288 \
      --gpu-memory-utilization 0.22 --enable-prefix-caching \
      --limit-mm-per-prompt '{"image":3,"video":0,"audio":0}' --seed 0 > $L/qwen.log 2>&1 < /dev/null &
    for i in $(seq 1 180); do
      curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$PORT/health 2>/dev/null | grep -q 200 && { echo "qwen ready $(ts)"; exit 0; }
      grep -q "Traceback" $L/qwen.log && { echo "qwen failed $(ts)"; tail -20 $L/qwen.log; exit 1; }
      sleep 5
    done
    echo "qwen not ready after 900 s"; exit 1;;
  smoke) common $O/smoke 0 standard 20;;
  main) common $O/main 0-5 standard,dr 60;;
  analyze) $PY tools/couple_dry/analyze.py --out $3 > $3/dry_analysis.out 2>&1; echo "analyze rc=$? $(ts)";;
  sheets)
    OUT=$3; S=$OUT/sheets; mkdir -p $S
    for d in $OUT/video/*/*/*; do
      tag=$(echo ${d#$OUT/video/} | tr '/' '_')
      $PYV tools/couple_dry/make_video.py frames --dir $d --mp4 $S/$tag.mp4 --sheet $S/$tag.jpg --n 12 > $S/$tag.out 2>&1
    done
    for f in $(find $OUT -name "*.jsonl" -path "*ours*" | grep cp-serial); do
      r=$(dirname $(dirname $(dirname $f))); tag=$(basename $(dirname $r))_$(basename $r)_$(basename $f .jsonl)
      $PYV tools/couple_dry/make_video.py requests --sidecar $f --sheet $S/req_$tag.jpg --n 6 > $S/req_$tag.out 2>&1
    done
    ls $S | wc -l;;
  stop) bash tools/couple_dry/stop_dry.sh;;
  *) echo "mode?"; exit 2;;
esac

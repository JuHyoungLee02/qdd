#!/bin/bash
# vLLM for the prompt health check (user-log 96): main pod GPU 3 only, three images per prompt (the coupling prompt
# sends head + both wrists), greedy by default (the client sets temperature / seed per call).
# usage: serve.sh <model_dir_name> <served_name> <port> [gpu_mem_util]   e.g. serve.sh Qwen3-VL-8B-Instruct qwen8b 8361 0.40
source /data/harvest/env.sh
export VLLM_CACHE_ROOT=/data/harvest/cache/vllm TRITON_CACHE_DIR=/data/harvest/cache/triton
export TORCHINDUCTOR_CACHE_DIR=/data/harvest/cache/inductor CUDA_CACHE_PATH=/data/harvest/cache/nv
export FLASHINFER_WORKSPACE_BASE=/data/harvest/cache/flashinfer
export VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1 VLLM_USE_FLASHINFER_SAMPLER=0
export CUDA_VISIBLE_DEVICES=3 VLLM_BATCH_INVARIANT=1 OMP_WAIT_POLICY=PASSIVE
export CC=/data/harvest/jevl/bin/cc ZIG_GLOBAL_CACHE_DIR=/data/harvest/cache/zig
M=/data/harvest/models/$1; NAME=$2; PORT=$3; UTIL=${4:-0.40}
exec /data/harvest/venv_vllm/bin/vllm serve $M --served-model-name $NAME --host 127.0.0.1 --port $PORT \
  --dtype bfloat16 --max-model-len 12288 --gpu-memory-utilization $UTIL \
  --enable-prefix-caching --limit-mm-per-prompt "{\"image\":3,\"video\":0,\"audio\":0}" --seed 0

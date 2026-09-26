#!/bin/bash
# vLLM for the R5 closed loop on GPU 3 (canon §59 supp 2026-09-26: prefix cache + multimodal cache ON, 3 images per
# prompt -- the coupling stream sends head + both wrists, BI on).
# usage: serve.sh <model_path> <served_name> <port> [gpu_mem_util]
source /data/harvest/env.sh
export VLLM_CACHE_ROOT=/data/harvest/cache/vllm TRITON_CACHE_DIR=/data/harvest/cache/triton
export TORCHINDUCTOR_CACHE_DIR=/data/harvest/cache/inductor CUDA_CACHE_PATH=/data/harvest/cache/nv
export FLASHINFER_WORKSPACE_BASE=/data/harvest/cache/flashinfer
export VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1 VLLM_USE_FLASHINFER_SAMPLER=0
export CUDA_VISIBLE_DEVICES=3 VLLM_BATCH_INVARIANT=1
export CC=/data/harvest/jevl/bin/cc ZIG_GLOBAL_CACHE_DIR=/data/harvest/cache/zig
M=$1; NAME=$2; PORT=$3; UTIL=${4:-0.45}
exec /data/harvest/venv_vllm/bin/vllm serve $M --served-model-name $NAME --host 127.0.0.1 --port $PORT \
  --dtype bfloat16 --max-model-len 8192 --gpu-memory-utilization $UTIL \
  --enable-prefix-caching --limit-mm-per-prompt "{\"image\":3,\"video\":0,\"audio\":0}" \
  --logprobs-mode raw_logprobs --seed 0

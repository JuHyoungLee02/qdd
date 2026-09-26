#!/bin/bash
# vLLM server for E-STRIP8 (copy of tools/teach_pt/vllm.sh: bf16, max_model_len 12288, prefix caching,
# greedy decoding from the client). usage: vllm.sh <gpu> <model dir> <served name pt_*> <port> [gpu mem util]
# log -> /data/harvest/logs/strip8/vllm_<name>.log ; stop: tools/teach_strip8/stop.sh <name>
source /data/harvest/env.sh
G=$1; M=$2; N=$3; PORT=$4; U=${5:-0.40}
L=/data/harvest/logs/strip8; mkdir -p $L
export CUDA_VISIBLE_DEVICES=$G TEACH_STRIP8_JOB=$N
# same environment as tools/prompt_health/serve.sh and the astra_solo / couple_dry Qwen runs (C compiler for Triton,
# caches under /data, batch-invariant kernels)
export VLLM_CACHE_ROOT=/data/harvest/cache/vllm TRITON_CACHE_DIR=/data/harvest/cache/triton
export TORCHINDUCTOR_CACHE_DIR=/data/harvest/cache/inductor CUDA_CACHE_PATH=/data/harvest/cache/nv
export FLASHINFER_WORKSPACE_BASE=/data/harvest/cache/flashinfer VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1
export VLLM_USE_FLASHINFER_SAMPLER=0 VLLM_BATCH_INVARIANT=1 OMP_WAIT_POLICY=PASSIVE
export CC=/data/harvest/jevl/bin/cc ZIG_GLOBAL_CACHE_DIR=/data/harvest/cache/zig
echo "START $(date -u +%FT%TZ) host=$(hostname) gpu=$G $M $N $PORT" >> $L/vllm_$N.log
exec /data/harvest/venv_vllm/bin/vllm serve $M --host 127.0.0.1 --port $PORT --dtype bfloat16 --max-model-len 12288 \
  --served-model-name $N --gpu-memory-utilization $U --enable-prefix-caching \
  --limit-mm-per-prompt '{"image":3,"video":0,"audio":0}' --seed 0 >> $L/vllm_$N.log 2>&1

#!/bin/bash
# vLLM server for Qwen3.5-35B-A3B (E-TEACH-35B). Environment block copied from tools/teach_l8/vllm.sh (P123: C
# compiler for Triton, caches under /data, batch-invariant kernels). Thinking is OFF by default for every request
# (--default-chat-template-kwargs; the runtime client LocalVLM sends no kwargs, and the LoRA was trained with the
# non-thinking prefix); a request can still send chat_template_kwargs {"enable_thinking": true}. --reasoning-parser
# qwen3 keeps any thinking text out of message.content. --max-num-seqs 32: the hybrid model needs one Mamba (GDN)
# state block per running sequence; the default 1024 does not fit at a 0.40 memory share.
# usage: vllm.sh <gpus e.g. 0 or 0,1> <model dir> <served name q35_*> <port> [gpu mem util] [extra vllm args...]
#   FP8 checkpoint: /data/harvest/models/Qwen3.5-35B-A3B-FP8 ; BF16 / merged LoRA: its folder (add --quantization fp8
#   as an extra arg for online FP8). TP = number of GPUs given.
# log -> /data/harvest/logs/teach_35b/vllm_<name>.log ; stop: tools/teach_35b/stop.sh <name>
source /data/harvest/env.sh
G=$1; M=$2; N=$3; PORT=$4; U=${5:-0.85}; shift 5 2>/dev/null || shift $#
L=/data/harvest/logs/teach_35b; mkdir -p $L
TP=$(echo $G | tr ',' '\n' | wc -l)
export CUDA_VISIBLE_DEVICES=$G TEACH_35B_JOB=$N
export VLLM_CACHE_ROOT=/data/harvest/cache/vllm TRITON_CACHE_DIR=/data/harvest/cache/triton
export TORCHINDUCTOR_CACHE_DIR=/data/harvest/cache/inductor CUDA_CACHE_PATH=/data/harvest/cache/nv
export FLASHINFER_WORKSPACE_BASE=/data/harvest/cache/flashinfer VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1
export VLLM_USE_FLASHINFER_SAMPLER=0 VLLM_BATCH_INVARIANT=0 OMP_WAIT_POLICY=PASSIVE
export CC=/data/harvest/jevl/bin/cc ZIG_GLOBAL_CACHE_DIR=/data/harvest/cache/zig
# the pod has no CUDA toolkit: DeepGEMM (FP8 block GEMM JIT) asserts on an empty CUDA home -> use the non-JIT kernels
export VLLM_USE_DEEP_GEMM=0
# batch-invariant mode is not supported for the Gated DeltaNet layers (GDN_ATTN) of Qwen3.5 -> off; greedy one-at-a-time
# requests stay deterministic enough for readiness numbers, batched evaluation may differ by bf16 noise (P110)
echo "START $(date -u +%FT%TZ) host=$(hostname) gpu=$G tp=$TP $M $N $PORT $*" >> $L/vllm_$N.log
exec /data/harvest/venv_vllm/bin/vllm serve $M --host 127.0.0.1 --port $PORT --max-model-len 12288 \
  --served-model-name $N --gpu-memory-utilization $U --enable-prefix-caching --tensor-parallel-size $TP \
  --limit-mm-per-prompt '{"image":3,"video":0,"audio":0}' --seed 0 --reasoning-parser qwen3 --max-num-seqs 32 \
  --default-chat-template-kwargs '{"enable_thinking": false}' "$@" >> $L/vllm_$N.log 2>&1

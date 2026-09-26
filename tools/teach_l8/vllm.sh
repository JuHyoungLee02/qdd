#!/bin/bash
# vLLM server for E-TEACH-L8 (same settings as the astra_solo dry run: bf16, max_model_len 12288, prefix caching,
# greedy decoding from the client). usage: vllm.sh <gpu> <model dir> <served name l8_*> <port> [gpu mem util]
# log -> /data/harvest/logs/teach_l8/vllm_<name>.log ; stop: tools/teach_l8/stop.sh <name>
source /data/harvest/env.sh
G=$1; M=$2; N=$3; PORT=$4; U=${5:-0.40}
L=/data/harvest/logs/teach_l8; mkdir -p $L
export CUDA_VISIBLE_DEVICES=$G TEACH_L8_JOB=$N
echo "START $(date -u +%FT%TZ) host=$(hostname) gpu=$G $M $N $PORT" >> $L/vllm_$N.log
exec /data/harvest/venv_vllm/bin/vllm serve $M --host 127.0.0.1 --port $PORT --dtype bfloat16 --max-model-len 12288 \
  --served-model-name $N --gpu-memory-utilization $U --enable-prefix-caching --limit-mm-per-prompt '{"image": 3, "video": 0}' \
  >> $L/vllm_$N.log 2>&1

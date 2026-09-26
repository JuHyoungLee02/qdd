#!/bin/bash
# E-TEACH-35B: LoRA SFT of Qwen3.5-35B-A3B on any teach_l8-format JSONL (L8 data, E-OPEN8 / E-XEMB8 mixtures, ...).
# Ready to run; nothing here starts on its own. Default path = solo (astra-solo@v2 rows, the upper model driving the
# executor alone — the main track since the VLA layer was set aside); astra-couple@v2 rows are accepted in the same
# file when a row says "format": "astra-couple@v2" (harvest/teach_35b/data.py).
# usage: train.sh <code dir> <gpus e.g. 0 or 0,1,2,3> <data.jsonl> <out dir> [extra harvest.teach_35b.train args]
#   defaults come from tools/teach_35b/train.conf (next to this script); extra args override them
#   (e.g. --epochs 1 --max-steps 50 for a smoke). 1 GPU = plain python, N GPUs = torchrun DDP (a full bf16 copy per
#   GPU, about 67 GB + activations; global batch = micro x accum x N).
# job name = basename of <out dir>; log /data/harvest/logs/teach_35b/<job>.log ; stop: tools/teach_35b/stop.sh <job>
# after training: python -m harvest.teach_35b.merge --adapter <out>/epoch<k> --out <merged dir>   (CPU, venv_train)
#                 tools/teach_35b/vllm.sh <gpu> <merged dir> q35_<name> <port>
C=$1; G=$2; D=$3; O=$4; shift 4
source /data/harvest/env.sh
source "$(dirname "$0")/train.conf"
J=$(basename "$O")
L=/data/harvest/logs/teach_35b; mkdir -p $L "$O"
N=$(echo $G | tr ',' '\n' | wc -l)
# PYLIB (train.conf): optional package overlay, e.g. flash-linear-attention for the Gated DeltaNet kernels (the shared
# venv_train is not changed; transformers picks 'fla' up when importable, else its slow torch path)
export CUDA_VISIBLE_DEVICES=$G TEACH_35B_JOB=$J PYTHONPATH=$C${PYLIB:+:$PYLIB} OMP_NUM_THREADS=8
export TRITON_CACHE_DIR=/data/harvest/cache/triton TORCHINDUCTOR_CACHE_DIR=/data/harvest/cache/inductor
export CC=/data/harvest/jevl/bin/cc
ARGS=(--data "$D" --out "$O" --model "$MODEL" --epochs $EPOCHS --lr $LR --r $R --alpha $ALPHA --micro $MICRO
      --accum $ACCUM --warmup $WARMUP --workers $WORKERS --log-every $LOG_EVERY --experts-impl $EXPERTS_IMPL "$@")
V=/data/harvest/venv_train/bin
echo "START $(date -u +%FT%TZ) host=$(hostname) gpus=$G n=$N code=$C ${ARGS[*]}" >> $L/$J.log
cd $C
if [ "$N" = 1 ]; then
  $V/python -m harvest.teach_35b.train "${ARGS[@]}" >> $L/$J.log 2>&1
else
  $V/torchrun --standalone --nproc-per-node $N -m harvest.teach_35b.train "${ARGS[@]}" >> $L/$J.log 2>&1
fi
echo "EXIT $? $(date -u +%FT%TZ)" >> $L/$J.log

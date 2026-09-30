#!/bin/bash
# E-CJ fused VLA server (docs/stage3/prereg_cj1.md): the E-SR1c C1 checkpoint on a VLA card (x2 GPU 0 / x3 GPU 0,
# never a render card), HTTP on the pod IP so render lanes on other pods reach it. Environment COUPLE_JOB=<name>
# identifies it for tools/couple_joy/stop.sh.
# usage: serve_vla.sh <code dir> <gpu> <port> [ckpt]     log -> /data/harvest/logs/couple/vla_<port>.log
C=$1; G=$2; PORT=$3; CK=${4:-/data/harvest/ckpt/sr1c/c1/last}
L=/data/harvest/logs/couple; mkdir -p $L
source /data/harvest/env.sh
export CUDA_VISIBLE_DEVICES=$G COUPLE_JOB=vla_$PORT PYTHONPATH=$C OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=4
export HF_HOME=/data/harvest/cache/hf TMPDIR=/data/harvest/tmp PYTHONPYCACHEPREFIX=/data/harvest/cache/pyc_couple
echo "START $(date -u +%FT%TZ) host=$(hostname) gpu=$G port=$PORT ckpt=$CK code=$C" >> $L/vla_$PORT.log
exec /data/harvest/venv_train/bin/python -m harvest.runtime.fused_model serve --ckpt $CK --port $PORT \
  --host 0.0.0.0 >> $L/vla_$PORT.log 2>&1

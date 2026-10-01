#!/bin/bash
# E-RC0 official pi0.5 RoboCasa365 server (robocasa-benchmark/openpi ca4c6d7, config pi05_pretrain_human300, HF checkpoint
# pi05_pretrain_human300/multitask_learning/75000). Tag LIB0_JOB=pi_RC. usage: serve_rc.sh <gpu> <port>
R=/data/harvest/rc; L=/data/harvest/logs/lib0
export CUDA_VISIBLE_DEVICES=$1 XLA_PYTHON_CLIENT_MEM_FRACTION=0.35 LIB0_JOB=pi_RC HOME=/data/harvest/home TMPDIR=/data/harvest/tmp
export XDG_CACHE_HOME=$R/cache OPENPI_DATA_HOME=$R/openpi_data HF_HOME=/data/harvest/cache/hf NUMBA_DISABLE_JIT=1 MUJOCO_GL=osmesa PYOPENGL_PLATFORM=osmesa
export LD_LIBRARY_PATH=/data/harvest/lib0/mesa24/lib  # the config module imports robocasa -> mujoco (OSMesa)
cd $R/openpi
echo "START $(date -u +%FT%TZ) host=$(hostname) gpu=$1 port=$2" >> $L/serve_RC.log
exec nice $R/openpi/.venv/bin/python /data/harvest/rc/serve_rc.py --port $2 policy:checkpoint --policy.config pi05_pretrain_human300 \
  --policy.dir $R/ckpt/pi05_pretrain_human300/multitask_learning/75000 >> $L/serve_RC.log 2>&1

#!/bin/bash
# JCR training / eval / serving launcher on a JCR card (x2 GPU0 / x3 GPU0; NOW.md §3). Env as tools/teach_35b/train.sh.
# usage: train.sh <code dir> <gpu> <job name> <python args...>   log -> /data/harvest/logs/jcr/<job>.log
# identify / stop: environment JCR_JOB=<job name> (never pkill -f)
C=$1; G=$2; JOB=$3; shift 3
Q=/data/harvest
mkdir -p $Q/logs/jcr $Q/cache/tmp
export CUDA_VISIBLE_DEVICES=$G PYTHONPATH=$C JCR_JOB=$JOB HF_HOME=$Q/cache/hf TMPDIR=$Q/cache/tmp
export TRITON_CACHE_DIR=$Q/cache/triton TORCHINDUCTOR_CACHE_DIR=$Q/cache/inductor
export CC=$Q/jevl/bin/cc ZIG_GLOBAL_CACHE_DIR=$Q/cache/zig OMP_NUM_THREADS=4
cd $C
echo "START $(date -u +%FT%TZ) host=$(hostname) gpu=$G $*" >> $Q/logs/jcr/$JOB.log
$Q/venv_train/bin/python "$@" >> $Q/logs/jcr/$JOB.log 2>&1
echo "EXIT $? $(date -u +%FT%TZ)" >> $Q/logs/jcr/$JOB.log

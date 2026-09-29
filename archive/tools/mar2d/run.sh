#!/bin/bash
# MolmoAct R2 data generator runner: one Isaac process (plan docs/superpowers/plans/2026-09-26-molmoact-r2-data.md).
# usage (on the pod, from /data/harvest/mar2d):  ./run.sh <tag> <gpu> <harvest.datagen.gen args...>
# Render GPUs allowed by main's allocation: main pod GPU 0, x2 pod GPU 1 (x2 GPU 0 had DEVICE_LOST; others are busy).
# Code: the pinned copy named in /data/harvest/mar2d/CODE_DIR (git archive, LF, CODE_VERSION JSON).
# Log: /data/harvest/mar2d/logs/<tag>.log (START / EXIT lines with UTC).
Q=/data/harvest
D=$Q/mar2d
TAG=$1; GPU=$2; shift 2
HOST=$(hostname)
case "$HOST:$GPU" in
  juhyoung-native-7a2a:0|juhyoung-native-7a2a-x2:1) ;;
  *) echo "GPU $GPU on $HOST refused (render: main GPU 0, x2 GPU 1 only)" >&2; exit 2 ;;
esac
CODE=$(cat $D/CODE_DIR)
mkdir -p $D/logs $D/tmp
ENVS="HOME=$Q/home TMPDIR=$D/tmp XDG_CACHE_HOME=$Q/cache HF_HOME=$Q/cache/hf TORCH_HOME=$Q/cache/torch PIP_CACHE_DIR=$Q/cache/pip WARP_CACHE_PATH=$Q/cache/warp PYTHONPATH=$CODE PYTHONPYCACHEPREFIX=$Q/cache/pyc_mar2d OMP_WAIT_POLICY=PASSIVE"
cd $Q/ir
export CUDA_VISIBLE_DEVICES=$GPU
echo "START $(date -u +%Y-%m-%dT%H:%M:%SZ) host=$HOST gpu=$GPU code=$CODE $*" >> $D/logs/$TAG.log
IR_ROOT=cyclo IR_INST=mar2d_$TAG timeout 43200 nice -n 10 ./ir_run.sh env $ENVS /isaac-sim/python.sh -m harvest.datagen.gen "$@" >> $D/logs/$TAG.log 2>&1
echo "EXIT $? $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> $D/logs/$TAG.log

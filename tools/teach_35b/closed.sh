#!/bin/bash
# E-TEACH-35B closed loop (prereg_teach_35b.md §7): one astra-solo episode driven by a served 35B model. Copy of
# tools/teach_l8/closed.sh (same runner and limits: prompt 40 calls / 180 s, runner early end 20 calls / 60 s, sparse
# frames for videos) with teach_35b output / log paths. The runner's 'qwen8b' model kind is the generic LocalVLM
# client (any served name). Isaac on <gpu>; the vLLM server must listen on this pod's 127.0.0.1:<port>.
# usage: closed.sh <code dir> <gpu> <arm> <served name> <port> <variant> <seed>
#   -> /data/harvest/out/teach_35b/closed/<arm>/qwen8b/<variant>/s<seed>/
Q=/data/harvest
C=$1; G=$2; ARM=$3; NAME=$4; PORT=$5; V=$6; S=$7
L=$Q/logs/teach_35b; O=$Q/out/teach_35b/closed/$ARM
mkdir -p $L $O $C/tmp
TAG=closed_${ARM}_${V}_${S}
ENVS="HOME=$Q/home TMPDIR=$C/tmp XDG_CACHE_HOME=$Q/cache HF_HOME=$Q/cache/hf TORCH_HOME=$Q/cache/torch PIP_CACHE_DIR=$Q/cache/pip WARP_CACHE_PATH=$Q/cache/warp MPLCONFIGDIR=$Q/cache/mpl PYTHONPATH=$C PYTHONPYCACHEPREFIX=$Q/cache/pyc_teach_35b OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=4"
cd $Q/ir
export CUDA_VISIBLE_DEVICES=$G
echo "START $(date -u +%FT%TZ) host=$(hostname) gpu=$G $ARM $NAME $V $S" >> $L/$TAG.log
IR_ROOT=cyclo IR_INST=teach_35b_$TAG timeout 3600 nice ./ir_run.sh env $ENVS /isaac-sim/python.sh -m harvest.astra_solo.run run \
  --out $O --model qwen8b --qwen-url http://127.0.0.1:$PORT --qwen-name $NAME --variant $V --seeds $S \
  --video-first 1 --stop-calls 20 --stop-motion 60 >> $L/$TAG.log 2>&1
echo "EXIT $? $(date -u +%FT%TZ)" >> $L/$TAG.log

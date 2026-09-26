#!/bin/bash
# E-TEACH-L8 stage 2: one closed-loop astra-solo episode driven by a local vLLM model (prereg §5). Same runner and
# limits as the Astra pilot / gpt-5.2 proxy: prompt limits 40 calls / 180 s, runner early end 20 calls / 60 s,
# sparse frames on (videos). Isaac on <gpu>; the vLLM server must listen on this pod's 127.0.0.1:<port>.
# usage: closed.sh <code dir> <gpu> <arm> <served name> <port> <variant> <seed>
Q=/data/harvest
C=$1; G=$2; ARM=$3; NAME=$4; PORT=$5; V=$6; S=$7
L=$Q/logs/teach_l8; O=$Q/out/teach_l8/closed/$ARM
mkdir -p $L $O $C/tmp
TAG=closed_${ARM}_${V}_${S}
ENVS="HOME=$Q/home TMPDIR=$C/tmp XDG_CACHE_HOME=$Q/cache HF_HOME=$Q/cache/hf TORCH_HOME=$Q/cache/torch PIP_CACHE_DIR=$Q/cache/pip WARP_CACHE_PATH=$Q/cache/warp MPLCONFIGDIR=$Q/cache/mpl PYTHONPATH=$C PYTHONPYCACHEPREFIX=$Q/cache/pyc_teach_l8 OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=4"
cd $Q/ir
export CUDA_VISIBLE_DEVICES=$G
echo "START $(date -u +%FT%TZ) host=$(hostname) gpu=$G $ARM $NAME $V $S" >> $L/$TAG.log
IR_ROOT=cyclo IR_INST=teach_l8_$TAG timeout 3600 nice ./ir_run.sh env $ENVS /isaac-sim/python.sh -m harvest.astra_solo.run run \
  --out $O --model qwen8b --qwen-url http://127.0.0.1:$PORT --qwen-name $NAME --variant $V --seeds $S \
  --video-first 1 --stop-calls 20 --stop-motion 60 >> $L/$TAG.log 2>&1
echo "EXIT $? $(date -u +%FT%TZ)" >> $L/$TAG.log

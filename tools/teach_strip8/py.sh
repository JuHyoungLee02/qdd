#!/bin/bash
# Run a harvest module (E-STRIP8: teach_strip8 / teach_pt / teach_l8 train, merge, evaluate) with a /data-only environment and a job tag.
# usage: py.sh <venv: train|vllm> <gpu or -> <job name> <code dir> <module or script> [args...]
# log -> /data/harvest/logs/strip8/<job>.log ; stop: tools/teach_strip8/stop.sh <job>
source /data/harvest/env.sh
V=$1; G=$2; J=$3; C=$4; shift 4
L=/data/harvest/logs/strip8; mkdir -p $L
[ "$G" != "-" ] && export CUDA_VISIBLE_DEVICES=$G
export TEACH_STRIP8_JOB=$J PYTHONPATH=$C
PY=/data/harvest/venv_$V/bin/python
echo "START $(date -u +%FT%TZ) host=$(hostname) gpu=$G $*" >> $L/$J.log
cd $C
if [[ "$1" == *.py ]]; then $PY "$@" >> $L/$J.log 2>&1; else $PY -m "$@" >> $L/$J.log 2>&1; fi
echo "EXIT $? $(date -u +%FT%TZ)" >> $L/$J.log

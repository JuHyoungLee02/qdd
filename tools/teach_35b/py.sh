#!/bin/bash
# Run a harvest module (teach_35b train / merge / probe, teach_l8 evaluate) with a /data-only environment and a job tag.
# usage: py.sh <venv: train|vllm> <gpu or -> <job name> <code dir> <module or script> [args...]
# log -> /data/harvest/logs/teach_35b/<job>.log ; stop: tools/teach_35b/stop.sh <job>
source /data/harvest/env.sh
V=$1; G=$2; J=$3; C=$4; shift 4
L=/data/harvest/logs/teach_35b; mkdir -p $L
[ "$G" != "-" ] && export CUDA_VISIBLE_DEVICES=$G
export TEACH_35B_JOB=$J PYTHONPATH=$C
PY=/data/harvest/venv_$V/bin/python
echo "START $(date -u +%FT%TZ) host=$(hostname) gpu=$G $*" >> $L/$J.log
cd $C
if [[ "$1" == *.py ]]; then $PY "$@" >> $L/$J.log 2>&1; else $PY -m "$@" >> $L/$J.log 2>&1; fi
echo "EXIT $? $(date -u +%FT%TZ)" >> $L/$J.log

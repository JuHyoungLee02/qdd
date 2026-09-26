#!/bin/bash
# MolmoAct real-data readiness runner (plan docs/superpowers/plans/2026-09-26-molmoact-real-readiness.md).
# usage on the pod: bash run_marr.sh <decode|point|analyze> [args...]    log: /data/harvest/logs/marr/<cmd>.out
# GPU: main pod GPU 0 only (point). Code: the directory holding this script's tools/ (git archive + tools/marr).
set -u
source /data/harvest/env.sh
export OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
C="$(cd "$(dirname "$0")/../.." && pwd)"
D=/data/harvest/data/marr
L=/data/harvest/logs/marr
mkdir -p $D $L
cmd="$1"; shift
echo "START $cmd $(date -u +%Y-%m-%dT%H:%M:%SZ) code=$C $*" >> $L/$cmd.out
case "$cmd" in
  decode)  PYTHONPATH=$C nice -n 10 /data/harvest/venv_e3st/bin/python $C/tools/marr/select_decode.py --out $D "$@" >> $L/$cmd.out 2>&1 ;;
  point)   CUDA_VISIBLE_DEVICES=0 PYTHONPATH=/data/harvest/pylib_molmo2:$C nice -n 10 /data/harvest/venv_train/bin/python \
             $C/tools/marr/point.py --jobs $D/point_jobs.jsonl "$@" >> $L/$cmd.out 2>&1 ;;
  analyze) PYTHONPATH=$C nice -n 10 /data/harvest/venv_e3st/bin/python $C/tools/marr/analyze.py --data $D --logs $L "$@" >> $L/$cmd.out 2>&1 ;;
  *) echo "unknown $cmd" >> $L/$cmd.out; exit 2 ;;
esac
echo "EXIT $? $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> $L/$cmd.out

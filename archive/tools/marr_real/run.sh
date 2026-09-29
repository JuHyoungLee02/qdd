#!/bin/bash
# E-MAR-real runner (docs/stage3/prereg_marr.md). usage on the pod: bash run.sh <cmd> [args...]
#   jobs [--count-only]   CPU: RB2 frames the row trace labels need (tools/marr_real/jobs.py)
#   point <shard> <n>     GPU (CUDA_VISIBLE_DEVICES from the caller, main pod GPU 0): Molmo2-ER pointing of shard
#                         <shard> of <n> of point_jobs.jsonl (tools/marr/point.py unchanged, batch 16)
#   labels [args]         CPU: filter v2 + MolmoAct trace labels per row + stats + blind eye sample (labels.py)
# log: /data/harvest/logs/marr_real/<cmd>[_<shard>].out. Code: the directory holding this script's tools/.
set -u
source /data/harvest/env.sh
export OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
C="$(cd "$(dirname "$0")/../.." && pwd)"
D=/data/harvest/data/marr_real
L=/data/harvest/logs/marr_real
mkdir -p $D $L
cmd="$1"; shift
tag=$cmd
[ "$cmd" = point ] && tag=point_$1
echo "START $cmd $(date -u +%Y-%m-%dT%H:%M:%SZ) code=$C $*" >> $L/$tag.out
case "$cmd" in
  jobs)   PYTHONPATH=$C nice -n 10 /data/harvest/venv_e3st/bin/python $C/tools/marr_real/jobs.py --out $D "$@" \
            >> $L/$tag.out 2>&1 ;;
  point)  s=$1; n=$2
          J=$D/point_jobs.shard${s}of${n}.jsonl
          [ -f $J ] || awk -v s=$s -v n=$n '(NR - 1) % n == s' $D/point_jobs.jsonl > $J
          IR_INST=marr_real_point_$s PYTHONPATH=/data/harvest/pylib_molmo2:$C nice -n 10 \
            /data/harvest/venv_train/bin/python $C/tools/marr/point.py --jobs $J --out $D/points.shard${s}.jsonl \
            --batch 16 >> $L/$tag.out 2>&1 ;;
  labels) PYTHONPATH=$C nice -n 10 /data/harvest/venv_e3st/bin/python $C/tools/marr_real/labels.py --data $D --logs $L \
            "$@" >> $L/$tag.out 2>&1 ;;
  *) echo "unknown $cmd" >> $L/$tag.out; exit 2 ;;
esac
echo "EXIT $? $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> $L/$tag.out

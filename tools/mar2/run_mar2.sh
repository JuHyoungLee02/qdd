#!/bin/bash
# MolmoAct-on-R2 readiness gates (CPU). Usage on the pod:  bash run_mar2.sh <cam|fk|trace|cond|res> [args]
# Code copy: /data/harvest/code_mar2 (git archive, LF); this folder's mar2_*.py next to this script.
set -u
source /data/harvest/env.sh
export OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
HERE="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH=/data/harvest/code_mar2:$HERE
cmd="$1"; shift
case "$cmd" in
  res) PY=/data/harvest/venv_train/bin/python ;;   # transformers
  *)   PY=/data/harvest/venv_e3st/bin/python ;;    # numpy + PIL + cv2 (MolmoAct draws with cv2.LINE_AA)
esac
mkdir -p /data/harvest/logs/mar2
nice -n 10 "$PY" "$HERE/mar2_gates.py" "$cmd" "$@" > "/data/harvest/logs/mar2/$cmd.out" 2>&1
echo "EXIT $?" >> "/data/harvest/logs/mar2/$cmd.out"

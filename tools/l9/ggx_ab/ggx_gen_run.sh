#!/bin/bash
# usage: ggx_gen_run.sh <ids file|all> <out> <nshard> ; spreads shards over queues q1 q4 q6, both grippers
IDS=$1; OUT=$2; N=$3; B=/data/harvest/l9v2/ggx_int; C=/data/harvest/l9v2/ggx_int_code_a4b01f4
PY=/data/harvest/l9v2/graspgenx/code/.venv/bin/python; Q=(1 4 6)
cd $C; mkdir -p $B/logs
for g in ffw_sg2 franka; do for i in $(seq 0 $((N-1))); do
  q=${Q[$((i % 3))]}; X=""; [ "$IDS" != all ] && X="--ids $IDS"
  GGX_QUEUE=$B/q$q nohup nice -n 5 $PY tools/l9/ggx_gen.py --meshes /data/harvest/l9v2/meshes --grip $g --out $OUT --shard $i/$N $X > $B/logs/gen_$(basename $OUT)_${g}_$i.log 2>&1 &
done; done
echo launched

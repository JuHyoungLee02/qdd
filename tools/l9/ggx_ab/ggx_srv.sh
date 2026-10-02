#!/bin/bash
# usage: ggx_srv.sh <gpu> ; bulk GGX server on its own queue (unmodified serve.py)
G=$1; B=/data/harvest/l9v2/ggx_int
mkdir -p $B/gj $B/q$G $B/logs
cp -n /data/harvest/l9v2/graspgenx/gripper_json/*.json $B/gj/ 2>/dev/null
cp -n /data/harvest/l9v2/ggx_int_code_a4b01f4/harvest/l9/assets9/grippers/franka_hand.json $B/gj/
cd /data/harvest/l9v2/graspgenx/code
export HF_HOME=/data/harvest/cache/hf TORCH_HOME=/data/harvest/cache/torch XDG_CACHE_HOME=/data/harvest/cache TMPDIR=/data/harvest/cache/tmp
CUDA_VISIBLE_DEVICES=$G GGX_QUEUE=$B/q$G GGX_GRIPPER_JSON_DIR=$B/gj nohup .venv/bin/python scripts_l9/serve.py > $B/logs/srv$G.log 2>&1 &
echo started $G $!

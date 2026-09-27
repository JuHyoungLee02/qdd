#!/bin/bash
# ManiSkill D/H conversion, one process per shard (e9f3, 48 CPU), then merge per-shard outputs into dh_maniskill and
# rebuild the pack with BEHAVIOR. usage: dh_msk_par.sh <parallel>
P=${1:-40}
X=/data/harvest/out/xemb_proto
S=/data/harvest/data/oxe_depth/maniskill
PY=/data/harvest/venv_e3st/bin/python
cd $X/code
rm -rf $X/dh_msk_parts; mkdir -p $X/dh_msk_parts
ls $S | xargs -P $P -I{} bash -c "$PY -m xemb.src_maniskill $S/{} $X/dh_msk_parts/{} 2000 > /dev/null 2>&1"
$PY -m xemb.dh_merge $X/dh_msk_parts $X/dh_maniskill
$PY -m xemb.dh_pack /data/harvest/out/xemb/dh_pack $X/dh_b1k $X/dh_maniskill > /data/harvest/logs/dh_pack.log 2>&1
touch /data/harvest/out/xemb/dh_pack/DONE2

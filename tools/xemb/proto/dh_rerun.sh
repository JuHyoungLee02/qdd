#!/bin/bash
# Re-run the D/H converters with per-row converter errors stored (e9f3 CPU), rebuild the 5 cm pack and a 2 cm pack.
X=/data/harvest/out/xemb_proto
S=/data/harvest/data/oxe_depth/maniskill
PY=/data/juhyoung_pi05/uvpython/cpython-3.12.13-linux-x86_64-gnu/bin/python3.12
export PYTHONPATH=$X/code:/data/harvest/venv_e3st/lib/python3.12/site-packages
cd $X/code
$PY -m xemb.src_behavior_dh /data/harvest/data/b1k_dh $X/dh_b1k 60 > /data/harvest/logs/dh_b1k.log 2>&1 &
rm -rf $X/dh_msk_parts; mkdir -p $X/dh_msk_parts
ls $S | xargs -P 16 -I{} bash -c "$PY -m xemb.src_maniskill $S/{} $X/dh_msk_parts/{} 2000 > /dev/null 2>&1"
$PY -m xemb.dh_merge $X/dh_msk_parts $X/dh_maniskill
wait
$PY -m xemb.dh_pack /data/harvest/out/xemb/dh_pack $X/dh_b1k $X/dh_maniskill > /data/harvest/logs/dh_pack.log 2>&1
$PY -m xemb.dh_pack --tol=0.02 /data/harvest/out/xemb/dh_pack $X/dh_b1k $X/dh_maniskill >> /data/harvest/logs/dh_pack.log 2>&1
touch /data/harvest/out/xemb/dh_pack/DONE3

#!/bin/bash
# One command for every ready D / H converter (user-log 158). usage: dh_all.sh <out root> [N rows per source, default all]
#   calibrated C' -> D (+ H where depth): RB2 (T4 camera + stereo depth), RB3 (T4 camera), MolmoBot Franka
#   depth-native D + H: BEHAVIOR 2025 (src_behavior_dh), OXE ManiSkill (src_maniskill; shards already on /data)
O=$1; N=${2:-}
X=/data/harvest/out/xemb_proto
PY=/data/juhyoung_pi05/uvpython/cpython-3.12.13-linux-x86_64-gnu/bin/python3.12
export PYTHONPATH=$X/code:/data/harvest/venv_e3st/lib/python3.12/site-packages
cd $X/code
NA=""; [ -n "$N" ] && NA="--n $N"
$PY -m xemb.cp_to_dh $X/rb2t4/records_C.jsonl $O/rb2 rb2 --cam $X/t4/t4c_fit_t4_fit_nominal.npz --depth $X/ffs_rb2_prod/depth $NA > $O/rb2.log 2>&1 &
$PY -m xemb.cp_to_dh $X/rb3t4v/records_C.jsonl $O/rb3 rb3 --cam $X/t4r2/rb3_box60g_r.npz $NA > $O/rb3.log 2>&1 &
$PY -m xemb.cp_to_dh $X/mbfranka/records_C.jsonl $O/mbfranka mbf $NA > $O/mbfranka.log 2>&1 &
# RoboTwin 2.0 left out: eye check showed object names swapped on some tasks (e.g. "kitchenpot" on a can) -> fix names first
if [ -z "$N" ]; then
  $PY -m xemb.src_behavior_dh /data/harvest/data/b1k_dh $O/behavior 60 > $O/behavior.log 2>&1 &
  mkdir -p $O/msk_parts
  ls /data/harvest/data/oxe_depth/maniskill | xargs -P 16 -I{} bash -c \
    "$PY -m xemb.src_maniskill /data/harvest/data/oxe_depth/maniskill/{} $O/msk_parts/{} 2000 > /dev/null 2>&1"
  $PY -m xemb.dh_merge $O/msk_parts $O/maniskill
fi
wait
for s in $O/*/report.json; do echo "== $s"; cat $s; done > $O/summary.txt

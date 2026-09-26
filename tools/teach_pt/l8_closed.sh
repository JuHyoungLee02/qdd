#!/bin/bash
# E-PT: the L8-xyz baseline (E-TEACH-L8 merged adapter, vLLM l8_xyz on 127.0.0.1:8395) closed loop on OOD-H
# (prereg_pt.md §5.3): v2 interface, s0 / s1 x table 0.82 / 0.88. usage: l8_closed.sh <code dir> <isaac gpu>
C=$1; G=$2
for z in 0.78 0.92; do
  bash $C/tools/teach_pt/isaac.sh $C $G cl_l8xyz_tz$z harvest.teach_pt.run_closed --iface v2 --model qwen8b \
    --qwen-url http://127.0.0.1:8395 --qwen-name l8_xyz --table-z $z --seeds 0,1 --out /data/harvest/out/teach_pt/closed_f2 --arm l8_xyz
done
echo "L8_CLOSED_DONE $(date -u +%FT%TZ)" >> /data/harvest/logs/teach_pt/lanes.log

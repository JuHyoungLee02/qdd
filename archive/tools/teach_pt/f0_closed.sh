#!/bin/bash
# E-PT F0 closed loop (prereg_pt.md §5.1): zero-shot Qwen3-VL-8B (vLLM pt_zs on 127.0.0.1:8394) through the pt
# interface, DEV standard / dr x s0 / s1, early end 20 calls / 60 s, sparse frames (videos). The 0-1000 wording is the
# registered arm; the pixel wording runs after it (descriptive). usage: f0_closed.sh <code dir> <gpu>
C=$1; G=$2
I="bash $C/tools/teach_pt/isaac.sh $C"
O=/data/harvest/out/teach_pt/closed_f0
for v in standard dr; do
  $I $G f0c_${v} harvest.teach_pt.run_closed --iface pt --model qwen8b --qwen-url http://127.0.0.1:8394 --qwen-name pt_zs --variant $v --seeds 0,1 --out $O --arm pt_zs
done
for v in standard dr; do
  $I $G f0c_px_${v} harvest.teach_pt.run_closed --iface pt --model qwen8b --qwen-url http://127.0.0.1:8394 --qwen-name pt_zs --variant $v --seeds 0,1 --out $O --arm pt_zs_px --coords px
done
echo "F0C_DONE $(date -u +%FT%TZ)" >> /data/harvest/logs/teach_pt/lanes.log

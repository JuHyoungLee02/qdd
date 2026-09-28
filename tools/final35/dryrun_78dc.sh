#!/bin/bash
# 35B main-training dry run (controller request, 09-29): L8-X b2 d-min + open point packs at 75 % of the file (additive),
# grid-free images only (check), DDP on 4 cards, global batch 24, --save-every; 100 steps, stop, --resume to 200 steps;
# samples GPU util / CPU load every 30 s (data-loader bottleneck). usage: dryrun_78dc.sh <code dir> [gpus 0,1,2,3]
C=$1; G=${2:-0,1,2,3}
P=/data/harvest/venv_train/bin/python; K=/data/harvest/out/xemb/dist8_packs
O=/data/harvest/out/final35/dryrun; L=/data/harvest/logs/final35; mkdir -p $O $L
cd $C; export PYTHONPATH=$C
$P tools/teach_pt/mix_pack.py /data/harvest/out/final35/data/train_d-min.jsonl $O/train_mix75.jsonl \
  $K/obj_pixel_train.jsonl:0.375 $K/t1t4_pixel.jsonl:0.375 > $O/mix.log 2>&1
$P tools/final35/grid_check.py $O/train_mix75.jsonl > $O/grid_check.json 2>&1 || { echo "DRYRUN_GRID_FAIL" >> $L/chain.log; exit 1; }
( while true; do echo "$(date -u +%T) gpu=$(nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader,nounits | tr '\n' ' ') load=$(cut -d' ' -f1 /proc/loadavg)"; sleep 30; done ) > $O/util.log 2>&1 &
MON=$!
ARGS=(--epochs 2 --micro 3 --accum 2 --max-steps 200 --save-every 100 --workers ${WORKERS:-8})
bash $C/tools/teach_35b/train.sh $C $G $O/train_mix75.jsonl $O/run "${ARGS[@]}" --stop-after 100
bash $C/tools/teach_35b/train.sh $C $G $O/train_mix75.jsonl $O/run "${ARGS[@]}" --resume
kill $MON
echo "DRYRUN_DONE $(date -u +%FT%TZ)" >> $L/chain.log

#!/bin/bash
# 35B main-training dry run 2 (controller 09-29): verified full open point pool (tools/final35/open_pool.py, repeat cap
# 1.5) + grid-free check; memory headroom: global batch 24 kept with micro 2 x accum 3 x 4 cards and
# PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True; 50 steps, nvidia-smi used-memory peak sampled every 10 s (goal <= 125 GB).
# usage: dryrun2_78dc.sh <code dir> [gpus 0,1,2,3]
C=$1; G=${2:-0,1,2,3}
P=/data/harvest/venv_train/bin/python
O=/data/harvest/out/final35/dryrun2; L=/data/harvest/logs/final35; mkdir -p $O $L
cd $C; export PYTHONPATH=$C
$P tools/final35/open_pool.py /data/harvest/out/final35/data/train_d-min.jsonl $O/train_open.jsonl 0.75 1.5 > $O/pool.log 2>&1 || { echo "DRYRUN2_POOL_FAIL" >> $L/chain.log; exit 1; }
$P tools/final35/grid_check.py $O/train_open.jsonl > $O/grid_check.json 2>&1 || { echo "DRYRUN2_GRID_FAIL" >> $L/chain.log; exit 1; }
( while true; do echo "$(date -u +%T) $(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits | tr '\n' ' ') load=$(cut -d' ' -f1 /proc/loadavg)"; sleep 10; done ) > $O/util.log 2>&1 &
MON=$!
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
bash $C/tools/teach_35b/train.sh $C $G $O/train_open.jsonl $O/run --epochs 2 --micro 2 --accum 3 --max-steps 50 \
  --save-every 50 --workers ${WORKERS:-8}
kill $MON
awk '{for (i = 2; i <= 9; i += 2) { gsub(",", "", $i); if ($i + 0 > m) m = $i + 0 }} END {print "PEAK_USED_MIB " m}' $O/util.log >> $O/util.log
echo "DRYRUN2_DONE $(tail -1 $O/util.log) $(date -u +%FT%TZ)" >> $L/chain.log

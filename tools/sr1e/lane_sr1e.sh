#!/bin/bash
# E-SR1e main (docs/stage3/prereg_sr1e.md §2): a training run peaks near 80 GB, so one training per GPU.
#   bash lane_sr1e.sh main      lane GPU 2 = A s1 -> D s1, lane GPU 3 = A s2 -> D s2 (in parallel), then the evaluation
#                               phase on GPU 2 (run_sr1e.sh eval 2) after both lanes ended
#   bash lane_sr1e.sh <gpu> <arm> <seed> [<arm> <seed> ...]   one lane
set -u
D=$(cd "$(dirname "$0")" && pwd)
L=/data/harvest/logs/sr1e$([ "${DRY:-0}" = "1" ] && echo /dry)
mkdir -p $L
if [ "$1" = "main" ]; then
  echo "main start $(date -u +%FT%TZ)" >> $L/lanes.out
  bash $D/lane_sr1e.sh 2 A 1 D 1 &
  bash $D/lane_sr1e.sh 3 A 2 D 2 &
  wait
  bash $D/run_sr1e.sh eval 2
  echo "main done $(date -u +%FT%TZ)" >> $L/lanes.out
  exit 0
fi
GPU=$1; shift
while [ $# -ge 2 ]; do
  bash $D/run_sr1e.sh train $1 $2 $GPU
  shift 2
done
echo "lane gpu $GPU done $(date -u +%FT%TZ)" >> $L/lanes.out

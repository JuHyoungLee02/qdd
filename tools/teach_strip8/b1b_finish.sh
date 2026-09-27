#!/bin/bash
# boost1b finish: wait for the lanes (B1B_LANE_DONE <tags>), stop the served B-D (<name>), make the videos.
# usage: b1b_finish.sh <code dir> <served name> <tag> [<tag> ...]
C=$1; N=$2; shift 2
L=/data/harvest/logs/strip8; O=/data/harvest/out/strip8/boost1b
P=/data/harvest/venv_train/bin/python
for t in "$@"; do until grep -q "B1B_LANE_DONE $t " $L/lanes.log; do sleep 60; done; done
bash $C/tools/teach_strip8/stop.sh $N
cd $C; export PYTHONPATH=$C
specs=()
for A in $(ls $O | grep -v vid_src); do
  mkdir -p $O/vid_src/$A
  for s in ood_h ood_o; do [ -d $O/$A/$s ] && ln -sfn $O/$A/$s $O/vid_src/$A/$s; done
  specs+=("$A=$O/vid_src/$A")
done
$P tools/astra_solo/make_videos.py /data/harvest/videos/boost1b "${specs[@]}" > $L/boost1b_videos.log 2>&1
echo "BOOST1B_DONE $(date -u +%FT%TZ)" >> $L/lanes.log

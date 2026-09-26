#!/bin/bash
# E-PT videos (mandatory, prereg_pt.md §5.3): continuous + model-view mp4 per closed-loop episode with
# tools/astra_solo/make_videos.py (venv_train python), index.json / index.md per stage.
# usage: videos.sh <code dir> <stage> <closed root> <arm> [<arm> ...]  -> /data/harvest/videos/pt/<stage>/<arm>/
C=$1; S=$2; R=$3; shift 3
V=/data/harvest/videos/pt/$S
LNK=/data/harvest/out/teach_pt/vid_src/$S
mkdir -p $V $LNK
args=()
for a in "$@"; do
  mkdir -p $LNK/$a
  ln -sfn $R/$a $LNK/$a/x   # make_videos globs <src>/*/*/s*/result.json
  args+=("$a=$LNK/$a")
done
cd $C
/data/harvest/venv_train/bin/python tools/astra_solo/make_videos.py $V "${args[@]}" > /data/harvest/logs/teach_pt/videos_$S.log 2>&1
echo "VIDEOS_DONE $S $(date -u +%FT%TZ)" >> /data/harvest/logs/teach_pt/lanes.log

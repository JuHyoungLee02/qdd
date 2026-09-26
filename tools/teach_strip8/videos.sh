#!/bin/bash
# E-STRIP8 closed-loop videos (prereg_strip8.md §5.5): per set (dev, oodh082 / 088 / 078 / 092; env STRIP8_VIDEO_SETS) one make_videos.py call with
# every arm, episodes linked (read-only symlinks) from the closed-loop roots. -> /data/harvest/videos/strip8/<set>/
# usage: videos.sh <code dir> <arm>=<closed root of that arm> [...]   (closed root = .../<arm> holding <variant dir>/s*)
C=$1; shift
V=/data/harvest/videos/strip8
S=/data/harvest/out/strip8/vidsrc
PY=/data/harvest/venv_train/bin/python
for set in ${STRIP8_VIDEO_SETS:-dev oodh082 oodh088 oodh078 oodh092}; do
  specs=()
  for spec in "$@"; do
    A=${spec%%=*}; R=${spec#*=}
    case $set in dev) dirs="standard dr";; oodh082) dirs="standard_tz0.82";; oodh088) dirs="standard_tz0.88";; oodh078) dirs="standard_tz0.78";; oodh092) dirs="standard_tz0.92";; esac
    n=0
    for d in $dirs; do
      [ -d $R/$d ] || continue
      mkdir -p $S/${set}_$A/x
      ln -sfn $R/$d $S/${set}_$A/x/$d
      n=1
    done
    [ $n = 1 ] && specs+=("$A=$S/${set}_$A")
  done
  [ ${#specs[@]} -gt 0 ] && (cd $C && $PY tools/astra_solo/make_videos.py $V/$set "${specs[@]}")
done
echo "VIDEOS_DONE $(date -u +%FT%TZ)" >> /data/harvest/logs/strip8/lanes.log

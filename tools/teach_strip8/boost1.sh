#!/bin/bash
# boost1 closed loop (prereg_boost1.md): B-D model served at 127.0.0.1:<port>; episodes = L8-X OOD-H 0.98 (4) and
# OOD-O 0.86 / 0.94 (2 + 2); arms before (fixes off) then after (fixes on), same episodes; one Isaac process per world
# group on <render gpu>; then videos into /data/harvest/videos/boost1/<arm>/ (+ index).
# usage: boost1.sh <code dir> <render gpu> <served name> <port>
C=$1; G=$2; N=$3; PORT=$4
P=/data/harvest/venv_train/bin/python
X=/data/harvest/out/teach_l8d/collect
L=/data/harvest/logs/strip8; O=/data/harvest/out/strip8/boost1
mkdir -p $L $O
cd $C; export PYTHONPATH=$C
{ $P tools/teach_pt/dist8_pick.py $X/ood_h 4 drx_tz0.980
  $P tools/teach_pt/dist8_pick.py $X/ood_o 2 drx_tz0.860 drx_tz0.940; } > $L/boost1_pick.txt
for fix in off on; do
  A=$([ $fix = off ] && echo before || echo after)
  while read -r v eps; do
    [ -n "$eps" ] || continue
    bash $C/tools/teach_strip8/isaac.sh $C $G bst_${A}_${v//./} harvest.teach_strip8.run_boost --fix $fix \
      --qwen-url http://127.0.0.1:$PORT --qwen-name $N --arm $A --out $O --episodes $eps
  done < $L/boost1_pick.txt
done
mkdir -p $O/vid_src
for A in before after; do
  mkdir -p $O/vid_src/$A
  for s in ood_h ood_o; do ln -sfn $O/$A/$s $O/vid_src/$A/$s; done
done
$P tools/astra_solo/make_videos.py /data/harvest/videos/boost1 before=$O/vid_src/before after=$O/vid_src/after \
  > $L/boost1_videos.log 2>&1
echo "BOOST1_DONE $(date -u +%FT%TZ)" >> $L/lanes.log

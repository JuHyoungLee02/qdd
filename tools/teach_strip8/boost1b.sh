#!/bin/bash
# boost1b (prereg_boost1b.md) on one GPU <g>: serve B-D, then per world group one Isaac process running all arms.
#  disturbed set (a)(b): OOD-H 0.98 s70088-91 + OOD-H 0.74 s70072-73, perturb tray / lift / head x mem none / img / pts
#  regression (c): the boost1 8 episodes, no disturbance, mem none / pts (img = boost1 'after', reused)
# videos /data/harvest/videos/boost1b/<arm>/ + index. usage: boost1b.sh <code dir> <gpu>
C=$1; G=$2
L=/data/harvest/logs/strip8; O=/data/harvest/out/strip8/boost1b
P=/data/harvest/venv_train/bin/python
X=/data/harvest/out/teach_l8d/collect
mkdir -p $L $O
cd $C; export PYTHONPATH=$C
(bash $C/tools/teach_strip8/vllm.sh $G /data/harvest/out/dist8/merged_b_d-min b1b_bd 8406 0.30 &)
for i in $(seq 120); do curl -s -m 5 http://127.0.0.1:8406/v1/models | grep -q '"id"' && break; sleep 10; done
PERT=none:tray,img:tray,pts:tray,none:lift,img:lift,pts:lift,none:head,img:head,pts:head
{ $P tools/teach_pt/dist8_pick.py $X/ood_h 4 drx_tz0.980 | sed "s/^/$PERT,none:none,pts:none /"
  $P tools/teach_pt/dist8_pick.py $X/ood_h 2 drx_tz0.740 | sed "s/^/$PERT /"
  $P tools/teach_pt/dist8_pick.py $X/ood_o 2 drx_tz0.860 drx_tz0.940 | sed "s/^/none:none,pts:none /"; } > $L/boost1b_plan.txt
while read -r combos v eps; do
  [ -n "$eps" ] || continue
  bash $C/tools/teach_strip8/isaac.sh $C $G b1b_${v//./} harvest.teach_strip8.run_boost --combos $combos \
    --qwen-url http://127.0.0.1:8406 --qwen-name b1b_bd --out $O --episodes $eps
done < $L/boost1b_plan.txt
bash $C/tools/teach_strip8/stop.sh b1b_bd
specs=()
for A in $(ls $O | grep -v vid_src); do
  mkdir -p $O/vid_src/$A
  for s in ood_h ood_o; do [ -d $O/$A/$s ] && ln -sfn $O/$A/$s $O/vid_src/$A/$s; done
  specs+=("$A=$O/vid_src/$A")
done
$P tools/astra_solo/make_videos.py /data/harvest/videos/boost1b "${specs[@]}" > $L/boost1b_videos.log 2>&1
echo "BOOST1B_DONE $(date -u +%FT%TZ)" >> $L/lanes.log

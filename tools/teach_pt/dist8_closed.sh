#!/bin/bash
# E-DIST8 closed loop on L8-X OOD scenes (prereg_dist8.md §5): for one arm (served by vLLM at 127.0.0.1:<port>),
# 2 episodes x 2 world groups per set (OOD-H: lowest / highest table; OOD-O: two heights), one Isaac process per
# group on <render gpu>; then the videos (continuous + model view) into /data/harvest/videos/dist8/<arm>/.
# usage: dist8_closed.sh <code dir> <render gpu> <arm tag> <iface> <served name> <port> [h_depth]
C=$1; G=$2; ARM=$3; IF=$4; N=$5; PORT=$6; HD=${7:-on}
P=/data/harvest/venv_train/bin/python
X=/data/harvest/out/teach_l8d/collect
L=/data/harvest/logs/dist8; O=/data/harvest/out/dist8/closed
mkdir -p $L $O
cd $C; export PYTHONPATH=$C
{ $P tools/teach_pt/dist8_pick.py $X/ood_h 2 drx_tz0.740 drx_tz0.980
  $P tools/teach_pt/dist8_pick.py $X/ood_o 2 drx_tz0.860 drx_tz0.940; } > $L/pick_$ARM.txt
while read -r v eps; do
  [ -n "$eps" ] || continue
  bash $C/tools/teach_pt/isaac.sh $C $G cl_${ARM}_$v harvest.teach_pt.run_closed_x --iface $IF --h-depth $HD \
    --qwen-url http://127.0.0.1:$PORT --qwen-name $N --arm $ARM --out $O --confirm-ood --episodes $eps
done < $L/pick_$ARM.txt
T=$ARM; [ "$IF" = "h-min" ] && T=${ARM}_$HD
mkdir -p /data/harvest/out/dist8/vid_src/$T
for s in ood_h ood_o; do ln -sfn $O/$T/$s /data/harvest/out/dist8/vid_src/$T/$s; done
$P tools/astra_solo/make_videos.py /data/harvest/videos/dist8/$T $T=/data/harvest/out/dist8/vid_src/$T > $L/videos_$T.log 2>&1
echo "CLOSED_DONE $T $(date -u +%FT%TZ)" >> $L/dist8_closed.log

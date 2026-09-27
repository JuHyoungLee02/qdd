#!/bin/bash
# E-DIST8 change 7 closed loops (BoostEpisode) for one arm: serve it on <serve gpu>, run the given L8-X episodes
# grouped by world config on <render gpu>, stop the server, make the videos.
# usage: dist8_cl_boost.sh <code dir> <serve gpu> <render gpu> <tag> <merged dir> <iface> <port> <h_depth> <ep dir> [...]
C=$1; SG=$2; RG=$3; TAG=$4; M=$5; IF=$6; PORT=$7; HD=$8; shift 8
L=/data/harvest/logs/dist8; O=/data/harvest/out/dist8/closed_boost; N=d8cl_${TAG//-/_}
mkdir -p $L $O
setsid nohup bash $C/tools/teach_pt/vllm.sh $SG $M $N $PORT 0.45 < /dev/null > /dev/null 2>&1 &
for i in $(seq 1 90); do curl -s 127.0.0.1:$PORT/v1/models | grep -q $N && break; sleep 10; done
curl -s 127.0.0.1:$PORT/v1/models | grep -q $N || { echo "CLB_FAIL $TAG server $(date -u +%FT%TZ)" >> $L/dist8_closed.log; exit 1; }
for g in $(for e in "$@"; do dirname $e; done | sort -u); do
  eps=$(for e in "$@"; do [ "$(dirname $e)" = "$g" ] && echo $e; done)
  bash $C/tools/teach_pt/isaac.sh $C $RG clb_${TAG}_$(basename $g) harvest.teach_pt.run_closed_x --iface $IF --h-depth $HD \
    --qwen-url http://127.0.0.1:$PORT --qwen-name $N --arm $TAG --out $O --confirm-ood --boost 1 --episodes $eps
done
bash $C/tools/teach_pt/stop.sh $N >> $L/dist8_closed.log 2>&1
T=$TAG; [ "$IF" = "h-min" ] && T=${TAG}_$HD
mkdir -p /data/harvest/out/dist8/vid_src_boost/$T
for s in ood_h ood_o; do [ -d $O/$T/$s ] && ln -sfn $O/$T/$s /data/harvest/out/dist8/vid_src_boost/$T/$s; done
/data/harvest/venv_train/bin/python $C/tools/astra_solo/make_videos.py /data/harvest/videos/dist8_boost/$T $T=/data/harvest/out/dist8/vid_src_boost/$T > $L/videos_boost_$T.log 2>&1
echo "CLB_DONE $T $(date -u +%FT%TZ)" >> $L/dist8_closed.log

#!/bin/bash
# Final 35B closed loop with the boost1 executor (BoostEpisode fix_mem + fix_loop, STRIP8 d1f33f3) for one arm, on the
# same 8 L8-X episodes as E-DIST8 (/data/harvest/logs/dist8/pick_b_d-min.txt): serve the merged arm (FP8 online,
# memory share 0.45) on <serve gpu>, Isaac on <render gpu> (same pod), stop the server, make the videos
# (/data/harvest/videos/final35/<tag>/ + index). Copy of tools/teach_pt/dist8_cl_boost.sh with the 35B server.
# usage: closed.sh <code dir> <serve gpu> <render gpu> <tag> <merged dir> <iface d-min|h-min> <port> <h_depth on|off>
C=$1; SG=$2; RG=$3; TAG=$4; M=$5; IF=$6; PORT=$7; HD=$8
L=/data/harvest/logs/final35; O=/data/harvest/out/final35/closed; N=f35cl_${TAG//-/_}
mkdir -p $L $O
EPS=$(cut -d' ' -f2- /data/harvest/logs/dist8/pick_b_d-min.txt | tr '\n' ' ')
until [ -f $M/config.json ]; do sleep 60; done
setsid nohup bash $C/tools/teach_35b/vllm.sh $SG $M $N $PORT 0.45 --quantization fp8 < /dev/null > /dev/null 2>&1 &
for i in $(seq 1 90); do curl -s 127.0.0.1:$PORT/v1/models | grep -q $N && break; sleep 10; done
curl -s 127.0.0.1:$PORT/v1/models | grep -q $N || { echo "CL_FAIL $TAG server $(date -u +%FT%TZ)" >> $L/chain.log; bash $C/tools/teach_35b/stop.sh $N; exit 1; }
echo "CL_START $TAG $(date -u +%FT%TZ)" >> $L/chain.log
for g in $(for e in $EPS; do dirname $e; done | sort -u); do
  eps=$(for e in $EPS; do [ "$(dirname $e)" = "$g" ] && echo $e; done)
  bash $C/tools/teach_pt/isaac.sh $C $RG f35cl_${TAG}_$(basename $g) harvest.teach_pt.run_closed_x --iface $IF --h-depth $HD \
    --qwen-url http://127.0.0.1:$PORT --qwen-name $N --arm $TAG --out $O --confirm-ood --boost 1 --episodes $eps
done
bash $C/tools/teach_35b/stop.sh $N >> $L/closed.log 2>&1
T=$TAG; [ "$IF" = "h-min" ] && T=${TAG}_$HD
mkdir -p /data/harvest/out/final35/vid_src/$T
for s in ood_h ood_o; do [ -d $O/$T/$s ] && ln -sfn $O/$T/$s /data/harvest/out/final35/vid_src/$T/$s; done
/data/harvest/venv_train/bin/python $C/tools/astra_solo/make_videos.py /data/harvest/videos/final35/$T $T=/data/harvest/out/final35/vid_src/$T > $L/videos_$T.log 2>&1
echo "CL_DONE $T $(date -u +%FT%TZ)" >> $L/chain.log

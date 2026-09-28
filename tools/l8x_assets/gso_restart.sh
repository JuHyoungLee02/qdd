#!/bin/bash
# L8X-assets: (re)start the GSO download as N parallel shards (stops earlier ones; pattern in a file = no self-match).
# usage: gso_restart.sh [N]
N=${1:-6}
C=/data/harvest/code_l8x_assets_dev
G=/data/harvest/assets_x/gso
pkill -f "gso_[f]etch.py get" || true
sleep 1
rm -f $G/models/*.part $G/models/*.zip
cd $C
for k in $(seq 0 $((N - 1))); do
  setsid nohup python3 tools/l8x_assets/gso_fetch.py get $G/models.json $G/models --shard $k/$N > $G/fetch$k.log 2>&1 < /dev/null &
done
echo "started $N shards"

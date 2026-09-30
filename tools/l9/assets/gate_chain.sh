#!/bin/bash
# L9 container gate chain (x2 pod, GPU 1 only): every KDIR/k*.json through tools.l9.assets.gate_containers9 with the
# L8S candidate pool + the L9 settled objects (L9OBJ...). Lane L of N; a chunk with containers_check.json and no
# current.txt is done (gate_containers9 resumes a chunk itself). Stop: touch $OUT/STOP.
# usage: gate_chain.sh CODE_DIR KDIR OUT LANE NLANES L9OBJ...
C=$1; K=$2; OUT=$3; L=$4; N=$5; shift 5
case "$(hostname)" in *x2) ;; *) echo "refused: run on juhyoung-native-7a2a-x2"; exit 2;; esac
A=$C/harvest/sim/assets_x
mkdir -p $OUT
[ -f $OUT/pass_none.json ] || echo '{"pass_ids": []}' > $OUT/pass_none.json
i=0
for t in $(ls $K/k*.json | sort); do
  if [ $((i % N)) -eq $L ] && [ ! -f $OUT/STOP ]; then
    b=$(basename $t .json)
    for try in 1 2 3; do
      if [ -s $OUT/$b/containers_check.json ] && [ ! -f $OUT/$b/current.txt ]; then break; fi
      bash $C/tools/l8x_assets/isaac.sh $C 1 l9g_$(basename $OUT)_$b tools.l9.assets.gate_containers9 \
        --containers $t --items $A/task_items.json --objects $A/objects_real.json --products $A/products.json \
        --pass-ids $OUT/pass_none.json --out $OUT/$b --l9-objects "$@"
    done
  fi
  i=$((i + 1))
done
echo "LANE_DONE $L $(date -u +%FT%TZ)" >> $OUT/lanes_done.txt
